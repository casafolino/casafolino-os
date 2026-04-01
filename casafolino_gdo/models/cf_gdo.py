# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfGdoRetailer(models.Model):
    _name = "cf.gdo.retailer"
    _description = "Retailer GDO"
    _inherit = ["mail.thread"]
    _rec_name = "partner_id"
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    retailer_type = fields.Selection([
        ("supermarket","Supermercato"),("hypermarket","Ipermercato"),
        ("discount","Discount"),("specialty","Specialty"),("online","Online"),
    ], required=True, default="supermarket")
    country_id = fields.Many2one(related="partner_id.country_id", store=True)
    num_stores = fields.Integer(string="N° Punti Vendita")
    buyer_id = fields.Many2one("res.partner", string="Buyer")
    annual_target = fields.Monetary(string="Target Annuale", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    listing_ids = fields.One2many("cf.gdo.listing", "retailer_id", string="Listing")
    active = fields.Boolean(default=True)
    notes = fields.Text()

class CfGdoListing(models.Model):
    _name = "cf.gdo.listing"
    _description = "Listing Prodotto GDO"
    _inherit = ["mail.thread"]
    _rec_name = "display_name_computed"
    display_name_computed = fields.Char(compute="_compute_display_name", store=True, compute_sudo=False)
    retailer_id = fields.Many2one("cf.gdo.retailer", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.template", required=True)
    state = fields.Selection([
        ("draft","Bozza"),("sample","Campione"),("evaluation","Valutazione"),
        ("approved","Approvato"),("active","Attivo"),("delisted","Delistato"),
    ], default="draft", tracking=True, required=True)
    date_submission = fields.Date(string="Data Sottomissione")
    date_approval = fields.Date(string="Data Approvazione")
    date_active = fields.Date(string="Data Attivazione")
    selling_price = fields.Monetary(string="Prezzo Vendita", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"))
    num_stores = fields.Integer(string="N° Store")
    date_expiry = fields.Date(string="Scadenza Contratto")
    listing_status = fields.Selection([
        ("active", "Attivo"), ("expiring", "In Scadenza"), ("expired", "Scaduto"), ("inactive", "Non attivo"),
    ], compute="_compute_listing_status", store=True)
    notes = fields.Text()

    @api.depends("state", "date_expiry")
    def _compute_listing_status(self):
        today = date.today()
        for rec in self:
            if rec.state in ("delisted", "draft"):
                rec.listing_status = "inactive"
            elif not rec.date_expiry:
                rec.listing_status = "active" if rec.state == "active" else "inactive"
            else:
                days = (rec.date_expiry - today).days
                rec.listing_status = (
                    "expired" if days < 0
                    else "expiring" if days <= 30
                    else "active"
                )

    @api.depends("retailer_id","product_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name_computed = f"{rec.retailer_id.partner_id.name or ''} - {rec.product_id.name or ''}"

class ResPartnerGdo(models.Model):
    _inherit = "res.partner"
    is_gdo_retailer = fields.Boolean(string="Retailer GDO", default=False)
