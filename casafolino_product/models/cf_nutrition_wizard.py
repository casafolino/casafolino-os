# -*- coding: utf-8 -*-

import csv
import logging
import os

import requests

from odoo import api, fields, models

from .cf_nutrition import _extract_usda_nutrients

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# USDA FoodData Central Wizard
# ---------------------------------------------------------------------------

class CfNutritionUsdaWizard(models.TransientModel):
    _name = "cf.nutrition.usda.wizard"
    _description = "Ricerca USDA FoodData Central"

    ingredient_id = fields.Many2one("cf.nutrition.ingredient", required=True)
    search_query = fields.Char(string="Ricerca", required=True)
    data_type_filter = fields.Selection([
        ('all', 'Tutti'),
        ('foundation_sr', 'Foundation + SR Legacy (consigliato)'),
        ('branded', 'Solo Branded'),
    ], string="Tipo dati", default='foundation_sr')
    result_ids = fields.One2many("cf.nutrition.usda.wizard.line", "wizard_id")

    def action_search(self):
        """Search USDA API with up to 15 results."""
        self.ensure_one()
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.usda_api_key', 'DEMO_KEY')
        dt_filter = self.data_type_filter or 'foundation_sr'
        if dt_filter == 'foundation_sr':
            data_type = 'SR Legacy,Foundation'
        elif dt_filter == 'branded':
            data_type = 'Branded'
        else:
            data_type = 'SR Legacy,Foundation,Survey (FNDDS),Branded'
        try:
            resp = requests.get(
                "https://api.nal.usda.gov/fdc/v1/foods/search",
                params={
                    'query': self.search_query,
                    'api_key': api_key,
                    'pageSize': 15,
                    'dataType': data_type,
                },
                timeout=8,
            )
            resp.raise_for_status()
            foods = resp.json().get('foods', [])
        except Exception:
            _logger.warning("USDA API search failed for query: %s",
                            self.search_query, exc_info=True)
            foods = []

        # Clear old results
        self.result_ids.unlink()

        lines = []
        for food in foods:
            result, fdc_id = _extract_usda_nutrients(food)
            name = food.get('description',
                            food.get('lowercaseDescription', ''))
            brand = food.get('brandOwner', '') or food.get('brandName', '') or ''
            category = food.get('foodCategory', '') or ''
            data_type_val = food.get('dataType', '') or ''
            lines.append({
                'wizard_id': self.id,
                'fdc_id': fdc_id,
                'name': name,
                'brand': brand,
                'usda_category': category,
                'usda_data_type': data_type_val,
                'energy_kcal': result.get('energy_kcal', 0),
                'fat': result.get('fat', 0),
                'carbs': result.get('carbs', 0),
                'protein': result.get('protein', 0),
                'sugars': result.get('sugars', 0),
                'fiber': result.get('fiber', 0),
                'saturated_fat': result.get('saturated_fat', 0),
                'salt': result.get('salt', 0),
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
            'energy_kj': round(line.energy_kcal * 4.184, 1),
            'fat': line.fat,
            'saturated_fat': line.saturated_fat,
            'carbs': line.carbs,
            'sugars': line.sugars,
            'fiber': line.fiber,
            'protein': line.protein,
            'salt': line.salt,
            'sodium_mg': round(line.salt / 2.5 * 1000, 1) if line.salt else 0,
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
    brand = fields.Char("Brand")
    usda_category = fields.Char("Categoria USDA")
    usda_data_type = fields.Char("Tipo")
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


# ---------------------------------------------------------------------------
# CREA (ISS Italia) Wizard
# ---------------------------------------------------------------------------

def _get_crea_csv_path():
    module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(module_path, 'data', 'crea_alimenti.csv')


def _parse_crea_float(val):
    if not val or val in ('-', '<', 'traces', 'nd', 'tr'):
        return 0.0
    val = val.replace(',', '.').replace('<', '').strip()
    try:
        return float(val)
    except ValueError:
        return 0.0


def _load_crea_db():
    """Load CREA CSV into list of dicts. Cached at module level."""
    path = _get_crea_csv_path()
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            rows.append({
                'codice': row.get('codice', ''),
                'nome': row.get('nome', ''),
                'categoria': row.get('categoria', ''),
                'energy_kcal': _parse_crea_float(row.get('energia_kcal', '')),
                'energy_kj': _parse_crea_float(row.get('energia_kj', '')),
                'water_g': _parse_crea_float(row.get('acqua_g', '')),
                'protein': _parse_crea_float(row.get('proteine_g', '')),
                'fat': _parse_crea_float(row.get('lipidi_g', '')),
                'saturated_fat': _parse_crea_float(row.get('saturi_g', '')),
                'carbs': _parse_crea_float(row.get('carboidrati_g', '')),
                'sugars': _parse_crea_float(row.get('zuccheri_g', '')),
                'fiber': _parse_crea_float(row.get('fibra_g', '')),
                'sodium_mg': _parse_crea_float(row.get('sodio_mg', '')),
                'potassium_mg': _parse_crea_float(row.get('potassio_mg', '')),
                'calcium_mg': _parse_crea_float(row.get('calcio_mg', '')),
                'iron_mg': _parse_crea_float(row.get('ferro_mg', '')),
                'vitamina_c': _parse_crea_float(row.get('vitamina_c_mg', '')),
            })
    return rows


# Simple fuzzy matching: ratio of common words
def _fuzzy_score(query, target):
    """Return 0-100 similarity score between query and target."""
    q_words = set(query.lower().split())
    t_words = set(target.lower().split())
    if not q_words or not t_words:
        return 0
    common = q_words & t_words
    # Score based on overlap
    score = len(common) / max(len(q_words), len(t_words)) * 100
    # Bonus for substring match
    if query.lower() in target.lower():
        score = max(score, 80)
    elif target.lower() in query.lower():
        score = max(score, 70)
    return int(score)


def _search_crea(query, limit=20):
    """Search CREA database by name. Returns list of matching dicts."""
    db = _load_crea_db()
    if not db or not query:
        return []
    q = query.lower()
    # Exact substring matches first
    exact = [r for r in db if q in r['nome'].lower()]
    if len(exact) >= limit:
        return exact[:limit]
    # Fuzzy matches
    scored = [(r, _fuzzy_score(q, r['nome'])) for r in db if r not in exact]
    scored = [(r, s) for r, s in scored if s > 30]
    scored.sort(key=lambda x: -x[1])
    results = exact + [r for r, _ in scored]
    return results[:limit]


class CfNutritionCreaWizard(models.TransientModel):
    _name = "cf.nutrition.crea.wizard"
    _description = "Ricerca CREA (ISS Italia)"

    ingredient_id = fields.Many2one("cf.nutrition.ingredient", required=True)
    search_query = fields.Char(string="Ricerca", required=True)
    result_ids = fields.One2many("cf.nutrition.crea.wizard.line", "wizard_id")

    def action_search(self):
        self.ensure_one()
        self.result_ids.unlink()

        if not os.path.exists(_get_crea_csv_path()):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'CREA',
                    'message': 'File crea_alimenti.csv non trovato in casafolino_product/data/',
                    'type': 'warning', 'sticky': True,
                },
            }

        results = _search_crea(self.search_query, limit=20)
        lines = [{
            'wizard_id': self.id,
            'crea_code': r['codice'],
            'name': r['nome'],
            'categoria': r['categoria'],
            'energy_kcal': r['energy_kcal'],
            'protein': r['protein'],
            'fat': r['fat'],
            'saturated_fat': r['saturated_fat'],
            'carbs': r['carbs'],
            'sugars': r['sugars'],
            'fiber': r['fiber'],
            'salt': round(r['sodium_mg'] * 2.5 / 1000, 3) if r['sodium_mg'] else 0,
        } for r in results]

        if lines:
            self.env["cf.nutrition.crea.wizard.line"].create(lines)

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
        # Find full row from CREA DB for extended nutrients
        db = _load_crea_db()
        full = next((r for r in db if r['codice'] == line.crea_code), {})
        sodium = full.get('sodium_mg', 0) or 0
        vals = {
            'energy_kcal': line.energy_kcal,
            'energy_kj': full.get('energy_kj') or round(line.energy_kcal * 4.184, 1),
            'fat': line.fat,
            'saturated_fat': line.saturated_fat,
            'carbs': line.carbs,
            'sugars': line.sugars,
            'fiber': line.fiber,
            'protein': line.protein,
            'salt': round(sodium * 2.5 / 1000, 3) if sodium else line.salt,
            'sodium_mg': sodium,
            'potassium_mg': full.get('potassium_mg', 0),
            'calcium_mg': full.get('calcium_mg', 0),
            'iron_mg': full.get('iron_mg', 0),
            'vitamina_c': full.get('vitamina_c', 0),
            'crea_code': line.crea_code,
            'external_id': line.crea_code,
            'data_source': 'crea',
            'last_sync': fields.Datetime.now(),
        }
        self.ingredient_id.write(vals)


class CfNutritionCreaWizardLine(models.TransientModel):
    _name = "cf.nutrition.crea.wizard.line"
    _description = "Risultato Ricerca CREA"

    wizard_id = fields.Many2one("cf.nutrition.crea.wizard", ondelete="cascade")
    selected = fields.Boolean(default=False)
    crea_code = fields.Char("Codice CREA")
    name = fields.Char("Alimento")
    categoria = fields.Char("Categoria")
    energy_kcal = fields.Float("kcal/100g")
    protein = fields.Float("Proteine g")
    fat = fields.Float("Grassi g")
    saturated_fat = fields.Float("Saturi g")
    carbs = fields.Float("Carb. g")
    sugars = fields.Float("Zuccheri g")
    fiber = fields.Float("Fibra g")
    salt = fields.Float("Sale g")


# ---------------------------------------------------------------------------
# Bulk CREA Import Wizard
# ---------------------------------------------------------------------------

class CfNutritionBulkImportWizard(models.TransientModel):
    _name = "cf.nutrition.bulk.import.wizard"
    _description = "Importazione massiva dati nutrizionali"

    filter_mode = fields.Selection([
        ('raw_materials', 'Materie Prime (categoria)'),
        ('purchasable', 'Prodotti acquistabili'),
        ('both', 'Entrambi'),
    ], string="Filtra prodotti", default='both', required=True)
    source = fields.Selection([
        ('crea', 'CREA (ISS Italia) — consigliato'),
        ('usda', 'USDA FoodData Central'),
        ('ciqual', 'CIQUAL (ANSES Francia)'),
    ], string="Fonte dati", default='crea', required=True)
    skip_existing = fields.Boolean(
        string="Salta prodotti con dati esistenti", default=True)
    result_message = fields.Text(string="Risultato", readonly=True)

    def action_run(self):
        """Find products, create ingredients, run sync from selected source."""
        self.ensure_one()
        NutrIngredient = self.env['cf.nutrition.ingredient']
        ProductTemplate = self.env['product.template']

        if self.filter_mode == 'raw_materials':
            domain = [('categ_id.name', 'ilike', 'materie prime')]
        elif self.filter_mode == 'purchasable':
            domain = [('purchase_ok', '=', True)]
        else:
            domain = ['|',
                       ('categ_id.name', 'ilike', 'materie prime'),
                       ('purchase_ok', '=', True)]

        products = ProductTemplate.search(domain)
        created = 0
        synced = 0
        failed = 0
        skipped = 0
        to_review = []

        for product in products:
            ingredient = product.nutrition_ingredient_id
            if not ingredient:
                ingredient = NutrIngredient.search(
                    [('product_id', '=', product.id)], limit=1)
            if not ingredient:
                ingredient = NutrIngredient.create({
                    'product_id': product.id,
                    'sync_name': product.name,
                    'data_source': 'manuale',
                })
                product.nutrition_ingredient_id = ingredient
                product.is_food_ingredient = True
                created += 1

            if self.skip_existing and ingredient.energy_kcal:
                skipped += 1
                continue

            if self.source == 'crea':
                results = _search_crea(product.name, limit=3)
                if results:
                    best = results[0]
                    score = _fuzzy_score(product.name, best['nome'])
                    if score >= 80:
                        sodium = best.get('sodium_mg', 0) or 0
                        ingredient._apply_nutrients({
                            'energy_kcal': best['energy_kcal'],
                            'energy_kj': best.get('energy_kj') or round(best['energy_kcal'] * 4.184, 1),
                            'fat': best['fat'],
                            'saturated_fat': best['saturated_fat'],
                            'carbs': best['carbs'],
                            'sugars': best['sugars'],
                            'fiber': best['fiber'],
                            'protein': best['protein'],
                            'salt': round(sodium * 2.5 / 1000, 3) if sodium else 0,
                            'sodium_mg': sodium,
                            'potassium_mg': best.get('potassium_mg', 0),
                            'calcium_mg': best.get('calcium_mg', 0),
                            'iron_mg': best.get('iron_mg', 0),
                            'vitamina_c': best.get('vitamina_c', 0),
                            'crea_code': best['codice'],
                            'external_id': best['codice'],
                            'data_source': 'crea',
                        })
                        synced += 1
                    else:
                        to_review.append(f"{product.name} → {best['nome']} ({score}%)")
                        failed += 1
                else:
                    failed += 1
            elif self.source == 'usda':
                try:
                    data = ingredient._fetch_usda(ingredient._get_search_name())
                    if data and data.get('energy_kcal', 0) > 0:
                        ingredient._apply_nutrients(data)
                        synced += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
            else:
                failed += 1

        msg = (
            f"Prodotti trovati: {len(products)}\n"
            f"Record nutrizionali creati: {created}\n"
            f"Importati automaticamente: {synced}\n"
            f"Saltati (dati esistenti): {skipped}\n"
            f"Non trovati / sotto soglia: {failed}"
        )
        if to_review:
            msg += "\n\nDa verificare manualmente:\n" + "\n".join(to_review[:20])
        self.result_message = msg

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
