import logging

from odoo import api, fields, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.2 → 7.3: AI classify cron + config + seed policy (idempotente)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo()
    IrConfig = env['ir.config_parameter'].sudo()

    # ── 1. Verifica/crea cron "CasaFolino: AI Classify Pending" ──
    _logger.info("[mail migration 7.3] Step 1: verifica cron AI Classify Pending...")
    if not Cron.search([('cron_name', '=', 'CasaFolino: AI Classify Pending')]):
        model = env.ref('casafolino_mail.model_casafolino_mail_message')
        server_action = env['ir.actions.server'].create({
            'name': 'CasaFolino AI Classify - Action',
            'model_id': model.id,
            'state': 'code',
            'code': 'model._cron_ai_classify_pending()',
        })
        Cron.create({
            'cron_name': 'CasaFolino: AI Classify Pending',
            'ir_actions_server_id': server_action.id,
            'interval_number': 10,
            'interval_type': 'minutes',
            'nextcall': fields.Datetime.now(),
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[mail migration 7.3] Cron AI Classify Pending creato.")
    else:
        _logger.info("[mail migration 7.3] Cron AI Classify Pending gia' presente, skip.")

    # ── 2. Verifica/crea config param ai_classifier_enabled ──
    _logger.info("[mail migration 7.3] Step 2: verifica config param ai_classifier_enabled...")
    if not IrConfig.get_param('casafolino_mail.ai_classifier_enabled'):
        IrConfig.set_param('casafolino_mail.ai_classifier_enabled', '1')
        _logger.info("[mail migration 7.3] Config param ai_classifier_enabled creato (default 1).")
    else:
        _logger.info("[mail migration 7.3] Config param ai_classifier_enabled gia' presente, skip.")

    # ── 3. Seed policy "Newsletter AI → auto_discard" (priority bassa) ──
    _logger.info("[mail migration 7.3] Step 3: verifica seed policy Newsletter AI...")
    Policy = env['casafolino.mail.sender_policy'].sudo()
    if not Policy.search([('name', '=', 'Newsletter AI-detected → discard')]):
        Policy.create({
            'name': 'Newsletter AI-detected → discard',
            'pattern_type': 'domain',
            'pattern_value': '*',
            'match_ai_category': 'newsletter',
            'action': 'auto_discard',
            'priority': 30,
            'notes': 'Auto-scarta email classificate come newsletter dall\'AI. '
                     'Priority 30: qualsiasi policy domain-specific con priority > 30 vince.',
        })
        _logger.info("[mail migration 7.3] Seed policy Newsletter AI creata (priority 30).")
    else:
        _logger.info("[mail migration 7.3] Seed policy Newsletter AI gia' presente, skip.")
