# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CfHaccpReception(models.Model):
    _name = "cf.haccp.reception"
    _description = "Controllo HACCP Ricezione Merce"
    _order = "date desc, id desc"
    _rec_name = "display_name"

    picking_id = fields.Many2one(
        "stock.picking", string="Ricezione",
        domain=[("picking_type_code", "=", "incoming")],
        ondelete="cascade", required=True,
    )
    date = fields.Datetime(
        related="picking_id.scheduled_date", store=True, string="Data",
    )
    partner_id = fields.Many2one(
        related="picking_id.partner_id", store=True, string="Fornitore",
    )
    picking_origin = fields.Char(
        related="picking_id.origin", store=True, string="Riferimento",
    )
    product_names = fields.Char(
        string="Prodotti", compute="_compute_product_names", store=True,
    )

    # Controlli HACCP
    temperature_ok = fields.Boolean("Temperatura OK")
    temperature_value = fields.Float("Temperatura rilevata (°C)")
    packaging_ok = fields.Boolean("Imballaggio integro")
    label_ok = fields.Boolean("Etichettatura corretta")
    lot_number = fields.Char("Numero Lotto")
    expiry_date = fields.Date("Data Scadenza")
    notes = fields.Text("Note")
    operator_id = fields.Many2one(
        "res.users", string="Operatore",
        default=lambda self: self.env.user,
    )

    # Stato calcolato automatico
    haccp_state = fields.Selection(
        [("pending", "Da completare"), ("done", "Completato")],
        string="Stato HACCP", compute="_compute_haccp_state", store=True,
    )

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("picking_id.name", "partner_id.name")
    def _compute_display_name(self):
        for rec in self:
            parts = [rec.picking_id.name or "", rec.partner_id.name or ""]
            rec.display_name = " — ".join(p for p in parts if p) or "Nuovo"

    @api.depends("picking_id.move_ids.product_id")
    def _compute_product_names(self):
        for rec in self:
            products = rec.picking_id.move_ids.mapped("product_id.name")
            rec.product_names = ", ".join(products) if products else ""

    @api.depends("temperature_ok", "packaging_ok", "label_ok", "lot_number", "expiry_date")
    def _compute_haccp_state(self):
        for rec in self:
            if rec.temperature_ok and rec.packaging_ok and rec.label_ok and rec.lot_number and rec.expiry_date:
                rec.haccp_state = "done"
            else:
                rec.haccp_state = "pending"


class StockPickingReception(models.Model):
    _inherit = "stock.picking"

    haccp_reception_ids = fields.One2many(
        "cf.haccp.reception", "picking_id", string="Controllo HACCP Ricezione",
    )
