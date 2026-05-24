from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    cf_corrispettivi_status = fields.Selection(
        [
            ("to_review", "Da gestire"),
            ("included", "Nei corrispettivi"),
            ("invoice_required", "Richiede fattura"),
            ("excluded", "Escluso"),
        ],
        string="Gestione corrispettivi",
        default="to_review",
        copy=False,
        tracking=True,
    )
    cf_corrispettivi_channel = fields.Selection(
        [
            ("website", "Sito"),
            ("amazon", "Amazon"),
            ("marketplace", "Marketplace"),
            ("manual", "Manuale"),
            ("other", "Altro"),
        ],
        string="Canale corrispettivi",
        copy=False,
    )
    cf_corrispettivi_date = fields.Date(
        string="Data corrispettivi",
        copy=False,
        help="Data con cui l'ordine e' stato incluso nel riepilogo corrispettivi.",
    )
    cf_corrispettivi_user_id = fields.Many2one(
        "res.users",
        string="Gestito da",
        copy=False,
        readonly=True,
    )
    cf_corrispettivi_move_id = fields.Many2one(
        "account.move",
        string="Movimento corrispettivi",
        copy=False,
        readonly=True,
        domain="[('move_type','=','out_receipt')]",
    )
    cf_corrispettivi_note = fields.Char(
        string="Nota corrispettivi",
        copy=False,
    )

    def action_cf_create_corrispettivi_receipt(self):
        self._cf_validate_corrispettivi_selection()
        journal = self._cf_get_corrispettivi_journal()
        created_moves = self.env["account.move"]
        today = fields.Date.context_today(self)

        for order in self:
            receipt = self.env["account.move"].create(order._cf_prepare_corrispettivi_move_vals(journal))
            receipt.action_post()
            order.write({
                "cf_corrispettivi_status": "included",
                "cf_corrispettivi_channel": order.cf_corrispettivi_channel or order._cf_guess_corrispettivi_channel(),
                "cf_corrispettivi_date": order.cf_corrispettivi_date or fields.Date.to_date(order.date_order) or today,
                "cf_corrispettivi_user_id": self.env.user.id,
                "cf_corrispettivi_move_id": receipt.id,
            })
            created_moves |= receipt

        if len(created_moves) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Corrispettivo"),
                "res_model": "account.move",
                "res_id": created_moves.id,
                "view_mode": "form",
                "target": "current",
            }

        return self._cf_corrispettivi_notification(
            _("Corrispettivi"),
            _("%s corrispettivi creati nel registro CORR.") % len(created_moves),
            "success",
        )

    def action_cf_mark_corrispettivi_included(self):
        self._cf_validate_corrispettivi_selection()
        today = fields.Date.context_today(self)
        for order in self:
            order.write({
                "cf_corrispettivi_status": "included",
                "cf_corrispettivi_channel": order.cf_corrispettivi_channel or order._cf_guess_corrispettivi_channel(),
                "cf_corrispettivi_date": order.cf_corrispettivi_date or today,
                "cf_corrispettivi_user_id": self.env.user.id,
            })
        return self._cf_corrispettivi_notification(
            _("Corrispettivi"),
            _("%s ordini segnati come inclusi nei corrispettivi.") % len(self),
            "success",
        )

    def action_cf_mark_invoice_required(self):
        self._cf_validate_corrispettivi_selection(allow_draft=True)
        self.write({
            "cf_corrispettivi_status": "invoice_required",
            "cf_corrispettivi_user_id": self.env.user.id,
        })
        return self._cf_corrispettivi_notification(
            _("Corrispettivi"),
            _("%s ordini segnati come da fatturare separatamente.") % len(self),
            "warning",
        )

    def action_cf_mark_corrispettivi_excluded(self):
        self._cf_validate_corrispettivi_selection(allow_draft=True)
        self.write({
            "cf_corrispettivi_status": "excluded",
            "cf_corrispettivi_user_id": self.env.user.id,
        })
        return self._cf_corrispettivi_notification(
            _("Corrispettivi"),
            _("%s ordini esclusi dalla procedura corrispettivi.") % len(self),
            "info",
        )

    def action_cf_reset_corrispettivi_status(self):
        self.write({
            "cf_corrispettivi_status": "to_review",
            "cf_corrispettivi_date": False,
            "cf_corrispettivi_user_id": False,
            "cf_corrispettivi_move_id": False,
        })
        return self._cf_corrispettivi_notification(
            _("Corrispettivi"),
            _("%s ordini riportati in 'Da gestire'.") % len(self),
            "info",
        )

    def _cf_validate_corrispettivi_selection(self, allow_draft=False):
        if not self:
            return
        invalid_states = self.filtered(lambda order: order.state not in ("sale", "done") and not allow_draft)
        if invalid_states:
            raise UserError(_(
                "La procedura corrispettivi si usa sugli ordini confermati.\n\n"
                "Da controllare:\n%s"
            ) % self._cf_format_orders(invalid_states))
        posted_invoices = self.filtered(lambda order: order.invoice_ids.filtered(lambda move: move.state == "posted"))
        if posted_invoices:
            raise UserError(_(
                "Alcuni ordini hanno gia fatture registrate: non vanno inseriti nei corrispettivi senza verifica.\n\n"
                "Da controllare:\n%s"
            ) % self._cf_format_orders(posted_invoices))
        linked_receipts = self.filtered(lambda order: order.cf_corrispettivi_move_id and order.cf_corrispettivi_move_id.state == "posted")
        if linked_receipts:
            raise UserError(_(
                "Alcuni ordini hanno gia un corrispettivo collegato.\n\n"
                "Da controllare:\n%s"
            ) % self._cf_format_orders(linked_receipts))
        empty_orders = self.filtered(lambda order: not order._cf_get_corrispettivi_order_lines())
        if empty_orders and not allow_draft:
            raise UserError(_(
                "Alcuni ordini non hanno righe fatturabili da portare nei corrispettivi.\n\n"
                "Da controllare:\n%s"
            ) % self._cf_format_orders(empty_orders))

    def _cf_get_corrispettivi_journal(self):
        journal = self.env["account.journal"].search([
            ("code", "=", "CORR"),
            ("type", "=", "sale"),
            ("active", "=", True),
        ], limit=1)
        if not journal:
            raise UserError(_("Non trovo il registro fiscale 'CORR' / Corrispettivi Clienti Italia."))
        return journal

    def _cf_prepare_corrispettivi_move_vals(self, journal):
        self.ensure_one()
        invoice_date = fields.Date.to_date(self.date_order) or fields.Date.context_today(self)
        invoice_lines = []
        for line in self._cf_get_corrispettivi_order_lines():
            account = line.product_id.property_account_income_id or line.product_id.categ_id.property_account_income_categ_id
            if self.fiscal_position_id and account:
                account = self.fiscal_position_id.map_account(account)
            if not account:
                raise UserError(_(
                    "Manca il conto di ricavo sul prodotto '%s' nell'ordine %s."
                ) % (line.product_id.display_name, self.name))
            taxes = line.tax_id
            if self.fiscal_position_id:
                taxes = self.fiscal_position_id.map_tax(taxes)
            quantity = line.qty_to_invoice or line.product_uom_qty
            invoice_lines.append((0, 0, {
                "name": line.name,
                "product_id": line.product_id.id,
                "product_uom_id": line.product_uom.id,
                "quantity": quantity,
                "price_unit": line.price_unit,
                "discount": line.discount,
                "account_id": account.id,
                "tax_ids": [(6, 0, taxes.ids)],
                "sale_line_ids": [(6, 0, [line.id])],
            }))
        return {
            "move_type": "out_receipt",
            "journal_id": journal.id,
            "partner_id": self.partner_invoice_id.id or self.partner_id.id,
            "invoice_date": invoice_date,
            "date": invoice_date,
            "invoice_origin": self.name,
            "invoice_user_id": self.user_id.id or self.env.user.id,
            "team_id": self.team_id.id,
            "currency_id": self.currency_id.id,
            "invoice_payment_term_id": self.payment_term_id.id,
            "invoice_line_ids": invoice_lines,
            "ref": self.client_order_ref or self.name,
        }

    def _cf_get_corrispettivi_order_lines(self):
        self.ensure_one()
        return self.order_line.filtered(
            lambda line: not line.display_type
            and line.product_id
            and (line.qty_to_invoice or line.product_uom_qty)
        )

    def _cf_guess_corrispettivi_channel(self):
        self.ensure_one()
        source = self.source_id.name if "source_id" in self._fields and self.source_id else ""
        medium = self.medium_id.name if "medium_id" in self._fields and self.medium_id else ""
        campaign = self.campaign_id.name if "campaign_id" in self._fields and self.campaign_id else ""
        text = " ".join(filter(None, [
            self.name,
            self.client_order_ref,
            self.origin,
            source,
            medium,
            campaign,
            self.team_id.name if self.team_id else "",
        ])).lower()
        if "amazon" in text:
            return "amazon"
        if getattr(self, "website_id", False):
            return "website"
        if "shopify" in text or "marketplace" in text:
            return "marketplace"
        return "manual"

    def _cf_format_orders(self, orders, limit=12):
        lines = []
        for order in orders[:limit]:
            lines.append("- %s, %s, %s" % (order.name, order.partner_id.display_name, order.state))
        remaining = len(orders) - limit
        if remaining > 0:
            lines.append("- ... e altri %s ordini" % remaining)
        return "\n".join(lines)

    def _cf_corrispettivi_notification(self, title, message, notification_type):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notification_type,
                "sticky": False,
            },
        }
