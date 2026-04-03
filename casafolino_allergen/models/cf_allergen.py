# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CfAllergenCategory(models.Model):
    _name = "cf.allergen.category"
    _description = "Categoria Allergene"
    _order = "sequence"

    name = fields.Char("Nome", required=True)
    code = fields.Char("Codice", help="Es: GLUTEN, NUTS, MILK")
    color = fields.Integer("Colore", default=1)
    sequence = fields.Integer(default=10)
    allergen_ids = fields.One2many("cf.allergen", "category_id", "Allergeni")
    allergen_count = fields.Integer(compute="_compute_count")
    is_eu = fields.Boolean("EU/UK (Reg. 1169/2011)")
    is_usa = fields.Boolean("USA (FDA FALCPA)")
    is_canada = fields.Boolean("Canada (CFIA)")
    is_australia = fields.Boolean("Australia/NZ (FSANZ)")
    is_japan = fields.Boolean("Giappone (CAA)")
    is_codex = fields.Boolean("Codex Alimentarius")

    def _compute_count(self):
        for rec in self:
            rec.allergen_count = len(rec.allergen_ids)


class CfAllergenAlias(models.Model):
    _name = "cf.allergen.alias"
    _description = "Nome Alternativo Allergene"
    _order = "allergen_id, name"

    allergen_id = fields.Many2one("cf.allergen", ondelete="cascade", required=True)
    name = fields.Char("Nome Alternativo", required=True)
    lang = fields.Char("Lingua", default="it")


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
    category_id = fields.Many2one("cf.allergen.category", "Categoria")
    name_en = fields.Char("Nome EN")
    name_de = fields.Char("Nome DE")
    name_fr = fields.Char("Nome FR")
    name_es = fields.Char("Nome ES")
    is_mandatory_eu = fields.Boolean("Obbligatorio EU/UK")
    is_mandatory_usa = fields.Boolean("Obbligatorio USA")
    is_mandatory_canada = fields.Boolean("Obbligatorio Canada")
    is_mandatory_australia = fields.Boolean("Obbligatorio Australia/NZ")
    is_mandatory_japan = fields.Boolean("Obbligatorio Giappone")
    is_recommended_japan = fields.Boolean("Raccomandato Giappone")
    alias_ids = fields.One2many("cf.allergen.alias", "allergen_id", "Nomi Alternativi")
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
    allergen_ids = fields.Many2many(
        "cf.allergen", "product_allergen_contains_rel",
        "product_id", "allergen_id",
        string="Allergeni Contenuti")
    allergen_may_contain_ids = fields.Many2many(
        "cf.allergen", "product_allergen_may_rel",
        "product_id", "allergen_id",
        string="Puo Contenere (tracce)")
    allergen_check_state = fields.Selection([
        ("unchecked", "Non Verificato"),
        ("ok", "Verificato - Conforme"),
        ("alert", "ATTENZIONE - Allergeni non dichiarati"),
    ], string="Stato Allergeni", compute="_compute_allergen_check", store=True)
    allergen_alert_msg = fields.Text(
        "Dettaglio Alert", compute="_compute_allergen_check", store=True)
    allergen_label_text = fields.Text(
        string="Testo etichetta allergeni",
        compute="_compute_product_allergen_text")
    allergen_alert_text = fields.Char(
        compute="_compute_product_allergen_text",
        string="Alert allergeni")

    @api.depends("allergen_ids", "bom_ids", "bom_ids.bom_line_ids",
                 "bom_ids.bom_line_ids.product_id")
    def _compute_allergen_check(self):
        for tmpl in self:
            boms = tmpl.bom_ids
            if not boms:
                tmpl.allergen_check_state = "unchecked"
                tmpl.allergen_alert_msg = ""
                continue
            bom_allergens = self.env["cf.allergen"]
            for bom in boms:
                for line in bom.bom_line_ids:
                    line_tmpl = line.product_id.product_tmpl_id
                    bom_allergens |= line_tmpl.sudo().allergen_ids
            declared = tmpl.allergen_ids
            undeclared = bom_allergens - declared
            if not bom_allergens:
                tmpl.allergen_check_state = "unchecked"
                tmpl.allergen_alert_msg = "Nessun allergene trovato negli ingredienti"
            elif undeclared:
                tmpl.allergen_check_state = "alert"
                names = ", ".join(undeclared.mapped("name"))
                tmpl.allergen_alert_msg = "ALLERGENI NON DICHIARATI: %s" % names
            else:
                tmpl.allergen_check_state = "ok"
                tmpl.allergen_alert_msg = "Tutti gli allergeni dichiarati correttamente"

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
                parts.append("Puo contenere tracce di: " + ", ".join(traces) + ".")
            rec.allergen_label_text = " ".join(parts) if parts else False


class MrpProductionAllergen(models.Model):
    _inherit = "mrp.production"

    allergen_alert = fields.Boolean(
        compute="_compute_allergen_alert", store=True)
    allergen_alert_msg = fields.Text(
        compute="_compute_allergen_alert", store=True)

    @api.depends("product_id")
    def _compute_allergen_alert(self):
        for rec in self:
            tmpl = rec.product_id.product_tmpl_id
            if tmpl.allergen_check_state == "alert":
                rec.allergen_alert = True
                rec.allergen_alert_msg = tmpl.allergen_alert_msg
            else:
                rec.allergen_alert = False
                rec.allergen_alert_msg = ""

    def button_mark_done(self):
        from odoo.exceptions import UserError
        for rec in self:
            if rec.allergen_alert:
                raise UserError(
                    "BLOCCO PRODUZIONE - Allergeni non dichiarati!\n"
                    "%s\n\n"
                    "Vai su prodotto > tab Allergeni e dichiara tutti gli allergeni." % rec.allergen_alert_msg
                )
        return super().button_mark_done()
