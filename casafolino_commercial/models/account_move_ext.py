from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class AccountMoveExt(models.Model):
    _inherit = 'account.move'

    footer_block_ids = fields.Many2many(
        'cf.doc.footer.block',
        'account_move_footer_block_rel',
        'move_id',
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
        Block = self.env['cf.doc.footer.block']

        blocks_to_insert = []

        # RIGA 1 — Termine di pagamento della fattura
        if self.invoice_payment_term_id:
            pt_block = Block.search([
                ('block_type', '=', 'payment_term'),
                ('payment_term_id', '=', self.invoice_payment_term_id.id),
                ('active', '=', True),
            ], limit=1)
            if pt_block:
                blocks_to_insert.append(pt_block)

        # RIGA 2 — Banca primaria
        bank_block = Block.search([
            ('block_type', '=', 'bank'),
            ('active', '=', True),
        ], order='sequence asc', limit=1)
        if bank_block:
            blocks_to_insert.append(bank_block)

        # RIGHE SUCCESSIVE — blocchi manuali
        already_ids = [b.id for b in blocks_to_insert]
        for block in self.footer_block_ids.sorted('sequence'):
            if block.id not in already_ids:
                blocks_to_insert.append(block)

        # Inserisci come righe nota sulla fattura
        # Su account.move le righe nota usano account.move.line
        for block in blocks_to_insert:
            # Per le banche sostituisci [N. Fattura] con il numero reale
            if block.block_type == 'note' or block.block_type == 'bank':
                note_text = (block.note or block.name).replace(
                    '[N. Fattura / N. Ordine]',
                    self.name or '[N. Fattura]'
                )
            elif block.block_type == 'payment_term' and block.payment_term_id:
                pt = block.payment_term_id
                parts = [f"Condizioni di pagamento: {pt.name}"]
                if pt.note:
                    parts.append(pt.note)
                note_text = "\n".join(parts)
            else:
                lines = block.get_display_lines()
                text_parts = []
                for label, value in lines:
                    if label:
                        text_parts.append(f"{label}: {value}")
                    else:
                        text_parts.append(value)
                note_text = "\n".join(text_parts) if text_parts else block.name

            self.env['account.move.line'].create({
                'move_id': self.id,
                'display_type': 'line_note',
                'name': note_text,
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
