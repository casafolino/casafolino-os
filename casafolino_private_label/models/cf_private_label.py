# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfPlClient(models.Model):
    _name = "cf.pl.client"
    _description = "Cliente Private Label"
    _inherit = ["mail.thread"]
    _rec_name = "partner_id"
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    country_id = fields.Many2one(related="partner_id.country_id", store=True)
    annual_target = fields.Monetary(string="Target Annuale", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    product_ids = fields.One2many("cf.pl.product", "client_id", string="Prodotti PL")
    active = fields.Boolean(default=True)
    notes = fields.Text()

class CfPlProduct(models.Model):
    _name = "cf.pl.product"
    _description = "Prodotto Private Label"
    _inherit = ["mail.thread"]
    _rec_name = "name"
    name = fields.Char(string="Nome Prodotto PL", required=True)
    client_id = fields.Many2one("cf.pl.client", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.template", string="Prodotto Base")
    state = fields.Selection([
        ("request","Richiesta"),("development","Sviluppo"),("sampling","Campionatura"),
        ("approved","Approvato"),("active","Attivo"),
    ], default="request", tracking=True, required=True)
    selling_price = fields.Monetary(string="Prezzo PL", currency_field="currency_id")
    production_cost = fields.Monetary(string="Costo Produzione", currency_field="currency_id")
    label_cost = fields.Monetary(string="Costo Etichetta", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    margin_pct = fields.Float(string="Margine %", compute="_compute_margin", store=True)
    min_order_qty = fields.Float(string="MOQ")
    notes = fields.Text()

    @api.depends("selling_price","production_cost","label_cost")
    def _compute_margin(self):
        for rec in self:
            cost = rec.production_cost + rec.label_cost
            rec.margin_pct = ((rec.selling_price - cost) / rec.selling_price * 100) if rec.selling_price else 0.0

class ResPartnerPl(models.Model):
    _inherit = "res.partner"
    is_pl_client = fields.Boolean(string="Cliente Private Label", default=False)
