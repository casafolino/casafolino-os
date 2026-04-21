import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """F9 post-migration: create backfill AI classification cron."""
    _logger.info("[F9 post-migration] Creating backfill AI cron...")

    # Check if cron already exists
    cr.execute("""
        SELECT id FROM ir_cron WHERE cron_name = 'Mail Hub: Backfill AI Classification'
    """)
    if cr.fetchone():
        _logger.info("[F9 post-migration] Backfill AI cron already exists, skip")
        return

    # Get model_id for casafolino.mail.message
    cr.execute("""
        SELECT id FROM ir_model WHERE model = 'casafolino.mail.message'
    """)
    row = cr.fetchone()
    if not row:
        _logger.warning("[F9 post-migration] Model casafolino.mail.message not found, skip cron creation")
        return
    model_id = row[0]

    # Get admin user id
    cr.execute("SELECT id FROM res_users WHERE login = '__system__' LIMIT 1")
    row = cr.fetchone()
    if not row:
        cr.execute("SELECT id FROM res_users WHERE active = true ORDER BY id LIMIT 1")
        row = cr.fetchone()
    user_id = row[0] if row else 1

    # Cleanup orphan server actions from failed previous migrations
    cr.execute("""
        DELETE FROM ir_act_server
        WHERE name::text ILIKE '%Backfill AI Classification%'
          AND id NOT IN (SELECT ir_actions_server_id FROM ir_cron WHERE ir_actions_server_id IS NOT NULL)
    """)

    # Create server action (Odoo 18: name is JSONB for translations)
    import json
    name_json = json.dumps({'en_US': 'Mail Hub: Backfill AI Classification - Action'})
    cr.execute("""
        INSERT INTO ir_act_server (name, type, model_id, state, code, binding_type, usage)
        VALUES (
            %s::jsonb,
            'ir.actions.server',
            %s,
            'code',
            'model._cron_backfill_ai_classification()',
            'action',
            'ir_cron'
        ) RETURNING id
    """, (name_json, model_id))
    sa_id = cr.fetchone()[0]

    # Create cron (Odoo 18: no numbercall column)
    cr.execute("""
        INSERT INTO ir_cron (
            cron_name, ir_actions_server_id, interval_number, interval_type,
            active, user_id, priority
        ) VALUES (
            'Mail Hub: Backfill AI Classification',
            %s, 10, 'minutes', true, %s, 15
        )
    """, (sa_id, user_id))

    _logger.info("[F9 post-migration] Backfill AI cron created (server_action=%s)", sa_id)
