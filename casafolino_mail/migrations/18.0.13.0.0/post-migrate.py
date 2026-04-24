import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """V13 migration: DELETE CASCADE existing messages, reset fetch dates for backfill."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env['ir.config_parameter'].sudo()

    # Idempotent check
    if ICP.get_param('casafolino.mail_raw_migration_done'):
        _logger.info("[V13 migrate] Already migrated, skipping")
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
