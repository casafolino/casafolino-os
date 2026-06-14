import logging
from datetime import timedelta

from odoo import api, fields, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.1 → 7.2: cron silent partners + config param (idempotente)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo()

    # ── 1. Verifica/crea cron "CasaFolino: Silent Partners Alert" ──
    _logger.info("[mail migration 7.2] Step 1: verifica cron Silent Partners Alert...")
    if not Cron.search([('cron_name', '=', 'CasaFolino: Silent Partners Alert')]):
        model = env.ref('casafolino_mail.model_casafolino_mail_account')
        server_action = env['ir.actions.server'].create({
            'name': 'CasaFolino Silent Partners - Action',
            'model_id': model.id,
            'state': 'code',
            'code': 'model._cron_silent_partners_alert()',
        })
        tomorrow_7am = fields.Datetime.now().replace(
            hour=7, minute=0, second=0) + timedelta(days=1)
        Cron.create({
            'cron_name': 'CasaFolino: Silent Partners Alert',
            'ir_actions_server_id': server_action.id,
            'interval_number': 1,
            'interval_type': 'days',
            'nextcall': tomorrow_7am,
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[mail migration 7.2] Cron Silent Partners Alert creato.")
    else:
        _logger.info("[mail migration 7.2] Cron Silent Partners Alert gia' presente, skip.")

    # ── 2. Verifica/crea ir.config_parameter silent_days_threshold ──
    _logger.info("[mail migration 7.2] Step 2: verifica config param silent_days_threshold...")
    IrConfig = env['ir.config_parameter'].sudo()
    if not IrConfig.get_param('casafolino_mail.silent_days_threshold'):
        IrConfig.set_param('casafolino_mail.silent_days_threshold', '21')
        _logger.info("[mail migration 7.2] Config param silent_days_threshold creato (default 21).")
    else:
        _logger.info("[mail migration 7.2] Config param silent_days_threshold gia' presente, skip.")
