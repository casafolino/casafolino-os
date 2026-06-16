from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_cf_reverse_charge_register_and_send(self):
        """Post selected vendor bills when needed, then send the Italian EDI integration."""
        if not self:
            return False

        unsupported_moves = self.filtered(lambda move: move.move_type not in ("in_invoice", "in_refund"))
        if unsupported_moves:
            raise UserError(_(
                "La procedura reverse charge deve essere usata solo su fatture o note credito fornitore.\n\n"
                "Record non compatibili:\n%s"
            ) % self._cf_reverse_charge_format_moves(unsupported_moves))

        already_sent = self.filtered(lambda move: move.is_move_sent or move.l10n_it_edi_attachment_id)
        if already_sent:
            raise UserError(_(
                "Alcune integrazioni risultano gia inviate o hanno gia un XML EDI allegato.\n\n"
                "Controlla prima questi record:\n%s"
            ) % self._cf_reverse_charge_format_moves(already_sent))

        draft_moves = self.filtered(lambda move: move.state == "draft")
        if draft_moves:
            draft_moves.action_post()

        invalid_moves = self.filtered(lambda move: move.state != "posted" or not move.name or move.name == "/")
        if invalid_moves:
            raise UserError(_(
                "Prima dell'invio reverse charge ogni fattura deve essere registrata e avere un numero interno.\n\n"
                "Da correggere:\n%s"
            ) % self._cf_reverse_charge_format_moves(invalid_moves))

        for move in self:
            result = move.action_l10n_it_edi_send()
            if result:
                return result

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Reverse charge"),
                "message": _("Integrazioni reverse charge registrate e inviate correttamente."),
                "type": "success",
                "sticky": False,
            },
        }

    def _cf_reverse_charge_format_moves(self, moves, limit=10):
        lines = []
        for move in moves[:limit]:
            label = move.display_name or move.ref or str(move.id)
            lines.append("- %s (ID %s, stato: %s)" % (label, move.id, move.state))
        remaining = len(moves) - limit
        if remaining > 0:
            lines.append("- ... e altri %s record" % remaining)
        return "\n".join(lines)

