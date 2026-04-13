from odoo import models, fields


class CfProjectChecklistItem(models.Model):
    _name = 'cf.project.checklist.item'
    _description = 'Checklist Item'
    _order = 'sequence'

    task_id = fields.Many2one('project.task', required=True, ondelete='cascade')
    name = fields.Char(string="Voce", required=True)
    sequence = fields.Integer(default=10)
    is_done = fields.Boolean(string="Completato")
    done_by = fields.Many2one('res.users', string="Completato da")
    done_date = fields.Datetime(string="Data Completamento")

    def write(self, vals):
        if 'is_done' in vals and vals['is_done']:
            vals['done_by'] = self.env.uid
            vals['done_date'] = fields.Datetime.now()
        elif 'is_done' in vals and not vals['is_done']:
            vals['done_by'] = False
            vals['done_date'] = False
        return super().write(vals)


class CfProjectChecklistTemplate(models.Model):
    _name = 'cf.project.checklist.template'
    _description = 'Checklist Template Item'
    _order = 'sequence'

    task_template_id = fields.Many2one(
        'cf.project.task.template', required=True, ondelete='cascade')
    name = fields.Char(string="Voce", required=True)
    sequence = fields.Integer(default=10)
