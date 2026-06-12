# -*- coding: utf-8 -*-
from collections import defaultdict

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
            lines.append({
                "product_id": product.id,
                "product_uom_id": uom.id,
                "required_qty": values["required_qty"],
                "available_qty": available_qty,
                "reserved_qty": values["reserved_qty"],
                "purchase_qty": purchase_qty,
                "source_count": values["source_count"],
                "production_names": ", ".join(sorted(values["production_names"])),
            })

        return sorted(lines, key=lambda vals: vals["purchase_qty"], reverse=True)

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
    product_uom_id = fields.Many2one("uom.uom", string="UdM", readonly=True)
    required_qty = fields.Float(string="Quantita richiesta", readonly=True)
    available_qty = fields.Float(string="Disponibile", readonly=True)
    reserved_qty = fields.Float(string="Gia riservata", readonly=True)
    purchase_qty = fields.Float(string="Da acquistare", readonly=True)
    source_count = fields.Integer(string="Righe origine", readonly=True)
    production_names = fields.Char(string="Ordini di Produzione", readonly=True)
