from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cf_project_id = fields.Many2one(
        comodel_name='project.project',
        string='Dossier / Progetto',
        index=True,
    )
    cf_is_sample_order = fields.Boolean(
        string='Ordine campionatura',
        index=True,
        copy=False,
    )
    cf_sample_id = fields.Many2one(
        comodel_name='cf.export.sample',
        string='Campionatura',
        index=True,
        copy=False,
    )
