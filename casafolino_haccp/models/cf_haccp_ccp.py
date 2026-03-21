# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfHaccpCcp(models.Model):
    _name = "cf.haccp.ccp"
    _description = "Punto Critico di Controllo"
    _order = "sp_id, sequence"

    sp_id = fields.Many2one("cf.haccp.sp", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Nome CCP", required=True)
    ccp_type = fields.Selection([
        ("temperature","Temperatura"),("time","Tempo"),("ph","pH"),
        ("aw","Attivita Acqua"),("visual","Visivo"),("weight","Peso"),("other","Altro"),
    ], string="Tipo", required=True)
    critical_limit_min = fields.Float(string="Limite Min")
    critical_limit_max = fields.Float(string="Limite Max")
    unit = fields.Char(string="Unita")
    corrective_action = fields.Text(string="Azione Correttiva")
    measured_value = fields.Float(string="Valore Misurato")
    visual_ok = fields.Boolean(string="Visivo OK")
    measurement_time = fields.Datetime(string="Ora Misurazione")
    measured_by = fields.Many2one("res.users", string="Rilevato da", default=lambda self: self.env.user)
    notes = fields.Text(string="Note")
    state = fields.Selection([
        ("pending","Da Misurare"),("ok","OK"),("ko","Fuori Limite"),
    ], string="Esito", default="pending", compute="_compute_state", store=True)

    @api.depends("measured_value","visual_ok","ccp_type","critical_limit_min","critical_limit_max","measurement_time")
    def _compute_state(self):
        for rec in self:
            if not rec.measurement_time:
                rec.state = "pending"
                continue
            if rec.ccp_type == "visual":
                rec.state = "ok" if rec.visual_ok else "ko"
            else:
                in_range = True
                if rec.critical_limit_min and rec.measured_value < rec.critical_limit_min:
                    in_range = False
                if rec.critical_limit_max and rec.measured_value > rec.critical_limit_max:
                    in_range = False
                rec.state = "ok" if in_range else "ko"
