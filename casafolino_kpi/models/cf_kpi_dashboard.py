# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date
import json
from collections import defaultdict


class CfKpiSnapshot(models.Model):
    _name = "cf.kpi.snapshot"
    _description = "Snapshot KPI Giornaliero"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date(required=True, default=fields.Date.today)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.ref("base.EUR"))
    sales_today = fields.Monetary(currency_field="currency_id")
    sales_mtd = fields.Monetary(currency_field="currency_id")
    sales_ytd = fields.Monetary(currency_field="currency_id")
    sales_amazon = fields.Monetary(currency_field="currency_id")
    sales_shopify = fields.Monetary(currency_field="currency_id")
    sales_b2b = fields.Monetary(currency_field="currency_id")
    sales_gdo = fields.Monetary(currency_field="currency_id")
    mo_open = fields.Integer()
    mo_done = fields.Integer()
    nc_open = fields.Integer()
    quarantine_active = fields.Integer()
    margin_mtd = fields.Monetary(currency_field="currency_id")
    margin_ytd = fields.Monetary(currency_field="currency_id")
    orders_pending = fields.Integer()
    orders_pending_value = fields.Monetary(currency_field="currency_id")
    top_clients_json = fields.Text()
    top_products_json = fields.Text()
    notes = fields.Text()

    # ========================================================================
    # LIVE DASHBOARD — calcola tutto in tempo reale, senza snapshot
    # ========================================================================

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.today()
        first_day_month = today.replace(day=1)
        first_day_year = today.replace(month=1, day=1)

        SO = self.env["sale.order"]
        AML = self.env["account.move"]

        # ── VENDITE ──────────────────────────────────────────────────────────
        def sum_sales(date_from, date_to=None, extra_domain=None):
            domain = [
                ("state", "in", ("sale", "done")),
                ("date_order", ">=", str(date_from)),
            ]
            if date_to:
                domain.append(("date_order", "<=", str(date_to)))
            if extra_domain:
                domain += extra_domain
            return sum(SO.search(domain).mapped("amount_untaxed"))

        sales_today = sum_sales(today)
        sales_mtd = sum_sales(first_day_month)
        sales_ytd = sum_sales(first_day_year)

        # ── VENDITE PER CANALE (tag partner YTD) ─────────────────────────────
        def sales_by_tag(tag_name):
            tag = self.env["res.partner.category"].search(
                [("name", "ilike", tag_name)], limit=1)
            if not tag:
                return 0.0
            return sum_sales(
                first_day_year,
                extra_domain=[("partner_id.category_id", "in", [tag.id])])

        sales_b2b = sales_by_tag("B2B")
        sales_gdo = sales_by_tag("GDO")
        sales_amazon = sales_by_tag("Amazon")
        sales_shopify = sales_by_tag("Shopify")

        # ── MARGINE (richiede sale_margin module) ────────────────────────────
        margin_mtd = 0.0
        margin_ytd = 0.0
        margin_pct_mtd = 0.0
        SOL = self.env["sale.order.line"]
        if "margin" in SOL._fields:
            lines_ytd = SOL.search([
                ("order_id.state", "in", ("sale", "done")),
                ("order_id.date_order", ">=", str(first_day_year)),
            ])
            margin_ytd = sum(lines_ytd.mapped("margin"))
            lines_mtd = lines_ytd.filtered(
                lambda l: l.order_id.date_order
                and l.order_id.date_order.date() >= first_day_month)
            margin_mtd = sum(lines_mtd.mapped("margin"))
            if sales_mtd > 0:
                margin_pct_mtd = round(margin_mtd / sales_mtd * 100, 1)

        # ── ORDINI PENDING ───────────────────────────────────────────────────
        pending_domain = [("state", "=", "sale")]
        if "delivery_status" in SO._fields:
            pending_domain.append(("delivery_status", "not in", ["full"]))
        pending = SO.search(pending_domain)
        orders_pending = len(pending)
        orders_pending_value = sum(pending.mapped("amount_untaxed"))

        # ── DA INCASSARE (fatture posted non pagate) ─────────────────────────
        unpaid = AML.search([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial", "in_payment")),
        ])
        receivable_value = sum(unpaid.mapped("amount_residual"))

        # ── SCADUTE ──────────────────────────────────────────────────────────
        overdue = unpaid.filtered(
            lambda m: m.invoice_date_due and m.invoice_date_due < today)
        overdue_count = len(overdue)
        overdue_value = sum(overdue.mapped("amount_residual"))

        # ── PRODUZIONE ───────────────────────────────────────────────────────
        MO = self.env["mrp.production"]
        mo_open = MO.search_count(
            [("state", "in", ("confirmed", "progress", "to_close"))])
        mo_done = MO.search_count([
            ("state", "=", "done"),
            ("date_finished", ">=", str(first_day_month)),
        ])

        # ── HACCP (opzionale) ────────────────────────────────────────────────
        nc_open = 0
        quarantine_active = 0
        if "cf.haccp.nc" in self.env:
            nc_open = self.env["cf.haccp.nc"].search_count(
                [("state", "not in", ("closed", "cancelled"))])
        if "cf.haccp.quarantine" in self.env:
            quarantine_active = self.env["cf.haccp.quarantine"].search_count(
                [("state", "=", "active")])

        # ── TOP 5 CLIENTI MTD ────────────────────────────────────────────────
        orders_mtd = SO.search([
            ("state", "in", ("sale", "done")),
            ("date_order", ">=", str(first_day_month)),
        ])
        client_sales = defaultdict(float)
        for o in orders_mtd:
            client_sales[o.partner_id.name or "N/A"] += o.amount_untaxed
        top_clients = sorted(
            client_sales.items(), key=lambda x: x[1], reverse=True)[:5]

        # ── TOP 6 PRODOTTI MTD (per fatturato, price_subtotal) ──────────────
        product_sales = defaultdict(float)
        for o in orders_mtd:
            for line in o.order_line:
                if line.product_id:
                    product_sales[line.product_id.name or "N/A"] += (
                        line.price_subtotal or 0.0)
        top_products = sorted(
            product_sales.items(), key=lambda x: x[1], reverse=True)[:6]

        return {
            "has_data": True,
            "date": str(today),
            "sales_today": sales_today,
            "sales_mtd": sales_mtd,
            "sales_ytd": sales_ytd,
            "sales_b2b": sales_b2b,
            "sales_gdo": sales_gdo,
            "sales_amazon": sales_amazon,
            "sales_shopify": sales_shopify,
            "margin_mtd": margin_mtd,
            "margin_ytd": margin_ytd,
            "margin_pct_mtd": margin_pct_mtd,
            "orders_pending": orders_pending,
            "orders_pending_value": orders_pending_value,
            "receivable_value": receivable_value,
            "overdue_count": overdue_count,
            "overdue_value": overdue_value,
            "mo_open": mo_open,
            "mo_done": mo_done,
            "nc_open": nc_open,
            "quarantine_active": quarantine_active,
            "top_clients": top_clients,
            "top_products": top_products,
            "currency_symbol": self.env.ref("base.EUR").symbol,
        }

    # ========================================================================
    # SNAPSHOT GIORNALIERO — mantenuto per storico
    # ========================================================================

    @api.model
    def create_daily_snapshot(self):
        today = date.today()
        if self.search([("date", "=", today)]):
            return
        data = self.get_dashboard_data()
        self.create({
            "date": today,
            "sales_today": data.get("sales_today", 0),
            "sales_mtd": data.get("sales_mtd", 0),
            "sales_ytd": data.get("sales_ytd", 0),
            "sales_amazon": data.get("sales_amazon", 0),
            "sales_shopify": data.get("sales_shopify", 0),
            "sales_b2b": data.get("sales_b2b", 0),
            "sales_gdo": data.get("sales_gdo", 0),
            "mo_open": data.get("mo_open", 0),
            "mo_done": data.get("mo_done", 0),
            "nc_open": data.get("nc_open", 0),
            "quarantine_active": data.get("quarantine_active", 0),
            "margin_mtd": data.get("margin_mtd", 0),
            "margin_ytd": data.get("margin_ytd", 0),
            "orders_pending": data.get("orders_pending", 0),
            "orders_pending_value": data.get("orders_pending_value", 0),
            "top_clients_json": json.dumps(data.get("top_clients", [])),
            "top_products_json": json.dumps(data.get("top_products", [])),
        })
