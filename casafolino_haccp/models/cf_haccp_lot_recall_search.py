# -*- coding: utf-8 -*-
from html import escape

from odoo import api, fields, models


class CfHaccpLotRecallSearch(models.Model):
    _name = "cf.haccp.lot.recall.search"
    _description = "Ricerca lotti e ritiro HACCP"
    _inherit = ["mail.thread"]
    _order = "write_date desc, id desc"

    name = fields.Char(
        string="Ricerca",
        compute="_compute_name",
        store=True,
    )
    query = fields.Char(
        string="Barcode, SKU, prodotto o lotto",
        required=True,
        tracking=True,
    )
    product_ids = fields.Many2many(
        "product.product",
        string="Prodotti associati",
        readonly=True,
    )
    lot_ids = fields.Many2many(
        "stock.lot",
        string="Lotti trovati",
        readonly=True,
    )
    trace_ids = fields.Many2many(
        "cf.haccp.tracciabilita",
        string="Cronostorie generate",
        readonly=True,
    )
    result_html = fields.Html(
        string="Risultato ricerca",
        sanitize=False,
        readonly=True,
    )
    product_count = fields.Integer(
        string="Prodotti",
        compute="_compute_counts",
    )
    lot_count = fields.Integer(
        string="Lotti",
        compute="_compute_counts",
    )
    trace_count = fields.Integer(
        string="Cronostorie",
        compute="_compute_counts",
    )

    @api.depends("query")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.query or "Ricerca lotto"

    @api.depends("product_ids", "lot_ids", "trace_ids")
    def _compute_counts(self):
        for rec in self:
            rec.product_count = len(rec.product_ids)
            rec.lot_count = len(rec.lot_ids)
            rec.trace_count = len(rec.trace_ids)

    def action_search_lots(self):
        for rec in self:
            rec._search_lots()

    def _search_lots(self):
        self.ensure_one()
        query = (self.query or "").strip()
        Product = self.env["product.product"].sudo()
        Lot = self.env["stock.lot"].sudo()
        Trace = self.env["cf.haccp.tracciabilita"].sudo()
        MoveLine = self.env["stock.move.line"].sudo()
        Production = self.env["mrp.production"].sudo()

        if not query:
            self.write({
                "product_ids": [(5, 0, 0)],
                "lot_ids": [(5, 0, 0)],
                "trace_ids": [(5, 0, 0)],
                "result_html": self._empty_html("Inserisci barcode, SKU, nome prodotto o lotto."),
            })
            return

        products = Product.search([
            "|", "|",
            ("barcode", "ilike", query),
            ("default_code", "ilike", query),
            ("name", "ilike", query),
        ], limit=80)
        lots = Lot.search([
            "|", "|",
            ("name", "ilike", query),
            ("ref", "ilike", query),
            ("product_id", "in", products.ids or [0]),
        ], limit=300)

        if not lots and products:
            lots = Lot.search([("product_id", "in", products.ids)], limit=300)

        raw_consumption_lines = MoveLine.search([("lot_id", "in", lots.ids)])
        consumed_productions = Production.search([
            ("move_raw_ids.move_line_ids.lot_id", "in", lots.ids or [0])
        ])
        produced_lots = consumed_productions.mapped("lot_producing_id")
        all_lots = lots | produced_lots
        all_products = products | lots.mapped("product_id") | produced_lots.mapped("product_id")

        traces = Trace.browse()
        for lot in all_lots:
            trace = Trace.search([("lot_id", "=", lot.id)], limit=1)
            if not trace:
                trace = Trace.create({"lot_id": lot.id, "lotto_pf": lot.name})
            trace.action_build_timeline_from_lot()
            traces |= trace

        self.write({
            "product_ids": [(6, 0, all_products.ids)],
            "lot_ids": [(6, 0, all_lots.ids)],
            "trace_ids": [(6, 0, traces.ids)],
            "result_html": self._render_results(
                query, all_products, lots, produced_lots, traces, raw_consumption_lines
            ),
        })
        self.message_post(body="Ricerca lotti eseguita per: %s" % escape(query))

    def _render_results(self, query, products, input_lots, produced_lots, traces, move_lines):
        if not products and not input_lots and not produced_lots:
            return self._empty_html("Nessun prodotto o lotto trovato per: %s" % escape(query))

        product_cards = []
        for product in products[:80]:
            lots = (input_lots | produced_lots).filtered(lambda lot: lot.product_id == product)
            lot_links = "".join(self._lot_chip(lot) for lot in lots[:80])
            product_cards.append(
                "<div class='cf-recall-card'>"
                "<div><strong>%s</strong><small>SKU %s · Barcode %s</small></div>"
                "<div class='cf-recall-chips'>%s</div>"
                "</div>"
                % (
                    escape(product.display_name or ""),
                    escape(product.default_code or "-"),
                    escape(product.barcode or "-"),
                    lot_links or "<span class='cf-recall-muted'>Nessun lotto collegato</span>",
                )
            )

        raw_sections = []
        for lot in input_lots[:120]:
            productions = self.env["mrp.production"].sudo().search([
                ("move_raw_ids.move_line_ids.lot_id", "=", lot.id)
            ])
            sale_pickings = self._sale_pickings_for_productions(productions)
            if not productions and not sale_pickings:
                continue
            raw_sections.append(
                "<div class='cf-recall-card cf-recall-card-warn'>"
                "<div><strong>Materia prima %s</strong><small>%s</small></div>"
                "<div class='cf-recall-block'><b>Prodotti finiti generati</b>%s</div>"
                "<div class='cf-recall-block'><b>Documenti vendita collegati</b>%s</div>"
                "</div>"
                % (
                    escape(lot.name or ""),
                    escape(lot.product_id.display_name or ""),
                    self._record_links(productions, "mrp.production") or "<span class='cf-recall-muted'>Nessuna produzione</span>",
                    self._record_links(sale_pickings, "stock.picking") or "<span class='cf-recall-muted'>Nessuna consegna cliente</span>",
                )
            )

        return (
            "<div class='cf-recall-result'>"
            "<h3>Ricerca ritiro: %s</h3>"
            "<div class='cf-recall-summary'>"
            "<span>%s prodotti</span><span>%s lotti Odoo</span><span>%s cronostorie</span>"
            "</div>"
            "<h4>Prodotti e lotti associati</h4>%s"
            "<h4>Materia prima → prodotti finiti → vendite</h4>%s"
            "</div>"
            % (
                escape(query),
                len(products),
                len(input_lots | produced_lots),
                len(traces),
                "".join(product_cards) or self._empty_inline("Nessun prodotto associato"),
                "".join(raw_sections) or self._empty_inline("Nessuna relazione materia prima → prodotto finito trovata"),
            )
        )

    def _sale_pickings_for_productions(self, productions):
        produced_lots = productions.mapped("lot_producing_id")
        if not produced_lots:
            return self.env["stock.picking"].browse()
        lines = self.env["stock.move.line"].sudo().search([
            ("lot_id", "in", produced_lots.ids),
            ("picking_id.picking_type_id.code", "=", "outgoing"),
        ])
        return lines.mapped("picking_id")

    def _lot_chip(self, lot):
        trace = self.env["cf.haccp.tracciabilita"].sudo().search([("lot_id", "=", lot.id)], limit=1)
        href = self._record_url("cf.haccp.tracciabilita", trace.id) if trace else "#"
        return (
            "<a class='cf-recall-chip' href='%s'>%s</a>"
            % (escape(href), escape(lot.name or "Lotto"))
        )

    def _record_links(self, records, model):
        links = []
        for record in records[:80]:
            links.append(
                "<a class='cf-recall-link' href='%s'>%s</a>"
                % (escape(self._record_url(model, record.id)), escape(record.display_name or record.name or str(record.id)))
            )
        return "".join(links)

    def _record_url(self, model, record_id):
        return "/odoo/%s/%s" % (model, record_id)

    def _empty_html(self, message):
        return "<div class='cf-recall-empty'>%s</div>" % escape(message)

    def _empty_inline(self, message):
        return "<div class='cf-recall-empty-inline'>%s</div>" % escape(message)

    def action_open_products(self):
        return self._open_records("product.product", self.product_ids, "Prodotti associati")

    def action_open_lots(self):
        return self._open_records("stock.lot", self.lot_ids, "Lotti associati")

    def action_open_traces(self):
        return self._open_records("cf.haccp.tracciabilita", self.trace_ids, "Cronostorie lotto")

    def _open_records(self, model, records, name):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "list,form",
            "domain": [("id", "in", records.ids)],
            "target": "current",
        }
