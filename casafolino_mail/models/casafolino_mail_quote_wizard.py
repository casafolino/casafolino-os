import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailQuoteWizard(models.TransientModel):
    _name = 'casafolino.mail.quote.wizard'
    _description = 'Wizard to quickly create sale.order from email thread'

    thread_id = fields.Many2one('casafolino.mail.thread', required=True)
    partner_id = fields.Many2one('res.partner', required=True)
    pricelist_id = fields.Many2one('product.pricelist')
    payment_term_id = fields.Many2one('account.payment.term')
    incoterm_id = fields.Many2one('account.incoterms')
    warehouse_id = fields.Many2one('stock.warehouse')
    line_ids = fields.One2many('casafolino.mail.quote.wizard.line', 'wizard_id')
    note = fields.Html()

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.pricelist_id = self.partner_id.property_product_pricelist
            self.payment_term_id = self.partner_id.property_payment_term_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get('thread_id'):
            thread = self.env['casafolino.mail.thread'].browse(res['thread_id'])
            if thread.exists():
                res['note'] = self._build_context_note(thread)
                partner = thread.partner_ids[:1]
                if partner and 'partner_id' not in res:
                    res['partner_id'] = partner.id
                    res['pricelist_id'] = partner.property_product_pricelist.id if partner.property_product_pricelist else False
                    res['payment_term_id'] = partner.property_payment_term_id.id if partner.property_payment_term_id else False
        return res

    def _build_context_note(self, thread):
        """Extract last 3 messages as context note."""
        msgs = thread.message_ids.filtered(
            lambda m: not m.is_deleted
        ).sorted('email_date', reverse=True)[:3]
        parts = []
        for msg in msgs:
            direction = '→' if msg.direction == 'outbound' else '←'
            date_str = msg.email_date.strftime('%d/%m/%Y %H:%M') if msg.email_date else ''
            sender = msg.sender_name or msg.sender_email or ''
            snippet = (msg.body_text or msg.subject or '')[:150]
            parts.append(f"<p><small><b>{direction} {sender}</b> ({date_str})</small><br/>{snippet}</p>")
        return ''.join(parts) or ''

    def action_create_sale_order(self):
        """Create sale.order from wizard data."""
        self.ensure_one()
        SaleOrder = self.env['sale.order']

        order_vals = {
            'partner_id': self.partner_id.id,
            'cf_mail_thread_id': self.thread_id.id,
            'note': self.note or '',
        }
        if self.pricelist_id:
            order_vals['pricelist_id'] = self.pricelist_id.id
        if self.payment_term_id:
            order_vals['payment_term_id'] = self.payment_term_id.id
        if self.warehouse_id:
            order_vals['warehouse_id'] = self.warehouse_id.id

        # Order lines
        order_line_vals = []
        for line in self.line_ids:
            order_line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'price_unit': line.price_unit,
            }))
        if order_line_vals:
            order_vals['order_line'] = order_line_vals

        order = SaleOrder.create(order_vals)

        # Log feedback
        try:
            self.env['casafolino.partner.intelligence.feedback'].create({
                'partner_id': self.partner_id.id,
                'user_id': self.env.uid,
                'action_type': 'quote_created_from_thread',
                'context_json': f'{{"thread_id": {self.thread_id.id}, "order_id": {order.id}}}',
            })
        except Exception as e:
            _logger.warning("[quote wizard] Feedback error: %s", e)

        _logger.info("[quote wizard] Created SO %s from thread %s", order.name, self.thread_id.id)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }


class CasafolinoMailQuoteWizardLine(models.TransientModel):
    _name = 'casafolino.mail.quote.wizard.line'
    _description = 'Quote wizard line'

    wizard_id = fields.Many2one('casafolino.mail.quote.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True,
        domain=[('sale_ok', '=', True)])
    product_uom_qty = fields.Float(default=1.0)
    price_unit = fields.Float(string='Prezzo unitario')
    name = fields.Char(related='product_id.name', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
