# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CfHaccpEtichettatura(models.Model):
    _name = "cf.haccp.etichettatura.log"
    _description = "Check Etichettatura HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"

    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    lot_id = fields.Many2one("stock.lot", string="Lotto")
    product_id = fields.Many2one("product.template", string="Prodotto",
                                  related="lot_id.product_id.product_tmpl_id",
                                  store=True, readonly=True)
    allergeni_ok = fields.Boolean(string="Allergeni dichiarati", default=False)
    lingue_ok = fields.Boolean(string="Lingue richieste presenti", default=False)
    lotto_presente = fields.Boolean(string="Numero lotto presente", default=False)
    scadenza_presente = fields.Boolean(string="Data scadenza presente", default=False)
    esito = fields.Selection([
        ('ok', 'OK — Conforme'),
        ('ko', 'KO — Non conforme'),
    ], string="Esito", compute="_compute_esito", store=True, tracking=True)
    operatore_id = fields.Many2one("res.users", string="Operatore",
                                    default=lambda self: self.env.user)
    firma_digitale = fields.Binary(string="Firma Digitale")
    note = fields.Text(string="Note")

    @api.depends("allergeni_ok", "lingue_ok", "lotto_presente", "scadenza_presente")
    def _compute_esito(self):
        for rec in self:
            if rec.allergeni_ok and rec.lotto_presente and rec.scadenza_presente:
                rec.esito = 'ok'
            else:
                rec.esito = 'ko'
