from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cf_project_id = fields.Many2one(
        comodel_name='project.project',
        string='Dossier / Progetto',
        index=True,
    )
