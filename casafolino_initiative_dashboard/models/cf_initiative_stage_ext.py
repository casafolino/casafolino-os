from odoo import fields, models


class CfInitiativeStageExt(models.Model):
    """Aggiunge task_ids a cf.initiative.stage dopo che cf.todo.stage_id è definito."""
    _inherit = 'cf.initiative.stage'

    task_ids = fields.One2many('cf.todo', 'stage_id', string='Task')
