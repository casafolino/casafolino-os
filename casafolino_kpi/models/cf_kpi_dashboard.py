# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
import json
from collections import defaultdict

class CfKpiSnapshot(models.Model):
    _name = "cf.kpi.snapshot"
    _description = "Snapshot KPI Giornaliero"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date(required=True, default=fields.Date.today)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    sales_today = fields.Monetary(string="Vendite Oggi", currency_field="currency_id")
    sales_mtd = fields.Monetary(string="Vendite MTD", currency_field="currency_id")
    sales_ytd = fields.Monetary(string="Vendite YTD", currency_field="currency_id")
    sales_amazon = fields.Monetary(string="Amazon", currency_field="currency_id")
    sales_shopify = fields.Monetary(string="Shopify", currency_field="currency_id")
    sales_b2b = fields.Monetary(string="B2B", currency_field="currency_id")
    sales_gdo = fields.Monetary(string="GDO", currency_field="currency_id")
    mo_open = fields.Integer(string="MO Aperti")
    mo_done = fields.Integer(string="MO Completati MTD")
    nc_open = fields.Integer(string="NC Aperte")
    quarantine_active = fields.Integer(string="Quarantene Attive")
    margin_mtd = fields.Monetary(string="Margine Lordo MTD", currency_field="currency_id")
    margin_ytd = fields.Monetary(string="Margine Lordo YTD", currency_field="currency_id")
    orders_pending = fields.Integer(string="Ordini in attesa evasione")
    orders_pending_value = fields.Monetary(string="Valore ordini pending", currency_field="currency_id")
    top_clients_json = fields.Text(string="Top 10 Clienti MTD (JSON)")
    top_products_json = fields.Text(string="Top 10 Prodotti MTD (JSON)")
    notes = fields.Text()

    @api.model
    def get_dashboard_data(self):
        latest = self.search([], limit=1)
        prev = self.search([], limit=1, offset=1)
        if not latest:
            return {"has_data": False}

        def delta(a, b):
            if not b or not b:
                return None
            return round((a - b) / b * 100, 1) if b else None

        return {
            "has_data": True,
            "date": str(latest.date),
            "sales_ytd": latest.sales_ytd,
            "sales_mtd": latest.sales_mtd,
            "sales_b2b": latest.sales_b2b,
            "sales_gdo": latest.sales_gdo,
            "sales_amazon": latest.sales_amazon,
            "sales_shopify": latest.sales_shopify,
            "mo_open": latest.mo_open,
            "mo_done": latest.mo_done,
            "nc_open": latest.nc_open,
            "quarantine_active": latest.quarantine_active,
            "margin_mtd": latest.margin_mtd,
            "margin_ytd": latest.margin_ytd,
            "orders_pending": latest.orders_pending,
            "orders_pending_value": latest.orders_pending_value,
            "top_clients": json.loads(latest.top_clients_json) if latest.top_clients_json else [],
            "top_products": json.loads(latest.top_products_json) if latest.top_products_json else [],
            "delta_ytd": delta(latest.sales_ytd, prev.sales_ytd) if prev else None,
            "delta_mtd": delta(latest.sales_mtd, prev.sales_mtd) if prev else None,
            "currency_symbol": self.env.ref("base.EUR").symbol,
        }

    @api.model
    def create_daily_snapshot(self):
        today = date.today()
        if self.search([("date","=",today)]): return
        first_day_month = today.replace(day=1)
        first_day_year = today.replace(month=1,day=1)

        def get_sales(domain_extra=[]):
            domain = [("state","in",("sale","done")),("date_order",">=",str(first_day_year))] + domain_extra
            orders = self.env["sale.order"].search(domain)
            return sum(orders.mapped("amount_untaxed"))

        def get_sales_by_tag(tag_name):
            tag = self.env["res.partner.category"].search([("name","ilike",tag_name)],limit=1)
            if not tag: return 0.0
            domain = [("state","in",("sale","done")),("date_order",">=",str(first_day_year)),
                      ("partner_id.category_id","in",[tag.id])]
            return sum(self.env["sale.order"].search(domain).mapped("amount_untaxed"))

        mo_open = self.env["mrp.production"].search_count([("state","in",("confirmed","progress"))])
        mo_done = self.env["mrp.production"].search_count([("state","=","done"),("date_finished",">=",str(first_day_month))])

        nc_open = 0
        quarantine = 0
        if "cf.haccp.nc" in self.env:
            nc_open = self.env["cf.haccp.nc"].search_count([("state","not in",("closed","cancelled"))])
        if "cf.haccp.quarantine" in self.env:
            quarantine = self.env["cf.haccp.quarantine"].search_count([("state","=","active")])

        # Margine lordo (richiede sale_margin)
        margin_mtd = 0.0
        margin_ytd = 0.0
        if "margin" in self.env["sale.order.line"]._fields:
            lines_ytd = self.env["sale.order.line"].search([
                ("order_id.state", "in", ("sale", "done")),
                ("order_id.date_order", ">=", str(first_day_year)),
            ])
            margin_ytd = sum(lines_ytd.mapped("margin"))
            lines_mtd = lines_ytd.filtered(
                lambda l: l.order_id.date_order.date() >= first_day_month
            )
            margin_mtd = sum(lines_mtd.mapped("margin"))

        # Ordini pending (confermati, non completamente evasi)
        pending = self.env["sale.order"].search([
            ("state", "=", "sale"),
            ("delivery_status", "not in", ["full"]),
        ])
        orders_pending = len(pending)
        orders_pending_value = sum(pending.mapped("amount_untaxed"))

        # Top 10 clienti MTD
        orders_mtd = self.env["sale.order"].search([
            ("state", "in", ("sale", "done")),
            ("date_order", ">=", str(first_day_month)),
        ])
        client_sales = defaultdict(float)
        for o in orders_mtd:
            client_sales[o.partner_id.name or "N/A"] += o.amount_untaxed
        top_clients = sorted(client_sales.items(), key=lambda x: x[1], reverse=True)[:10]

        # Top 10 prodotti MTD
        product_sales = defaultdict(float)
        for o in orders_mtd:
            for line in o.order_line:
                if line.product_id:
                    product_sales[line.product_id.name or "N/A"] += line.product_uom_qty
        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:10]

        self.create({
            "date": today,
            "sales_ytd": get_sales(),
            "sales_mtd": get_sales([("date_order",">=",str(first_day_month))]),
            "sales_amazon": get_sales_by_tag("Amazon"),
            "sales_shopify": get_sales_by_tag("Shopify"),
            "sales_b2b": get_sales_by_tag("B2B"),
            "sales_gdo": get_sales_by_tag("GDO"),
            "mo_open": mo_open,
            "mo_done": mo_done,
            "nc_open": nc_open,
            "quarantine_active": quarantine,
            "margin_mtd": margin_mtd,
            "margin_ytd": margin_ytd,
            "orders_pending": orders_pending,
            "orders_pending_value": orders_pending_value,
            "top_clients_json": json.dumps(top_clients),
            "top_products_json": json.dumps(top_products),
        })
