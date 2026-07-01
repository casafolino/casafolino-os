from odoo import api, fields, models


class FancyFoodEvent(models.Model):
    _name = "casafolino.fancyfood.event"
    _description = "Fancy Food NY 2026 — Engagement Event"
    _order = "create_date desc"

    partner_id = fields.Many2one(
        "res.partner", string="Contatto", required=True,
        ondelete="cascade", index=True,
    )
    event_type = fields.Selection(
        [
            ("open", "Apertura mail"),
            ("click", "Click catalogo"),
            ("logo", "Load logo firma"),
        ],
        string="Tipo evento", required=True, index=True,
    )
    meta = fields.Char(string="Dettaglio")

    @api.depends("partner_id.display_name", "event_type", "create_date")
    def _compute_display_name(self):
        labels = dict(self._fields["event_type"].selection)
        for rec in self:
            rec.display_name = "%s — %s" % (
                rec.partner_id.display_name or "?",
                labels.get(rec.event_type, rec.event_type or ""),
            )
