import logging
from datetime import timedelta

from odoo import fields

from . import models
from . import wizard
from . import controllers

_logger = logging.getLogger(__name__)


def _post_init_hook(env):
    """Setup iniziale modulo Mail CRM V2."""
    Cron = env['ir.cron'].sudo()

    # ── 1. Elimina cron orfani del vecchio stack ──
    old_cron_names = [
        'CasaFolino: IMAP Sync',
        'CF Mail: Sync ogni 20 minuti',
        'CasaFolino: Fetch nuove email (Hub)',
        'CasaFolino: Cleanup email scartate',
        'Mail Hub: Scarica body email in coda',
        'Mail Hub: Pulizia email scartate (30gg)',
    ]
    old_crons = Cron.search([('cron_name', 'in', old_cron_names)])
    if old_crons:
        old_crons.unlink()

    # Disattiva anche per ID noti (80, 81) se ancora presenti
    for cron_id in [80, 81]:
        try:
            c = Cron.browse(cron_id)
            if c.exists():
                c.active = False
        except Exception:
            pass

    # ── 2. Crea/aggiorna unico cron V2 (intervallo 5 min) ──
    model = env.ref('casafolino_mail.model_casafolino_mail_account')
    existing_cron = Cron.search([('cron_name', '=', 'CasaFolino: Mail Sync V2')], limit=1)
    if existing_cron:
        if existing_cron.interval_number != 5 or existing_cron.interval_type != 'minutes':
            existing_cron.write({
                'interval_number': 5,
                'interval_type': 'minutes',
            })
            _logger.info("[casafolino_mail] Cron 82 interval updated to 5 minutes")
    else:
        server_action = env['ir.actions.server'].create({
            'name': 'CasaFolino Mail Sync V2 - Action',
            'model_id': model.id,
            'state': 'code',
            'code': 'model._cron_fetch_all_accounts()',
        })
        Cron.create({
            'cron_name': 'CasaFolino: Mail Sync V2',
            'ir_actions_server_id': server_action.id,
            'interval_number': 5,
            'interval_type': 'minutes',
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })

    # ── 2b. Trigger fetch immediato post-install/update ──
    _logger.info("[casafolino_mail] Post-init: triggering initial fetch")
    try:
        accounts = env['casafolino.mail.account'].sudo().search([
            ('state', '=', 'connected'),
        ])
        for acc in accounts:
            try:
                acc._fetch_emails()
            except Exception as e:
                _logger.warning(
                    "[casafolino_mail] Initial fetch failed for %s: %s",
                    acc.name, e,
                )
        _logger.info(
            "[casafolino_mail] Post-init fetch done: %d accounts processed",
            len(accounts),
        )
    except Exception as e:
        _logger.error("[casafolino_mail] Post-init fetch block error: %s", e)

    # ── 3. Seed sender_policy di esempio ──
    Policy = env['casafolino.mail.sender_policy'].sudo()
    if not Policy.search_count([]):
        Policy.create([
            {
                'name': 'Newsletter domain → discard',
                'pattern_type': 'domain',
                'pattern_value': '*mailup*',
                'action': 'auto_discard',
                'priority': 80,
            },
            {
                'name': 'REWE group → keep auto',
                'pattern_type': 'domain',
                'pattern_value': '*rewe-group*',
                'action': 'auto_keep',
                'priority': 50,
                'auto_create_partner': True,
            },
            {
                'name': 'Default: review',
                'pattern_type': 'domain',
                'pattern_value': '*',
                'action': 'review',
                'priority': 1,
            },
        ])

    # ── 4. Cron Silent Partners Alert ──
    if not Cron.search([('cron_name', '=', 'CasaFolino: Silent Partners Alert')]):
        server_action_silent = env['ir.actions.server'].create({
            'name': 'CasaFolino Silent Partners - Action',
            'model_id': model.id,
            'state': 'code',
            'code': 'model._cron_silent_partners_alert()',
        })
        tomorrow_7am = fields.Datetime.now().replace(
            hour=7, minute=0, second=0) + timedelta(days=1)
        Cron.create({
            'cron_name': 'CasaFolino: Silent Partners Alert',
            'ir_actions_server_id': server_action_silent.id,
            'interval_number': 1,
            'interval_type': 'days',
            'nextcall': tomorrow_7am,
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })

    # ── 5. Config parameter: silent_days_threshold ──
    IrConfig = env['ir.config_parameter'].sudo()
    if not IrConfig.get_param('casafolino_mail.silent_days_threshold'):
        IrConfig.set_param('casafolino_mail.silent_days_threshold', '21')
