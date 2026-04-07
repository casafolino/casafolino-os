from odoo import models, fields

class SaleDiscountWizard(models.TransientModel):
    _name = 'sale.discount.wizard'
    _description = 'Applica Sconto a Tutte le Righe'

    discount = fields.Float(string='Sconto 1 (%)', digits=(5, 2), required=True)
    order_id = fields.Many2one('sale.order', string='Ordine')

    def action_apply(self):
        for line in self.order_id.order_line:
            line.discount = self.discount
        return {'type': 'ir.actions.act_window_close'}
