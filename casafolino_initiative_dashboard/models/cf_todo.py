from odoo import api, fields, models


class CfTodo(models.Model):
    _name = 'cf.todo'
    _description = 'Sotto-attività Checklist (Lavagna)'
    _order = 'sequence asc, create_date asc'

    name = fields.Char(required=True)
    task_id = fields.Many2one(
        'project.task', required=True, ondelete='cascade', index=True,
        string='Task',
    )
    initiative_id = fields.Many2one(
        'cf.initiative', related='task_id.initiative_id',
        store=True, index=True, string='Iniziativa',
    )
    done = fields.Boolean(default=False)
    done_date = fields.Datetime(
        compute='_compute_done_date', store=True, readonly=True,
    )
    assigned_user_id = fields.Many2one(
        'res.users', string='Assegnato a',
    )
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('name_not_empty', "CHECK(length(trim(name)) > 0)",
         'Il testo del todo non può essere vuoto.'),
    ]

    @api.depends('done')
    def _compute_done_date(self):
        for rec in self:
            if rec.done and not rec.done_date:
                rec.done_date = fields.Datetime.now()
            elif not rec.done:
                rec.done_date = False
