import logging
from datetime import timedelta

from odoo import fields

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """V15 migration: mass actions + trash cleanup cron."""
    from odoo.api import Environment
    from odoo import SUPERUSER_ID

    env = Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo().with_context(active_test=False)

    # ── 1. Add is_deleted_at column if not exists ──
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'casafolino_mail_message'
        AND column_name = 'is_deleted_at'
    """)
    if not cr.fetchone():
        cr.execute("""
            ALTER TABLE casafolino_mail_message
            ADD COLUMN is_deleted_at TIMESTAMP WITHOUT TIME ZONE
        """)
        cr.execute("""
            CREATE INDEX IF NOT EXISTS casafolino_mail_message_is_deleted_at_idx
            ON casafolino_mail_message (is_deleted_at)
            WHERE is_deleted_at IS NOT NULL
        """)
        _logger.info("[V15] Added is_deleted_at column + index to casafolino_mail_message")

    # ── 2. Create cron: Cleanup Trash (daily 04:00 UTC) ──
    msg_model = env.ref('casafolino_mail.model_casafolino_mail_message')
    trash_crons = Cron.search([('cron_name', 'ilike', 'CasaFolino%Cleanup Trash%')])
    if not trash_crons:
        sa_trash = env['ir.actions.server'].create({
            'name': 'CasaFolino Cleanup Trash - Action',
            'model_id': msg_model.id,
            'state': 'code',
            'code': 'model._cron_cleanup_trash()',
        })
        tomorrow_4am = fields.Datetime.now().replace(
            hour=4, minute=0, second=0) + timedelta(days=1)
        Cron.create({
            'cron_name': 'CasaFolino Cleanup Trash - Action',
            'ir_actions_server_id': sa_trash.id,
            'interval_number': 1,
            'interval_type': 'days',
            'nextcall': tomorrow_4am,
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[V15] Created cron: Cleanup Trash (daily 04:00)")

    # ── 3. Create cron: Cleanup Mass Action Logs (every 30 min) ──
    log_model = env.ref('casafolino_mail.model_casafolino_mail_mass_action_log')
    log_crons = Cron.search([('cron_name', 'ilike', 'CasaFolino%Cleanup Mass Action%')])
    if not log_crons:
        sa_log = env['ir.actions.server'].create({
            'name': 'CasaFolino Cleanup Mass Action Logs - Action',
            'model_id': log_model.id,
            'state': 'code',
            'code': 'model._cron_cleanup_expired_logs()',
        })
        Cron.create({
            'cron_name': 'CasaFolino Cleanup Mass Action Logs - Action',
            'ir_actions_server_id': sa_log.id,
            'interval_number': 30,
            'interval_type': 'minutes',
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[V15] Created cron: Cleanup Mass Action Logs (30 min)")

    # ── 4. Cleanup 6 orphan crons (methods removed in V15) ──
    orphan_patterns = [
        '%check_snooze%',
        '%auto_link_leads%',
        '%scheduled_send%',
        '%cleanup_old_drafts%',
        '%cleanup_old_outbox%',
        '%cleanup_discarded%',
    ]
    for pattern in orphan_patterns:
        # Delete cron entries (code is jsonb in Odoo 18, cast to text)
        cr.execute("""
            DELETE FROM ir_cron
            WHERE id IN (
                SELECT c.id FROM ir_cron c
                JOIN ir_act_server s ON c.ir_actions_server_id = s.id
                WHERE s.code::text ILIKE %s OR s.name ILIKE %s
            )
        """, (pattern, pattern))
        deleted_crons = cr.rowcount
        # Delete orphan server actions
        cr.execute("""
            DELETE FROM ir_act_server
            WHERE (code::text ILIKE %s OR name ILIKE %s)
              AND id NOT IN (SELECT ir_actions_server_id FROM ir_cron WHERE ir_actions_server_id IS NOT NULL)
        """, (pattern, pattern))
        deleted_actions = cr.rowcount
        if deleted_crons or deleted_actions:
            _logger.info("[V15] Cleaned orphan cron '%s': %d crons, %d actions removed",
                         pattern.strip('%'), deleted_crons, deleted_actions)

    _logger.info("[V15] Migration complete: mass actions ready")
