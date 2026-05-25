from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    cf_project_id = fields.Many2one(
        comodel_name='project.project',
        string='Dossier / Progetto',
        index=True,
    )
