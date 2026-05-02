"""
Migration v18.0.5.0.0 — CRM Export pipeline restructure

1. Map old stages → new 9-stage pipeline
2. Migrate cf_market / cf_channel Selection → crm.tag M2M
3. Drop cf_market / cf_channel columns from crm_lead and cf_export_sample

NOTE: In Odoo 18 translated fields (crm_stage.name, crm_tag.name) are JSONB.
All queries use name->>'en_US' or name->>'it_IT' for comparison.
"""
import logging

_logger = logging.getLogger(__name__)

# Old stage it_IT name → new stage en_US name (as created by XML data)
STAGE_MAP = {
    'Contatto': 'Primo Contatto',
    'Qualificazione': 'Interesse',
    # 'Preventivo' → 'Preventivo' — same name, skip
    # 'Negoziazione' → 'Negoziazione' — same name, skip
    # 'Vinta' → 'Vinta' — same name, skip
    # 'Persa' → 'Persa' — same name, skip
}

# cf_market selection key → tag name
MARKET_TAG_MAP = {
    'america': 'America',
    'europa': 'Europa',
    'italia': 'Italia',
    'medio_oriente': 'Medio Oriente',
    'australia': 'Australia',
    'altri': 'Altri',
}

# cf_channel selection key → tag name
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

    # ──────────────────────────────────────────────
    # 1. Stage migration
    # ─────────────────────────���────────────────────
    _migrate_stages(cr)

    # ───���──────────────────────────────────────────
    # 2. Tag migration (cf_market → crm.tag)
    # ───────────────��──────────────────��───────────
    _migrate_market_tags(cr)
    _migrate_channel_tags(cr)

    # ────────────────────────────────────────────���─
    # 3. Drop old columns
    # ────────��────────────────────────────────────��
    _drop_old_columns(cr)

    _logger.info('CasaFolino: v18.0.5.0.0 migration completed')


def _find_stage_by_name(cr, name):
    """Find stage by name checking both en_US and it_IT JSONB keys."""
    cr.execute("""
        SELECT id FROM crm_stage
        WHERE name->>'en_US' = %s OR name->>'it_IT' = %s
        LIMIT 1
    """, (name, name))
    row = cr.fetchone()
    return row[0] if row else None


def _migrate_stages(cr):
    """Map leads from old stages to new stages, delete orphan old stages."""
    for old_name, new_name in STAGE_MAP.items():
        new_id = _find_stage_by_name(cr, new_name)
        if not new_id:
            _logger.warning('CasaFolino migration: new stage "%s" not found, skip', new_name)
            continue

        # Find old stage by it_IT name, excluding the new stage id
        cr.execute("""
            SELECT id FROM crm_stage
            WHERE (name->>'it_IT' = %s OR name->>'en_US' = %s) AND id != %s
        """, (old_name, old_name, new_id))
        old_row = cr.fetchone()
        if not old_row:
            _logger.info('CasaFolino migration: old stage "%s" not found or already migrated', old_name)
            continue
        old_id = old_row[0]

        # Move leads
        cr.execute("UPDATE crm_lead SET stage_id = %s WHERE stage_id = %s", (new_id, old_id))
        moved = cr.rowcount
        _logger.info('CasaFolino migration: moved %d leads from stage "%s" (id=%d) to "%s" (id=%d)',
                      moved, old_name, old_id, new_name, new_id)

        # Delete old stage if no leads remain
        cr.execute("SELECT COUNT(*) FROM crm_lead WHERE stage_id = %s", (old_id,))
        remaining = cr.fetchone()[0]
        if remaining == 0:
            cr.execute("DELETE FROM crm_stage WHERE id = %s", (old_id,))
            _logger.info('CasaFolino migration: deleted old stage "%s" (id=%d)', old_name, old_id)


def _find_or_create_tag(cr, name, color):
    """Get tag id by name (JSONB), create if not exists. Idempotent."""
    cr.execute("""
        SELECT id FROM crm_tag
        WHERE name->>'en_US' = %s OR name->>'it_IT' = %s
        LIMIT 1
    """, (name, name))
    row = cr.fetchone()
    if row:
        return row[0]
    # Create with JSONB name
    import json
    name_json = json.dumps({"en_US": name})
    cr.execute("""
        INSERT INTO crm_tag (name, color, create_uid, write_uid, create_date, write_date)
        VALUES (%s::jsonb, %s, 1, 1, NOW(), NOW()) RETURNING id
    """, (name_json, color))
    tag_id = cr.fetchone()[0]
    _logger.info('CasaFolino migration: created tag "%s" (id=%d)', name, tag_id)
    return tag_id


def _add_tag_to_lead(cr, lead_id, tag_id):
    """Add tag to lead's tag_ids M2M (crm_tag_rel). Idempotent."""
    cr.execute(
        "INSERT INTO crm_tag_rel (lead_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (lead_id, tag_id)
    )


def _migrate_market_tags(cr):
    """Convert cf_market Selection values to crm.tag entries."""
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'crm_lead' AND column_name = 'cf_market'
    """)
    if not cr.fetchone():
        _logger.info('CasaFolino migration: cf_market column not found, skip market tags')
        return

    for key, tag_name in MARKET_TAG_MAP.items():
        tag_id = _find_or_create_tag(cr, tag_name, 1)  # color 1 = blue
        cr.execute("SELECT id FROM crm_lead WHERE cf_market = %s", (key,))
        lead_ids = [row[0] for row in cr.fetchall()]
        for lead_id in lead_ids:
            _add_tag_to_lead(cr, lead_id, tag_id)
        if lead_ids:
            _logger.info('CasaFolino migration: tagged %d leads with "%s"', len(lead_ids), tag_name)


def _migrate_channel_tags(cr):
    """Convert cf_channel Selection values to crm.tag entries."""
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'crm_lead' AND column_name = 'cf_channel'
    """)
    if not cr.fetchone():
        _logger.info('CasaFolino migration: cf_channel column not found, skip channel tags')
        return

    for key, tag_name in CHANNEL_TAG_MAP.items():
        tag_id = _find_or_create_tag(cr, tag_name, 2)  # color 2 = orange
        cr.execute("SELECT id FROM crm_lead WHERE cf_channel = %s", (key,))
        lead_ids = [row[0] for row in cr.fetchall()]
        for lead_id in lead_ids:
            _add_tag_to_lead(cr, lead_id, tag_id)
        if lead_ids:
            _logger.info('CasaFolino migration: tagged %d leads with "%s"', len(lead_ids), tag_name)


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
            _logger.info('CasaFolino migration: dropped column %s.%s', table, col)
