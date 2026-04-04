# -*- coding: utf-8 -*-
from odoo import models, fields


class CfHaccpPestControl(models.Model):
    _name = "cf.haccp.pest.control"
    _description = "Pest Control HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"

    date = fields.Date(string="Data Ispezione", required=True,
                        default=fields.Date.today)
    esche_integre = fields.Boolean(string="Esche integre", default=True)
    tracce_infestanti = fields.Boolean(string="Tracce infestanti rilevate",
                                        default=False)
    mappa_aggiornata = fields.Boolean(string="Mappa trappole aggiornata",
                                       default=True)
    azienda_esterna = fields.Char(string="Azienda DDD esterna")
    prossima_visita = fields.Date(string="Prossima visita programmata")
    operatore_id = fields.Many2one("res.users", string="Operatore",
                                    default=lambda self: self.env.user)
    firma_digitale = fields.Binary(string="Firma Digitale")
    note = fields.Text(string="Note / Osservazioni")
