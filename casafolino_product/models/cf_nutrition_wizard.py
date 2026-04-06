# -*- coding: utf-8 -*-

import csv
import logging
import os

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# USDA FoodData Central Wizard
# ---------------------------------------------------------------------------

class CfNutritionUsdaWizard(models.TransientModel):
    _name = "cf.nutrition.usda.wizard"
    _description = "Ricerca USDA FoodData Central"

    ingredient_id = fields.Many2one("cf.nutrition.ingredient", required=True)
    search_query = fields.Char(string="Ricerca", required=True)
    result_ids = fields.One2many("cf.nutrition.usda.wizard.line", "wizard_id")

    def action_search(self):
        """Search USDA API with up to 10 results."""
        self.ensure_one()
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.usda_api_key', 'DEMO_KEY')
        try:
            resp = requests.get(
                "https://api.nal.usda.gov/fdc/v1/foods/search",
                params={
                    'query': self.search_query,
                    'api_key': api_key,
                    'pageSize': 10,
                    'dataType': 'SR Legacy,Foundation',
                },
                timeout=8,
            )
            resp.raise_for_status()
            foods = resp.json().get('foods', [])
        except Exception:
            _logger.warning("USDA API search failed for query: %s", self.search_query, exc_info=True)
            foods = []

        # Clear old results
        self.result_ids.unlink()

        # USDA nutrient IDs
        NUTRIENT_MAP = {
            1008: 'energy_kcal',
            1062: 'energy_kj',
            1004: 'fat',
            1258: 'saturated_fat',
            1257: 'trans_fat_g',
            1005: 'carbs',
            2000: 'sugars',
            1079: 'fiber',
            1003: 'protein',
            1093: 'sodium_mg',
            1253: 'cholesterol_mg',
        }

        lines = []
        for food in foods:
            fdc_id = str(food.get('fdcId', ''))
            name = food.get('description', food.get('lowercaseDescription', ''))
            nutrients = {
                n['nutrientId']: n.get('value', 0)
                for n in food.get('foodNutrients', [])
                if 'nutrientId' in n
            }

            sodium_val = nutrients.get(1093, 0) or 0
            lines.append({
                'wizard_id': self.id,
                'fdc_id': fdc_id,
                'name': name,
                'energy_kcal': nutrients.get(1008, 0) or 0,
                'fat': nutrients.get(1004, 0) or 0,
                'carbs': nutrients.get(1005, 0) or 0,
                'protein': nutrients.get(1003, 0) or 0,
                'sugars': nutrients.get(2000, 0) or 0,
                'fiber': nutrients.get(1079, 0) or 0,
                'saturated_fat': nutrients.get(1258, 0) or 0,
                'salt': round(sodium_val * 2.5 / 1000, 3),
            })

        self.env["cf.nutrition.usda.wizard.line"].create(lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        """Apply selected result to ingredient."""
        self.ensure_one()
        selected = self.result_ids.filtered('selected')
        if not selected:
            return
        line = selected[0]
        self.ingredient_id.write({
            'energy_kcal': line.energy_kcal,
            'fat': line.fat,
            'saturated_fat': line.saturated_fat,
            'carbs': line.carbs,
            'sugars': line.sugars,
            'fiber': line.fiber,
            'protein': line.protein,
            'salt': line.salt,
            'fdc_id': line.fdc_id,
            'external_id': line.fdc_id,
            'data_source': 'usda',
            'last_sync': fields.Datetime.now(),
        })


class CfNutritionUsdaWizardLine(models.TransientModel):
    _name = "cf.nutrition.usda.wizard.line"
    _description = "Risultato Ricerca USDA"

    wizard_id = fields.Many2one("cf.nutrition.usda.wizard", ondelete="cascade")
    selected = fields.Boolean(default=False)
    fdc_id = fields.Char("FDC ID")
    name = fields.Char("Alimento")
    energy_kcal = fields.Float("kcal/100g")
    fat = fields.Float("Grassi g")
    saturated_fat = fields.Float("Saturi g")
    carbs = fields.Float("Carb. g")
    sugars = fields.Float("Zuccheri g")
    fiber = fields.Float("Fibra g")
    protein = fields.Float("Proteine g")
    salt = fields.Float("Sale g")


# ---------------------------------------------------------------------------
# CIQUAL (ANSES) Wizard
# ---------------------------------------------------------------------------

class CfNutritionCiqualWizard(models.TransientModel):
    _name = "cf.nutrition.ciqual.wizard"
    _description = "Ricerca CIQUAL (ANSES)"

    ingredient_id = fields.Many2one("cf.nutrition.ingredient", required=True)
    search_query = fields.Char(string="Ricerca", required=True)
    result_ids = fields.One2many("cf.nutrition.ciqual.wizard.line", "wizard_id")

    def _get_ciqual_csv_path(self):
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(module_path, 'data', 'ciqual.csv')

    def action_search(self):
        self.ensure_one()
        csv_path = self._get_ciqual_csv_path()
        self.result_ids.unlink()

        if not os.path.exists(csv_path):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'CIQUAL',
                    'message': (
                        'File ciqual.csv non trovato. Scaricalo da '
                        'https://ciqual.anses.fr/ e copialo in '
                        'casafolino_product/data/ciqual.csv'
                    ),
                    'type': 'warning',
                    'sticky': True,
                },
            }

        query = self.search_query.lower()
        lines = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                name = row.get('alim_nom_fr', row.get('alim_nom_eng', ''))
                if query not in name.lower():
                    continue

                def parse_float(val):
                    if not val or val in ('-', '<', 'traces', 'nd'):
                        return 0.0
                    val = val.replace(',', '.').replace('<', '').strip()
                    try:
                        return float(val)
                    except ValueError:
                        return 0.0

                lines.append({
                    'wizard_id': self.id,
                    'ciqual_code': row.get('alim_code', ''),
                    'name': name,
                    'energy_kcal': parse_float(row.get(
                        'Energie, Règlement UE N° 1169/2011 (kcal/100 g)',
                        row.get('energy_kcal', ''),
                    )),
                    'fat': parse_float(row.get(
                        'Lipides (g/100 g)', row.get('fat', ''),
                    )),
                    'saturated_fat': parse_float(row.get(
                        'AG saturés (g/100 g)', row.get('saturated_fat', ''),
                    )),
                    'carbs': parse_float(row.get(
                        'Glucides (g/100 g)', row.get('carbs', ''),
                    )),
                    'sugars': parse_float(row.get(
                        'Sucres (g/100 g)', row.get('sugars', ''),
                    )),
                    'fiber': parse_float(row.get(
                        'Fibres alimentaires (g/100 g)', row.get('fiber', ''),
                    )),
                    'protein': parse_float(row.get(
                        'Protéines, N x facteur de Jones (g/100 g)',
                        row.get('protein', ''),
                    )),
                    'salt': parse_float(row.get(
                        'Sel chlorure de sodium (g/100 g)', row.get('salt', ''),
                    )),
                })
                if len(lines) >= 20:
                    break

        if lines:
            self.env["cf.nutrition.ciqual.wizard.line"].create(lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        self.ensure_one()
        selected = self.result_ids.filtered('selected')
        if not selected:
            return
        line = selected[0]
        self.ingredient_id.write({
            'energy_kcal': line.energy_kcal,
            'energy_kj': round(line.energy_kcal * 4.184, 1),
            'fat': line.fat,
            'saturated_fat': line.saturated_fat,
            'carbs': line.carbs,
            'sugars': line.sugars,
            'fiber': line.fiber,
            'protein': line.protein,
            'salt': line.salt,
            'sodium_mg': round(line.salt / 2.5 * 1000, 1),
            'ciqual_code': line.ciqual_code,
            'external_id': line.ciqual_code,
            'data_source': 'ciqual',
            'last_sync': fields.Datetime.now(),
        })


class CfNutritionCiqualWizardLine(models.TransientModel):
    _name = "cf.nutrition.ciqual.wizard.line"
    _description = "Risultato Ricerca CIQUAL"

    wizard_id = fields.Many2one("cf.nutrition.ciqual.wizard", ondelete="cascade")
    selected = fields.Boolean(default=False)
    ciqual_code = fields.Char("Codice CIQUAL")
    name = fields.Char("Alimento")
    energy_kcal = fields.Float("kcal/100g")
    fat = fields.Float("Grassi g")
    saturated_fat = fields.Float("Saturi g")
    carbs = fields.Float("Carb. g")
    sugars = fields.Float("Zuccheri g")
    fiber = fields.Float("Fibra g")
    protein = fields.Float("Proteine g")
    salt = fields.Float("Sale g")
