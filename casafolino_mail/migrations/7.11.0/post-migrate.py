import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.10.2 → 7.11.0: register missing body-fetch cron (idempotente)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo()

    cron_name = 'CasaFolino: Body Fetch Pending'

    _logger.info("[mail migration 7.11.0] Verifica cron '%s'...", cron_name)

    if Cron.search([('cron_name', '=', cron_name)]):
        _logger.warning(
            "[mail migration 7.11.0] Cron '%s' gia' presente, skip.", cron_name)
        return

    model = env.ref('casafolino_mail.model_casafolino_mail_message')
    server_action = env['ir.actions.server'].create({
        'name': 'CasaFolino Body Fetch Pending - Action',
        'model_id': model.id,
        'state': 'code',
        'code': 'model._cron_fetch_pending_bodies()',
    })
    Cron.create({
        'cron_name': cron_name,
        'ir_actions_server_id': server_action.id,
        'interval_number': 10,
        'interval_type': 'minutes',
        'active': True,
        'user_id': env.ref('base.user_admin').id,
    })
    _logger.info("[mail migration 7.11.0] Cron '%s' creato (ogni 10 min).", cron_name)
