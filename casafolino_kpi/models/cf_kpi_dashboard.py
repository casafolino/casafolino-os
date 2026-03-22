# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta

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
    notes = fields.Text()

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
        })
