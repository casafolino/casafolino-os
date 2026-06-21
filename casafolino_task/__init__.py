from . import models


def post_init_hook(env):
    """Configura calendario lavorativo di default e crea il cron di escalation.

    Cron via ORM (non XML) come da regole Odoo 18 del progetto, sul pattern del
    cron 53218 'Traffic Check Staffetta'.
    """
    ICP = env['ir.config_parameter'].sudo()

    # Calendario lavorativo di default: il 9-16 Lun-Ven creato in data/.
    try:
        cal = env.ref('casafolino_task.cf_task_work_calendar_916')
    except ValueError:
        cal = False
    if cal and not ICP.get_param('casafolino_task.work_calendar_id'):
        ICP.set_param('casafolino_task.work_calendar_id', str(cal.id))

    # Cron escalation (idempotente)
    existing = env['ir.cron'].sudo().search(
        [('name', '=', 'CasaFolino: Task Escalation Check')], limit=1)
    if not existing:
        model_id = env['ir.model'].sudo().search(
            [('model', '=', 'cf.task')], limit=1)
        if model_id:
            env['ir.cron'].sudo().create({
                'name': 'CasaFolino: Task Escalation Check',
                'model_id': model_id.id,
                'state': 'code',
                'code': 'model._cron_escalation_check()',
                'interval_number': 1,
                'interval_type': 'hours',
                'numbercall': -1,
                'active': True,
                'priority': 5,
            })
