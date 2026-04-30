from odoo import api, fields, models


class ProjectTaskExt(models.Model):
    _inherit = 'project.task'

    cf_todo_ids = fields.One2many('cf.todo', 'task_id', string='Checklist')
    cf_todo_count = fields.Integer(compute='_compute_cf_todo_stats')
    cf_todo_progress = fields.Float(compute='_compute_cf_todo_stats')

    @api.depends('cf_todo_ids', 'cf_todo_ids.done')
    def _compute_cf_todo_stats(self):
        for task in self:
            todos = task.cf_todo_ids
            total = len(todos)
            done = len(todos.filtered('done'))
            task.cf_todo_count = total
            task.cf_todo_progress = (done / total * 100) if total else 0.0
