from . import models


def _post_init_hook(env):
    """Crea cron Mail Hub se non esistono."""
    Cron = env['ir.cron'].sudo()

    if not Cron.search([('name', '=', 'CasaFolino: Fetch nuove email (Hub)')]):
        Cron.create({
            'name': 'CasaFolino: Fetch nuove email (Hub)',
            'model_id': env.ref('casafolino_mail.model_casafolino_mail_account').id,
            'state': 'code',
            'code': 'model._cron_fetch_all_accounts()',
            'interval_number': 2,
            'interval_type': 'hours',
            'numbercall': -1,
            'active': True,
        })

    if not Cron.search([('name', '=', 'CasaFolino: Cleanup email scartate')]):
        Cron.create({
            'name': 'CasaFolino: Cleanup email scartate',
            'model_id': env.ref('casafolino_mail.model_casafolino_mail_message').id,
            'state': 'code',
            'code': 'model._cron_cleanup_discarded()',
            'interval_number': 1,
            'interval_type': 'days',
            'numbercall': -1,
            'active': True,
        })
