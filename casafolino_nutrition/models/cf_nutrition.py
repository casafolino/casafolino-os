# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta

import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

# ─── API constants ────────────────────────────────────────────────────────────
_USDA_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
_USDA_API_KEY = "DEMO_KEY"  # Replace with real key in production
_OFF_API_URL = "https://world.openfoodfacts.org/cgi/search.pl"
_API_TIMEOUT = 8  # seconds

# USDA nutrient IDs we care about
_USDA_NUTRIENT_IDS = {
    1008: 'energy_kcal',   # Energy kcal
    1062: 'energy_kj',     # Energy kJ
    1004: 'fat',           # Total lipid (fat)
    1258: 'saturated_fat', # Fatty acids, total saturated
    1257: 'trans_fat_g',   # Fatty acids, total trans
    1005: 'carbs',         # Carbohydrate, by difference
    2000: 'sugars',        # Sugars, total including NLEA
    1079: 'fiber',         # Fiber, total dietary
    1003: 'protein',       # Protein
    1093: '_sodium_mg_raw',# Sodium, Na (mg) — converted to salt separately
    1253: 'cholesterol_mg',# Cholesterol
    1092: 'potassium_mg',  # Potassium, K
    1087: 'calcium_mg',    # Calcium, Ca
    1089: 'iron_mg',       # Iron, Fe
    1110: 'vitamin_d_mcg', # Vitamin D (D2 + D3)
    1162: '_vitc_mg_raw',  # Vitamin C (mg)
}


# ─── Reference constants ─────────────────────────────────────────────────────

_EU_RI = {
    'energy_kcal': 2000.0,
    'energy_kj': 8400.0,
    'fat': 70.0,
    'saturated_fat': 20.0,
    'carbs': 260.0,
    'sugars': 90.0,
    'protein': 50.0,
    'salt': 6.0,
    'fiber': 25.0,
}

_US_DV = {
    'fat': 78.0,
    'saturated_fat': 20.0,
    'cholesterol_mg': 300.0,
    'sodium_mg': 2300.0,
    'carbs': 275.0,
    'fiber': 28.0,
    'added_sugars_g': 50.0,
    'protein': 50.0,
    'vitamin_d_mcg': 20.0,
    'calcium_mg': 1300.0,
    'iron_mg': 18.0,
    'potassium_mg': 4700.0,
}

_UK_TL = {
    'fat': (3.0, 17.5),
    'saturated_fat': (1.5, 5.0),
    'sugars': (5.0, 22.5),
    'salt': (0.3, 1.5),
}


def _tl_color(value, thresholds):
    if not value:
        return 'green'
    if value <= thresholds[0]:
        return 'green'
    elif value <= thresholds[1]:
        return 'amber'
    return 'red'


# ─── Ingredient ──────────────────────────────────────────────────────────────

class CfNutritionIngredient(models.Model):
    _name = "cf.nutrition.ingredient"
    _description = "Valori Nutrizionali Ingrediente"
    _rec_name = "product_id"

    product_id = fields.Many2one("product.template", required=True,
                                  ondelete="cascade")
    # ── sync metadata ─────────────────────────────────────────────────────────
    data_source = fields.Selection([
        ('usda', 'USDA FoodData Central'),
        ('openfoodfacts', 'Open Food Facts'),
        ('crea', 'CREA / Alimentinutrizione'),
        ('manuale', 'Inserimento Manuale'),
    ], string="Fonte Dati", default='manuale')
    external_id = fields.Char(string="ID Esterno (fonte)")
    last_sync = fields.Datetime(string="Ultima Sincronizzazione")
    sync_name = fields.Char(string="Nome usato per ricerca esterna",
                             help="Lascia vuoto per usare il nome del prodotto Odoo")

    # ── Core EU nutrients (per 100g) ──────────────────────────────────────────
    energy_kcal = fields.Float(string="Energia (kcal/100g)")
    energy_kj = fields.Float(string="Energia (kJ/100g)")
    fat = fields.Float(string="Grassi (g/100g)")
    saturated_fat = fields.Float(string="Saturi (g/100g)")
    trans_fat_g = fields.Float(string="Grassi Trans (g/100g)")
    carbs = fields.Float(string="Carboidrati (g/100g)")
    sugars = fields.Float(string="Zuccheri (g/100g)")
    added_sugars_g = fields.Float(string="Zuccheri Aggiunti (g/100g)")
    fiber = fields.Float(string="Fibra (g/100g)")
    protein = fields.Float(string="Proteine (g/100g)")
    salt = fields.Float(string="Sale (g/100g)")

    # ── Extended (mg per 100g — US/Canada/AUS mandatory) ─────────────────────
    sodium_mg = fields.Float(string="Sodio (mg/100g)")
    cholesterol_mg = fields.Float(string="Colesterolo (mg/100g)")
    potassium_mg = fields.Float(string="Potassio (mg/100g)")
    calcium_mg = fields.Float(string="Calcio (mg/100g)")
    iron_mg = fields.Float(string="Ferro (mg/100g)")
    vitamin_d_mcg = fields.Float(string="Vitamina D (mcg/100g)")
    vitamina_c = fields.Float(string="Vitamina C (mg/100g)")

    # ── Legacy USDA reference ─────────────────────────────────────────────────
    fdc_id = fields.Char(string="USDA FDC ID")
    notes = fields.Text()

    # ── API helpers ───────────────────────────────────────────────────────────

    def _get_search_name(self):
        return self.sync_name or (self.product_id.name if self.product_id else '')

    def _apply_nutrients(self, data):
        """Write nutrient dict to self, set last_sync."""
        writable = {k: v for k, v in data.items() if hasattr(self, k) and v is not None}
        writable['last_sync'] = fields.Datetime.now()
        self.write(writable)

    def _fetch_openfoodfacts(self, name):
        """Call Open Food Facts API. Returns nutrient dict or {}."""
        try:
            resp = requests.get(_OFF_API_URL, params={
                'search_terms': name,
                'search_simple': 1,
                'action': 'process',
                'json': 1,
                'page_size': 1,
                'fields': 'nutriments,product_name,id',
            }, timeout=_API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            products = data.get('products', [])
            if not products:
                return {}
            n = products[0].get('nutriments', {})
            product_id_off = products[0].get('id', '')
            sodium_g = n.get('sodium_100g', 0) or 0
            result = {
                'energy_kcal': n.get('energy-kcal_100g') or 0,
                'energy_kj': n.get('energy-kj_100g') or n.get('energy_100g') or 0,
                'fat': n.get('fat_100g') or 0,
                'saturated_fat': n.get('saturated-fat_100g') or 0,
                'trans_fat_g': n.get('trans-fat_100g') or 0,
                'carbs': n.get('carbohydrates_100g') or 0,
                'sugars': n.get('sugars_100g') or 0,
                'fiber': n.get('fiber_100g') or 0,
                'protein': n.get('proteins_100g') or 0,
                'salt': n.get('salt_100g') or 0,
                'sodium_mg': round(sodium_g * 1000, 1),
                'cholesterol_mg': round((n.get('cholesterol_100g') or 0) * 1000, 1),
                'calcium_mg': round((n.get('calcium_100g') or 0) * 1000, 1),
                'iron_mg': round((n.get('iron_100g') or 0) * 1000, 1),
                'vitamin_d_mcg': round((n.get('vitamin-d_100g') or 0) * 1000000, 2),
                'vitamina_c': round((n.get('vitamin-c_100g') or 0) * 1000, 1),
                'data_source': 'openfoodfacts',
                'external_id': product_id_off,
            }
            return result
        except Exception as e:
            _logger.warning("Open Food Facts API error for '%s': %s", name, e)
            return {}

    def _fetch_usda(self, name):
        """Call USDA FoodData Central API. Returns nutrient dict or {}."""
        try:
            resp = requests.get(_USDA_API_URL, params={
                'query': name,
                'api_key': _USDA_API_KEY,
                'pageSize': 1,
                'dataType': 'SR Legacy,Foundation',
            }, timeout=_API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            foods = data.get('foods', [])
            if not foods:
                return {}
            food = foods[0]
            fdc_id = str(food.get('fdcId', ''))
            nutrients = {n['nutrientId']: n.get('value', 0)
                         for n in food.get('foodNutrients', [])
                         if 'nutrientId' in n}
            result = {}
            for nid, field in _USDA_NUTRIENT_IDS.items():
                val = nutrients.get(nid, 0) or 0
                if field == '_sodium_mg_raw':
                    result['sodium_mg'] = val
                    result['salt'] = round(val * 2.5 / 1000, 3)
                elif field == '_vitc_mg_raw':
                    result['vitamina_c'] = val
                else:
                    result[field] = val
            result['data_source'] = 'usda'
            result['external_id'] = fdc_id
            result['fdc_id'] = fdc_id
            return result
        except Exception as e:
            _logger.warning("USDA API error for '%s': %s", name, e)
            return {}

    def action_sync_openfoodfacts(self):
        self.ensure_one()
        name = self._get_search_name()
        if not name:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'title': 'Attenzione', 'message': 'Imposta un prodotto o sync_name prima di sincronizzare.', 'type': 'warning'},
            }
        data = self._fetch_openfoodfacts(name)
        if not data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'title': 'Open Food Facts', 'message': f'Nessun risultato per "{name}".', 'type': 'warning'},
            }
        self._apply_nutrients(data)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Open Food Facts', 'message': f'Valori aggiornati da Open Food Facts (ID: {data.get("external_id","")}).', 'type': 'success'},
        }

    def action_sync_usda(self):
        self.ensure_one()
        name = self._get_search_name()
        if not name:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'title': 'Attenzione', 'message': 'Imposta un prodotto o sync_name prima di sincronizzare.', 'type': 'warning'},
            }
        data = self._fetch_usda(name)
        if not data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'title': 'USDA FDC', 'message': f'Nessun risultato per "{name}".', 'type': 'warning'},
            }
        self._apply_nutrients(data)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'USDA FDC', 'message': f'Valori aggiornati da USDA (FDC ID: {data.get("fdc_id","")}).', 'type': 'success'},
        }

    def action_resync(self):
        self.ensure_one()
        if self.data_source == 'openfoodfacts':
            return self.action_sync_openfoodfacts()
        elif self.data_source == 'usda':
            return self.action_sync_usda()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Resync', 'message': 'Fonte dati manuale — scegli Open Food Facts o USDA.', 'type': 'info'},
        }

    def action_sync_all_stale(self):
        """Pulsante massivo: sincronizza tutti gli ingredienti con last_sync > 30gg o mai sincronizzati."""
        self._cron_sync_ingredients()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Sincronizzazione completata', 'message': 'Aggiornamento completato per tutti gli ingredienti scaduti.', 'type': 'success'},
        }

    @api.model
    def _cron_sync_ingredients(self):
        """Cron giornaliero: aggiorna ingredienti con last_sync > 30 giorni o mai sincronizzati."""
        cutoff = fields.Datetime.now() - timedelta(days=30)
        stale = self.search([
            '|',
            ('last_sync', '=', False),
            ('last_sync', '<', cutoff),
            ('data_source', '!=', 'manuale'),
        ])
        _logger.info("CRON nutrition sync: %d ingredienti da aggiornare", len(stale))
        for ingredient in stale:
            try:
                if ingredient.data_source == 'openfoodfacts':
                    ingredient.action_sync_openfoodfacts()
                elif ingredient.data_source == 'usda':
                    ingredient.action_sync_usda()
            except Exception as e:
                _logger.error("Sync fallita per ingrediente %s: %s",
                              ingredient.product_id.name, e)


# ─── Reference constants (exported for bom model) ────────────────────────────

class CfNutritionBom(models.Model):
    _name = "cf.nutrition.bom"
    _description = "Etichetta Nutrizionale Ricetta"
    _rec_name = "bom_id"

    bom_id = fields.Many2one("mrp.bom", required=True, ondelete="cascade",
                              string="Distinta Base")
    regulation_id = fields.Many2one("cf.nutrition.regulation",
                                    string="Normativa di Riferimento")
    regulation_market = fields.Selection(related='regulation_id.market',
                                         store=False, string="Mercato")
    product_id = fields.Many2one("product.template",
                                  string="Prodotto Singolo (auto-fill)")
    serving_size_g = fields.Float(string="Porzione (g)", default=100.0)

    # ── Core nutritional values per 100g ─────────────────────────────────────
    energy_kcal = fields.Float(string="Energia (kcal/100g)")
    energy_kj = fields.Float(string="Energia (kJ/100g)")
    fat = fields.Float(string="Grassi (g/100g)")
    saturated_fat = fields.Float(string="Saturi (g/100g)")
    trans_fat_g = fields.Float(string="Grassi Trans (g/100g)")
    carbs = fields.Float(string="Carboidrati (g/100g)")
    sugars = fields.Float(string="Zuccheri (g/100g)")
    added_sugars_g = fields.Float(string="Zuccheri Aggiunti (g/100g)")
    fiber = fields.Float(string="Fibra (g/100g)")
    protein = fields.Float(string="Proteine (g/100g)")
    salt = fields.Float(string="Sale (g/100g)")
    sodium_mg = fields.Float(string="Sodio (mg/100g)")
    cholesterol_mg = fields.Float(string="Colesterolo (mg/100g)")
    potassium_mg = fields.Float(string="Potassio (mg/100g)")
    calcium_mg = fields.Float(string="Calcio (mg/100g)")
    iron_mg = fields.Float(string="Ferro (mg/100g)")
    vitamin_d_mcg = fields.Float(string="Vitamina D (mcg/100g)")
    last_computed = fields.Datetime(string="Ultimo Calcolo", readonly=True)

    # ── Per-serving computed values ───────────────────────────────────────────
    _SERVING_DEPENDS = [
        'serving_size_g', 'energy_kcal', 'energy_kj', 'fat', 'saturated_fat',
        'trans_fat_g', 'carbs', 'sugars', 'added_sugars_g', 'fiber', 'protein',
        'salt', 'sodium_mg', 'cholesterol_mg', 'potassium_mg', 'calcium_mg',
        'iron_mg', 'vitamin_d_mcg',
    ]

    energy_kcal_srv = fields.Float(compute="_compute_per_serving",
                                    string="Energia kcal/porz.")
    energy_kj_srv = fields.Float(compute="_compute_per_serving",
                                  string="Energia kJ/porz.")
    fat_srv = fields.Float(compute="_compute_per_serving", string="Grassi/porz.")
    saturated_fat_srv = fields.Float(compute="_compute_per_serving",
                                      string="Saturi/porz.")
    trans_fat_srv = fields.Float(compute="_compute_per_serving",
                                  string="Trans/porz.")
    carbs_srv = fields.Float(compute="_compute_per_serving",
                              string="Carboidrati/porz.")
    sugars_srv = fields.Float(compute="_compute_per_serving",
                               string="Zuccheri/porz.")
    added_sugars_srv = fields.Float(compute="_compute_per_serving",
                                     string="Zucc. Agg./porz.")
    fiber_srv = fields.Float(compute="_compute_per_serving", string="Fibra/porz.")
    protein_srv = fields.Float(compute="_compute_per_serving",
                                string="Proteine/porz.")
    salt_srv = fields.Float(compute="_compute_per_serving", string="Sale/porz.")
    sodium_srv = fields.Float(compute="_compute_per_serving", string="Sodio/porz.")
    cholesterol_srv = fields.Float(compute="_compute_per_serving",
                                    string="Colest./porz.")
    potassium_srv = fields.Float(compute="_compute_per_serving",
                                  string="Potassio/porz.")
    calcium_srv = fields.Float(compute="_compute_per_serving",
                                string="Calcio/porz.")
    iron_srv = fields.Float(compute="_compute_per_serving", string="Ferro/porz.")
    vitamin_d_srv = fields.Float(compute="_compute_per_serving",
                                  string="Vit. D/porz.")

    @api.depends(*_SERVING_DEPENDS)
    def _compute_per_serving(self):
        for rec in self:
            ratio = (rec.serving_size_g or 0.0) / 100.0
            rec.energy_kcal_srv = round(rec.energy_kcal * ratio, 1)
            rec.energy_kj_srv = round(rec.energy_kj * ratio, 1)
            rec.fat_srv = round(rec.fat * ratio, 1)
            rec.saturated_fat_srv = round(rec.saturated_fat * ratio, 1)
            rec.trans_fat_srv = round(rec.trans_fat_g * ratio, 1)
            rec.carbs_srv = round(rec.carbs * ratio, 1)
            rec.sugars_srv = round(rec.sugars * ratio, 1)
            rec.added_sugars_srv = round(rec.added_sugars_g * ratio, 1)
            rec.fiber_srv = round(rec.fiber * ratio, 1)
            rec.protein_srv = round(rec.protein * ratio, 1)
            rec.salt_srv = round(rec.salt * ratio, 1)
            rec.sodium_srv = round(rec.sodium_mg * ratio, 1)
            rec.cholesterol_srv = round(rec.cholesterol_mg * ratio, 1)
            rec.potassium_srv = round(rec.potassium_mg * ratio, 1)
            rec.calcium_srv = round(rec.calcium_mg * ratio, 1)
            rec.iron_srv = round(rec.iron_mg * ratio, 1)
            rec.vitamin_d_srv = round(rec.vitamin_d_mcg * ratio, 1)

    # ── EU %RI (per 100g) ─────────────────────────────────────────────────────
    ri_energy = fields.Float(compute="_compute_eu_ri", string="%RI Energia")
    ri_fat = fields.Float(compute="_compute_eu_ri", string="%RI Grassi")
    ri_sat_fat = fields.Float(compute="_compute_eu_ri", string="%RI Saturi")
    ri_carbs = fields.Float(compute="_compute_eu_ri", string="%RI Carb.")
    ri_sugars = fields.Float(compute="_compute_eu_ri", string="%RI Zuccheri")
    ri_protein = fields.Float(compute="_compute_eu_ri", string="%RI Proteine")
    ri_salt = fields.Float(compute="_compute_eu_ri", string="%RI Sale")

    @api.depends('energy_kcal', 'fat', 'saturated_fat', 'carbs',
                 'sugars', 'protein', 'salt')
    def _compute_eu_ri(self):
        for rec in self:
            rec.ri_energy = round(rec.energy_kcal / _EU_RI['energy_kcal'] * 100, 0) if rec.energy_kcal else 0
            rec.ri_fat = round(rec.fat / _EU_RI['fat'] * 100, 0) if rec.fat else 0
            rec.ri_sat_fat = round(rec.saturated_fat / _EU_RI['saturated_fat'] * 100, 0) if rec.saturated_fat else 0
            rec.ri_carbs = round(rec.carbs / _EU_RI['carbs'] * 100, 0) if rec.carbs else 0
            rec.ri_sugars = round(rec.sugars / _EU_RI['sugars'] * 100, 0) if rec.sugars else 0
            rec.ri_protein = round(rec.protein / _EU_RI['protein'] * 100, 0) if rec.protein else 0
            rec.ri_salt = round(rec.salt / _EU_RI['salt'] * 100, 0) if rec.salt else 0

    # ── US/Canada %DV (per serving) ───────────────────────────────────────────
    dv_fat = fields.Integer(compute="_compute_us_dv", string="%DV Grassi")
    dv_sat_fat = fields.Integer(compute="_compute_us_dv", string="%DV Saturi")
    dv_cholesterol = fields.Integer(compute="_compute_us_dv", string="%DV Colest.")
    dv_sodium = fields.Integer(compute="_compute_us_dv", string="%DV Sodio")
    dv_carbs = fields.Integer(compute="_compute_us_dv", string="%DV Carb.")
    dv_fiber = fields.Integer(compute="_compute_us_dv", string="%DV Fibra")
    dv_added_sugars = fields.Integer(compute="_compute_us_dv",
                                      string="%DV Zucc. Agg.")
    dv_protein = fields.Integer(compute="_compute_us_dv", string="%DV Proteine")
    dv_vitamin_d = fields.Integer(compute="_compute_us_dv", string="%DV Vit. D")
    dv_calcium = fields.Integer(compute="_compute_us_dv", string="%DV Calcio")
    dv_iron = fields.Integer(compute="_compute_us_dv", string="%DV Ferro")
    dv_potassium = fields.Integer(compute="_compute_us_dv", string="%DV Potassio")

    @api.depends('serving_size_g', 'fat', 'saturated_fat', 'cholesterol_mg',
                 'sodium_mg', 'carbs', 'fiber', 'added_sugars_g', 'protein',
                 'vitamin_d_mcg', 'calcium_mg', 'iron_mg', 'potassium_mg')
    def _compute_us_dv(self):
        for rec in self:
            r = (rec.serving_size_g or 0.0) / 100.0

            def dv(val, ref):
                return round(val * r / ref * 100) if val and ref else 0

            rec.dv_fat = dv(rec.fat, _US_DV['fat'])
            rec.dv_sat_fat = dv(rec.saturated_fat, _US_DV['saturated_fat'])
            rec.dv_cholesterol = dv(rec.cholesterol_mg, _US_DV['cholesterol_mg'])
            rec.dv_sodium = dv(rec.sodium_mg, _US_DV['sodium_mg'])
            rec.dv_carbs = dv(rec.carbs, _US_DV['carbs'])
            rec.dv_fiber = dv(rec.fiber, _US_DV['fiber'])
            rec.dv_added_sugars = dv(rec.added_sugars_g, _US_DV['added_sugars_g'])
            rec.dv_protein = dv(rec.protein, _US_DV['protein'])
            rec.dv_vitamin_d = dv(rec.vitamin_d_mcg, _US_DV['vitamin_d_mcg'])
            rec.dv_calcium = dv(rec.calcium_mg, _US_DV['calcium_mg'])
            rec.dv_iron = dv(rec.iron_mg, _US_DV['iron_mg'])
            rec.dv_potassium = dv(rec.potassium_mg, _US_DV['potassium_mg'])

    # ── UK Traffic Light (per 100g) ───────────────────────────────────────────
    _TL_COLORS = [('green', 'Verde'), ('amber', 'Arancio'), ('red', 'Rosso')]

    tl_fat = fields.Selection(_TL_COLORS, compute="_compute_uk_tl",
                               string="Semaforo Grassi")
    tl_sat_fat = fields.Selection(_TL_COLORS, compute="_compute_uk_tl",
                                   string="Semaforo Saturi")
    tl_sugars = fields.Selection(_TL_COLORS, compute="_compute_uk_tl",
                                  string="Semaforo Zuccheri")
    tl_salt = fields.Selection(_TL_COLORS, compute="_compute_uk_tl",
                                string="Semaforo Sale")

    @api.depends('fat', 'saturated_fat', 'sugars', 'salt')
    def _compute_uk_tl(self):
        for rec in self:
            rec.tl_fat = _tl_color(rec.fat, _UK_TL['fat'])
            rec.tl_sat_fat = _tl_color(rec.saturated_fat, _UK_TL['saturated_fat'])
            rec.tl_sugars = _tl_color(rec.sugars, _UK_TL['sugars'])
            rec.tl_salt = _tl_color(rec.salt, _UK_TL['salt'])

    # ── Nutri-Score ────────────────────────────────────────────────────────────
    nutri_score = fields.Selection([
        ("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("E", "E"),
    ], compute="_compute_nutri_score", store=True, string="Nutri-Score")

    @api.depends("energy_kcal", "sugars", "saturated_fat", "salt",
                 "fiber", "protein")
    def _compute_nutri_score(self):
        for rec in self:
            if not rec.energy_kcal:
                rec.nutri_score = False
                continue
            e = rec.energy_kcal
            neg = (0 if e <= 335 else 1 if e <= 670 else 2 if e <= 1005 else
                   3 if e <= 1340 else 4 if e <= 1675 else 5 if e <= 2010 else
                   6 if e <= 2345 else 7 if e <= 2680 else 8 if e <= 3015 else
                   9 if e <= 3350 else 10)
            s = rec.sugars
            neg += (0 if s <= 4.5 else 1 if s <= 9 else 2 if s <= 13.5 else
                    3 if s <= 18 else 4 if s <= 22.5 else 5 if s <= 27 else
                    6 if s <= 31 else 7 if s <= 36 else 8 if s <= 40 else
                    9 if s <= 45 else 10)
            sf = rec.saturated_fat
            neg += (0 if sf <= 1 else 1 if sf <= 2 else 2 if sf <= 3 else
                    3 if sf <= 4 else 4 if sf <= 5 else 5 if sf <= 6 else
                    6 if sf <= 7 else 7 if sf <= 8 else 8 if sf <= 9 else
                    9 if sf <= 10 else 10)
            sl = rec.salt
            neg += (0 if sl <= 0.2 else 1 if sl <= 0.4 else 2 if sl <= 0.6 else
                    3 if sl <= 0.8 else 4 if sl <= 1.0 else 5 if sl <= 1.2 else
                    6 if sl <= 1.4 else 7 if sl <= 1.6 else 8 if sl <= 1.8 else
                    9 if sl <= 2.0 else 10)
            pos = min(5, int((rec.fiber or 0) / 0.9)) + min(5, int((rec.protein or 0) / 1.6))
            score = neg - pos
            rec.nutri_score = ("A" if score <= -1 else "B" if score <= 2
                               else "C" if score <= 10 else "D" if score <= 18
                               else "E")

    # ── Macronutrient chart data (JSON for OWL widget) ─────────────────────────
    macro_chart_data = fields.Char(compute="_compute_macro_chart_data")

    @api.depends('fat', 'carbs', 'protein', 'fiber')
    def _compute_macro_chart_data(self):
        for rec in self:
            total = (rec.fat or 0) + (rec.carbs or 0) + (rec.protein or 0) + (rec.fiber or 0)
            if total > 0:
                rec.macro_chart_data = json.dumps({
                    'fat': round(rec.fat / total * 100, 1),
                    'carbs': round(rec.carbs / total * 100, 1),
                    'protein': round(rec.protein / total * 100, 1),
                    'fiber': round(rec.fiber / total * 100, 1),
                    'labels': {
                        'fat': 'Grassi',
                        'carbs': 'Carboidrati',
                        'protein': 'Proteine',
                        'fiber': 'Fibre',
                    },
                })
            else:
                rec.macro_chart_data = '{}'

    # ── Related BoM lines for Tab BOM ─────────────────────────────────────────
    bom_line_ids = fields.One2many(related='bom_id.bom_line_ids',
                                    string="Ingredienti BoM")

    # ── Regulation display fields ──────────────────────────────────────────────
    regulation_notes = fields.Text(related='regulation_id.notes',
                                    string="Note Normativa")
    regulation_ref_url = fields.Char(related='regulation_id.reference_url',
                                      string="Riferimento Ufficiale")
    regulation_mandatory = fields.Text(related='regulation_id.mandatory_nutrients',
                                        string="Nutrienti Obbligatori")
    regulation_updated = fields.Date(related='regulation_id.last_updated',
                                      string="Normativa aggiornata al")

    # ── helper: calcola valori nutrizionali dalla BoM ─────────────────────────
    _NUTRIENT_FIELDS = [
        'energy_kcal', 'energy_kj', 'fat', 'saturated_fat', 'trans_fat_g',
        'carbs', 'sugars', 'added_sugars_g', 'fiber', 'protein', 'salt',
        'sodium_mg', 'cholesterol_mg', 'potassium_mg', 'calcium_mg',
        'iron_mg', 'vitamin_d_mcg',
    ]

    def _compute_from_bom(self, bom):
        """Calcola media pesata dei valori nutrizionali dalle righe BoM.
        Salta componenti con is_food_ingredient=False (imballaggi, overhead).
        Usa nutrition_ingredient_id (link diretto) se presente, altrimenti cerca per product_id.
        Restituisce (totals_dict, missing_names_list).
        """
        food_lines = [l for l in bom.bom_line_ids if l.product_id.product_tmpl_id.is_food_ingredient]
        total_qty = sum(line.product_qty for line in food_lines)
        if not total_qty:
            return {}, []
        totals = {f: 0.0 for f in self._NUTRIENT_FIELDS}
        missing = []
        for line in food_lines:
            tmpl = line.product_id.product_tmpl_id
            ingredient = tmpl.nutrition_ingredient_id
            if not ingredient:
                ingredient = self.env['cf.nutrition.ingredient'].search(
                    [('product_id', '=', tmpl.id)], limit=1)
            if not ingredient or not ingredient.energy_kcal:
                missing.append(line.product_id.display_name)
                continue
            ratio = line.product_qty / total_qty
            for f in self._NUTRIENT_FIELDS:
                totals[f] += getattr(ingredient, f, 0.0) * ratio
        return totals, missing

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        bom = self.env['mrp.bom'].search(
            [('product_tmpl_id', '=', self.product_id.id),
             ('active', '=', True)], limit=1)
        if bom:
            self.bom_id = bom
            # Auto-crea ingredienti mancanti nella BoM
            cutoff = fields.Datetime.now() - timedelta(days=30)
            for line in bom.bom_line_ids:
                tmpl_id = line.product_id.product_tmpl_id.id
                ingredient = self.env['cf.nutrition.ingredient'].search(
                    [('product_id', '=', tmpl_id)], limit=1)
                if not ingredient:
                    self.env['cf.nutrition.ingredient'].create({
                        'product_id': tmpl_id,
                        'sync_name': line.product_id.display_name,
                        'data_source': 'manuale',
                    })
            totals, missing = self._compute_from_bom(bom)
            for f, v in totals.items():
                setattr(self, f, round(v, 3))
            if missing:
                return {'warning': {
                    'title': 'Valori nutrizionali mancanti',
                    'message': 'Mancano valori per: ' + ', '.join(missing),
                }}
            return
        ingredient = self.env['cf.nutrition.ingredient'].search(
            [('product_id', '=', self.product_id.id)], limit=1)
        if ingredient:
            for f in self._NUTRIENT_FIELDS:
                setattr(self, f, getattr(ingredient, f, 0.0))

    def action_compute(self):
        self.ensure_one()
        bom = self.bom_id
        if not bom:
            return
        totals, missing = self._compute_from_bom(bom)
        if not totals:
            return
        totals['last_computed'] = fields.Datetime.now()
        self.write(totals)
        if missing:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Attenzione — valori mancanti',
                    'message': 'Mancano valori per: ' + ', '.join(missing),
                    'type': 'warning',
                },
            }


# ─── mrp.bom inherit ─────────────────────────────────────────────────────────

class MrpBomNutrition(models.Model):
    _inherit = "mrp.bom"

    nutrition_ids = fields.One2many("cf.nutrition.bom", "bom_id",
                                     string="Etichette Nutrizionali")


# ─── product.template inherit ─────────────────────────────────────────────────

class ProductTemplateNutrition(models.Model):
    _inherit = "product.template"

    is_food_ingredient = fields.Boolean(
        string="E un ingrediente alimentare",
        default=False,
        help="Attiva per includere questo prodotto nel calcolo nutrizionale. "
             "Lascia disattivato per imballaggi, overhead, materiali non food."
    )

    nutrition_ingredient_id = fields.Many2one(
        "cf.nutrition.ingredient",
        string="Dati Nutrizionali",
        help="Collega manualmente il record nutrizionale a questo prodotto. "
             "Prioritario rispetto alla ricerca automatica per nome."
    )

    nutrition_bom_ids = fields.Many2many(
        "cf.nutrition.bom",
        compute="_compute_nutrition_bom_ids",
        string="Etichette Nutrizionali",
    )

    def _compute_nutrition_bom_ids(self):
        for rec in self:
            boms = self.env["mrp.bom"].search(
                [("product_tmpl_id", "=", rec.id)])
            nutrition = self.env["cf.nutrition.bom"].search([
                '|',
                ("bom_id", "in", boms.ids),
                ("product_id", "=", rec.id),
            ])
            rec.nutrition_bom_ids = nutrition

    def action_create_nutrition(self):
        self.ensure_one()
        bom = self.env["mrp.bom"].search(
            [("product_tmpl_id", "=", self.id), ("active", "=", True)], limit=1)
        vals = {'product_id': self.id}
        if bom:
            vals['bom_id'] = bom.id
        nutrition = self.env["cf.nutrition.bom"].create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cf.nutrition.bom',
            'view_mode': 'form',
            'res_id': nutrition.id,
            'target': 'current',
        }

    def _get_or_create_ingredient(self):
        """Recupera o crea il record nutrizionale per questo prodotto."""
        self.ensure_one()
        ingredient = self.nutrition_ingredient_id
        if not ingredient:
            ingredient = self.env['cf.nutrition.ingredient'].search(
                [('product_id', '=', self.id)], limit=1)
        if not ingredient:
            ingredient = self.env['cf.nutrition.ingredient'].create({
                'product_id': self.id,
                'sync_name': self.name,
                'data_source': 'manuale',
            })
        self.nutrition_ingredient_id = ingredient
        return ingredient

    def action_sync_ingredient_usda(self):
        self.ensure_one()
        ingredient = self._get_or_create_ingredient()
        return ingredient.action_sync_usda()

    def action_sync_ingredient_off(self):
        self.ensure_one()
        ingredient = self._get_or_create_ingredient()
        return ingredient.action_sync_openfoodfacts()
