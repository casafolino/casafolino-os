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

    # Create server action (Odoo 18: name is JSONB for translations)
    import json
    name_json = json.dumps({'en_US': 'Mail Hub: Backfill AI Classification - Action'})
    cr.execute("""
        INSERT INTO ir_act_server (name, model_id, state, code, binding_type)
        VALUES (
            %s::jsonb,
            %s,
            'code',
            'model._cron_backfill_ai_classification()',
            'action'
        ) RETURNING id
    """, (name_json, model_id))
    sa_id = cr.fetchone()[0]

    # Create cron
    cr.execute("""
        INSERT INTO ir_cron (
            cron_name, ir_actions_server_id, interval_number, interval_type,
            numbercall, active, user_id, priority
        ) VALUES (
            'Mail Hub: Backfill AI Classification',
            %s, 10, 'minutes', -1, true, %s, 15
        )
    """, (sa_id, user_id))

    _logger.info("[F9 post-migration] Backfill AI cron created (server_action=%s)", sa_id)
