from odoo import models, fields


class CfDocFooterBlock(models.Model):
    _name = 'cf.doc.footer.block'
    _description = 'Blocco Piè di Pagina Documento'
    _order = 'sequence, name'

    name = fields.Char(string='Etichetta', required=True)
    sequence = fields.Integer(default=10)
    block_type = fields.Selection([
        ('bank', 'Conto Bancario'),
        ('payment_term', 'Termini di Pagamento'),
        ('note', 'Nota Libera'),
    ], string='Tipo', required=True, default='note')

    bank_id = fields.Many2one(
        'res.partner.bank',
        string='Conto Bancario',
        domain=[('partner_id.is_company', '=', True)],
    )
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Termini di Pagamento',
    )
    note = fields.Text(string='Testo Nota')
    active = fields.Boolean(default=True)

    def get_display_lines(self):
        self.ensure_one()
        lines = []
        if self.block_type == 'bank' and self.bank_id:
            b = self.bank_id
            if b.acc_number:
                lines.append(('IBAN', b.acc_number))
            if b.bank_bic:
                lines.append(('BIC/SWIFT', b.bank_bic))
            if b.bank_id and b.bank_id.name:
                lines.append(('Banca', b.bank_id.name))
        elif self.block_type == 'payment_term' and self.payment_term_id:
            pt = self.payment_term_id
            lines.append(('Condizioni', pt.name))
            if pt.note:
                lines.append(('', pt.note))
        elif self.block_type == 'note' and self.note:
            lines.append(('', self.note))
        return lines
