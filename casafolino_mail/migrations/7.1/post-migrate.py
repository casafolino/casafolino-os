import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.0 → 7.1: cron V2 + sender_policy seed (idempotente)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo()

    # ── 1a. Elimina cron orfani del vecchio stack ──
    _logger.info("[mail migration 7.1] Step 1a: cleanup cron orfani vecchio stack...")
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
        _logger.info("[mail migration 7.1] Trovati %d cron orfani, elimino...", len(old_crons))
        old_crons.unlink()
    else:
        _logger.info("[mail migration 7.1] Nessun cron orfano trovato.")

    for cron_id in [80, 81]:
        try:
            c = Cron.browse(cron_id)
            if c.exists():
                c.active = False
                _logger.info("[mail migration 7.1] Cron ID %d disattivato.", cron_id)
        except Exception:
            pass

    # ── 1b. Crea/verifica cron "CasaFolino: Mail Sync V2" ──
    _logger.info("[mail migration 7.1] Step 1b: verifica cron Mail Sync V2...")
    if not Cron.search([('cron_name', '=', 'CasaFolino: Mail Sync V2')]):
        model = env.ref('casafolino_mail.model_casafolino_mail_account')
        server_action = env['ir.actions.server'].create({
            'name': 'CasaFolino Mail Sync V2 - Action',
            'model_id': model.id,
            'state': 'code',
            'code': 'model._cron_fetch_all_accounts()',
        })
        Cron.create({
            'cron_name': 'CasaFolino: Mail Sync V2',
            'ir_actions_server_id': server_action.id,
            'interval_number': 15,
            'interval_type': 'minutes',
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[mail migration 7.1] Cron Mail Sync V2 creato.")
    else:
        _logger.info("[mail migration 7.1] Cron Mail Sync V2 gia' presente, skip.")

    # ── 1c. Seed sender_policy di esempio ──
    _logger.info("[mail migration 7.1] Step 1c: verifica seed sender_policy...")
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
        _logger.info("[mail migration 7.1] Creati 3 sender_policy di esempio.")
    else:
        _logger.info("[mail migration 7.1] sender_policy gia' presenti (%d), skip.", Policy.search_count([]))
