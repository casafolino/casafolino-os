# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

FDC_API_BASE = "https://api.nal.usda.gov/fdc/v1"
# DEMO_KEY: 30 req/hr. Get a free key at https://fdc.nal.usda.gov/api-guide.html
FDC_API_KEY = "DEMO_KEY"

# USDA FoodData Central nutrient IDs
FDC_NUTRIENT_MAP = {
    'energy_kcal': 1008,
    'energy_kj': 1062,
    'protein': 1003,
    'fat': 1004,
    'saturated_fat': 1258,
    'trans_fat': 1257,
    'carbs': 1005,
    'fiber': 1079,
    'sugars': 2000,
    'added_sugars': 1235,
    'sodium': 1093,
    'cholesterol_mg': 1253,
    'potassium_mg': 1092,
    'calcium_mg': 1087,
    'iron_mg': 1089,
    'vitamin_d_mcg': 1114,
}

# Stored fields computed by weighted-average from BoM lines (all per 100g)
COMPUTE_FIELDS = list(FDC_NUTRIENT_MAP.keys()) + ['salt']


class CfNutritionIngredient(models.Model):
    _name = "cf.nutrition.ingredient"
    _description = "Valori Nutrizionali Ingrediente"
    _rec_name = "product_id"

    product_id = fields.Many2one("product.template", required=True, ondelete="cascade")

    # Macronutrienti per 100g
    energy_kcal = fields.Float(string="Energia (kcal/100g)")
    energy_kj = fields.Float(string="Energia (kJ/100g)")
    fat = fields.Float(string="Grassi totali (g/100g)")
    saturated_fat = fields.Float(string="Grassi Saturi (g/100g)")
    trans_fat = fields.Float(string="Grassi Trans (g/100g)")
    carbs = fields.Float(string="Carboidrati (g/100g)")
    sugars = fields.Float(string="Zuccheri (g/100g)")
    added_sugars = fields.Float(string="Zuccheri Aggiunti (g/100g)")
    fiber = fields.Float(string="Fibra Alimentare (g/100g)")
    protein = fields.Float(string="Proteine (g/100g)")
    salt = fields.Float(string="Sale (g/100g)")
    sodium = fields.Float(string="Sodio (mg/100g)")

    # Micronutrienti per 100g
    cholesterol_mg = fields.Float(string="Colesterolo (mg/100g)")
    potassium_mg = fields.Float(string="Potassio (mg/100g)")
    calcium_mg = fields.Float(string="Calcio (mg/100g)")
    iron_mg = fields.Float(string="Ferro (mg/100g)")
    vitamin_d_mcg = fields.Float(string="Vitamina D (mcg/100g)")

    fdc_id = fields.Char(string="USDA FDC ID")
    notes = fields.Text(string="Note")

    @api.onchange('sodium')
    def _onchange_sodium(self):
        """Sync salt from sodium: salt(g) = sodium(mg) / 400"""
        if self.sodium:
            self.salt = round(self.sodium / 400.0, 3)

    @api.onchange('salt')
    def _onchange_salt(self):
        """Sync sodium from salt when sodium is empty: sodium(mg) = salt(g) * 400"""
        if self.salt and not self.sodium:
            self.sodium = round(self.salt * 400.0, 1)

    def action_fetch_fdc(self):
        """Fetch nutritional data from USDA FoodData Central API."""
        self.ensure_one()
        if not self.fdc_id:
            raise UserError(
                "Inserisci prima un USDA FDC ID nel campo apposito.\n"
                "Cerca l'ID su https://fdc.nal.usda.gov/"
            )
        url = f"{FDC_API_BASE}/food/{self.fdc_id.strip()}?api_key={FDC_API_KEY}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            raise UserError("Impossibile connettersi a api.nal.usda.gov. Verificare la connessione.")
        except requests.exceptions.Timeout:
            raise UserError("Timeout durante la richiesta USDA FDC (>15s).")
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 404:
                raise UserError(f"FDC ID '{self.fdc_id}' non trovato. Verifica su https://fdc.nal.usda.gov/")
            raise UserError(f"Errore HTTP {resp.status_code}: {e}")

        nutrients_raw = {}
        for n in data.get('foodNutrients', []):
            nutrient = n.get('nutrient') or {}
            nid = nutrient.get('id') if nutrient else n.get('nutrientId')
            amt = n.get('amount')
            if nid and amt is not None:
                nutrients_raw[int(nid)] = float(amt)

        vals = {}
        for field, nid in FDC_NUTRIENT_MAP.items():
            if nid in nutrients_raw:
                vals[field] = nutrients_raw[nid]

        if 'sodium' in vals:
            vals['salt'] = round(vals['sodium'] / 400.0, 3)

        if not vals:
            raise UserError(
                f"Nessun dato nutrizionale trovato per FDC ID {self.fdc_id}.\n"
                "Verifica che l'ID sia corretto su https://fdc.nal.usda.gov/"
            )

        self.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'USDA FDC importato',
                'message': f'Aggiornati {len(vals)} valori per "{data.get("description", self.fdc_id)}".',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_fdc_search(self):
        """Open FDC search wizard pre-filled with product name."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cerca Prodotto USDA FDC',
            'res_model': 'cf.nutrition.fdc.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ingredient_id': self.id,
                'default_query': self.product_id.name or '',
            }
        }


class CfNutritionFdcWizard(models.TransientModel):
    """Wizard per cercare prodotti nel database USDA FoodData Central."""
    _name = "cf.nutrition.fdc.wizard"
    _description = "Ricerca Prodotti USDA FDC"

    ingredient_id = fields.Many2one("cf.nutrition.ingredient", string="Ingrediente")
    query = fields.Char(string="Cerca prodotto", required=True)
    results_html = fields.Html(string="Risultati", readonly=True, sanitize=False)
    fdc_id_selected = fields.Char(string="FDC ID selezionato")

    def action_search(self):
        self.ensure_one()
        if not self.query:
            raise UserError("Inserisci un termine di ricerca.")
        url = (
            f"{FDC_API_BASE}/foods/search"
            f"?query={requests.utils.quote(self.query)}"
            f"&pageSize=20&api_key={FDC_API_KEY}"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            raise UserError(f"Errore di ricerca USDA FDC: {e}")

        foods = data.get('foods', [])
        if not foods:
            self.results_html = "<p class='text-muted'>Nessun risultato. Prova un termine diverso.</p>"
        else:
            rows = ""
            for f in foods:
                fdc_id = f.get('fdcId', '')
                desc = f.get('description', '')
                brand = f.get('brandOwner', '') or f.get('dataType', '')
                category = f.get('foodCategory', '')
                rows += (
                    f"<tr>"
                    f"<td><code style='font-weight:bold;color:#5A6E3A;'>{fdc_id}</code></td>"
                    f"<td>{desc}</td>"
                    f"<td style='color:#666;'>{brand}</td>"
                    f"<td style='color:#666;'>{category}</td>"
                    f"</tr>"
                )
            self.results_html = (
                "<div style='max-height:400px;overflow-y:auto;'>"
                "<table class='table table-sm table-bordered table-hover' style='font-size:12px;'>"
                "<thead style='position:sticky;top:0;background:#343a40;color:#fff;'>"
                "<tr><th>FDC ID</th><th>Prodotto</th><th>Marca / Tipo</th><th>Categoria</th></tr>"
                "</thead>"
                f"<tbody>{rows}</tbody>"
                "</table>"
                "</div>"
                "<p class='text-muted small mt-2'>Copia il FDC ID (in verde) nel campo sottostante, poi clicca <b>Importa</b>.</p>"
            )
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_import(self):
        self.ensure_one()
        if not self.fdc_id_selected:
            raise UserError("Inserisci un FDC ID nel campo 'FDC ID selezionato'.")
        if not self.ingredient_id:
            raise UserError("Nessun ingrediente collegato al wizard.")
        self.ingredient_id.fdc_id = self.fdc_id_selected.strip()
        return self.ingredient_id.action_fetch_fdc()


class CfNutritionBom(models.Model):
    _name = "cf.nutrition.bom"
    _description = "Valori Nutrizionali Ricetta"
    _rec_name = "bom_id"

    bom_id = fields.Many2one("mrp.bom", required=True, ondelete="cascade", string="Ricetta (BoM)")
    serving_size_g = fields.Float(string="Porzione (g)", default=100.0)

    # ── Per 100g — stored, computed by action_compute / onchange ──────────
    energy_kcal = fields.Float(string="Energia (kcal)", readonly=True)
    energy_kj = fields.Float(string="Energia (kJ)", readonly=True)
    fat = fields.Float(string="Grassi (g)", readonly=True)
    saturated_fat = fields.Float(string="Saturi (g)", readonly=True)
    trans_fat = fields.Float(string="Trans (g)", readonly=True)
    carbs = fields.Float(string="Carboidrati (g)", readonly=True)
    sugars = fields.Float(string="Zuccheri (g)", readonly=True)
    added_sugars = fields.Float(string="Zucch. Aggiunti (g)", readonly=True)
    fiber = fields.Float(string="Fibra (g)", readonly=True)
    protein = fields.Float(string="Proteine (g)", readonly=True)
    salt = fields.Float(string="Sale (g)", readonly=True)
    sodium = fields.Float(string="Sodio (mg)", readonly=True)
    cholesterol_mg = fields.Float(string="Colesterolo (mg)", readonly=True)
    potassium_mg = fields.Float(string="Potassio (mg)", readonly=True)
    calcium_mg = fields.Float(string="Calcio (mg)", readonly=True)
    iron_mg = fields.Float(string="Ferro (mg)", readonly=True)
    vitamin_d_mcg = fields.Float(string="Vitamina D (mcg)", readonly=True)
    last_computed = fields.Datetime(string="Ultimo Calcolo", readonly=True)

    # Nutri-Score
    nutri_score = fields.Selection([
        ("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("E", "E"),
    ], compute="_compute_nutri_score", store=True, string="Nutri-Score")
    nutri_score_color = fields.Char(compute="_compute_nutri_score_color")

    # ── Per porzione (computed, not stored) ───────────────────────────────
    srv_energy_kcal = fields.Float(compute="_compute_per_serving", string="Energia kcal/porz.")
    srv_energy_kj = fields.Float(compute="_compute_per_serving", string="Energia kJ/porz.")
    srv_fat = fields.Float(compute="_compute_per_serving", string="Grassi/porz.")
    srv_saturated_fat = fields.Float(compute="_compute_per_serving", string="Saturi/porz.")
    srv_trans_fat = fields.Float(compute="_compute_per_serving", string="Trans/porz.")
    srv_carbs = fields.Float(compute="_compute_per_serving", string="Carb./porz.")
    srv_sugars = fields.Float(compute="_compute_per_serving", string="Zuccheri/porz.")
    srv_added_sugars = fields.Float(compute="_compute_per_serving", string="Agg./porz.")
    srv_fiber = fields.Float(compute="_compute_per_serving", string="Fibra/porz.")
    srv_protein = fields.Float(compute="_compute_per_serving", string="Proteine/porz.")
    srv_salt = fields.Float(compute="_compute_per_serving", string="Sale/porz.")
    srv_sodium = fields.Float(compute="_compute_per_serving", string="Sodio/porz.")
    srv_cholesterol_mg = fields.Float(compute="_compute_per_serving", string="Colest./porz.")
    srv_potassium_mg = fields.Float(compute="_compute_per_serving", string="Potassio/porz.")
    srv_calcium_mg = fields.Float(compute="_compute_per_serving", string="Calcio/porz.")
    srv_iron_mg = fields.Float(compute="_compute_per_serving", string="Ferro/porz.")
    srv_vitamin_d_mcg = fields.Float(compute="_compute_per_serving", string="Vit.D/porz.")

    # ── US/Canada % Daily Value per porzione (computed, not stored) ───────
    dv_fat = fields.Float(compute="_compute_us_dv", string="% DV Grassi")
    dv_sat_fat = fields.Float(compute="_compute_us_dv", string="% DV Saturi")
    dv_cholesterol = fields.Float(compute="_compute_us_dv", string="% DV Colest.")
    dv_sodium = fields.Float(compute="_compute_us_dv", string="% DV Sodio")
    dv_carbs = fields.Float(compute="_compute_us_dv", string="% DV Carb.")
    dv_fiber = fields.Float(compute="_compute_us_dv", string="% DV Fibra")
    dv_added_sugars = fields.Float(compute="_compute_us_dv", string="% DV Zucc.Agg.")
    dv_protein = fields.Float(compute="_compute_us_dv", string="% DV Proteine")
    dv_vit_d = fields.Float(compute="_compute_us_dv", string="% DV Vit.D")
    dv_calcium = fields.Float(compute="_compute_us_dv", string="% DV Calcio")
    dv_iron = fields.Float(compute="_compute_us_dv", string="% DV Ferro")
    dv_potassium = fields.Float(compute="_compute_us_dv", string="% DV Potassio")

    @api.depends(
        'serving_size_g', 'energy_kcal', 'energy_kj', 'fat', 'saturated_fat',
        'trans_fat', 'carbs', 'sugars', 'added_sugars', 'fiber', 'protein',
        'salt', 'sodium', 'cholesterol_mg', 'potassium_mg', 'calcium_mg',
        'iron_mg', 'vitamin_d_mcg'
    )
    def _compute_per_serving(self):
        for rec in self:
            f = (rec.serving_size_g or 100.0) / 100.0
            rec.srv_energy_kcal = round(rec.energy_kcal * f, 1)
            rec.srv_energy_kj = round(rec.energy_kj * f, 1)
            rec.srv_fat = round(rec.fat * f, 2)
            rec.srv_saturated_fat = round(rec.saturated_fat * f, 2)
            rec.srv_trans_fat = round(rec.trans_fat * f, 2)
            rec.srv_carbs = round(rec.carbs * f, 2)
            rec.srv_sugars = round(rec.sugars * f, 2)
            rec.srv_added_sugars = round(rec.added_sugars * f, 2)
            rec.srv_fiber = round(rec.fiber * f, 2)
            rec.srv_protein = round(rec.protein * f, 2)
            rec.srv_salt = round(rec.salt * f, 2)
            rec.srv_sodium = round(rec.sodium * f, 1)
            rec.srv_cholesterol_mg = round(rec.cholesterol_mg * f, 1)
            rec.srv_potassium_mg = round(rec.potassium_mg * f, 1)
            rec.srv_calcium_mg = round(rec.calcium_mg * f, 1)
            rec.srv_iron_mg = round(rec.iron_mg * f, 3)
            rec.srv_vitamin_d_mcg = round(rec.vitamin_d_mcg * f, 2)

    @api.depends(
        'serving_size_g', 'fat', 'saturated_fat', 'cholesterol_mg', 'sodium',
        'carbs', 'fiber', 'added_sugars', 'protein',
        'vitamin_d_mcg', 'calcium_mg', 'iron_mg', 'potassium_mg'
    )
    def _compute_us_dv(self):
        """% Daily Value (FDA 2020 reference amounts per serving)."""
        for rec in self:
            f = (rec.serving_size_g or 100.0) / 100.0

            def pct(base, dv):
                return round(base * f / dv * 100) if base and dv else 0

            rec.dv_fat = pct(rec.fat, 78.0)
            rec.dv_sat_fat = pct(rec.saturated_fat, 20.0)
            rec.dv_cholesterol = pct(rec.cholesterol_mg, 300.0)
            rec.dv_sodium = pct(rec.sodium, 2300.0)
            rec.dv_carbs = pct(rec.carbs, 275.0)
            rec.dv_fiber = pct(rec.fiber, 28.0)
            rec.dv_added_sugars = pct(rec.added_sugars, 50.0)
            rec.dv_protein = pct(rec.protein, 50.0)
            rec.dv_vit_d = pct(rec.vitamin_d_mcg, 20.0)
            rec.dv_calcium = pct(rec.calcium_mg, 1300.0)
            rec.dv_iron = pct(rec.iron_mg, 18.0)
            rec.dv_potassium = pct(rec.potassium_mg, 4700.0)

    @api.depends("energy_kcal", "sugars", "saturated_fat", "salt", "fiber", "protein")
    def _compute_nutri_score(self):
        """Nutri-Score semplificato (A=migliore, E=peggiore) — Reg. UE."""
        for rec in self:
            if not rec.energy_kcal:
                rec.nutri_score = False
                continue
            neg = 0
            neg += 0 if rec.energy_kcal <= 335 else 1 if rec.energy_kcal <= 670 else 2 if rec.energy_kcal <= 1005 else 3 if rec.energy_kcal <= 1340 else 4 if rec.energy_kcal <= 1675 else 5 if rec.energy_kcal <= 2010 else 6 if rec.energy_kcal <= 2345 else 7 if rec.energy_kcal <= 2680 else 8 if rec.energy_kcal <= 3015 else 9 if rec.energy_kcal <= 3350 else 10
            neg += 0 if rec.sugars <= 4.5 else 1 if rec.sugars <= 9 else 2 if rec.sugars <= 13.5 else 3 if rec.sugars <= 18 else 4 if rec.sugars <= 22.5 else 5 if rec.sugars <= 27 else 6 if rec.sugars <= 31 else 7 if rec.sugars <= 36 else 8 if rec.sugars <= 40 else 9 if rec.sugars <= 45 else 10
            neg += 0 if rec.saturated_fat <= 1 else 1 if rec.saturated_fat <= 2 else 2 if rec.saturated_fat <= 3 else 3 if rec.saturated_fat <= 4 else 4 if rec.saturated_fat <= 5 else 5 if rec.saturated_fat <= 6 else 6 if rec.saturated_fat <= 7 else 7 if rec.saturated_fat <= 8 else 8 if rec.saturated_fat <= 9 else 9 if rec.saturated_fat <= 10 else 10
            neg += 0 if rec.salt <= 0.2 else 1 if rec.salt <= 0.4 else 2 if rec.salt <= 0.6 else 3 if rec.salt <= 0.8 else 4 if rec.salt <= 1.0 else 5 if rec.salt <= 1.2 else 6 if rec.salt <= 1.4 else 7 if rec.salt <= 1.6 else 8 if rec.salt <= 1.8 else 9 if rec.salt <= 2.0 else 10
            pos = min(5, int(rec.fiber / 0.9)) + min(5, int(rec.protein / 1.6))
            score = neg - pos
            rec.nutri_score = "A" if score <= -1 else "B" if score <= 2 else "C" if score <= 10 else "D" if score <= 18 else "E"

    @api.depends("nutri_score")
    def _compute_nutri_score_color(self):
        colors = {"A": "#1a7e3c", "B": "#85bb2f", "C": "#f7c325", "D": "#e8821e", "E": "#e63312"}
        for rec in self:
            rec.nutri_score_color = colors.get(rec.nutri_score, "#6c757d")

    def _get_computed_vals(self):
        """Weighted-average nutrition per 100g from BoM lines."""
        bom = self.bom_id
        if not bom:
            return {}
        total_qty = sum(line.product_qty for line in bom.bom_line_ids)
        if not total_qty:
            return {}
        totals = {f: 0.0 for f in COMPUTE_FIELDS}
        missing = []
        for line in bom.bom_line_ids:
            ingr = self.env["cf.nutrition.ingredient"].search(
                [("product_id", "=", line.product_id.product_tmpl_id.id)], limit=1
            )
            if not ingr:
                missing.append(line.product_id.display_name)
                continue
            ratio = line.product_qty / total_qty
            for f in COMPUTE_FIELDS:
                totals[f] += getattr(ingr, f) * ratio
        totals["last_computed"] = fields.Datetime.now()
        if missing:
            totals['_missing'] = missing
        return totals

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        """Auto-generate nutritional values when a recipe is selected."""
        if not self.bom_id:
            return
        vals = self._get_computed_vals()
        missing = vals.pop('_missing', [])
        for k, v in vals.items():
            setattr(self, k, v)
        if missing:
            return {
                'warning': {
                    'title': 'Ingredienti senza dati nutrizionali',
                    'message': (
                        "I seguenti ingredienti non hanno valori nutrizionali configurati "
                        f"e sono stati esclusi dal calcolo:\n\n\u2022 " + "\n\u2022 ".join(missing) +
                        "\n\nAggiungili in Nutrizione \u2192 Ingredienti."
                    )
                }
            }

    def action_compute(self):
        """Ricalcola e salva i valori nutrizionali dal BoM."""
        self.ensure_one()
        vals = self._get_computed_vals()
        vals.pop('_missing', None)
        if vals:
            self.write(vals)


class MrpBomNutrition(models.Model):
    _inherit = "mrp.bom"
    nutrition_ids = fields.One2many("cf.nutrition.bom", "bom_id", string="Valori Nutrizionali")
