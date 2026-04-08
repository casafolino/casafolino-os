# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
import json
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)


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
    # LIVE DASHBOARD — calcola tutto in tempo reale, mai errore
    # ========================================================================

    def _safe(self, fn, default=0):
        """Wrap fn() in try/except — return default on any error."""
        try:
            return fn()
        except Exception as e:
            _logger.warning("KPI safe call failed: %s", e)
            return default

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.today()
        first_day_month = today.replace(day=1)
        first_day_year = today.replace(month=1, day=1)
        ninety_days_ago = today - timedelta(days=90)
        thirty_days_ahead = today + timedelta(days=30)

        SO = self.env["sale.order"]
        AM = self.env["account.move"]
        SOL = self.env["sale.order.line"]

        # ── ORDINI (sale.order amount_untaxed) ───────────────────────────────
        def sum_orders(date_from, date_to=None, extra=None):
            domain = [
                ("state", "in", ("sale", "done")),
                ("date_order", ">=", str(date_from)),
            ]
            if date_to:
                domain.append(("date_order", "<=", str(date_to)))
            if extra:
                domain += extra
            return sum(SO.search(domain).mapped("amount_untaxed"))

        orders_ytd = self._safe(lambda: sum_orders(first_day_year))
        orders_mtd = self._safe(lambda: sum_orders(first_day_month))
        orders_today = self._safe(lambda: sum_orders(today))

        # ── FATTURATO FATTURE EMESSE (account.move out_invoice posted) ───────
        def sum_invoiced(date_from):
            domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", str(date_from)),
            ]
            moves = AM.search(domain)
            return sum(moves.mapped("amount_untaxed_signed"))

        invoiced_ytd = self._safe(lambda: sum_invoiced(first_day_year))
        invoiced_mtd = self._safe(lambda: sum_invoiced(first_day_month))

        # ── MARGINE (richiede sale_margin) ───────────────────────────────────
        margin_mtd = 0.0
        margin_ytd = 0.0
        if "margin" in SOL._fields:
            try:
                lines_ytd = SOL.search([
                    ("order_id.state", "in", ("sale", "done")),
                    ("order_id.date_order", ">=", str(first_day_year)),
                ])
                margin_ytd = sum(lines_ytd.mapped("margin"))
                lines_mtd = lines_ytd.filtered(
                    lambda l: l.order_id.date_order
                    and l.order_id.date_order.date() >= first_day_month)
                margin_mtd = sum(lines_mtd.mapped("margin"))
            except Exception as e:
                _logger.warning("Margin calc failed: %s", e)
        margin_pct_mtd = round(margin_mtd / orders_mtd * 100, 1) if orders_mtd else 0.0

        # ── DA INCASSARE (out_invoice non pagate) ────────────────────────────
        def receivable_data():
            unpaid = AM.search([
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial", "in_payment")),
            ])
            total = sum(unpaid.mapped("amount_residual"))
            overdue = unpaid.filtered(
                lambda m: m.invoice_date_due and m.invoice_date_due < today)
            return {
                "total": total,
                "overdue_value": sum(overdue.mapped("amount_residual")),
                "overdue_count": len(overdue),
            }

        rec = self._safe(receivable_data,
                         {"total": 0, "overdue_value": 0, "overdue_count": 0})

        # ── DA PAGARE (in_invoice non pagate) ────────────────────────────────
        def payable_data():
            unpaid = AM.search([
                ("move_type", "=", "in_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial", "in_payment")),
            ])
            total = sum(unpaid.mapped("amount_residual"))
            overdue = unpaid.filtered(
                lambda m: m.invoice_date_due and m.invoice_date_due < today)
            return {
                "total": total,
                "overdue_value": sum(overdue.mapped("amount_residual")),
                "overdue_count": len(overdue),
            }

        pay = self._safe(payable_data,
                         {"total": 0, "overdue_value": 0, "overdue_count": 0})

        # ── FATTURE MTD (count) ──────────────────────────────────────────────
        invoices_issued_mtd = self._safe(lambda: AM.search_count([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", str(first_day_month)),
        ]))
        invoices_paid_mtd = self._safe(lambda: AM.search_count([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "=", "paid"),
            ("invoice_date", ">=", str(first_day_month)),
        ]))

        # ── CANALI VENDITA YTD ───────────────────────────────────────────────
        def sales_by_team(name_pattern):
            team = self.env["crm.team"].search(
                [("name", "ilike", name_pattern)], limit=1)
            if not team:
                return 0.0
            return sum_orders(
                first_day_year,
                extra=[("team_id", "=", team.id)])

        def sales_by_partner_tag(tag_pattern):
            tag = self.env["res.partner.category"].search(
                [("name", "ilike", tag_pattern)], limit=1)
            if not tag:
                return 0.0
            return sum_orders(
                first_day_year,
                extra=[("partner_id.category_id", "in", [tag.id])])

        def sales_by_country(country_code):
            return sum_orders(
                first_day_year,
                extra=[("partner_id.country_id.code", "=", country_code)])

        channel_export_b2b = self._safe(lambda: sales_by_team("Estero")) or \
            self._safe(lambda: sales_by_team("Sales"))
        channel_amazon = self._safe(lambda: sales_by_team("Amazon"))
        channel_shopify = self._safe(lambda: sales_by_partner_tag("Shopify"))
        channel_italia = self._safe(lambda: sales_by_country("IT"))
        channel_gdo = self._safe(lambda: sales_by_partner_tag("GDO"))
        channel_pos = self._safe(lambda: sales_by_partner_tag("POS"))

        # ── GEO YTD ──────────────────────────────────────────────────────────
        def geo_data():
            geo_italy = sales_by_country("IT")
            eu_group = self.env["res.country.group"].search(
                [("name", "ilike", "Europe")], limit=1)
            eu_country_ids = eu_group.country_ids.ids if eu_group else []
            geo_eu = 0.0
            if eu_country_ids:
                geo_eu = sum_orders(
                    first_day_year,
                    extra=[("partner_id.country_id", "in", eu_country_ids),
                           ("partner_id.country_id.code", "!=", "IT")])
            geo_extra_eu = sum_orders(
                first_day_year,
                extra=[("partner_id.country_id", "!=", False),
                       ("partner_id.country_id", "not in", eu_country_ids)])
            return geo_italy, geo_eu, geo_extra_eu

        geo_italy, geo_eu, geo_extra_eu = self._safe(geo_data, (0, 0, 0))

        # ── ORDINI PENDING ───────────────────────────────────────────────────
        def pending_data():
            domain = [("state", "=", "sale")]
            if "delivery_status" in SO._fields:
                domain.append(("delivery_status", "not in", ["full"]))
            pending = SO.search(domain)
            return len(pending), sum(pending.mapped("amount_untaxed"))

        orders_pending_count, orders_pending_value = self._safe(
            pending_data, (0, 0))

        # ── TOP CLIENTI MTD ──────────────────────────────────────────────────
        def top_clients_data():
            orders_mtd_recs = SO.search([
                ("state", "in", ("sale", "done")),
                ("date_order", ">=", str(first_day_month)),
            ])
            client_sales = defaultdict(float)
            for o in orders_mtd_recs:
                client_sales[o.partner_id.name or "N/A"] += o.amount_untaxed
            return sorted(
                client_sales.items(), key=lambda x: x[1], reverse=True)[:10]

        top_clients = self._safe(top_clients_data, [])

        # ── TOP PRODOTTI MTD/YTD (per price_subtotal) ────────────────────────
        def top_products_period(date_from):
            lines = SOL.search([
                ("order_id.state", "in", ("sale", "done")),
                ("order_id.date_order", ">=", str(date_from)),
            ])
            product_sales = defaultdict(float)
            for line in lines:
                if line.product_id:
                    product_sales[line.product_id.name or "N/A"] += (
                        line.price_subtotal or 0.0)
            return sorted(
                product_sales.items(), key=lambda x: x[1], reverse=True)[:10]

        top_products_mtd = self._safe(
            lambda: top_products_period(first_day_month), [])
        top_products_ytd = self._safe(
            lambda: top_products_period(first_day_year), [])

        # ── PRODOTTI SENZA ORDINI 90gg ───────────────────────────────────────
        def products_no_orders():
            sold_template_ids = SOL.search([
                ("order_id.state", "in", ("sale", "done")),
                ("order_id.date_order", ">=", str(ninety_days_ago)),
            ]).mapped("product_id.product_tmpl_id.id")
            sold_set = set(sold_template_ids)
            active_products = self.env["product.template"].search([
                ("sale_ok", "=", True),
                ("active", "=", True),
            ])
            return sum(1 for p in active_products if p.id not in sold_set)

        products_no_orders_90d = self._safe(products_no_orders, 0)

        # ── PRODUZIONE ───────────────────────────────────────────────────────
        MO = self.env.get("mrp.production")
        mo_open = 0
        mo_in_progress = 0
        mo_done_mtd = 0
        if MO is not None:
            mo_open = self._safe(lambda: MO.search_count(
                [("state", "in", ("confirmed", "progress", "to_close"))]))
            mo_in_progress = self._safe(lambda: MO.search_count(
                [("state", "=", "progress")]))
            mo_done_mtd = self._safe(lambda: MO.search_count([
                ("state", "=", "done"),
                ("date_finished", ">=", str(first_day_month)),
            ]))

        # ── STOCK SOTTO MINIMO ───────────────────────────────────────────────
        def stock_below_min():
            orderpoints = self.env["stock.warehouse.orderpoint"].search([])
            count = 0
            for op in orderpoints:
                if op.product_id and op.product_id.qty_available < op.product_min_qty:
                    count += 1
            return count

        stock_below = self._safe(stock_below_min, 0)

        # ── LOTTI IN SCADENZA 30gg ───────────────────────────────────────────
        def lots_expiring():
            Lot = self.env.get("stock.lot")
            if Lot is None or "expiration_date" not in Lot._fields:
                return 0
            return Lot.search_count([
                ("expiration_date", ">=", str(today)),
                ("expiration_date", "<=", str(thirty_days_ahead)),
            ])

        lots_expiring_30d = self._safe(lots_expiring, 0)

        # ── HACCP ────────────────────────────────────────────────────────────
        nc_open = 0
        nc_closed_mtd = 0
        quarantine_active = 0
        calibration_due_30d = 0
        if "cf.haccp.nc" in self.env:
            nc_open = self._safe(lambda: self.env["cf.haccp.nc"].search_count(
                [("state", "not in", ("closed", "cancelled"))]))
            nc_closed_mtd = self._safe(
                lambda: self.env["cf.haccp.nc"].search_count([
                    ("state", "=", "closed"),
                    ("write_date", ">=", str(first_day_month)),
                ]))
        if "cf.haccp.quarantine" in self.env:
            quarantine_active = self._safe(
                lambda: self.env["cf.haccp.quarantine"].search_count(
                    [("state", "=", "active")]))
        if "cf.haccp.calibration" in self.env:
            calibration_due_30d = self._safe(
                lambda: self.env["cf.haccp.calibration"].search_count([
                    ("next_calibration_date", ">=", str(today)),
                    ("next_calibration_date", "<=", str(thirty_days_ahead)),
                ]))

        return {
            "has_data": True,
            "date": str(today),

            # FINANZA
            "orders_ytd": orders_ytd,
            "orders_mtd": orders_mtd,
            "orders_today": orders_today,
            "invoiced_ytd": invoiced_ytd,
            "invoiced_mtd": invoiced_mtd,
            "margin_mtd": margin_mtd,
            "margin_ytd": margin_ytd,
            "margin_pct_mtd": margin_pct_mtd,
            "receivable_total": rec["total"],
            "receivable_overdue_value": rec["overdue_value"],
            "receivable_overdue_count": rec["overdue_count"],
            "payable_total": pay["total"],
            "payable_overdue_value": pay["overdue_value"],
            "payable_overdue_count": pay["overdue_count"],
            "invoices_issued_mtd": invoices_issued_mtd,
            "invoices_paid_mtd": invoices_paid_mtd,

            # VENDITE — canali
            "channel_export_b2b": channel_export_b2b,
            "channel_amazon": channel_amazon,
            "channel_shopify": channel_shopify,
            "channel_italia": channel_italia,
            "channel_gdo": channel_gdo,
            "channel_pos": channel_pos,

            # GEO
            "geo_italy": geo_italy,
            "geo_eu": geo_eu,
            "geo_extra_eu": geo_extra_eu,

            # ORDINI
            "orders_pending_count": orders_pending_count,
            "orders_pending_value": orders_pending_value,

            # TOP CLIENTI
            "top_clients": top_clients,

            # PRODOTTI
            "top_products_mtd": top_products_mtd,
            "top_products_ytd": top_products_ytd,
            "products_no_orders_90d": products_no_orders_90d,

            # OPERATIONS
            "mo_open": mo_open,
            "mo_in_progress": mo_in_progress,
            "mo_done_mtd": mo_done_mtd,
            "stock_below_min": stock_below,
            "lots_expiring_30d": lots_expiring_30d,

            # QUALITA'
            "nc_open": nc_open,
            "nc_closed_mtd": nc_closed_mtd,
            "quarantine_active": quarantine_active,
            "calibration_due_30d": calibration_due_30d,
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
            "sales_today": data.get("orders_today", 0),
            "sales_mtd": data.get("orders_mtd", 0),
            "sales_ytd": data.get("orders_ytd", 0),
            "sales_amazon": data.get("channel_amazon", 0),
            "sales_shopify": data.get("channel_shopify", 0),
            "sales_b2b": data.get("channel_export_b2b", 0),
            "sales_gdo": data.get("channel_gdo", 0),
            "mo_open": data.get("mo_open", 0),
            "mo_done": data.get("mo_done_mtd", 0),
            "nc_open": data.get("nc_open", 0),
            "quarantine_active": data.get("quarantine_active", 0),
            "margin_mtd": data.get("margin_mtd", 0),
            "margin_ytd": data.get("margin_ytd", 0),
            "orders_pending": data.get("orders_pending_count", 0),
            "orders_pending_value": data.get("orders_pending_value", 0),
            "top_clients_json": json.dumps(data.get("top_clients", [])),
            "top_products_json": json.dumps(data.get("top_products_mtd", [])),
        })
