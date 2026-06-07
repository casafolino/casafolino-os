# -*- coding: utf-8 -*-
from html import escape

from odoo import models, fields, api
from odoo.exceptions import UserError


class CfHaccpTracciabilita(models.Model):
    _name = "cf.haccp.tracciabilita"
    _description = "Scheda Tracciabilità HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"
    _rec_name = "lotto_pf"

    lot_id = fields.Many2one(
        "stock.lot",
        string="Lotto Odoo",
        tracking=True,
        help="Lotto ufficiale Odoo da cui ricostruire la cronostoria.",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Prodotto",
        related="lot_id.product_id",
        store=True,
        readonly=True,
    )
    lotto_mp = fields.Char(string="Lotto Materia Prima")
    lotto_pf = fields.Char(string="Lotto Prodotto Finito", required=True)
    production_id = fields.Many2one("mrp.production",
                                     string="Ordine di Produzione")
    partner_ids = fields.Many2many("res.partner", string="Clienti / Destinatari")
    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    note = fields.Text(string="Note")
    timeline_html = fields.Html(
        string="Cronostoria Lotto",
        sanitize=False,
        readonly=True,
    )
    move_line_count = fields.Integer(
        string="Movimenti lotto",
        compute="_compute_trace_counts",
    )
    picking_count = fields.Integer(
        string="Trasferimenti",
        compute="_compute_trace_counts",
    )
    production_count = fields.Integer(
        string="Produzioni",
        compute="_compute_trace_counts",
    )

    @api.depends("lot_id")
    def _compute_trace_counts(self):
        MoveLine = self.env["stock.move.line"].sudo()
        Production = self.env["mrp.production"].sudo()
        for rec in self:
            if not rec.lot_id:
                rec.move_line_count = 0
                rec.picking_count = 0
                rec.production_count = 0
                continue
            move_lines = MoveLine.search([("lot_id", "=", rec.lot_id.id)])
            rec.move_line_count = len(move_lines)
            rec.picking_count = len(move_lines.mapped("picking_id"))
            rec.production_count = Production.search_count(
                [
                    "|",
                    ("lot_producing_id", "=", rec.lot_id.id),
                    ("move_raw_ids.move_line_ids.lot_id", "=", rec.lot_id.id),
                ]
            )

    @api.onchange("lot_id")
    def _onchange_lot_id(self):
        for rec in self:
            if rec.lot_id:
                rec.lotto_pf = rec.lot_id.name
                if not rec.date:
                    rec.date = fields.Date.today()

    def action_build_timeline_from_lot(self):
        for rec in self:
            rec._build_timeline_from_lot()

    def _build_timeline_from_lot(self):
        self.ensure_one()
        if not self.lot_id:
            raise UserError("Seleziona prima un lotto Odoo.")

        MoveLine = self.env["stock.move.line"].sudo()
        Production = self.env["mrp.production"].sudo()
        Quarantine = self.env["cf.haccp.quarantine"].sudo()
        Nc = self.env["cf.haccp.nc"].sudo()

        move_lines = MoveLine.search(
            [("lot_id", "=", self.lot_id.id)],
            order="date asc, id asc",
        )
        pickings = move_lines.mapped("picking_id")
        produced = Production.search([("lot_producing_id", "=", self.lot_id.id)])
        consumed = Production.search(
            [("move_raw_ids.move_line_ids.lot_id", "=", self.lot_id.id)]
        )
        productions = produced | consumed
        quarantines = Quarantine.search([("lot_id", "=", self.lot_id.id)])
        ncs = Nc.search([("lot_id", "=", self.lot_id.id)])
        partners = pickings.mapped("partner_id")

        self.write(
            {
                "lotto_pf": self.lot_id.name,
                "lotto_mp": ", ".join(
                    sorted(
                        set(
                            consumed.mapped("move_raw_ids.move_line_ids.lot_id.name")
                        )
                    )
                ),
                "production_id": produced[:1].id or consumed[:1].id or False,
                "partner_ids": [(6, 0, partners.ids)],
                "timeline_html": self._render_lot_timeline(
                    move_lines, produced, consumed, quarantines, ncs
                ),
            }
        )
        self.message_post(
            body="Cronostoria lotto ricostruita da Odoo per %s." % escape(self.lot_id.name)
        )

    def _render_lot_timeline(self, move_lines, produced, consumed, quarantines, ncs):
        self.ensure_one()
        rows = []

        for production in produced:
            rows.append(
                (
                    production.date_finished or production.date_start or production.create_date,
                    "Produzione",
                    production.display_name,
                    "Prodotto finito generato",
                    production.state,
                    "mrp.production",
                    production.id,
                )
            )
        for production in consumed:
            rows.append(
                (
                    production.date_start or production.create_date,
                    "Consumo in produzione",
                    production.display_name,
                    "Lotto usato come materia prima",
                    production.state,
                    "mrp.production",
                    production.id,
                )
            )
        for line in move_lines:
            picking = line.picking_id
            partner = picking.partner_id.display_name if picking and picking.partner_id else ""
            rows.append(
                (
                    line.date,
                    self._picking_label(picking),
                    picking.display_name if picking else line.reference or line.display_name,
                    "%s → %s%s" % (
                        line.location_id.display_name or "",
                        line.location_dest_id.display_name or "",
                        (" · " + partner) if partner else "",
                    ),
                    line.state,
                    "stock.picking" if picking else "stock.move.line",
                    picking.id if picking else line.id,
                )
            )
        for quarantine in quarantines:
            rows.append(
                (
                    quarantine.create_date,
                    "Quarantena",
                    quarantine.display_name,
                    quarantine.state,
                    "attenzione",
                    "cf.haccp.quarantine",
                    quarantine.id,
                )
            )
        for nc in ncs:
            rows.append(
                (
                    nc.create_date,
                    "Non conformita",
                    nc.display_name,
                    nc.state,
                    nc.severity if "severity" in nc._fields else "",
                    "cf.haccp.nc",
                    nc.id,
                )
            )

        rows = sorted(rows, key=lambda row: row[0] or fields.Datetime.now())
        if not rows:
            return (
                "<div class='alert alert-warning mb-0'>"
                "Nessun movimento trovato per questo lotto Odoo."
                "</div>"
            )

        items = []
        for date, kind, title, detail, status, model, record_id in rows:
            date_text = fields.Datetime.to_string(date) if date else ""
            href = self._record_url(model, record_id)
            items.append(
                "<li class='cf-lot-timeline-item'>"
                "<div class='cf-lot-timeline-date'>%s</div>"
                "<div class='cf-lot-timeline-card'>"
                "<strong>%s</strong>"
                "<a class='cf-lot-timeline-link' href='%s'>%s</a>"
                "<small>%s</small>"
                "<em>%s</em>"
                "</div>"
                "</li>"
                % (
                    escape(date_text),
                    escape(kind or ""),
                    escape(href),
                    escape(title or ""),
                    escape(detail or ""),
                    escape(status or ""),
                )
            )
        return "<ol class='cf-lot-timeline'>%s</ol>" % "".join(items)

    def _record_url(self, model, record_id):
        return "/odoo/%s/%s" % (model, record_id)

    def _picking_label(self, picking):
        if not picking:
            return "Movimento"
        code = picking.picking_type_id.code
        if code == "incoming":
            return "Ricezione"
        if code == "outgoing":
            return "Consegna cliente"
        if code == "internal":
            return "Movimento interno"
        return "Trasferimento"

    def action_open_lot(self):
        self.ensure_one()
        if not self.lot_id:
            raise UserError("Seleziona prima un lotto Odoo.")
        return {
            "type": "ir.actions.act_window",
            "name": "Lotto Odoo",
            "res_model": "stock.lot",
            "res_id": self.lot_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_lot_moves(self):
        self.ensure_one()
        if not self.lot_id:
            raise UserError("Seleziona prima un lotto Odoo.")
        return {
            "type": "ir.actions.act_window",
            "name": "Movimenti del lotto",
            "res_model": "stock.move.line",
            "view_mode": "list,form",
            "domain": [("lot_id", "=", self.lot_id.id)],
            "target": "current",
        }

    def action_open_lot_productions(self):
        self.ensure_one()
        if not self.lot_id:
            raise UserError("Seleziona prima un lotto Odoo.")
        return {
            "type": "ir.actions.act_window",
            "name": "Produzioni del lotto",
            "res_model": "mrp.production",
            "view_mode": "list,form",
            "domain": [
                "|",
                ("lot_producing_id", "=", self.lot_id.id),
                ("move_raw_ids.move_line_ids.lot_id", "=", self.lot_id.id),
            ],
            "target": "current",
        }
