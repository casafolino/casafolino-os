# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfHaccpCalibration(models.Model):
    _name = "cf.haccp.calibration"
    _description = "Calibrazione Strumento HACCP"
    _inherit = ["mail.thread"]
    _order = "date_next_calibration asc"
    _rec_name = "instrument_name"

    instrument_name = fields.Char(string="Nome Strumento", required=True)
    instrument_code = fields.Char(string="Codice")
    instrument_type = fields.Selection([
        ("thermometer","Termometro"),("scale","Bilancia"),("ph_meter","pH-metro"),
        ("hygrometer","Igrometro"),("timer","Timer"),("other","Altro"),
    ], string="Tipo", required=True)
    location = fields.Char(string="Ubicazione")
    workcenter_id = fields.Many2one("mrp.workcenter", string="Centro di Lavoro")
    state = fields.Selection([
        ("valid","Valida"),("expiring","In Scadenza"),("expired","Scaduta"),
    ], string="Stato", compute="_compute_state", store=True)
    date_last_calibration = fields.Date(string="Ultima Calibrazione")
    date_next_calibration = fields.Date(string="Prossima Calibrazione", required=True)
    calibration_interval_months = fields.Integer(string="Intervallo (mesi)", default=12)
    calibrated_by = fields.Many2one("res.users", string="Calibrato da")
    certificate_ref = fields.Char(string="N° Certificato")
    result_ok = fields.Boolean(string="Superata", default=True)
    notes = fields.Text(string="Note")

    @api.depends("date_next_calibration")
    def _compute_state(self):
        today = date.today()
        for rec in self:
            if not rec.date_next_calibration:
                rec.state = "expired"
                continue
            days = (rec.date_next_calibration - today).days
            rec.state = "expired" if days < 0 else "expiring" if days <= 30 else "valid"

    @api.model
    def send_expiring_alerts(self):
        expiring = self.search([("state", "in", ["expiring", "expired"])])
        for rec in expiring:
            rec.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=rec.date_next_calibration,
                note=f"Strumento {rec.instrument_name} richiede calibrazione.",
                user_id=rec.calibrated_by.id if rec.calibrated_by else self.env.uid,
            )

class CfHaccpCalibrationHistory(models.Model):
    _name = "cf.haccp.calibration.history"
    _description = "Storico Calibrazione"
    _order = "date desc"

    calibration_id = fields.Many2one("cf.haccp.calibration", required=True, ondelete="cascade")
    date = fields.Date(string="Data", required=True)
    calibrated_by = fields.Many2one("res.users", string="Eseguita da")
    result_ok = fields.Boolean(string="Superata", default=True)
    notes = fields.Text(string="Note")
