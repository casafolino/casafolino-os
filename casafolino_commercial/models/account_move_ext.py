from decimal import Decimal, InvalidOperation

from odoo import api, models, fields, _
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

    def _cf_resolve_archived_bank(self):
        """Resolve archived partner_bank_id on this move."""
        self.ensure_one()
        bank = self.partner_bank_id
        if not bank or bank.active:
            return {'action': 'noop', 'bank_id': bank.id if bank else False, 'old_bank_id': None}

        old_bank_id = bank.id
        sanitized = bank.sanitized_acc_number

        # Try to find an active bank with the same IBAN on the partner
        if sanitized and self.partner_id:
            active_bank = self.env['res.partner.bank'].search([
                ('partner_id', '=', self.partner_id.id),
                ('sanitized_acc_number', '=', sanitized),
                ('active', '=', True),
            ], limit=1)
            if active_bank:
                self.partner_bank_id = active_bank
                self.message_post(
                    body=_(
                        "Bank account riassegnato da archiviato (ID %(old)s) "
                        "a attivo (ID %(new)s), stesso IBAN %(iban)s.",
                        old=old_bank_id, new=active_bank.id, iban=sanitized,
                    ),
                )
                _logger.info("CF Bank Resilience: fattura %s — riassegnato bank %s → %s",
                             self.name, old_bank_id, active_bank.id)
                return {'action': 'reassigned', 'bank_id': active_bank.id, 'old_bank_id': old_bank_id}

        # No active duplicate found — reactivate the archived one
        bank.with_context(force_archive=True).write({'active': True})
        self.message_post(
            body=_(
                "Bank account riattivato automaticamente (ID %(bank)s, IBAN %(iban)s): "
                "era archiviato ma in uso su questa fattura.",
                bank=bank.id, iban=sanitized or 'N/A',
            ),
        )
        _logger.info("CF Bank Resilience: fattura %s — riattivato bank %s", self.name, bank.id)
        return {'action': 'unarchived', 'bank_id': bank.id, 'old_bank_id': old_bank_id}

    def action_post(self):
        """Before posting, auto-resolve archived partner bank accounts."""
        for move in self:
            if move.partner_bank_id and not move.partner_bank_id.active:
                move._cf_resolve_archived_bank()
        return super().action_post()

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


class AccountMoveLineExt(models.Model):
    _inherit = 'account.move.line'

    cf_vendor_bill_quantity_six_decimals = fields.Float(
        string='Quantita',
        compute='_compute_cf_vendor_bill_decimal_fields',
        inverse='_inverse_cf_vendor_bill_quantity_six_decimals',
        digits=(16, 6),
        readonly=False,
    )
    cf_vendor_bill_price_unit_six_decimals = fields.Float(
        string='Prezzo',
        compute='_compute_cf_vendor_bill_decimal_fields',
        inverse='_inverse_cf_vendor_bill_price_unit_six_decimals',
        digits=(16, 6),
        readonly=False,
    )
    cf_vendor_bill_discount_six_decimals = fields.Float(
        string='Sconto %',
        compute='_compute_cf_vendor_bill_decimal_fields',
        inverse='_inverse_cf_vendor_bill_discount_six_decimals',
        digits=(16, 6),
        readonly=False,
    )
    cf_price_subtotal_six_decimals = fields.Float(
        string='Imponibile',
        compute='_compute_cf_price_subtotal_six_decimals',
        digits=(16, 6),
        readonly=True,
    )

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_cf_vendor_bill_decimal_fields(self):
        for line in self:
            line.cf_vendor_bill_quantity_six_decimals = line.quantity
            line.cf_vendor_bill_price_unit_six_decimals = line.price_unit
            line.cf_vendor_bill_discount_six_decimals = line.discount

    @api.onchange(
        'cf_vendor_bill_quantity_six_decimals',
        'cf_vendor_bill_price_unit_six_decimals',
        'cf_vendor_bill_discount_six_decimals',
    )
    def _onchange_cf_vendor_bill_decimal_fields(self):
        for line in self:
            if line.move_id.move_type not in ('in_invoice', 'in_refund'):
                continue
            line.quantity = line.cf_vendor_bill_quantity_six_decimals
            line.price_unit = line.cf_vendor_bill_price_unit_six_decimals
            line.discount = line.cf_vendor_bill_discount_six_decimals
            line._compute_cf_price_subtotal_six_decimals()

    def _inverse_cf_vendor_bill_quantity_six_decimals(self):
        for line in self:
            line.quantity = line.cf_vendor_bill_quantity_six_decimals

    def _inverse_cf_vendor_bill_price_unit_six_decimals(self):
        for line in self:
            line.price_unit = line.cf_vendor_bill_price_unit_six_decimals

    def _inverse_cf_vendor_bill_discount_six_decimals(self):
        for line in self:
            line.discount = line.cf_vendor_bill_discount_six_decimals

    @api.depends('quantity', 'price_unit', 'discount', 'display_type')
    def _compute_cf_price_subtotal_six_decimals(self):
        for line in self:
            if line.display_type:
                line.cf_price_subtotal_six_decimals = 0.0
                continue
            try:
                quantity = Decimal(str(line.quantity or 0.0))
                price_unit = Decimal(str(line.price_unit or 0.0))
                discount = Decimal(str(line.discount or 0.0))
            except (InvalidOperation, ValueError):
                line.cf_price_subtotal_six_decimals = line.price_subtotal
                continue

            subtotal = quantity * price_unit * (Decimal("1.0") - (discount / Decimal("100.0")))
            subtotal = subtotal.quantize(Decimal("0.000001"))
            line.cf_price_subtotal_six_decimals = float(subtotal)
