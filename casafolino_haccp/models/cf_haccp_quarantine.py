# -*- coding: utf-8 -*-
from odoo import models, fields

class CfHaccpQuarantine(models.Model):
    _name = "cf.haccp.quarantine"
    _description = "Quarantena HACCP"
    _inherit = ["mail.thread"]
    _order = "date_start desc"
    _rec_name = "reference"

    reference = fields.Char(string="N° Quarantena", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.quarantine") or "QUA-NUOVO")
    state = fields.Selection([
        ("active","In Quarantena"),("released","Rilasciato"),
        ("destroyed","Distrutto"),("returned","Reso"),
    ], string="Stato", default="active", tracking=True)
    lot_id = fields.Many2one("stock.lot", string="Lotto", required=True)
    product_id = fields.Many2one("product.template", string="Prodotto")
    receipt_id = fields.Many2one("cf.haccp.receipt", string="Ricezione")
    operator_id = fields.Many2one("res.users", string="Operatore", default=lambda self: self.env.user)
    date_start = fields.Datetime(string="Inizio", default=fields.Datetime.now)
    date_end = fields.Datetime(string="Fine")
    reason = fields.Text(string="Motivo", required=True)
    location = fields.Char(string="Zona Quarantena")
    resolution = fields.Text(string="Risoluzione")

    def action_release(self):
        for rec in self:
            rec.state = "released"
            rec.date_end = fields.Datetime.now()

    def action_destroy(self):
        for rec in self:
            rec.state = "destroyed"
            rec.date_end = fields.Datetime.now()
