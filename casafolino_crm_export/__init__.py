from . import controllers
from . import models


def _post_init_hook(env):
    """Create cron for auto-standby inactive leads (via Python, not XML)."""
    cron = env['ir.cron'].search(
        [('cron_name', '=', 'CasaFolino: Auto-Standby Lead inattivi')], limit=1
    )
    if not cron:
        env['ir.cron'].create({
            'cron_name': 'CasaFolino: Auto-Standby Lead inattivi',
            'name': 'CasaFolino: Auto-Standby Lead inattivi',
            'model_id': env.ref('crm.model_crm_lead').id,
            'state': 'code',
            'code': 'model._cron_move_to_standby()',
            'interval_number': 1,
            'interval_type': 'days',
            'active': True,
        })
