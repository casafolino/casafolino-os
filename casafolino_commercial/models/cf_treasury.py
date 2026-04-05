# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
import json


class CfTreasury(models.Model):
    _name = "cf.treasury.snapshot"
    _description = "Snapshot Tesoreria"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    total_balance = fields.Monetary(string="Saldo Totale", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))

    # Legacy fields (usati da _compute_forecast e backward compat)
    receivable_30d = fields.Monetary(string="Crediti 30gg", currency_field="currency_id")
    payable_30d = fields.Monetary(string="Debiti 30gg", currency_field="currency_id")
    forecast_30d = fields.Monetary(string="Forecast 30gg", currency_field="currency_id",
                                   compute="_compute_forecast", store=True)
    forecast_60d = fields.Monetary(string="Forecast 60gg", currency_field="currency_id",
                                   compute="_compute_forecast", store=True)
    forecast_90d = fields.Monetary(string="Forecast 90gg", currency_field="currency_id",
                                   compute="_compute_forecast", store=True)

    # Aging crediti
    receivables_overdue = fields.Float(string="Crediti Scaduti")
    receivables_30d = fields.Float(string="Crediti 0-30gg")
    receivables_60d = fields.Float(string="Crediti 31-60gg")
    receivables_90d = fields.Float(string="Crediti 61-90gg")

    # Aging debiti
    payables_overdue = fields.Float(string="Debiti Scaduti")
    payables_30d = fields.Float(string="Debiti 0-30gg")
    payables_60d = fields.Float(string="Debiti 31-60gg")
    payables_90d = fields.Float(string="Debiti 61-90gg")

    # KPI
    dso = fields.Float(string="DSO (giorni)")
    runway_days = fields.Integer(string="Runway (giorni)")

    # Cashflow JSON — array 12 mesi [{month, inflow, outflow, balance}]
    cashflow_json = fields.Text(string="Cashflow 12 mesi (JSON)")

    # Scenari 90gg
    scenario_base = fields.Float(string="Scenario Base 90gg")
    scenario_opt = fields.Float(string="Scenario Ottimistico 90gg")
    scenario_pes = fields.Float(string="Scenario Pessimistico 90gg")

    notes = fields.Text(string="Note")

    @api.depends("total_balance", "receivable_30d", "payable_30d")
    def _compute_forecast(self):
        for rec in self:
            base = rec.total_balance + rec.receivable_30d - rec.payable_30d
            rec.forecast_30d = base
            rec.forecast_60d = base * 1.05
            rec.forecast_90d = base * 1.10

    @api.model
    def get_dashboard_data(self):
        latest = self.search([], limit=1, order="date desc")
        if not latest:
            return {"has_data": False}

        cashflow = []
        if latest.cashflow_json:
            try:
                cashflow = json.loads(latest.cashflow_json)
            except Exception:
                cashflow = []

        return {
            "has_data": True,
            "date": str(latest.date),
            "total_balance": latest.total_balance,
            "runway_days": latest.runway_days,
            # Aging crediti
            "receivables_overdue": latest.receivables_overdue,
            "receivables_30d": latest.receivables_30d,
            "receivables_60d": latest.receivables_60d,
            "receivables_90d": latest.receivables_90d,
            # Aging debiti
            "payables_overdue": latest.payables_overdue,
            "payables_30d": latest.payables_30d,
            "payables_60d": latest.payables_60d,
            "payables_90d": latest.payables_90d,
            # KPI
            "dso": latest.dso,
            # Scenari
            "scenario_base": latest.scenario_base,
            "scenario_opt": latest.scenario_opt,
            "scenario_pes": latest.scenario_pes,
            # Cashflow chart
            "cashflow": cashflow,
            # Legacy (usato da views classiche)
            "receivable_30d": latest.receivable_30d,
            "payable_30d": latest.payable_30d,
            "forecast_30d": latest.forecast_30d,
            "forecast_60d": latest.forecast_60d,
            "forecast_90d": latest.forecast_90d,
            "currency_symbol": self.env.ref("base.EUR").symbol,
        }

    @api.model
    def create_daily_snapshot(self):
        today = date.today()
        if self.search([("date", "=", today)]):
            return

        # --- Saldo banche/cassa ---
        journals = self.env["account.journal"].search([("type", "in", ("bank", "cash"))])
        total_balance = sum(
            j.default_account_id.current_balance for j in journals if j.default_account_id
        )

        aml = self.env["account.move.line"]
        d30 = str(today + timedelta(days=30))
        d60 = str(today + timedelta(days=60))
        d90 = str(today + timedelta(days=90))
        today_str = str(today)

        # --- Aging crediti ---
        recv_overdue = sum(aml.search([
            ("account_id.account_type", "=", "asset_receivable"),
            ("reconciled", "=", False),
            ("date_maturity", "<", today_str),
        ]).mapped("amount_residual"))

        recv_30 = sum(aml.search([
            ("account_id.account_type", "=", "asset_receivable"),
            ("reconciled", "=", False),
            ("date_maturity", ">=", today_str),
            ("date_maturity", "<=", d30),
        ]).mapped("amount_residual"))

        recv_60 = sum(aml.search([
            ("account_id.account_type", "=", "asset_receivable"),
            ("reconciled", "=", False),
            ("date_maturity", ">", d30),
            ("date_maturity", "<=", d60),
        ]).mapped("amount_residual"))

        recv_90 = sum(aml.search([
            ("account_id.account_type", "=", "asset_receivable"),
            ("reconciled", "=", False),
            ("date_maturity", ">", d60),
            ("date_maturity", "<=", d90),
        ]).mapped("amount_residual"))

        # --- Aging debiti ---
        pay_overdue = abs(sum(aml.search([
            ("account_id.account_type", "=", "liability_payable"),
            ("reconciled", "=", False),
            ("date_maturity", "<", today_str),
        ]).mapped("amount_residual")))

        pay_30 = abs(sum(aml.search([
            ("account_id.account_type", "=", "liability_payable"),
            ("reconciled", "=", False),
            ("date_maturity", ">=", today_str),
            ("date_maturity", "<=", d30),
        ]).mapped("amount_residual")))

        pay_60 = abs(sum(aml.search([
            ("account_id.account_type", "=", "liability_payable"),
            ("reconciled", "=", False),
            ("date_maturity", ">", d30),
            ("date_maturity", "<=", d60),
        ]).mapped("amount_residual")))

        pay_90 = abs(sum(aml.search([
            ("account_id.account_type", "=", "liability_payable"),
            ("reconciled", "=", False),
            ("date_maturity", ">", d60),
            ("date_maturity", "<=", d90),
        ]).mapped("amount_residual")))

        # --- DSO (Days Sales Outstanding) ---
        # DSO = (crediti_totali / fatturato_90gg) * 90
        inv_90d = self.env["account.move"].search([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", str(today - timedelta(days=90))),
            ("invoice_date", "<=", today_str),
        ])
        revenue_90d = sum(inv_90d.mapped("amount_untaxed"))
        total_recv = recv_overdue + recv_30 + recv_60 + recv_90
        dso = round((total_recv / revenue_90d * 90), 1) if revenue_90d > 0 else 0.0

        # --- Runway days ---
        # Burn rate basato sulle uscite previste nei prossimi 30gg
        bills_due = self.env["account.move"].search([
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "not in", ["paid", "in_payment"]),
            ("invoice_date_due", "<=", d30),
        ])
        outflow_30d = sum(bills_due.mapped("amount_residual"))
        daily_burn = outflow_30d / 30.0 if outflow_30d > 0 else 0.0
        runway_days = int(total_balance / daily_burn) if daily_burn > 0 and total_balance > 0 else 0

        # --- Scenari 90gg ---
        net_monthly = recv_30 - pay_30
        scenario_base = round(total_balance + net_monthly * 3, 2)
        scenario_opt = round(total_balance + net_monthly * 3 * 1.15, 2)
        scenario_pes = round(total_balance + net_monthly * 3 * 0.75, 2)

        # --- Cashflow JSON 12 mesi ---
        cashflow_data = []
        for i in range(11, -1, -1):
            # Calcolo mese start/end senza dateutil
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            month_start = date(y, m, 1)
            if i == 0:
                month_end = today
            else:
                nm = m + 1
                ny = y
                if nm > 12:
                    nm = 1
                    ny += 1
                month_end = date(ny, nm, 1) - timedelta(days=1)

            month_inv = self.env["account.move"].search([
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", str(month_start)),
                ("invoice_date", "<=", str(month_end)),
            ])
            month_bills = self.env["account.move"].search([
                ("move_type", "=", "in_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", str(month_start)),
                ("invoice_date", "<=", str(month_end)),
            ])
            inflow = round(sum(month_inv.mapped("amount_untaxed")), 2)
            outflow = round(sum(month_bills.mapped("amount_untaxed")), 2)
            cashflow_data.append({
                "month": month_start.strftime("%b %Y"),
                "inflow": inflow,
                "outflow": outflow,
                "balance": round(inflow - outflow, 2),
            })

        self.create({
            "date": today,
            "total_balance": total_balance,
            # Legacy
            "receivable_30d": recv_30,
            "payable_30d": pay_30,
            # Aging crediti
            "receivables_overdue": recv_overdue,
            "receivables_30d": recv_30,
            "receivables_60d": recv_60,
            "receivables_90d": recv_90,
            # Aging debiti
            "payables_overdue": pay_overdue,
            "payables_30d": pay_30,
            "payables_60d": pay_60,
            "payables_90d": pay_90,
            # KPI
            "dso": dso,
            "runway_days": runway_days,
            # Scenari
            "scenario_base": scenario_base,
            "scenario_opt": scenario_opt,
            "scenario_pes": scenario_pes,
            # JSON
            "cashflow_json": json.dumps(cashflow_data),
        })

    @api.model
    def cron_liquidity_alert(self):
        """Alert se liquidita scende sotto soglia."""
        threshold = float(self.env["ir.config_parameter"].sudo().get_param(
            "casafolino.treasury_alert_threshold", "10000"
        ))
        journals = self.env["account.journal"].search([("type", "in", ("bank", "cash"))])
        cash_available = sum(
            j.default_account_id.current_balance for j in journals if j.default_account_id
        )
        cutoff = date.today() + timedelta(days=30)
        pending_bills = self.env["account.move"].search([
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "not in", ["paid", "in_payment"]),
            ("invoice_date_due", "<=", str(cutoff)),
        ])
        outflows = sum(pending_bills.mapped("amount_residual"))
        runway = cash_available - outflows

        if runway < threshold:
            antonio = self.env["res.users"].search(
                [("login", "=", "antonio@casafolino.com")], limit=1
            )
            if antonio and antonio.email:
                body = (
                    "<p><b>Alert Liquidita CasaFolino</b></p>"
                    "<p>Cash disponibile: <b>€ %.0f</b></p>"
                    "<p>Uscite previste 30gg: <b>€ %.0f</b></p>"
                    "<p>Cash runway netto: <b>€ %.0f</b></p>"
                    "<p>Soglia configurata: € %.0f</p>"
                ) % (cash_available, outflows, runway, threshold)
                self.env["mail.mail"].create({
                    "subject": "Alert Liquidita — Runway %.0f EUR" % runway,
                    "email_to": antonio.email,
                    "body_html": body,
                }).send()
