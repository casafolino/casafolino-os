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
    def _compute_live_data(self):
        """
        Calcola tutti i KPI tesoreria in tempo reale.
        Fonti: account.journal, account.move.line, account.move.
        Nessuna query SQL diretta — solo ORM.
        """
        today = date.today()
        today_str = str(today)
        d_90ago = str(today - timedelta(days=90))
        d30 = str(today + timedelta(days=30))
        d60 = str(today + timedelta(days=60))
        d90 = str(today + timedelta(days=90))

        # ==============================================================
        # 1. SALDO BANCHE/CASSA
        #    current_balance su account.account del journal bank/cash
        # ==============================================================
        journals = self.env["account.journal"].search([("type", "in", ("bank", "cash"))])
        total_balance = sum(
            j.default_account_id.current_balance
            for j in journals if j.default_account_id
        )
        # IDs dei conti liquidità — riutilizzati per cashflow e runway
        bank_account_ids = journals.mapped("default_account_id").ids

        aml = self.env["account.move.line"]

        # ==============================================================
        # 2. CREDITI DA INCASSARE (aging)
        #    account.move.line su conti asset_receivable, non riconciliati,
        #    move in stato posted. parent_state è indicizzato su aml.
        # ==============================================================
        base_recv = [
            ("account_id.account_type", "=", "asset_receivable"),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
        ]

        recv_overdue = sum(
            aml.search(base_recv + [("date_maturity", "<", today_str)])
            .mapped("amount_residual")
        )
        recv_30 = sum(
            aml.search(base_recv + [
                ("date_maturity", ">=", today_str),
                ("date_maturity", "<=", d30),
            ]).mapped("amount_residual")
        )
        recv_60 = sum(
            aml.search(base_recv + [
                ("date_maturity", ">", d30),
                ("date_maturity", "<=", d60),
            ]).mapped("amount_residual")
        )
        recv_90 = sum(
            aml.search(base_recv + [
                ("date_maturity", ">", d60),
                ("date_maturity", "<=", d90),
            ]).mapped("amount_residual")
        )

        # ==============================================================
        # 3. DEBITI DA PAGARE (aging)
        #    Stesso schema, liability_payable. amount_residual è negativo
        #    per i debiti, quindi prendiamo abs().
        # ==============================================================
        base_pay = [
            ("account_id.account_type", "=", "liability_payable"),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
        ]

        pay_overdue = abs(sum(
            aml.search(base_pay + [("date_maturity", "<", today_str)])
            .mapped("amount_residual")
        ))
        pay_30 = abs(sum(
            aml.search(base_pay + [
                ("date_maturity", ">=", today_str),
                ("date_maturity", "<=", d30),
            ]).mapped("amount_residual")
        ))
        pay_60 = abs(sum(
            aml.search(base_pay + [
                ("date_maturity", ">", d30),
                ("date_maturity", "<=", d60),
            ]).mapped("amount_residual")
        ))
        pay_90 = abs(sum(
            aml.search(base_pay + [
                ("date_maturity", ">", d60),
                ("date_maturity", "<=", d90),
            ]).mapped("amount_residual")
        ))

        # ==============================================================
        # 4. DSO — Days Sales Outstanding
        #    DSO = (totale crediti aperti / fatturato ultimi 90gg) × 90
        #    Fatturato = sum(amount_untaxed) su out_invoice posted
        # ==============================================================
        rev_groups = self.env["account.move"].read_group(
            domain=[
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", d_90ago),
                ("invoice_date", "<=", today_str),
            ],
            fields=["amount_untaxed:sum"],
            groupby=[],
        )
        revenue_90d = rev_groups[0]["amount_untaxed"] if rev_groups else 0.0
        total_recv = recv_overdue + recv_30 + recv_60 + recv_90
        dso = round((total_recv / revenue_90d * 90), 1) if revenue_90d > 0 else 0.0

        # ==============================================================
        # 5. RUNWAY — giorni di liquidità rimanenti
        #    Media uscite giornaliere = uscite effettive ultimi 90gg / 90
        #    Uscite = movimenti in avere (credit) sui conti banca/cassa
        #    da account.move.line, parent_state=posted
        # ==============================================================
        if bank_account_ids:
            out_groups = aml.read_group(
                domain=[
                    ("account_id", "in", bank_account_ids),
                    ("parent_state", "=", "posted"),
                    ("date", ">=", d_90ago),
                    ("date", "<=", today_str),
                    ("credit", ">", 0),
                ],
                fields=["credit:sum"],
                groupby=[],
            )
            total_outflow_90d = out_groups[0]["credit"] if out_groups else 0.0
        else:
            total_outflow_90d = 0.0

        avg_daily_outflow = total_outflow_90d / 90.0 if total_outflow_90d > 0 else 0.0
        runway_days = int(total_balance / avg_daily_outflow) if avg_daily_outflow > 0 and total_balance > 0 else 0

        # ==============================================================
        # 6. CASHFLOW 12 MESI
        #    Per ogni mese: movimenti in dare sui conti banca/cassa
        #    = inflow (incassi); movimenti in avere = outflow (pagamenti).
        #    Fonte: account.move.line con date = data effettiva.
        #    Usa read_group per evitare N query separate.
        # ==============================================================
        # Calcola start/end dei 12 mesi in anticipo
        month_ranges = []
        for i in range(11, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            ms = date(y, m, 1)
            if i == 0:
                me = today
            else:
                nm, ny = m + 1, y
                if nm > 12:
                    nm, ny = 1, y + 1
                me = date(ny, nm, 1) - timedelta(days=1)
            month_ranges.append((ms, me))

        period_start = str(month_ranges[0][0])
        period_end = str(month_ranges[-1][1])

        cashflow = []
        if bank_account_ids:
            # Fetch tutte le righe del periodo in un colpo solo
            cf_lines = aml.search([
                ("account_id", "in", bank_account_ids),
                ("parent_state", "=", "posted"),
                ("date", ">=", period_start),
                ("date", "<=", period_end),
            ], order="date asc")

            # Indicizza per mese
            month_totals = {}
            for line in cf_lines:
                key = (line.date.year, line.date.month)
                if key not in month_totals:
                    month_totals[key] = [0.0, 0.0]  # [debit, credit]
                month_totals[key][0] += line.debit
                month_totals[key][1] += line.credit

            for ms, me in month_ranges:
                key = (ms.year, ms.month)
                debit, credit = month_totals.get(key, [0.0, 0.0])
                inflow = round(debit, 2)
                outflow = round(credit, 2)
                cashflow.append({
                    "month": ms.strftime("%b %Y"),
                    "inflow": inflow,
                    "outflow": outflow,
                    "balance": round(inflow - outflow, 2),
                })
        else:
            for ms, _me in month_ranges:
                cashflow.append({
                    "month": ms.strftime("%b %Y"),
                    "inflow": 0.0,
                    "outflow": 0.0,
                    "balance": 0.0,
                })

        # ==============================================================
        # 7. SCENARI 90GG
        #    Base trend: media mensile inflow/outflow degli ultimi 90gg
        #    da account.move.line banca (stessa fonte del cashflow).
        #    - Base:         saldo + net_monthly × 3
        #    - Ottimistico:  saldo + (inflow×1.15 − outflow) × 3
        #    - Pessimistico: saldo + (inflow×0.75 − outflow×1.10) × 3
        # ==============================================================
        # Media mensile inflow/outflow dagli ultimi 3 mesi già calcolati
        recent_inflow_90d = sum(
            m["inflow"] for m in cashflow[-3:]
        ) if len(cashflow) >= 3 else 0.0
        recent_outflow_90d = sum(
            m["outflow"] for m in cashflow[-3:]
        ) if len(cashflow) >= 3 else 0.0

        avg_monthly_inflow = recent_inflow_90d / 3.0
        avg_monthly_outflow = recent_outflow_90d / 3.0

        scenario_base = round(total_balance + (avg_monthly_inflow - avg_monthly_outflow) * 3, 2)
        scenario_opt = round(total_balance + (avg_monthly_inflow * 1.15 - avg_monthly_outflow) * 3, 2)
        scenario_pes = round(total_balance + (avg_monthly_inflow * 0.75 - avg_monthly_outflow * 1.10) * 3, 2)

        return {
            "today_str": today_str,
            "total_balance": total_balance,
            "recv_overdue": recv_overdue,
            "recv_30": recv_30,
            "recv_60": recv_60,
            "recv_90": recv_90,
            "pay_overdue": pay_overdue,
            "pay_30": pay_30,
            "pay_60": pay_60,
            "pay_90": pay_90,
            "dso": dso,
            "runway_days": runway_days,
            "scenario_base": scenario_base,
            "scenario_opt": scenario_opt,
            "scenario_pes": scenario_pes,
            "cashflow": cashflow,
        }

    @api.model
    def get_dashboard_data(self):
        """Restituisce i dati tesoreria in tempo reale, senza bisogno di snapshot."""
        d = self._compute_live_data()
        return {
            "has_data": True,
            "date": d["today_str"],
            "total_balance": d["total_balance"],
            "runway_days": d["runway_days"],
            "receivables_overdue": d["recv_overdue"],
            "receivables_30d": d["recv_30"],
            "receivables_60d": d["recv_60"],
            "receivables_90d": d["recv_90"],
            "payables_overdue": d["pay_overdue"],
            "payables_30d": d["pay_30"],
            "payables_60d": d["pay_60"],
            "payables_90d": d["pay_90"],
            "dso": d["dso"],
            "scenario_base": d["scenario_base"],
            "scenario_opt": d["scenario_opt"],
            "scenario_pes": d["scenario_pes"],
            "cashflow": d["cashflow"],
            "currency_symbol": self.env.ref("base.EUR").symbol,
        }

    @api.model
    def create_daily_snapshot(self):
        """Salva uno snapshot giornaliero per storico. Usa _compute_live_data()."""
        today = date.today()
        if self.search([("date", "=", today)]):
            return
        d = self._compute_live_data()
        self.create({
            "date": today,
            "total_balance": d["total_balance"],
            "receivable_30d": d["recv_30"],
            "payable_30d": d["pay_30"],
            "receivables_overdue": d["recv_overdue"],
            "receivables_30d": d["recv_30"],
            "receivables_60d": d["recv_60"],
            "receivables_90d": d["recv_90"],
            "payables_overdue": d["pay_overdue"],
            "payables_30d": d["pay_30"],
            "payables_60d": d["pay_60"],
            "payables_90d": d["pay_90"],
            "dso": d["dso"],
            "runway_days": d["runway_days"],
            "scenario_base": d["scenario_base"],
            "scenario_opt": d["scenario_opt"],
            "scenario_pes": d["scenario_pes"],
            "cashflow_json": json.dumps(d["cashflow"]),
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
