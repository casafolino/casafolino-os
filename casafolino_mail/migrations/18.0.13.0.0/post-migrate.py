import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """V13 migration: DELETE CASCADE existing messages, reset fetch dates for backfill."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env['ir.config_parameter'].sudo()

    # Always register crons (even if data migration already done)
    _register_v13_crons(env)

    # Idempotent check for data migration
    if ICP.get_param('casafolino.mail_raw_migration_done'):
        _logger.info("[V13 migrate] Data migration already done, skipping")
        return

    _logger.info("[V13 migrate] Starting DELETE CASCADE migration")

    # Count before delete
    cr.execute("SELECT COUNT(*) FROM casafolino_mail_message")
    msg_count = cr.fetchone()[0]
    _logger.info("[V13 migrate] Messages before delete: %d", msg_count)

    # Delete all messages (CASCADE handles related records like attachments)
    cr.execute("DELETE FROM casafolino_mail_message")
    _logger.info("[V13 migrate] Deleted %d messages", msg_count)

    # Clean RAW table if it exists already
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'casafolino_mail_raw'
        )
    """)
    if cr.fetchone()[0]:
        cr.execute("DELETE FROM casafolino_mail_raw")
        _logger.info("[V13 migrate] Cleaned RAW table")

    # Reset last_fetch_datetime to trigger backfill from sync_start_date
    cr.execute("""
        UPDATE casafolino_mail_account
        SET last_fetch_datetime = '2026-04-01 00:00:00',
            last_successful_fetch_datetime = NULL
        WHERE active = true
    """)
    _logger.info("[V13 migrate] Reset fetch dates to 2026-04-01 for backfill")

    # Mark migration as done
    ICP.set_param('casafolino.mail_raw_migration_done', 'true')
    _logger.info("[V13 migrate] Migration complete")

    # ── Always: register Triage RAW + Cleanup RAW crons (idempotent) ──
    _register_v13_crons(env)


def _register_v13_crons(env):
    """Register Triage RAW and Cleanup RAW crons if missing."""
    from datetime import timedelta
    from odoo import fields

    Cron = env['ir.cron'].sudo().with_context(active_test=False)

    try:
        raw_model = env['ir.model'].sudo().search([
            ('model', '=', 'casafolino.mail.raw')
        ], limit=1)
        if not raw_model:
            _logger.warning("[V13 migrate] casafolino.mail.raw model not found, skip cron creation")
            return
    except Exception:
        _logger.warning("[V13 migrate] Cannot find RAW model, skip cron creation")
        return

    # Triage RAW cron
    existing_triage = Cron.search([('cron_name', 'ilike', 'CasaFolino%Triage RAW%')])
    if not existing_triage:
        sa_triage = env['ir.actions.server'].create({
            'name': 'CasaFolino Triage RAW - Action',
            'model_id': raw_model.id,
            'state': 'code',
            'code': 'model._cron_triage_raw()',
        })
        Cron.create({
            'cron_name': 'CasaFolino Triage RAW - Action',
            'ir_actions_server_id': sa_triage.id,
            'interval_number': 5,
            'interval_type': 'minutes',
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[V13 migrate] Created Triage RAW cron")
    else:
        _logger.info("[V13 migrate] Triage RAW cron already exists (id=%d)", existing_triage[0].id)

    # Cleanup RAW cron
    existing_cleanup = Cron.search([('cron_name', 'ilike', 'CasaFolino%Cleanup RAW%')])
    if not existing_cleanup:
        sa_cleanup = env['ir.actions.server'].create({
            'name': 'CasaFolino Cleanup RAW - Action',
            'model_id': raw_model.id,
            'state': 'code',
            'code': 'model._cron_cleanup_raw()',
        })
        tomorrow_3am = fields.Datetime.now().replace(
            hour=3, minute=0, second=0) + timedelta(days=1)
        Cron.create({
            'cron_name': 'CasaFolino Cleanup RAW - Action',
            'ir_actions_server_id': sa_cleanup.id,
            'interval_number': 1,
            'interval_type': 'days',
            'nextcall': tomorrow_3am,
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[V13 migrate] Created Cleanup RAW cron")
    else:
        _logger.info("[V13 migrate] Cleanup RAW cron already exists (id=%d)", existing_cleanup[0].id)
