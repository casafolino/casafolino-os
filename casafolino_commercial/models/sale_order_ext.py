from odoo import models

class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    def action_open_discount_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Applica Sconto Massivo',
            'res_model': 'sale.discount.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_discount': self.order_line[0].discount if self.order_line else 0,
            },
        }
