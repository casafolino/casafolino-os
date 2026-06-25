# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CfHaccpProduction(models.Model):
    _name = "cf.haccp.production"
    _description = "Scheda HACCP Produzione"
    _order = "date_start desc, id desc"
    _rec_name = "display_name"

    production_id = fields.Many2one(
        "mrp.production", string="Ordine di Produzione",
        ondelete="cascade", required=True,
    )
    date_start = fields.Datetime(
        related="production_id.date_start", store=True, string="Data Inizio",
    )
    product_id = fields.Many2one(
        related="production_id.product_id", store=True, string="Prodotto",
    )
    lot_producing_id = fields.Many2one(
        related="production_id.lot_producing_id", store=True, string="Lotto",
    )
    qty_production = fields.Float(
        related="production_id.product_qty", store=True, string="Quantità",
    )

    # Controlli HACCP produzione
    temp_lavorazione = fields.Float("Temperatura lavorazione (°C)")
    temp_ok = fields.Boolean("Temperatura nella norma")
    ccp_check = fields.Boolean("CCP verificati")
    ccp_notes = fields.Text("Note CCP")
    igiene_ok = fields.Boolean("Igiene personale verificata")
    attrezzature_ok = fields.Boolean("Attrezzature sanificate")
    operator_id = fields.Many2one(
        "res.users", string="Operatore",
        default=lambda self: self.env.user,
    )
    notes = fields.Text("Note generali")

    # Stato calcolato automatico
    haccp_state = fields.Selection(
        [("pending", "Da completare"), ("done", "Completato")],
        string="Stato HACCP", compute="_compute_haccp_state", store=True,
    )

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("production_id.name", "product_id.name")
    def _compute_display_name(self):
        for rec in self:
            parts = [rec.production_id.name or "", rec.product_id.name or ""]
            rec.display_name = " — ".join(p for p in parts if p) or "Nuovo"

    @api.depends("temp_ok", "ccp_check", "igiene_ok", "attrezzature_ok")
    def _compute_haccp_state(self):
        for rec in self:
            if rec.temp_ok and rec.ccp_check and rec.igiene_ok and rec.attrezzature_ok:
                rec.haccp_state = "done"
            else:
                rec.haccp_state = "pending"


class MrpProductionHaccpCheck(models.Model):
    _inherit = "mrp.production"

    haccp_production_ids = fields.One2many(
        "cf.haccp.production", "production_id", string="Schede HACCP Produzione",
    )
