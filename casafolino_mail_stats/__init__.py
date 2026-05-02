from . import models
from . import controllers


def _post_init_hook(env):
    """Create crons after install — XML cron with model_id ref breaks in Odoo 18."""
    Cron = env['ir.cron']
    model_id = env['ir.model']._get_id('casafolino.mail.engagement')

    if not Cron.search([('cron_name', '=', 'Mail Stats: Rebuild Engagement Cache')], limit=1):
        Cron.create({
            'name': 'Mail Stats: Rebuild Engagement Cache',
            'model_id': model_id,
            'state': 'code',
            'code': 'model._rebuild_cache_full()',
            'interval_number': 15,
            'interval_type': 'minutes',
            'active': True,
        })

    if not Cron.search([('cron_name', '=', 'Mail Stats: Auto-Activity Hot Leads')], limit=1):
        Cron.create({
            'name': 'Mail Stats: Auto-Activity Hot Leads',
            'model_id': model_id,
            'state': 'code',
            'code': 'model._check_hot_leads_activity()',
            'interval_number': 1,
            'interval_type': 'hours',
            'active': True,
        })

    # Initial cache build
    env['casafolino.mail.engagement']._rebuild_cache_full()
    env.cr.commit()
