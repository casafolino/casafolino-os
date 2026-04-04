# -*- coding: utf-8 -*-
from odoo import models, fields


class CfHaccpIgienePersonale(models.Model):
    _name = "cf.haccp.igiene.personale"
    _description = "Check Igiene Personale HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"

    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    operatore_id = fields.Many2one("res.users", string="Operatore",
                                    required=True,
                                    default=lambda self: self.env.user)
    mani_lavate = fields.Boolean(string="Mani lavate correttamente",
                                  default=False)
    dpi_ok = fields.Boolean(string="DPI indossati correttamente", default=False)
    no_gioielli = fields.Boolean(string="Nessun gioiello / accessori", default=False)
    stato_salute_ok = fields.Boolean(
        string="Stato di salute idoneo (nessuna malattia infettiva)",
        default=False)
    firma_digitale = fields.Binary(string="Firma Digitale")
