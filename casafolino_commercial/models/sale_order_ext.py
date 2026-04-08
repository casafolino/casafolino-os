from odoo import models, fields, _
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

    def action_insert_footer_blocks(self):
        self.ensure_one()
        SaleOrderLine = self.env['sale.order.line']
        Block = self.env['cf.doc.footer.block']
        max_seq = max((l.sequence for l in self.order_line), default=10)

        blocks_to_insert = []

        # RIGA 1 — Termine di pagamento del documento
        if self.payment_term_id:
            _logger.info("CF Footer: payment_term_id = %s (ID %s)", 
                        self.payment_term_id.name, self.payment_term_id.id)
            pt_block = Block.search([
                ('block_type', '=', 'payment_term'),
                ('payment_term_id', '=', self.payment_term_id.id),
                ('active', '=', True),
            ], limit=1)
            _logger.info("CF Footer: blocco trovato = %s", pt_block)
            if pt_block:
                blocks_to_insert.append(pt_block)

        # RIGA 2 — Banca primaria (sequence più bassa)
        bank_block = Block.search([
            ('block_type', '=', 'bank'),
            ('active', '=', True),
        ], order='sequence asc', limit=1)
        if bank_block:
            blocks_to_insert.append(bank_block)

        # RIGHE SUCCESSIVE — blocchi manuali selezionati (escludi già inseriti)
        already_ids = [b.id for b in blocks_to_insert]
        for block in self.footer_block_ids.sorted('sequence'):
            if block.id not in already_ids:
                blocks_to_insert.append(block)

        _logger.info("CF Footer: blocchi da inserire = %s", 
                    [(b.name, b.block_type) for b in blocks_to_insert])

        # Inserisci come righe nota
        for block in blocks_to_insert:
            lines = block.get_display_lines()
            if not lines:
                # Fallback: usa il nome del blocco come nota
                note_text = block.name
            else:
                text_parts = []
                for label, value in lines:
                    if label:
                        text_parts.append(f"{label}: {value}")
                    else:
                        text_parts.append(value)
                note_text = "\n".join(text_parts)

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
