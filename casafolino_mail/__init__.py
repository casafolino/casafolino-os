from . import models
from . import wizard
from . import controllers


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

    # ── 2. Crea unico cron V2 ──
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
