from odoo import api, fields, models

# Mirror del pattern mrp.workcenter.productivity (date_start/date_end/duration/user).
# Non si scrive su mrp.workcenter.productivity perché quel modello è legato a
# workcenter/workorder/loss (dati di manifattura); per i task generici si usa
# un log dedicato che ne rispecchia la struttura. Durata calcolata in ORE
# LAVORATIVE (mai wall-clock), coerente col cronometro semaforo.


class CfTaskTimeLog(models.Model):
    _name = 'cf.task.time.log'
    _description = 'CasaFolino Task Time Log'
    _order = 'date_start desc, id desc'

    step_id = fields.Many2one(
        'cf.task.step', string="Step", required=True, ondelete='cascade', index=True)
    task_id = fields.Many2one(related='step_id.task_id', store=True, string="Task")
    user_id = fields.Many2one('res.users', string="Operatore", required=True)
    date_start = fields.Datetime(string="Inizio", required=True)
    date_end = fields.Datetime(string="Fine")
    duration = fields.Float(
        string="Durata (ore lavorative)", compute='_compute_duration', store=True)

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for log in self:
            if log.date_start and log.date_end and log.step_id:
                log.duration = log.step_id._work_hours_between(
                    log.date_start, log.date_end)
            else:
                log.duration = 0.0
