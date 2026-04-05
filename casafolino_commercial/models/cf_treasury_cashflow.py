# -*- coding: utf-8 -*-
from odoo import models, fields

class CfTreasuryCashflowLine(models.Model):
    _name = "cf.treasury.cashflow.line"
    _description = "Riga Cashflow Tesoreria"
    _order = "date desc, id desc"
    _rec_name = "name"

    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    name = fields.Char(string="Descrizione", required=True)
    move_type = fields.Selection([
        ("in", "Entrata"),
        ("out", "Uscita"),
        ("forecast", "Previsione"),
    ], string="Tipo", required=True, default="forecast")
    amount = fields.Monetary(string="Importo", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.ref("base.EUR"),
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Conto",
        domain="[('type', 'in', ('bank', 'cash'))]",
    )
    source = fields.Selection([
        ("auto", "Automatica"),
        ("manual", "Manuale"),
    ], string="Origine", default="manual", readonly=True)
    origin_move_id = fields.Many2one("account.move", string="Fattura origine")
    note = fields.Text(string="Note")
