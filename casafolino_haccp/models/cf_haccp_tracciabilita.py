# -*- coding: utf-8 -*-
from odoo import models, fields


class CfHaccpTracciabilita(models.Model):
    _name = "cf.haccp.tracciabilita"
    _description = "Scheda Tracciabilità HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"
    _rec_name = "lotto_pf"

    lotto_mp = fields.Char(string="Lotto Materia Prima")
    lotto_pf = fields.Char(string="Lotto Prodotto Finito", required=True)
    production_id = fields.Many2one("mrp.production",
                                     string="Ordine di Produzione")
    partner_ids = fields.Many2many("res.partner", string="Clienti / Destinatari")
    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    note = fields.Text(string="Note")
