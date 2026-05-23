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
    cf_corrispettivi_note = fields.Char(
        string="Nota corrispettivi",
        copy=False,
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
