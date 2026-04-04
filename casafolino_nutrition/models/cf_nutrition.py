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

    def action_compute(self):
        for rec in self:
            bom = rec.bom_id
            total_qty = sum(line.product_qty for line in bom.bom_line_ids)
            if not total_qty: continue
            cooked_qty = total_qty * (bom.cf_yield_factor or 1.0)
            if not cooked_qty: continue
            fields_map = ["energy_kcal","energy_kj","fat","saturated_fat","carbs","sugars","fiber","protein","salt"]
            totals = {f: 0.0 for f in fields_map}
            for line in bom.bom_line_ids:
                ingredient = self.env["cf.nutrition.ingredient"].search(
                    [("product_id","=",line.product_id.product_tmpl_id.id)], limit=1)
                if not ingredient: continue
                ratio = line.product_qty / cooked_qty
                for f in fields_map:
                    totals[f] += getattr(ingredient, f) * ratio
            totals["last_computed"] = fields.Datetime.now()
            rec.write(totals)

class MrpBomNutrition(models.Model):
    _inherit = "mrp.bom"
    nutrition_ids = fields.One2many("cf.nutrition.bom", "bom_id", string="Valori Nutrizionali")
    cf_yield_factor = fields.Float("Fattore di Sfrido/Cottura (Resa)", default=1.0)
