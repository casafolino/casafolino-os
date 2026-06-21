from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_campione = fields.Boolean(
        string="Campione", default=False, index=True, copy=False,
        help="Ordine generato dal flusso Campionatura (KPI campione→ordine).")
    sample_code = fields.Char(string="Codice Campionatura", copy=False, readonly=True)
    campione_lead_id = fields.Many2one(
        'crm.lead', string="Lead campionatura", copy=False, index=True,
        help="Lead di origine: rende queryabile il tasso campione→ordine.")
    campione_task_id = fields.Many2one('cf.task', string="Task campionatura", copy=False)
    campione_shipment_id = fields.Many2one('cf.shipment', string="Spedizione campione", copy=False)
