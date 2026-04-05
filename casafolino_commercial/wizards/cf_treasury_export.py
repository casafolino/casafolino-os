# -*- coding: utf-8 -*-
import io
import base64
from datetime import date

from odoo import models, fields
from odoo.exceptions import UserError

try:
    import xlsxwriter
    _HAS_XLS = True
except ImportError:
    _HAS_XLS = False


class CfTreasuryExportWizard(models.TransientModel):
    _name = "cf.treasury.export.wizard"
    _description = "Esporta Dati Tesoreria XLS"

    section = fields.Selection([
        ("receivables", "Crediti Clienti"),
        ("payables", "Debiti Fornitori"),
        ("cashflow", "Cashflow"),
        ("snapshots", "Snapshots"),
    ], string="Sezione", required=True, default="receivables")
    date_from = fields.Date(
        string="Dal",
        default=lambda self: date(date.today().year, 1, 1),
    )
    date_to = fields.Date(string="Al", default=fields.Date.today)

    def action_export(self):
        if not _HAS_XLS:
            raise UserError("Installa xlsxwriter: pip install xlsxwriter")
        handlers = {
            "receivables": self._export_receivables,
            "payables": self._export_payables,
            "cashflow": self._export_cashflow,
            "snapshots": self._export_snapshots,
        }
        return handlers[self.section]()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_workbook(self):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        hdr = wb.add_format({
            "bold": True, "bg_color": "#5A6E3A",
            "font_color": "#FFFFFF", "border": 1,
        })
        cell = wb.add_format({"border": 1})
        money = wb.add_format({"border": 1, "num_format": "#,##0.00"})
        return wb, output, hdr, cell, money

    def _attach_and_return(self, wb, output, filename):
        wb.close()
        data = base64.b64encode(output.getvalue()).decode()
        att = self.env["ir.attachment"].create({
            "name": filename,
            "type": "binary",
            "datas": data,
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": (
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{att.id}?download=true",
            "target": "self",
        }

    @staticmethod
    def _aging_bucket(dm, today):
        if not dm:
            return 0, ""
        delta = (dm - today).days
        if delta < 0:
            return abs(delta), "Scaduto"
        if delta <= 30:
            return 0, "0-30 gg"
        if delta <= 60:
            return 0, "31-60 gg"
        if delta <= 90:
            return 0, "61-90 gg"
        return 0, ">90 gg"

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    def _export_receivables(self):
        wb, output, hdr, cell, money = self._make_workbook()
        ws = wb.add_worksheet("Crediti Clienti")
        cols = ["Cliente", "Fattura", "Scadenza", "Data Incasso Prevista",
                "Da Incassare", "Giorni Scaduto", "Fascia", "Stato", "Note"]
        for c, h in enumerate(cols):
            ws.write(0, c, h, hdr)

        today = date.today()
        domain = [
            ("account_id.account_type", "=", "asset_receivable"),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
        ]
        if self.date_from:
            domain.append(("date_maturity", ">=", str(self.date_from)))
        if self.date_to:
            domain.append(("date_maturity", "<=", str(self.date_to)))

        stato_labels = dict(
            self.env["account.move.line"]._fields["x_treasury_stato"].selection
        )
        for r, ln in enumerate(
            self.env["account.move.line"].search(domain, order="date_maturity asc"), 1
        ):
            overdue, bucket = self._aging_bucket(ln.date_maturity, today)
            ws.write(r, 0, ln.partner_id.name or "", cell)
            ws.write(r, 1, ln.move_id.name or "", cell)
            ws.write(r, 2, str(ln.date_maturity) if ln.date_maturity else "", cell)
            ws.write(r, 3, str(ln.x_treasury_date_prevista) if ln.x_treasury_date_prevista else "", cell)
            ws.write(r, 4, ln.amount_residual, money)
            ws.write(r, 5, overdue, cell)
            ws.write(r, 6, bucket, cell)
            ws.write(r, 7, stato_labels.get(ln.x_treasury_stato, ""), cell)
            ws.write(r, 8, ln.x_treasury_note or "", cell)

        ws.set_column(0, 0, 32)
        ws.set_column(1, 3, 16)
        ws.set_column(4, 4, 16)
        return self._attach_and_return(wb, output, "crediti_clienti.xlsx")

    def _export_payables(self):
        wb, output, hdr, cell, money = self._make_workbook()
        ws = wb.add_worksheet("Debiti Fornitori")
        cols = ["Fornitore", "Fattura", "Scadenza", "Data Pagamento Pianificata",
                "Da Pagare", "Giorni Scaduto", "Fascia", "Stato", "Note"]
        for c, h in enumerate(cols):
            ws.write(0, c, h, hdr)

        today = date.today()
        domain = [
            ("account_id.account_type", "=", "liability_payable"),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
        ]
        if self.date_from:
            domain.append(("date_maturity", ">=", str(self.date_from)))
        if self.date_to:
            domain.append(("date_maturity", "<=", str(self.date_to)))

        stato_labels = dict(
            self.env["account.move.line"]._fields["x_treasury_stato"].selection
        )
        for r, ln in enumerate(
            self.env["account.move.line"].search(domain, order="date_maturity asc"), 1
        ):
            overdue, bucket = self._aging_bucket(ln.date_maturity, today)
            ws.write(r, 0, ln.partner_id.name or "", cell)
            ws.write(r, 1, ln.move_id.name or "", cell)
            ws.write(r, 2, str(ln.date_maturity) if ln.date_maturity else "", cell)
            ws.write(r, 3, str(ln.x_treasury_date_prevista) if ln.x_treasury_date_prevista else "", cell)
            ws.write(r, 4, abs(ln.amount_residual), money)
            ws.write(r, 5, overdue, cell)
            ws.write(r, 6, bucket, cell)
            ws.write(r, 7, stato_labels.get(ln.x_treasury_stato, ""), cell)
            ws.write(r, 8, ln.x_treasury_note or "", cell)

        ws.set_column(0, 0, 32)
        ws.set_column(1, 3, 16)
        ws.set_column(4, 4, 16)
        return self._attach_and_return(wb, output, "debiti_fornitori.xlsx")

    def _export_cashflow(self):
        wb, output, hdr, cell, money = self._make_workbook()
        ws = wb.add_worksheet("Cashflow")
        cols = ["Data", "Descrizione", "Tipo", "Importo", "Conto", "Origine", "Note"]
        for c, h in enumerate(cols):
            ws.write(0, c, h, hdr)

        domain = []
        if self.date_from:
            domain.append(("date", ">=", str(self.date_from)))
        if self.date_to:
            domain.append(("date", "<=", str(self.date_to)))

        type_map = {"in": "Entrata", "out": "Uscita", "forecast": "Previsione"}
        for r, ln in enumerate(
            self.env["cf.treasury.cashflow.line"].search(domain, order="date asc"), 1
        ):
            ws.write(r, 0, str(ln.date) if ln.date else "", cell)
            ws.write(r, 1, ln.name or "", cell)
            ws.write(r, 2, type_map.get(ln.move_type, ""), cell)
            ws.write(r, 3, ln.amount, money)
            ws.write(r, 4, ln.journal_id.name or "", cell)
            ws.write(r, 5, "Automatica" if ln.source == "auto" else "Manuale", cell)
            ws.write(r, 6, ln.note or "", cell)

        ws.set_column(0, 0, 12)
        ws.set_column(1, 1, 36)
        ws.set_column(3, 3, 16)
        return self._attach_and_return(wb, output, "cashflow.xlsx")

    def _export_snapshots(self):
        wb, output, hdr, cell, money = self._make_workbook()
        ws = wb.add_worksheet("Snapshots")
        cols = ["Data", "Saldo Banca", "Crediti Scaduti", "Debiti Scaduti",
                "DSO", "Runway", "Scenario Base", "Scenario Ott.", "Scenario Pess."]
        for c, h in enumerate(cols):
            ws.write(0, c, h, hdr)

        domain = []
        if self.date_from:
            domain.append(("date", ">=", str(self.date_from)))
        if self.date_to:
            domain.append(("date", "<=", str(self.date_to)))

        for r, s in enumerate(
            self.env["cf.treasury.snapshot"].search(domain, order="date desc"), 1
        ):
            ws.write(r, 0, str(s.date), cell)
            ws.write(r, 1, s.total_balance, money)
            ws.write(r, 2, s.receivables_overdue, money)
            ws.write(r, 3, s.payables_overdue, money)
            ws.write(r, 4, s.dso, cell)
            ws.write(r, 5, s.runway_days, cell)
            ws.write(r, 6, s.scenario_base, money)
            ws.write(r, 7, s.scenario_opt, money)
            ws.write(r, 8, s.scenario_pes, money)

        ws.set_column(0, 0, 12)
        ws.set_column(1, 8, 16)
        return self._attach_and_return(wb, output, "snapshots.xlsx")
