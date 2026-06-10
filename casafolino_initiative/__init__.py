from . import models
from . import wizard


def post_init_hook(env):
    """Crea cron staffetta se non esiste."""
    existing = env['ir.cron'].sudo().search(
        [('name', '=', 'CasaFolino: Traffic Check Staffetta')], limit=1)
    if not existing:
        model_id = env['ir.model'].sudo().search(
            [('model', '=', 'cf.initiative')], limit=1)
        if model_id:
            env['ir.cron'].sudo().create({
                'name': 'CasaFolino: Traffic Check Staffetta',
                'model_id': model_id.id,
                'state': 'code',
                'code': 'model._cron_traffic_check()',
                'interval_number': 1,
                'interval_type': 'days',
                'numbercall': -1,
                'active': True,
                'nextcall': '2026-06-11 05:30:00',
                'priority': 5,
            })
