from odoo import models, fields


class SaleOrderMailV3(models.Model):
    _inherit = 'sale.order'

    cf_mail_thread_id = fields.Many2one('casafolino.mail.thread',
        string='Thread Mail V3', ondelete='set null', index=True)

    def action_open_mail_v3_thread(self):
        """Open linked Mail V3 thread."""
        self.ensure_one()
        if not self.cf_mail_thread_id:
            return
        return {
            'type': 'ir.actions.client',
            'tag': 'cf_mail_v3_client',
            'params': {'open_thread_id': self.cf_mail_thread_id.id},
        }
