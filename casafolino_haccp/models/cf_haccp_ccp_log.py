# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CfHaccpCcpLog(models.Model):
    _name = "cf.haccp.ccp.log"
    _description = "Registro CCP — Punti di Controllo Critico"
    _inherit = ["mail.thread"]
    _order = "date desc"

    date = fields.Datetime(string="Data/Ora", required=True,
                            default=fields.Datetime.now)
    ccp_type = fields.Selection([
        ('temperaggio_cioccolato', 'Temperaggio Cioccolato'),
        ('umidita', 'Controllo Umidità'),
        ('contaminazione', 'Rischio Contaminazione'),
        ('altro', 'Altro CCP'),
    ], string="Tipo CCP", required=True, default='temperaggio_cioccolato')
    temperatura_ingresso = fields.Float(string="T° ingresso (°C)", default=50.0,
                                         digits=(5, 1))
    temperatura_min = fields.Float(string="T° min limite (°C)", default=27.0,
                                    digits=(5, 1))
    temperatura_max = fields.Float(string="T° max limite (°C)", default=31.0,
                                    digits=(5, 1))
    temperatura_uscita = fields.Float(string="T° uscita (°C)", default=30.5,
                                       digits=(5, 1))
    esito = fields.Selection([
        ('ok', 'OK — Nei limiti'),
        ('fuori_limite', 'FUORI LIMITE — Azione richiesta'),
    ], string="Esito", compute="_compute_esito", store=True, tracking=True)
    azione_correttiva = fields.Text(string="Azione Correttiva Applicata")
    operatore_id = fields.Many2one("res.users", string="Operatore",
                                    default=lambda self: self.env.user)
    production_id = fields.Many2one("mrp.production", string="Ordine di Produzione")
    firma_digitale = fields.Binary(string="Firma Digitale")

    @api.depends("temperatura_uscita", "temperatura_min", "temperatura_max")
    def _compute_esito(self):
        for rec in self:
            if rec.temperatura_uscita and (
                rec.temperatura_uscita < rec.temperatura_min or
                rec.temperatura_uscita > rec.temperatura_max
            ):
                rec.esito = 'fuori_limite'
            else:
                rec.esito = 'ok'

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.esito == 'fuori_limite':
            _logger.warning(
                "HACCP CCP ALERT: temperatura uscita %s°C fuori limite [%s-%s°C] "
                "— CCP: %s",
                rec.temperatura_uscita, rec.temperatura_min,
                rec.temperatura_max, rec.ccp_type)
        return rec


class MrpProductionCcp(models.Model):
    _inherit = "mrp.production"

    ccp_log_ids = fields.One2many("cf.haccp.ccp.log", "production_id",
                                   string="Log CCP")
    ccp_ok = fields.Boolean(compute="_compute_ccp_ok", string="CCP OK",
                             store=True)

    @api.depends("ccp_log_ids", "ccp_log_ids.esito")
    def _compute_ccp_ok(self):
        for rec in self:
            ko = rec.ccp_log_ids.filtered(lambda c: c.esito == 'fuori_limite')
            rec.ccp_ok = not bool(ko)
