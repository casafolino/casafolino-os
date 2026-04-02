# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CfHaccpTemperatureLog(models.Model):
    _name = "cf.haccp.temperature.log"
    _description = "Registro Temperature HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"

    date = fields.Date(string="Data", required=True, default=fields.Date.today,
                       tracking=True)
    frigo1_temp = fields.Float(string="Frigo 1 (°C)", digits=(5, 1))
    frigo2_temp = fields.Float(string="Frigo 2 (°C)", digits=(5, 1))
    ambiente_temp = fields.Float(string="Temperatura Ambiente (°C)", digits=(5, 1))
    esito = fields.Selection([
        ('ok', 'OK — Tutto nei limiti'),
        ('ko', 'KO — Superato limite critico'),
    ], string="Esito", compute="_compute_esito", store=True, tracking=True)
    operatore_id = fields.Many2one("res.users", string="Operatore",
                                    default=lambda self: self.env.user)
    firma_digitale = fields.Binary(string="Firma Digitale")
    note = fields.Text(string="Note / Azioni correttive")

    # Limite critico: frigo ≤ 4°C
    LIMITE_FRIGO = 4.0

    @api.depends("frigo1_temp", "frigo2_temp")
    def _compute_esito(self):
        for rec in self:
            if (rec.frigo1_temp and rec.frigo1_temp > self.LIMITE_FRIGO) or \
               (rec.frigo2_temp and rec.frigo2_temp > self.LIMITE_FRIGO):
                rec.esito = 'ko'
            else:
                rec.esito = 'ok'

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.esito == 'ko':
            _logger.warning(
                "HACCP ALERT: temperatura frigo fuori limite il %s — "
                "Frigo1: %s°C, Frigo2: %s°C",
                rec.date, rec.frigo1_temp, rec.frigo2_temp)
        return rec
