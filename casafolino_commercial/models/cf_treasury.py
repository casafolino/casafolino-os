# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta

class CfTreasury(models.Model):
    _name = "cf.treasury.snapshot"
    _description = "Snapshot Tesoreria"
    _order = "date desc"
    _rec_name = "date"

    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    total_balance = fields.Monetary(string="Saldo Totale", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    receivable_30d = fields.Monetary(string="Crediti 30gg", currency_field="currency_id")
    payable_30d = fields.Monetary(string="Debiti 30gg", currency_field="currency_id")
    forecast_30d = fields.Monetary(string="Forecast 30gg", currency_field="currency_id", compute="_compute_forecast", store=True)
    forecast_60d = fields.Monetary(string="Forecast 60gg", currency_field="currency_id", compute="_compute_forecast", store=True)
    forecast_90d = fields.Monetary(string="Forecast 90gg", currency_field="currency_id", compute="_compute_forecast", store=True)
    notes = fields.Text(string="Note")

    @api.depends("total_balance","receivable_30d","payable_30d")
    def _compute_forecast(self):
        for rec in self:
            base = rec.total_balance + rec.receivable_30d - rec.payable_30d
            rec.forecast_30d = base
            rec.forecast_60d = base * 1.05
            rec.forecast_90d = base * 1.10

    @api.model
    def get_dashboard_data(self):
        snapshots = self.search([], limit=90, order="date desc")
        if not snapshots:
            return {"has_data": False}
        latest = snapshots[0]
        history = [{"date": str(s.date), "balance": s.total_balance} for s in reversed(snapshots)]
        currency_symbol = self.env.ref("base.EUR").symbol
        return {
            "has_data": True,
            "date": str(latest.date),
            "total_balance": latest.total_balance,
            "receivable_30d": latest.receivable_30d,
            "payable_30d": latest.payable_30d,
            "forecast_30d": latest.forecast_30d,
            "forecast_60d": latest.forecast_60d,
            "forecast_90d": latest.forecast_90d,
            "currency_symbol": currency_symbol,
            "history": history[-30:],
        }

    @api.model
    def create_daily_snapshot(self):
        today = date.today()
        existing = self.search([("date","=",today)])
        if existing: return
        journals = self.env["account.journal"].search([("type","in",("bank","cash"))])
        total = sum(j.default_account_id.current_balance for j in journals if j.default_account_id)
        domain_recv = [("account_id.account_type","=","asset_receivable"),
                       ("reconciled","=",False),("date_maturity","<=",str(today+timedelta(days=30)))]
        domain_pay  = [("account_id.account_type","=","liability_payable"),
                       ("reconciled","=",False),("date_maturity","<=",str(today+timedelta(days=30)))]
        recv = sum(self.env["account.move.line"].search(domain_recv).mapped("amount_residual"))
        pay  = abs(sum(self.env["account.move.line"].search(domain_pay).mapped("amount_residual")))
        self.create({"date":today,"total_balance":total,"receivable_30d":recv,"payable_30d":pay})

    @api.model
    def cron_liquidity_alert(self):
        """Alert se liquidita scende sotto soglia."""
        threshold = float(self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.treasury_alert_threshold', '10000'))

        journals = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))])
        cash_available = sum(
            j.default_account_id.current_balance for j in journals if j.default_account_id
        )

        cutoff = date.today() + timedelta(days=30)
        pending_bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'in_payment']),
            ('invoice_date_due', '<=', str(cutoff)),
        ])
        outflows = sum(pending_bills.mapped('amount_residual'))
        runway = cash_available - outflows

        if runway < threshold:
            antonio = self.env['res.users'].search(
                [('login', '=', 'antonio@casafolino.com')], limit=1)
            if antonio and antonio.email:
                body = (
                    "<p><b>Alert Liquidita CasaFolino</b></p>"
                    "<p>Cash disponibile: <b>%s %.0f</b></p>"
                    "<p>Uscite previste 30gg: <b>%s %.0f</b></p>"
                    "<p>Cash runway netto: <b>%s %.0f</b></p>"
                    "<p>Soglia configurata: %s %.0f</p>"
                ) % ('€', cash_available, '€', outflows, '€', runway, '€', threshold)
                self.env['mail.mail'].create({
                    'subject': 'Alert Liquidita — Runway %.0f EUR' % runway,
                    'email_to': antonio.email,
                    'body_html': body,
                }).send()
