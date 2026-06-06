# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfHaccpNc(models.Model):
    _name = "cf.haccp.nc"
    _description = "Non Conformita HACCP"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(string="N° NC", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.nc") or "NC-NUOVO")
    state = fields.Selection([
        ("open","Aperta"),("analysis","In Analisi"),("action","Azione Correttiva"),
        ("verified","Verificata"),("closed","Chiusa"),("cancelled","Annullata"),
    ], string="Stato", default="open", tracking=True, required=True)
    severity = fields.Selection([
        ("low","Bassa"),("medium","Media"),("high","Alta"),("critical","Critica"),
    ], string="Gravita", default="medium", tracking=True, required=True)
    origin = fields.Selection([
        ("ccp","CCP Fuori Limite"),("receipt","Controllo Ricezione"),
        ("manual","Segnalazione Manuale"),("audit","Audit"),("customer","Reclamo Cliente"),
    ], string="Origine", default="manual", required=True)
    sp_id = fields.Many2one("cf.haccp.sp", string="Scheda Produzione")
    ccp_id = fields.Many2one("cf.haccp.ccp", string="CCP")
    receipt_id = fields.Many2one("cf.haccp.receipt", string="Ricezione")
    product_id = fields.Many2one("product.template", string="Prodotto")
    lot_id = fields.Many2one("stock.lot", string="Lotto")
    date = fields.Datetime(string="Data", default=fields.Datetime.now)
    reported_by = fields.Many2one("res.users", string="Segnalato da", default=lambda self: self.env.user)
    assigned_to = fields.Many2one("res.users", string="Assegnato a")
    responsabile_id = fields.Many2one("res.users", string="Responsabile chiusura")
    description = fields.Text(string="Descrizione", required=True)
    corrective_action = fields.Text(string="Azione Correttiva")
    azione_correttiva = fields.Text(string="Azione Correttiva Dettagliata")
    verifica_efficacia = fields.Text(string="Verifica Efficacia")
    data_chiusura = fields.Date(string="Data Chiusura Effettiva")
    notes = fields.Text(string="Note")
    firma_digitale = fields.Binary(string="Firma Digitale")

    def action_to_analysis(self):
        self.write({"state": "analysis"})

    def action_to_corrective(self):
        self.write({"state": "action"})

    def action_to_verified(self):
        self.write({"state": "verified"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    @api.model
    def get_dashboard_data(self):
        nc_counts = {}
        for key in ("open", "analysis", "action", "verified", "closed", "cancelled"):
            nc_counts[key] = self.search_count([("state", "=", key)])

        critical_open = self.search_count([
            ("state", "not in", ("closed", "cancelled")),
            ("severity", "in", ("high", "critical")),
        ])

        calib = self.env["cf.haccp.calibration"]
        docs = self.env["cf.haccp.document"]
        picking = self.env["stock.picking"]
        production = self.env["mrp.production"]
        trace = self.env["cf.haccp.tracciabilita"]
        quarantine = self.env["cf.haccp.quarantine"]
        temperature = self.env["cf.haccp.temperature.log"]
        sanification = self.env["cf.haccp.sanification.log"]
        ccp_log = self.env["cf.haccp.ccp.log"]

        today = fields.Date.today()
        temp_pending_today = temperature.search_count([
            ("date", "=", today), ("esito", "=", "pending")])
        temp_ko_today = temperature.search_count([
            ("date", "=", today), ("esito", "=", "ko")])
        san_missing_today = sanification.search_count([
            ("date", "=", today), ("eseguita", "=", False)])
        ccp_ko = ccp_log.search_count([
            ("esito", "=", "fuori_limite")])
        pest_next = self.env["cf.haccp.pest.control"].search(
            [("prossima_visita", "!=", False)], limit=1, order="prossima_visita asc")
        recent_traces = trace.search([], limit=5, order="date desc, id desc")
        all_traces = trace.search([])
        active_quarantines = quarantine.search([("state", "=", "active")], limit=5, order="date_start desc")
        receipt_pending = picking.search_count([
            ("picking_type_code", "=", "incoming"),
            ("haccp_state", "=", "pending"),
        ])
        receipt_done = picking.search_count([
            ("picking_type_code", "=", "incoming"),
            ("haccp_state", "=", "done"),
        ])
        receipt_blocked = picking.search_count([
            ("picking_type_code", "=", "incoming"),
            ("haccp_esito", "in", ("quarantena", "rifiutato")),
        ])
        production_pending = production.search_count([("haccp_state", "=", "pending")])
        production_done = production.search_count([("haccp_state", "=", "done")])
        production_blocked = production.search_count([
            ("haccp_esito", "in", ("non_conforme", "bloccato", "attesa_analisi")),
        ])
        traced_lots = len(all_traces)
        trace_with_customer = len(all_traces.filtered(lambda rec: rec.customer_count > 0))
        trace_coverage = round((trace_with_customer / traced_lots) * 100) if traced_lots else 0
        trace_ready_score = round(
            sum(all_traces.mapped("audit_ready_score")) / traced_lots
        ) if traced_lots else 0
        trace_recall_tested = len(all_traces.filtered(lambda rec: rec.recall_test_date))
        trace_blocked = len(all_traces.filtered(lambda rec: rec.trace_status == "blocked"))
        audit_alerts = (
            critical_open + temp_ko_today + temp_pending_today + san_missing_today +
            ccp_ko + quarantine.search_count([("state", "=", "active")]) +
            receipt_pending + production_pending +
            calib.search_count([("state", "=", "expired")]) +
            docs.search_count([("state", "=", "expired")])
        )

        return {
            "nc_open": nc_counts.get("open", 0),
            "nc_analysis": nc_counts.get("analysis", 0),
            "nc_action": nc_counts.get("action", 0),
            "nc_closed": nc_counts.get("closed", 0),
            "nc_critical_open": critical_open,
            "receipt_pending": receipt_pending,
            "receipt_done": receipt_done,
            "receipt_blocked": receipt_blocked,
            "production_pending": production_pending,
            "production_done": production_done,
            "production_blocked": production_blocked,
            "traced_lots": traced_lots,
            "trace_with_customer": trace_with_customer,
            "trace_coverage": trace_coverage,
            "trace_ready_score": trace_ready_score,
            "trace_recall_tested": trace_recall_tested,
            "trace_blocked": trace_blocked,
            "active_quarantines": quarantine.search_count([("state", "=", "active")]),
            "instruments_expiring": calib.search_count([("state", "=", "expiring")]),
            "instruments_expired": calib.search_count([("state", "=", "expired")]),
            "docs_expiring": docs.search_count([("state", "=", "expiring")]),
            "docs_expired": docs.search_count([("state", "=", "expired")]),
            "temp_pending_today": temp_pending_today,
            "temp_ko_today": temp_ko_today,
            "san_missing_today": san_missing_today,
            "ccp_ko_total": ccp_ko,
            "pest_next_visit": str(pest_next.prossima_visita) if pest_next else "",
            "audit_alerts": audit_alerts,
            "recent_traces": [{
                "id": rec.id,
                "lotto_pf": rec.lotto_pf or "-",
                "lotto_mp": rec.lotto_mp or "-",
                "date": str(rec.date or ""),
                "production": rec.production_id.name or "-",
                "customers": ", ".join((rec.partner_ids | rec.auto_partner_ids).mapped("name")[:2]) or "-",
                "audit_ready_score": rec.audit_ready_score,
                "mass_balance": rec.mass_balance_status or "missing",
                "status": rec.trace_status or "watch",
                "status_label": dict(rec._fields["trace_status"].selection).get(
                    rec.trace_status, "Da presidiare"),
                "risk_count": rec.nc_count + rec.quarantine_count + rec.ccp_ko_count,
            } for rec in recent_traces],
            "active_quarantine_rows": [{
                "id": rec.id,
                "reference": rec.reference,
                "lot": rec.lot_id.name or "-",
                "product": rec.product_id.display_name or "-",
                "date_start": str(rec.date_start or ""),
            } for rec in active_quarantines],
            "overall_state": (
                "red" if (critical_open > 0 or temp_ko_today > 0 or receipt_blocked > 0 or
                          production_blocked > 0 or quarantine.search_count([("state", "=", "active")]) > 0 or
                          calib.search_count([("state", "=", "expired")]) > 0)
                else "yellow" if (nc_counts.get("open", 0) > 0 or ccp_ko > 0 or
                                   receipt_pending > 0 or production_pending > 0 or
                                   temp_pending_today > 0 or san_missing_today > 0 or
                                   calib.search_count([("state", "=", "expiring")]) > 0)
                else "green"
            ),
        }
