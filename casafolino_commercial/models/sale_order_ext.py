from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class SaleOrderExt(models.Model):
    _inherit = 'sale.order'

    footer_block_ids = fields.Many2many(
        'cf.doc.footer.block',
        'sale_order_footer_block_rel',
        'order_id',
        'block_id',
        string='Blocchi Documento',
    )
    footer_block_count = fields.Integer(
        compute='_compute_footer_block_count',
        string='Blocchi',
    )

    def _compute_footer_block_count(self):
        for rec in self:
            rec.footer_block_count = len(rec.footer_block_ids)

    def _get_bank_note_text(self):
        """Restituisce il testo del blocco banca primaria con numero ordine."""
        Block = self.env['cf.doc.footer.block']
        bank_block = Block.search([
            ('block_type', '=', 'bank'),
            ('active', '=', True),
        ], order='sequence asc', limit=1)
        if not bank_block:
            return None
        note = bank_block.note or bank_block.name
        return note.replace('[N. Fattura / N. Ordine]', self.name or '')

    def _has_bank_note_line(self):
        """Controlla se esiste già una riga nota con coordinate bancarie."""
        for line in self.order_line:
            if line.display_type == 'line_note' and 'COORDINATE BANCARIE' in (line.name or ''):
                return True
        return False

    def _insert_bank_block(self):
        """Inserisce la riga coordinate bancarie se non già presente."""
        if self._has_bank_note_line():
            return
        note_text = self._get_bank_note_text()
        if not note_text:
            return
        max_seq = max((l.sequence for l in self.order_line), default=10)
        self.env['sale.order.line'].create({
            'order_id': self.id,
            'display_type': 'line_note',
            'name': note_text,
            'sequence': max_seq + 1,
        })

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            order._insert_bank_block()
        return orders

    def write(self, vals):
        result = super().write(vals)
        # Inserisce il blocco solo se non già presente
        for order in self:
            if order.state in ('draft', 'sent'):
                order._insert_bank_block()
        return result

    def action_insert_footer_blocks(self):
        """Inserimento manuale blocchi aggiuntivi."""
        self.ensure_one()
        SaleOrderLine = self.env['sale.order.line']
        Block = self.env['cf.doc.footer.block']
        max_seq = max((l.sequence for l in self.order_line), default=10)

        # Blocco payment_term dal documento
        if self.payment_term_id:
            pt_block = Block.search([
                ('block_type', '=', 'payment_term'),
                ('payment_term_id', '=', self.payment_term_id.id),
                ('active', '=', True),
            ], limit=1)
            if pt_block:
                note_text = pt_block.note or pt_block.name
                max_seq += 1
                SaleOrderLine.create({
                    'order_id': self.id,
                    'display_type': 'line_note',
                    'name': note_text,
                    'sequence': max_seq,
                })

        # Blocchi manuali selezionati
        for block in self.footer_block_ids.sorted('sequence'):
            if block.block_type == 'bank':
                note_text = (block.note or block.name).replace(
                    '[N. Fattura / N. Ordine]', self.name or '')
            elif block.block_type == 'note':
                note_text = block.note or block.name
            else:
                note_text = block.name
            max_seq += 1
            SaleOrderLine.create({
                'order_id': self.id,
                'display_type': 'line_note',
                'name': note_text,
                'sequence': max_seq,
            })

        return True

    def action_open_footer_blocks(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Blocchi Documento',
            'res_model': 'cf.doc.footer.block',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.footer_block_ids.ids)],
            'context': {'default_active': True},
            'target': 'current',
        }

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
