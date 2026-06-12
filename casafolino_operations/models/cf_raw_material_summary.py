# -*- coding: utf-8 -*-
from collections import defaultdict
from html import escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CfRawMaterialSummaryWizard(models.TransientModel):
    _name = "cf.raw.material.summary.wizard"
    _description = "Resoconto Materie Prime Produzione"

    production_ids = fields.Many2many(
        "mrp.production",
        string="Ordini di Produzione",
        readonly=True,
    )
    sale_order_ids = fields.Many2many(
        "sale.order",
        string="Ordini di Vendita",
        readonly=True,
    )
    line_ids = fields.One2many(
        "cf.raw.material.summary.line",
        "wizard_id",
        string="Materie Prime",
        readonly=True,
    )
    note = fields.Text(readonly=True)
    summary_html = fields.Html(
        string="Sintesi",
        compute="_compute_summary_html",
        sanitize=False,
        readonly=True,
    )
    sale_order_count = fields.Integer(compute="_compute_summary_counts")
    production_count = fields.Integer(compute="_compute_summary_counts")
    material_count = fields.Integer(compute="_compute_summary_counts")
    purchase_line_count = fields.Integer(compute="_compute_summary_counts")
    available_line_count = fields.Integer(compute="_compute_summary_counts")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []

        productions = self.env["mrp.production"]
        sale_orders = self.env["sale.order"]
        if active_model == "mrp.production":
            productions = self.env["mrp.production"].browse(active_ids).exists()
        elif active_model == "sale.order":
            sale_orders = self.env["sale.order"].browse(active_ids).exists()
            productions = self._find_productions_from_sale_orders(sale_orders)

        if not productions:
            raise UserError(_(
                "Nessun ordine di produzione trovato. Se parti dagli ordini di "
                "vendita, verifica che gli MO siano gia stati creati."
            ))

        values.update({
            "production_ids": [(6, 0, productions.ids)],
            "line_ids": [(0, 0, line) for line in self._prepare_summary_lines(productions)],
            "note": self._prepare_note(productions),
        })
        if sale_orders:
            values["sale_order_ids"] = [(6, 0, sale_orders.ids)]
        return values

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref(
            "casafolino_operations.report_cf_raw_material_summary"
        ).report_action(self)

    @api.depends("sale_order_ids", "production_ids", "line_ids", "line_ids.need_purchase")
    def _compute_summary_counts(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_ids)
            rec.production_count = len(rec.production_ids)
            rec.material_count = len(rec.line_ids)
            rec.purchase_line_count = len(rec.line_ids.filtered("need_purchase"))
            rec.available_line_count = rec.material_count - rec.purchase_line_count

    @api.depends(
        "sale_order_ids",
        "production_ids",
        "line_ids",
        "line_ids.need_purchase",
        "line_ids.purchase_qty",
    )
    def _compute_summary_html(self):
        for rec in self:
            cards = [
                ("Ordini vendita", rec.sale_order_count),
                ("Ordini produzione", rec.production_count),
                ("Materie prime", rec.material_count),
                ("Da acquistare", rec.purchase_line_count),
                ("Gia coperte", rec.available_line_count),
            ]
            rec.summary_html = "".join([
                '<div class="d-flex flex-wrap gap-2 mb-3">',
                *[
                    (
                        '<div class="border rounded p-2 bg-light" style="min-width:120px;">'
                        f'<div class="text-muted" style="font-size:12px;">{escape(label)}</div>'
                        f'<div class="fw-bold" style="font-size:22px; line-height:1.1;">{value}</div>'
                        '</div>'
                    )
                    for label, value in cards
                ],
                '</div>',
            ])

    @api.model
    def _find_productions_from_sale_orders(self, sale_orders):
        if not sale_orders:
            return self.env["mrp.production"]

        Production = self.env["mrp.production"]
        domain = [("state", "!=", "cancel")]
        parts = []

        group_ids = sale_orders.mapped("procurement_group_id").ids
        if group_ids and "procurement_group_id" in Production._fields:
            parts.append(("procurement_group_id", "in", group_ids))

        if "sale_line_id" in Production._fields:
            sale_line_ids = sale_orders.mapped("order_line").ids
            if sale_line_ids:
                parts.append(("sale_line_id", "in", sale_line_ids))

        order_names = [name for name in sale_orders.mapped("name") if name]
        if order_names:
            parts.append(("origin", "in", order_names))
            for name in order_names:
                parts.append(("origin", "ilike", name))

        if not parts:
            return Production

        return Production.search(domain + self._or_domain(parts))

    @api.model
    def _or_domain(self, clauses):
        if len(clauses) == 1:
            return [clauses[0]]
        return ["|"] * (len(clauses) - 1) + clauses

    @api.model
    def _prepare_summary_lines(self, productions):
        totals = defaultdict(lambda: {
            "required_qty": 0.0,
            "reserved_qty": 0.0,
            "production_names": set(),
            "source_count": 0,
        })

        for production in productions:
            entries = self._production_component_entries(production)
            for product, qty, uom, reserved_qty in entries:
                key = (product.id, uom.id)
                totals[key]["product_id"] = product.id
                totals[key]["product_uom_id"] = uom.id
                totals[key]["required_qty"] += qty
                totals[key]["reserved_qty"] += reserved_qty
                totals[key]["production_names"].add(production.name or production.display_name)
                totals[key]["source_count"] += 1

        lines = []
        Product = self.env["product.product"]
        Uom = self.env["uom.uom"]
        for values in totals.values():
            product = Product.browse(values["product_id"])
            uom = Uom.browse(values["product_uom_id"])
            available_qty = product.uom_id._compute_quantity(product.qty_available, uom)
            purchase_qty = max(values["required_qty"] - available_qty, 0.0)
            production_names = sorted(values["production_names"])
            display_values = self._prepare_display_quantities(
                uom,
                values["required_qty"],
                available_qty,
                values["reserved_qty"],
                purchase_qty,
            )
            lines.append({
                "product_id": product.id,
                "product_code": product.default_code or "",
                "product_category_id": product.categ_id.id,
                "product_uom_id": uom.id,
                "required_qty": values["required_qty"],
                "available_qty": available_qty,
                "reserved_qty": values["reserved_qty"],
                "purchase_qty": purchase_qty,
                "need_purchase": purchase_qty > 0.0,
                "availability_state": "shortage" if purchase_qty > 0.0 else "covered",
                "source_count": values["source_count"],
                "production_summary": self._short_origin_summary(production_names),
                "production_names": ", ".join(production_names),
                **display_values,
            })

        return sorted(lines, key=lambda vals: vals["purchase_qty"], reverse=True)

    @api.model
    def _prepare_display_quantities(self, uom, required_qty, available_qty, reserved_qty, purchase_qty):
        display_uom = self._display_uom(uom)
        quantities = {
            "required_qty": required_qty,
            "available_qty": available_qty,
            "reserved_qty": reserved_qty,
            "purchase_qty": purchase_qty,
        }
        if display_uom != uom:
            quantities = {
                key: uom._compute_quantity(value, display_uom)
                for key, value in quantities.items()
            }

        unit_like = self._is_unit_uom(display_uom)
        return {
            "display_uom_name": display_uom.name,
            "required_qty_display": self._format_display_qty(quantities["required_qty"], unit_like),
            "available_qty_display": self._format_display_qty(quantities["available_qty"], unit_like),
            "reserved_qty_display": self._format_display_qty(quantities["reserved_qty"], unit_like),
            "purchase_qty_display": self._format_display_qty(quantities["purchase_qty"], unit_like),
        }

    @api.model
    def _display_uom(self, uom):
        if not self._is_gram_uom(uom):
            return uom
        kg_uom = self.env["uom.uom"].search([
            ("category_id", "=", uom.category_id.id),
            ("name", "in", ["kg", "Kg", "KG", "Kilogram", "Kilograms", "Chilogrammo", "Chilogrammi"]),
        ], limit=1)
        if kg_uom:
            return kg_uom
        return uom

    @api.model
    def _is_gram_uom(self, uom):
        name = (uom.name or "").strip().lower()
        return name in {"g", "gr", "gram", "grams", "grammo", "grammi"}

    @api.model
    def _is_unit_uom(self, uom):
        name = (uom.name or "").strip().lower()
        category = (uom.category_id.name or "").strip().lower()
        return (
            name in {"unit", "units", "unita", "unità", "pz", "pezzo", "pezzi"}
            or category in {"unit", "units", "unita", "unità"}
        )

    @api.model
    def _format_display_qty(self, qty, unit_like=False):
        if unit_like:
            return str(int(round(qty or 0.0)))
        value = f"{qty or 0.0:.3f}".rstrip("0").rstrip(".")
        if value == "-0":
            value = "0"
        return value.replace(".", ",")

    @api.model
    def _short_origin_summary(self, production_names):
        visible = production_names[:3]
        hidden_count = max(len(production_names) - len(visible), 0)
        summary = ", ".join(visible)
        if hidden_count:
            summary = _("%s + altri %s") % (summary, hidden_count)
        return summary

    @api.model
    def _production_component_entries(self, production):
        entries = []
        moves = production.move_raw_ids.filtered(lambda move: move.state != "cancel")
        for move in moves:
            qty = move.product_uom_qty
            reserved_qty = move.reserved_availability if "reserved_availability" in move._fields else 0.0
            entries.append((move.product_id, qty, move.product_uom, reserved_qty))

        if entries:
            return entries

        bom = production.bom_id or self._find_bom_for_production(production)
        if not bom:
            return entries

        factor = production.product_qty / (bom.product_qty or 1.0)
        for bom_line in bom.bom_line_ids:
            qty = bom_line.product_qty * factor
            entries.append((bom_line.product_id, qty, bom_line.product_uom_id, 0.0))
        return entries

    @api.model
    def _find_bom_for_production(self, production):
        domain = [
            ("type", "=", "normal"),
            ("product_tmpl_id", "=", production.product_id.product_tmpl_id.id),
            "|",
            ("product_id", "=", production.product_id.id),
            ("product_id", "=", False),
        ]
        return self.env["mrp.bom"].search(domain, limit=1)

    @api.model
    def _prepare_note(self, productions):
        draft_without_components = productions.filtered(
            lambda production: not production.move_raw_ids and not production.bom_id
        )
        if not draft_without_components:
            return False
        names = ", ".join(draft_without_components.mapped("name"))
        return _(
            "Alcuni ordini non avevano righe componenti gia generate; per questi "
            "il calcolo usa la distinta base disponibile: %s"
        ) % names


class CfRawMaterialSummaryLine(models.TransientModel):
    _name = "cf.raw.material.summary.line"
    _description = "Riga Resoconto Materie Prime"
    _order = "purchase_qty desc, required_qty desc"

    wizard_id = fields.Many2one(
        "cf.raw.material.summary.wizard",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one("product.product", string="Materia Prima", readonly=True)
    product_code = fields.Char(string="Codice", readonly=True)
    product_category_id = fields.Many2one("product.category", string="Categoria", readonly=True)
    product_uom_id = fields.Many2one("uom.uom", string="UdM", readonly=True)
    required_qty = fields.Float(
        string="Serve",
        digits="Product Unit of Measure",
        readonly=True,
    )
    available_qty = fields.Float(
        string="In magazzino",
        digits="Product Unit of Measure",
        readonly=True,
    )
    reserved_qty = fields.Float(
        string="Gia riservata",
        digits="Product Unit of Measure",
        readonly=True,
    )
    purchase_qty = fields.Float(
        string="Da acquistare",
        digits="Product Unit of Measure",
        readonly=True,
    )
    required_qty_display = fields.Char(string="Serve", readonly=True)
    available_qty_display = fields.Char(string="In magazzino", readonly=True)
    reserved_qty_display = fields.Char(string="Gia riservata", readonly=True)
    purchase_qty_display = fields.Char(string="Da acquistare", readonly=True)
    display_uom_name = fields.Char(string="UdM", readonly=True)
    need_purchase = fields.Boolean(string="Da acquistare", readonly=True)
    availability_state = fields.Selection(
        [("shortage", "Da acquistare"), ("covered", "Coperto")],
        string="Stato",
        readonly=True,
    )
    source_count = fields.Integer(string="Righe", readonly=True)
    production_summary = fields.Char(string="Origine", readonly=True)
    production_names = fields.Char(string="Dettaglio MO", readonly=True)
