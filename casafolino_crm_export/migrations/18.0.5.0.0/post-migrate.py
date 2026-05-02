"""
Migration v18.0.5.0.0 — CRM Export pipeline restructure

1. Map old stages → new 9-stage pipeline (handles renamed + same-name duplicates)
2. Migrate cf_market / cf_channel Selection → crm.tag M2M
3. Drop cf_market / cf_channel columns
4. Create Standby cron (post_init_hook only fires on install, not update)

NOTE: In Odoo 18 translated fields (crm_stage.name, crm_tag.name) are JSONB.
All queries use name->>'en_US' or name->>'it_IT' for comparison.
"""
import json
import logging

_logger = logging.getLogger(__name__)

# Old stage it_IT name → new stage en_US name (XML creates with en_US key)
STAGE_RENAME_MAP = {
    'Contatto': 'Primo Contatto',
    'Qualificazione': 'Interesse',
}

# Stages with same name in old and new — need to consolidate duplicates.
# For these, XML data created a NEW record while the OLD still has leads.
# Strategy: move leads from old → new, delete old.
# Key = name that appears in both old it_IT and new en_US
STAGE_SAME_NAME = ['Preventivo', 'Negoziazione', 'Vinta', 'Persa']

# New stage sequences (the target state after migration)
NEW_STAGE_SEQUENCES = {
    'Primo Contatto': 10,
    'Interesse': 20,
    'Trattativa': 30,
    'Preventivo': 40,
    'Campionatura': 50,
    'Negoziazione': 60,
    'Vinta': 70,
    'Persa': 80,
    'Standby': 90,
}

MARKET_TAG_MAP = {
    'america': 'America',
    'europa': 'Europa',
    'italia': 'Italia',
    'medio_oriente': 'Medio Oriente',
    'australia': 'Australia',
    'altri': 'Altri',
}

CHANNEL_TAG_MAP = {
    'gdo': 'GDO',
    'importatore': 'Importatore',
    'distributore': 'Distributore',
    'horeca': 'Ho.Re.Ca.',
    'ecommerce': 'E-commerce',
    'private_label': 'Private Label',
    'foodservice': 'Foodservice',
}


def migrate(cr, version):
    if not version:
        return

    _logger.info('CasaFolino: starting v18.0.5.0.0 migration')

    _migrate_renamed_stages(cr)
    _consolidate_same_name_stages(cr)
    _migrate_market_tags(cr)
    _migrate_channel_tags(cr)
    _drop_old_columns(cr)
    _ensure_standby_cron(cr)

    _logger.info('CasaFolino: v18.0.5.0.0 migration completed')


def _migrate_renamed_stages(cr):
    """Handle stages where old it_IT name differs from new en_US name."""
    for old_it_name, new_en_name in STAGE_RENAME_MAP.items():
        # Find new stage (created by XML data with en_US key)
        new_id = _find_new_stage(cr, new_en_name)
        if not new_id:
            _logger.warning('Migration: new stage "%s" not found, skip', new_en_name)
            continue

        # Find old stage by it_IT name, excluding the new one
        cr.execute("""
            SELECT id FROM crm_stage
            WHERE name->>'it_IT' = %s AND id != %s
        """, (old_it_name, new_id))
        old_row = cr.fetchone()
        if not old_row:
            _logger.info('Migration: old stage "%s" not found or already migrated', old_it_name)
            continue
        old_id = old_row[0]

        _move_leads_and_delete(cr, old_id, old_it_name, new_id, new_en_name)


def _consolidate_same_name_stages(cr):
    """Handle stages where old and new have the same name but are separate records.

    XML data (noupdate=0) creates new records. Old records still have leads.
    For each name: find the NEW stage (matching target sequence), move leads
    from any OTHER stage with the same name to it, then delete the old one.
    """
    for stage_name in STAGE_SAME_NAME:
        target_seq = NEW_STAGE_SEQUENCES.get(stage_name)
        if not target_seq:
            continue

        # Find all stages with this name
        cr.execute("""
            SELECT id, sequence FROM crm_stage
            WHERE name->>'en_US' = %s OR name->>'it_IT' = %s
            ORDER BY sequence
        """, (stage_name, stage_name))
        rows = cr.fetchall()

        if len(rows) <= 1:
            _logger.info('Migration: stage "%s" — no duplicates found', stage_name)
            continue

        # Target = the one with the target sequence (created by XML)
        target_id = None
        old_ids = []
        for row_id, row_seq in rows:
            if row_seq == target_seq:
                target_id = row_id
            else:
                old_ids.append(row_id)

        if not target_id:
            # No stage with target sequence — pick highest id as target (newest)
            target_id = rows[-1][0]
            old_ids = [r[0] for r in rows if r[0] != target_id]

        for old_id in old_ids:
            _move_leads_and_delete(cr, old_id, stage_name, target_id, stage_name)


def _move_leads_and_delete(cr, old_id, old_name, new_id, new_name):
    """Move all leads from old_id to new_id, then delete old stage."""
    cr.execute("UPDATE crm_lead SET stage_id = %s WHERE stage_id = %s", (new_id, old_id))
    moved = cr.rowcount
    _logger.info('Migration: moved %d leads from stage "%s" (id=%d) to "%s" (id=%d)',
                  moved, old_name, old_id, new_name, new_id)

    # Verify no leads remain, then delete
    cr.execute("SELECT COUNT(*) FROM crm_lead WHERE stage_id = %s", (old_id,))
    remaining = cr.fetchone()[0]
    if remaining == 0:
        cr.execute("DELETE FROM crm_stage WHERE id = %s", (old_id,))
        _logger.info('Migration: deleted old stage "%s" (id=%d)', old_name, old_id)
    else:
        _logger.warning('Migration: %d leads still on old stage "%s" (id=%d), NOT deleting',
                        remaining, old_name, old_id)


def _find_new_stage(cr, en_name):
    """Find stage by en_US name."""
    cr.execute("SELECT id FROM crm_stage WHERE name->>'en_US' = %s LIMIT 1", (en_name,))
    row = cr.fetchone()
    return row[0] if row else None


def _find_or_create_tag(cr, name, color):
    """Get tag id by JSONB name, create if not exists. Idempotent."""
    cr.execute("""
        SELECT id FROM crm_tag
        WHERE name->>'en_US' = %s OR name->>'it_IT' = %s
        LIMIT 1
    """, (name, name))
    row = cr.fetchone()
    if row:
        return row[0]
    name_json = json.dumps({"en_US": name})
    cr.execute("""
        INSERT INTO crm_tag (name, color, create_uid, write_uid, create_date, write_date)
        VALUES (%s::jsonb, %s, 1, 1, NOW(), NOW()) RETURNING id
    """, (name_json, color))
    tag_id = cr.fetchone()[0]
    _logger.info('Migration: created tag "%s" (id=%d)', name, tag_id)
    return tag_id


def _add_tag_to_lead(cr, lead_id, tag_id):
    """Add tag to lead M2M. Idempotent."""
    cr.execute(
        "INSERT INTO crm_tag_rel (lead_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (lead_id, tag_id)
    )


def _migrate_market_tags(cr):
    """Convert cf_market Selection → crm.tag."""
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'crm_lead' AND column_name = 'cf_market'
    """)
    if not cr.fetchone():
        _logger.info('Migration: cf_market column not found, skip')
        return

    for key, tag_name in MARKET_TAG_MAP.items():
        tag_id = _find_or_create_tag(cr, tag_name, 1)
        cr.execute("SELECT id FROM crm_lead WHERE cf_market = %s", (key,))
        lead_ids = [row[0] for row in cr.fetchall()]
        for lead_id in lead_ids:
            _add_tag_to_lead(cr, lead_id, tag_id)
        if lead_ids:
            _logger.info('Migration: tagged %d leads with "%s"', len(lead_ids), tag_name)


def _migrate_channel_tags(cr):
    """Convert cf_channel Selection → crm.tag."""
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'crm_lead' AND column_name = 'cf_channel'
    """)
    if not cr.fetchone():
        _logger.info('Migration: cf_channel column not found, skip')
        return

    for key, tag_name in CHANNEL_TAG_MAP.items():
        tag_id = _find_or_create_tag(cr, tag_name, 2)
        cr.execute("SELECT id FROM crm_lead WHERE cf_channel = %s", (key,))
        lead_ids = [row[0] for row in cr.fetchall()]
        for lead_id in lead_ids:
            _add_tag_to_lead(cr, lead_id, tag_id)
        if lead_ids:
            _logger.info('Migration: tagged %d leads with "%s"', len(lead_ids), tag_name)


def _drop_old_columns(cr):
    """Drop cf_market and cf_channel from crm_lead and cf_export_sample."""
    for table, col in [
        ('crm_lead', 'cf_market'),
        ('crm_lead', 'cf_channel'),
        ('cf_export_sample', 'cf_market'),
    ]:
        cr.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        """, (table, col))
        if cr.fetchone():
            cr.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
            _logger.info('Migration: dropped column %s.%s', table, col)


def _ensure_standby_cron(cr):
    """Create Standby cron if not exists. post_init_hook only fires on install."""
    cr.execute("""
        SELECT id FROM ir_cron WHERE cron_name = 'CasaFolino: Auto-Standby Lead inattivi'
    """)
    if cr.fetchone():
        _logger.info('Migration: Standby cron already exists')
        return

    # Get model_id for crm.lead
    cr.execute("SELECT id FROM ir_model WHERE model = 'crm.lead' LIMIT 1")
    model_row = cr.fetchone()
    if not model_row:
        _logger.warning('Migration: crm.lead model not found, cannot create cron')
        return
    model_id = model_row[0]

    # Step 1: create ir.actions.server (name is JSONB in Odoo 18)
    name_json = json.dumps({"en_US": "CasaFolino: Auto-Standby Lead inattivi"})
    cr.execute("""
        INSERT INTO ir_act_server (
            name, model_id, state, code, type,
            binding_type, usage,
            create_uid, write_uid, create_date, write_date
        ) VALUES (
            %s::jsonb,
            %s, 'code', 'model._cron_move_to_standby()', 'ir.actions.server',
            'action', 'ir_cron',
            1, 1, NOW(), NOW()
        ) RETURNING id
    """, (name_json, model_id))
    server_id = cr.fetchone()[0]

    # Step 2: create ir.cron
    cr.execute("""
        INSERT INTO ir_cron (
            cron_name, ir_actions_server_id, active, interval_number, interval_type,
            numbercall, priority, create_uid, write_uid, create_date, write_date
        ) VALUES (
            'CasaFolino: Auto-Standby Lead inattivi',
            %s, true, 1, 'days', -1, 5, 1, 1, NOW(), NOW()
        )
    """, (server_id,))
    _logger.info('Migration: created Standby cron (server_id=%d)', server_id)
