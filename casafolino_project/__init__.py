from . import models


def post_init_hook(env):
    """Registra il cron CasaFolino Fair Alerts se non esiste."""
    existing = env['ir.cron'].search([('name', '=', 'CasaFolino: Fair Alerts')])
    if existing:
        return
    model_id = env['ir.model'].search([('model', '=', 'project.project')], limit=1)
    if not model_id:
        return
    env['ir.cron'].create({
        'name': 'CasaFolino: Fair Alerts',
        'model_id': model_id.id,
        'state': 'code',
        'code': 'model._cron_fair_alerts()',
        'interval_number': 1,
        'interval_type': 'days',
        'numbercall': -1,
        'active': True,
    })
