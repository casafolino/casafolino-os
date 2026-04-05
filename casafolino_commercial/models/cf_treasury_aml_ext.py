# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date as _date


class AccountMoveLineExt(models.Model):
    _inherit = "account.move.line"

    x_treasury_note = fields.Text(string="Note Tesoreria")
    x_treasury_date_prevista = fields.Date(string="Data Incasso/Pagamento Prevista")
    x_treasury_stato = fields.Selection([
        ("da_fare", "Da Fare"),
        ("approvato", "Approvato"),
        ("fatto", "Fatto"),
    ], string="Stato Tesoreria", default="da_fare")

    # Campi calcolati per display (non stored — dipendono da "oggi")
    x_treasury_overdue_days = fields.Integer(
        string="Giorni Scaduto",
        compute="_compute_treasury_aging",
        store=False,
    )
    x_treasury_aging_bucket = fields.Selection([
        ("scaduto", "Scaduto"),
        ("0_30", "0-30 gg"),
        ("31_60", "31-60 gg"),
        ("61_90", "61-90 gg"),
        ("oltre_90", ">90 gg"),
    ], string="Fascia", compute="_compute_treasury_aging", store=False)

    @api.depends("date_maturity")
    def _compute_treasury_aging(self):
        today = _date.today()
        for rec in self:
            dm = rec.date_maturity
            if not dm:
                rec.x_treasury_overdue_days = 0
                rec.x_treasury_aging_bucket = False
                continue
            delta = (dm - today).days
            if delta < 0:
                rec.x_treasury_overdue_days = abs(delta)
                rec.x_treasury_aging_bucket = "scaduto"
            elif delta <= 30:
                rec.x_treasury_overdue_days = 0
                rec.x_treasury_aging_bucket = "0_30"
            elif delta <= 60:
                rec.x_treasury_overdue_days = 0
                rec.x_treasury_aging_bucket = "31_60"
            elif delta <= 90:
                rec.x_treasury_overdue_days = 0
                rec.x_treasury_aging_bucket = "61_90"
            else:
                rec.x_treasury_overdue_days = 0
                rec.x_treasury_aging_bucket = "oltre_90"
