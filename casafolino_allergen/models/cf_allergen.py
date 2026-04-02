# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CfAllergen(models.Model):
    _name = "cf.allergen"
    _description = "Allergene"
    _order = "sequence"
    _rec_name = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    market = fields.Selection([
        ('eu', 'Unione Europea'),
        ('usa', 'USA (FDA)'),
        ('canada', 'Canada'),
        ('australia', 'Australia / NZ'),
        ('uk', 'Regno Unito'),
    ], string="Mercato", default='eu', required=True, index=True)
    severity_default = fields.Selection([
        ('presente', 'Presente'),
        ('tracce', 'Può contenere tracce'),
        ('assente', 'Assente'),
    ], string="Severità default", default='assente')
    description = fields.Text(string="Descrizione")
    regulation_ref = fields.Char(string="Rif. Regolamento", default="Reg. 1169/2011")
    active = fields.Boolean(default=True)
    keyword_ids = fields.One2many('cf.allergen.keyword', 'allergen_id',
                                   string="Keywords rilevamento")
    products_count = fields.Integer(
        string="Prodotti", compute="_compute_products_count", store=False)

    def _compute_products_count(self):
        for rec in self:
            rec.products_count = self.env["cf.recipe.allergen"].search_count([
                ("allergen_id", "=", rec.id),
                ("status", "in", ("present", "traces")),
            ])


class CfAllergenKeyword(models.Model):
    _name = "cf.allergen.keyword"
    _description = "Keyword Allergene"
    _order = "allergen_id, keyword"

    allergen_id = fields.Many2one("cf.allergen", required=True, ondelete="cascade")
    keyword = fields.Char(required=True)
    match_type = fields.Selection([
        ("exact", "Esatta"),
        ("partial", "Parziale"),
        ("starts", "Inizia con"),
    ], default="partial")


class CfRecipeAllergen(models.Model):
    _name = "cf.recipe.allergen"
    _description = "Allergene Ricetta / Prodotto"

    bom_id = fields.Many2one("mrp.bom", ondelete="cascade")
    product_id = fields.Many2one("product.template",
                                  string="Prodotto",
                                  compute="_compute_product_id", store=True)
    allergen_id = fields.Many2one("cf.allergen", required=True)
    status = fields.Selection([
        ("present", "Presente"),
        ("traces", "Può Contenere Tracce"),
        ("absent", "Assente"),
    ], required=True, default="absent")
    source_ingredient = fields.Char(string="Ingrediente fonte")
    auto_detected = fields.Boolean(string="Rilevato auto", default=False)
    verified = fields.Boolean(string="Verificato manualmente", default=False)
    cross_contamination = fields.Boolean(default=False)
    notes = fields.Text()
    validated_by = fields.Many2one("res.users", string="Validato da")
    validation_date = fields.Date(string="Data Validazione")

    @api.depends('bom_id', 'bom_id.product_tmpl_id')
    def _compute_product_id(self):
        for rec in self:
            rec.product_id = rec.bom_id.product_tmpl_id if rec.bom_id else False


class MrpBomAllergen(models.Model):
    _inherit = "mrp.bom"

    allergen_ids = fields.One2many("cf.recipe.allergen", "bom_id",
                                    string="Allergeni")
    allergen_validated = fields.Boolean(string="Dichiarazione Validata",
                                         default=False)
    allergen_alert_text = fields.Char(compute="_compute_allergen_texts",
                                       string="Alert allergeni")
    allergen_label_text = fields.Text(compute="_compute_allergen_texts",
                                       string="Testo etichetta")

    @api.depends('allergen_ids', 'allergen_ids.status', 'allergen_ids.allergen_id')
    def _compute_allergen_texts(self):
        for rec in self:
            present = rec.allergen_ids.filtered(
                lambda a: a.status == 'present').mapped('allergen_id.name')
            traces = rec.allergen_ids.filtered(
                lambda a: a.status == 'traces').mapped('allergen_id.name')
            if present:
                rec.allergen_alert_text = "ALLERGENI PRESENTI: " + ", ".join(present)
            elif traces:
                rec.allergen_alert_text = "Tracce possibili: " + ", ".join(traces)
            else:
                rec.allergen_alert_text = False
            parts = []
            if present:
                parts.append("Contiene: " + ", ".join(present) + ".")
            if traces:
                parts.append("Può contenere tracce di: " + ", ".join(traces) + ".")
            rec.allergen_label_text = " ".join(parts) if parts else False

    def action_analyze_allergens(self):
        self.ensure_one()
        keywords = self.env["cf.allergen.keyword"].search([])
        # Build dict: allergen_id → list of (keyword, match_type)
        kw_map = {}
        for kw in keywords:
            kw_map.setdefault(kw.allergen_id.id, []).append(kw)

        allergens = self.env["cf.allergen"].search([])
        for allergen in allergens:
            # Check each BoM ingredient against this allergen's keywords
            found_status = 'absent'
            source_names = []
            kws = kw_map.get(allergen.id, [])
            for line in self.bom_line_ids:
                ingredient_name = (line.product_id.name or '').lower()
                for kw in kws:
                    k = kw.keyword.lower()
                    matched = False
                    if kw.match_type == "exact" and k == ingredient_name:
                        matched = True
                    elif kw.match_type == "partial" and k in ingredient_name:
                        matched = True
                    elif kw.match_type == "starts" and ingredient_name.startswith(k):
                        matched = True
                    if matched:
                        found_status = 'present'
                        source_names.append(line.product_id.name)
                        break

            existing = self.allergen_ids.filtered(
                lambda a: a.allergen_id.id == allergen.id)
            vals = {
                'status': found_status,
                'source_ingredient': ", ".join(source_names) if source_names else False,
                'auto_detected': True,
            }
            if existing:
                # Only update if not manually verified
                if not existing[0].verified:
                    existing[0].write(vals)
            else:
                self.env["cf.recipe.allergen"].create({
                    'bom_id': self.id,
                    'allergen_id': allergen.id,
                    **vals,
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Analisi completata',
                'message': f'Analizzati {len(allergens)} allergeni su {len(self.bom_line_ids)} ingredienti.',
                'type': 'success',
                'sticky': False,
            }
        }


class ProductTemplateAllergen(models.Model):
    _inherit = "product.template"

    allergen_bom_ids = fields.One2many(
        "cf.recipe.allergen", "product_id",
        string="Allergeni (da BoM)", readonly=True)
    allergen_label_text = fields.Text(
        string="Testo etichetta allergeni",
        compute="_compute_product_allergen_text")
    allergen_alert_text = fields.Char(
        compute="_compute_product_allergen_text",
        string="Alert allergeni")

    @api.depends('allergen_bom_ids', 'allergen_bom_ids.status')
    def _compute_product_allergen_text(self):
        for rec in self:
            present = rec.allergen_bom_ids.filtered(
                lambda a: a.status == 'present').mapped('allergen_id.name')
            traces = rec.allergen_bom_ids.filtered(
                lambda a: a.status == 'traces').mapped('allergen_id.name')
            if present:
                rec.allergen_alert_text = "ALLERGENI PRESENTI: " + ", ".join(present)
            else:
                rec.allergen_alert_text = False
            parts = []
            if present:
                parts.append("Contiene: " + ", ".join(present) + ".")
            if traces:
                parts.append("Può contenere tracce di: " + ", ".join(traces) + ".")
            rec.allergen_label_text = " ".join(parts) if parts else False
