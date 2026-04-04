# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfAllergen(models.Model):
    _name = "cf.allergen"
    _description = "Allergene UE"
    _order = "sequence"
    _rec_name = "name"
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    regulation_ref = fields.Char(string="Rif. Regolamento", default="Reg. 1169/2011")
    market = fields.Selection([('eu', 'EU'), ('us', 'US'), ('all', 'Globale')], string="Mercato", default='eu', required=True)
    active = fields.Boolean(default=True)

class CfAllergenKeyword(models.Model):
    _name = "cf.allergen.keyword"
    _description = "Keyword Allergene"
    allergen_id = fields.Many2one("cf.allergen", required=True, ondelete="cascade")
    keyword = fields.Char(required=True)
    match_type = fields.Selection([("exact","Esatta"),("partial","Parziale"),("starts","Inizia con")], default="partial")

class CfRecipeAllergen(models.Model):
    _name = "cf.recipe.allergen"
    _description = "Allergene Ricetta"
    bom_id = fields.Many2one("mrp.bom", required=True, ondelete="cascade")
    allergen_id = fields.Many2one("cf.allergen", required=True)
    status = fields.Selection([
        ("present","Presente"),("traces","Puo Contenere Tracce"),("absent","Assente"),
    ], required=True, default="absent")
    market = fields.Selection(related="allergen_id.market", string="Mercato", store=True)
    cross_contamination = fields.Boolean(default=False)
    notes = fields.Text()
    validated_by = fields.Many2one("res.users", string="Validato da")
    validation_date = fields.Date(string="Data Validazione")

class MrpBomAllergen(models.Model):
    _inherit = "mrp.bom"
    allergen_ids = fields.One2many("cf.recipe.allergen", "bom_id", string="Allergeni")
    allergen_validated = fields.Boolean(string="Dichiarazione Validata", default=False)

    def action_analyze_allergens(self):
        self.ensure_one()
        allergens = self.env["cf.allergen"].search([])
        keywords = self.env["cf.allergen.keyword"].search([])
        ingredient_names = " ".join(self.bom_line_ids.mapped("product_id.name")).lower()
        for allergen in allergens:
            existing = self.allergen_ids.filtered(lambda a: a.allergen_id.id == allergen.id)
            if existing: continue
            kws = keywords.filtered(lambda k: k.allergen_id.id == allergen.id)
            found = False
            for kw in kws:
                k = kw.keyword.lower()
                if kw.match_type == "exact" and k == ingredient_names: found = True
                elif kw.match_type == "partial" and k in ingredient_names: found = True
                elif kw.match_type == "starts" and ingredient_names.startswith(k): found = True
            self.env["cf.recipe.allergen"].create({
                "bom_id": self.id,
                "allergen_id": allergen.id,
                "status": "present" if found else "absent",
            })

class CfAllergenProductMatch(models.Model):
    _name = "cf.allergen.product.match"
    _description = "Match Allergeni Prodotto per Mercato"

    product_id = fields.Many2one("product.template", required=True)
    market = fields.Selection([('eu', 'EU'), ('us', 'US')], required=True, default='eu')
    matched_allergen_ids = fields.Many2many("cf.allergen", compute="_compute_matched_allergens")

    @api.depends('product_id', 'market')
    def _compute_matched_allergens(self):
        for rec in self:
            bom = self.env['mrp.bom'].search([('product_tmpl_id', '=', rec.product_id.id)], limit=1)
            if not bom:
                rec.matched_allergen_ids = False
                continue
            # Filtra gli allergeni della distinta base che corrispondono al mercato (e globale)
            allergens = bom.allergen_ids.filtered(
                lambda a: a.status in ('present', 'traces') and a.allergen_id.market in (rec.market, 'all')
            ).mapped("allergen_id")
            rec.matched_allergen_ids = allergens

class MrpBomAllergenAlert(models.Model):
    _inherit = "mrp.bom"

    allergen_alert = fields.Char(string="Alert Allergeni", compute="_compute_allergen_alert")

    @api.depends('bom_line_ids.product_id')
    def _compute_allergen_alert(self):
        for rec in self:
            alerts = []
            for line in rec.bom_line_ids:
                name = (line.product_id.name or "").lower()
                if "nocciol" in name or "hazelnut" in name:
                    alerts.append(f"Attenzione: presenti Nocciole ({line.product_id.name}). Per il mercato US questo va dichiarato come 'Tree Nuts'.")
            rec.allergen_alert = " | ".join(alerts) if alerts else False

class ProductTemplateAllergen(models.Model):
    _inherit = "product.template"

    allergen_match_ids = fields.One2many("cf.allergen.product.match", "product_id", string="Allergeni Mercato")
