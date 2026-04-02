# -*- coding: utf-8 -*-
from odoo import models, fields


class CfHaccpFormazione(models.Model):
    _name = "cf.haccp.formazione"
    _description = "Registro Formazione HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"

    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    argomento = fields.Selection([
        ('haccp', 'HACCP — Principi generali'),
        ('igiene', 'Igiene personale e ambienti'),
        ('procedure', 'Procedure operative'),
        ('allergeni', 'Gestione allergeni'),
        ('ccp', 'Punti di controllo critico (CCP)'),
        ('altro', 'Altro'),
    ], string="Argomento", required=True)
    partecipanti_ids = fields.Many2many("res.users", string="Partecipanti")
    docente = fields.Char(string="Docente / Formatore")
    durata_ore = fields.Float(string="Durata (ore)", digits=(4, 1))
    esito = fields.Selection([
        ('superato', 'Superato'),
        ('non_superato', 'Non superato'),
    ], string="Esito", default='superato')
    firma_digitale = fields.Binary(string="Firma Digitale")
    note = fields.Text(string="Note")
