# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CfHaccpReceipt(models.Model):
    _name = "cf.haccp.receipt"
    _description = "Controllo Ricezione Materia Prima"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(string="Riferimento", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.receipt") or "RIC-NUOVO")
    state = fields.Selection([
        ("draft","Da Compilare"),("in_progress","In Corso"),
        ("accepted","Accettato"),("quarantine","Quarantena"),("rejected","Rifiutato"),
    ], string="Esito", default="draft", tracking=True, required=True)
    picking_id = fields.Many2one("stock.picking", string="Ricezione Odoo")
    lot_id = fields.Many2one("stock.lot", string="Lotto")
    product_id = fields.Many2one("product.template", string="Prodotto", required=True,
        domain="[(\"is_raw_material\",\"=\",True)]")
    partner_id = fields.Many2one("res.partner", string="Fornitore")
    date = fields.Datetime(string="Data/Ora", default=fields.Datetime.now, required=True)
    operator_id = fields.Many2one("res.users", string="Operatore", default=lambda self: self.env.user)
    quantity_received = fields.Float(string="Quantita Ricevuta")
    temperature_measured = fields.Float(string="Temperatura (C)")
    appearance_ok = fields.Boolean(string="Aspetto OK", default=True)
    smell_ok = fields.Boolean(string="Odore OK", default=True)
    color_ok = fields.Boolean(string="Colore OK", default=True)
    ddt_present = fields.Boolean(string="DDT Presente", default=True)
    cert_present = fields.Boolean(string="Certificati Presenti", default=True)
    packaging_intact = fields.Boolean(string="Packaging Integro", default=True)
    general_notes = fields.Text(string="Note")

    def action_accept(self):
        self.write({"state": "accepted"})

    def action_quarantine(self):
        for rec in self:
            rec.state = "quarantine"
            if rec.lot_id:
                self.env["cf.haccp.quarantine"].create({
                    "lot_id": rec.lot_id.id, "product_id": rec.product_id.id,
                    "receipt_id": rec.id, "reason": "Anomalia al controllo ricezione.",
                    "operator_id": rec.operator_id.id,
                })

    def action_reject(self):
        self.write({"state": "rejected"})

class StockPickingHaccp(models.Model):
    _inherit = "stock.picking"
    haccp_receipt_ids = fields.One2many("cf.haccp.receipt", "picking_id", string="Controlli HACCP")
    haccp_receipt_count = fields.Integer(compute="_compute_haccp_count")
    haccp_required = fields.Boolean(compute="_compute_haccp_required")

    def _compute_haccp_count(self):
        for rec in self:
            rec.haccp_receipt_count = len(rec.haccp_receipt_ids)

    @api.depends("move_ids.product_id")
    def _compute_haccp_required(self):
        for rec in self:
            if rec.picking_type_code != "incoming":
                rec.haccp_required = False
                continue
            products = rec.move_ids.mapped("product_id.product_tmpl_id")
            rec.haccp_required = any(p.is_raw_material for p in products)
