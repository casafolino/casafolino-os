# -*- coding: utf-8 -*-
from odoo import models, fields

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
    description = fields.Text(string="Descrizione", required=True)
    corrective_action = fields.Text(string="Azione Correttiva")
    notes = fields.Text(string="Note")

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

        return {
            "nc_open": nc_counts.get("open", 0),
            "nc_analysis": nc_counts.get("analysis", 0),
            "nc_action": nc_counts.get("action", 0),
            "nc_critical_open": critical_open,
            "instruments_expiring": calib.search_count([("state", "=", "expiring")]),
            "instruments_expired": calib.search_count([("state", "=", "expired")]),
            "docs_expiring": docs.search_count([("state", "=", "expiring")]),
            "docs_expired": docs.search_count([("state", "=", "expired")]),
            "overall_state": (
                "red" if (critical_open > 0 or calib.search_count([("state", "=", "expired")]) > 0)
                else "yellow" if (nc_counts.get("open", 0) > 0 or calib.search_count([("state", "=", "expiring")]) > 0)
                else "green"
            ),
        }
