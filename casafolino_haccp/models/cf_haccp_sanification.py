# -*- coding: utf-8 -*-
from odoo import models, fields


class CfHaccpSanificationLog(models.Model):
    _name = "cf.haccp.sanification.log"
    _description = "Registro Sanificazione HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"

    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    area = fields.Selection([
        ('zone1', 'Zona Produzione 1'),
        ('zone2', 'Zona Produzione 2'),
        ('zone3', 'Zona Produzione 3'),
        ('frigo', 'Celle Frigorifere'),
        ('attrezzature', 'Attrezzature'),
        ('pavimenti', 'Pavimenti e Superfici'),
    ], string="Area", required=True)
    frequenza = fields.Selection([
        ('giornaliera', 'Giornaliera'),
        ('settimanale', 'Settimanale'),
        ('mensile', 'Mensile'),
    ], string="Frequenza", required=True, default='giornaliera')
    prodotto_usato = fields.Char(string="Prodotto Sanificante Usato")
    eseguita = fields.Boolean(string="Sanificazione Eseguita", default=False)
    operatore_id = fields.Many2one("res.users", string="Operatore",
                                    default=lambda self: self.env.user)
    firma_digitale = fields.Binary(string="Firma Digitale")
    note = fields.Text(string="Note")
