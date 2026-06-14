import logging
from datetime import timedelta
from odoo import fields

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """V17: Register cron for scheduled send + auto lead AI config param."""
    from odoo.api import Environment
    from odoo import SUPERUSER_ID

    env = Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo().with_context(active_test=False)

    # ── 1. Cron: Send Scheduled Drafts (every 5 min) ──
    cron_name = 'CasaFolino Send Scheduled Drafts'
    existing = Cron.search([('cron_name', 'ilike', cron_name)], limit=1)
    if not existing:
        draft_model = env.ref('casafolino_mail.model_casafolino_mail_draft')
        sa = env['ir.actions.server'].create({
            'name': cron_name,
            'model_id': draft_model.id,
            'state': 'code',
            'code': 'model._cron_send_scheduled()',
        })
        Cron.create({
            'cron_name': cron_name,
            'ir_actions_server_id': sa.id,
            'interval_number': 5,
            'interval_type': 'minutes',
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[V17] Cron '%s' created", cron_name)
    else:
        _logger.info("[V17] Cron '%s' already exists (id=%s)", cron_name, existing.id)

    # ── 2. Config param: auto_create_lead_from_ai (default ON) ──
    IrConfig = env['ir.config_parameter'].sudo()
    if not IrConfig.get_param('casafolino.auto_create_lead_from_ai'):
        IrConfig.set_param('casafolino.auto_create_lead_from_ai', '1')
        _logger.info("[V17] Config param casafolino.auto_create_lead_from_ai set to 1")

    # ── 3. Add crm.lead fields if missing ──
    # cf_mail_thread_id, cf_auto_created, cf_mail_lead_rule_id
    # These are now declared in ORM (crm_lead_ext.py), Odoo will add columns
    # automatically during -u. No manual SQL needed.

    _logger.info("[V17] Migration complete — Send Later cron + Auto Lead AI config")
