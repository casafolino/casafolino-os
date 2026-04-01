# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfNutritionIngredient(models.Model):
    _name = "cf.nutrition.ingredient"
    _description = "Valori Nutrizionali Ingrediente"
    _rec_name = "product_id"
    product_id = fields.Many2one("product.template", required=True, ondelete="cascade")
    energy_kcal = fields.Float(string="Energia (kcal/100g)")
    energy_kj = fields.Float(string="Energia (kJ/100g)")
    fat = fields.Float(string="Grassi (g/100g)")
    saturated_fat = fields.Float(string="Acidi Grassi Saturi (g/100g)")
    carbs = fields.Float(string="Carboidrati (g/100g)")
    sugars = fields.Float(string="Zuccheri (g/100g)")
    fiber = fields.Float(string="Fibra (g/100g)")
    protein = fields.Float(string="Proteine (g/100g)")
    salt = fields.Float(string="Sale (g/100g)")
    sodium = fields.Float(string="Sodio (g/100g)")
    fdc_id = fields.Char(string="USDA FDC ID")
    notes = fields.Text()

class CfNutritionBom(models.Model):
    _name = "cf.nutrition.bom"
    _description = "Valori Nutrizionali Ricetta"
    _rec_name = "bom_id"
    bom_id = fields.Many2one("mrp.bom", required=True, ondelete="cascade")
    serving_size_g = fields.Float(string="Porzione (g)", default=100.0)
    energy_kcal = fields.Float(string="Energia (kcal/100g)", readonly=True)
    energy_kj = fields.Float(string="Energia (kJ/100g)", readonly=True)
    fat = fields.Float(string="Grassi (g/100g)", readonly=True)
    saturated_fat = fields.Float(string="Saturi (g/100g)", readonly=True)
    carbs = fields.Float(string="Carboidrati (g/100g)", readonly=True)
    sugars = fields.Float(string="Zuccheri (g/100g)", readonly=True)
    fiber = fields.Float(string="Fibra (g/100g)", readonly=True)
    protein = fields.Float(string="Proteine (g/100g)", readonly=True)
    salt = fields.Float(string="Sale (g/100g)", readonly=True)
    last_computed = fields.Datetime(string="Ultimo Calcolo", readonly=True)
    nutri_score = fields.Selection([
        ("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("E", "E"),
    ], compute="_compute_nutri_score", store=True, string="Nutri-Score")
    nutri_score_color = fields.Char(compute="_compute_nutri_score_color")

    @api.depends("energy_kcal", "sugars", "saturated_fat", "salt", "fiber", "protein")
    def _compute_nutri_score(self):
        """Simplified Nutri-Score estimate (A=best, E=worst)."""
        for rec in self:
            if not rec.energy_kcal:
                rec.nutri_score = False
                continue
            # Negative points (higher = worse)
            neg = 0
            neg += 0 if rec.energy_kcal <= 335 else 1 if rec.energy_kcal <= 670 else 2 if rec.energy_kcal <= 1005 else 3 if rec.energy_kcal <= 1340 else 4 if rec.energy_kcal <= 1675 else 5 if rec.energy_kcal <= 2010 else 6 if rec.energy_kcal <= 2345 else 7 if rec.energy_kcal <= 2680 else 8 if rec.energy_kcal <= 3015 else 9 if rec.energy_kcal <= 3350 else 10
            neg += 0 if rec.sugars <= 4.5 else 1 if rec.sugars <= 9 else 2 if rec.sugars <= 13.5 else 3 if rec.sugars <= 18 else 4 if rec.sugars <= 22.5 else 5 if rec.sugars <= 27 else 6 if rec.sugars <= 31 else 7 if rec.sugars <= 36 else 8 if rec.sugars <= 40 else 9 if rec.sugars <= 45 else 10
            neg += 0 if rec.saturated_fat <= 1 else 1 if rec.saturated_fat <= 2 else 2 if rec.saturated_fat <= 3 else 3 if rec.saturated_fat <= 4 else 4 if rec.saturated_fat <= 5 else 5 if rec.saturated_fat <= 6 else 6 if rec.saturated_fat <= 7 else 7 if rec.saturated_fat <= 8 else 8 if rec.saturated_fat <= 9 else 9 if rec.saturated_fat <= 10 else 10
            neg += 0 if rec.salt <= 0.2 else 1 if rec.salt <= 0.4 else 2 if rec.salt <= 0.6 else 3 if rec.salt <= 0.8 else 4 if rec.salt <= 1.0 else 5 if rec.salt <= 1.2 else 6 if rec.salt <= 1.4 else 7 if rec.salt <= 1.6 else 8 if rec.salt <= 1.8 else 9 if rec.salt <= 2.0 else 10
            # Positive points
            pos = min(5, int(rec.fiber / 0.9)) + min(5, int(rec.protein / 1.6))
            score = neg - pos
            rec.nutri_score = "A" if score <= -1 else "B" if score <= 2 else "C" if score <= 10 else "D" if score <= 18 else "E"

    @api.depends("nutri_score")
    def _compute_nutri_score_color(self):
        colors = {"A": "#1a7e3c", "B": "#85bb2f", "C": "#f7c325", "D": "#e8821e", "E": "#e63312"}
        for rec in self:
            rec.nutri_score_color = colors.get(rec.nutri_score, "#6c757d")

    def action_compute(self):
        self.ensure_one()
        bom = self.bom_id
        total_qty = sum(line.product_qty for line in bom.bom_line_ids)
        if not total_qty: return
        fields_map = ["energy_kcal","energy_kj","fat","saturated_fat","carbs","sugars","fiber","protein","salt"]
        totals = {f: 0.0 for f in fields_map}
        for line in bom.bom_line_ids:
            ingredient = self.env["cf.nutrition.ingredient"].search(
                [("product_id","=",line.product_id.product_tmpl_id.id)], limit=1)
            if not ingredient: continue
            ratio = line.product_qty / total_qty
            for f in fields_map:
                totals[f] += getattr(ingredient, f) * ratio
        totals["last_computed"] = fields.Datetime.now()
        self.write(totals)

class MrpBomNutrition(models.Model):
    _inherit = "mrp.bom"
    nutrition_ids = fields.One2many("cf.nutrition.bom", "bom_id", string="Valori Nutrizionali")
