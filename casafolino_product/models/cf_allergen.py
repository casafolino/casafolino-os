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
    legislation = fields.Text(string="Note legislative / CasaFolino")
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
    allergen_summary_html = fields.Html(
        compute="_compute_allergen_summary_html",
        string="Sommario Allergeni",
        sanitize=False,
    )

    @api.depends('allergen_ids', 'allergen_ids.status', 'allergen_ids.allergen_id')
    def _compute_allergen_texts(self):
        for rec in self:
            present = rec.allergen_ids.filtered(
                lambda a: a.status == 'present').mapped('allergen_id.name')
            traces = rec.allergen_ids.filtered(
                lambda a: a.status == 'traces').mapped('allergen_id.name')
            if present:
                rec.allergen_alert_text = "ALLERGENI PRESENTI: " + ", ".join(
                    n.upper() for n in present)
            elif traces:
                rec.allergen_alert_text = "Tracce possibili: " + ", ".join(
                    n.upper() for n in traces)
            else:
                rec.allergen_alert_text = False
            parts = []
            if present:
                parts.append("Contiene: " + ", ".join(n.upper() for n in present) + ".")
            if traces:
                parts.append("Può contenere tracce di: " + ", ".join(
                    n.upper() for n in traces) + ".")
            rec.allergen_label_text = " ".join(parts) if parts else False

    @api.depends('allergen_ids', 'allergen_ids.status', 'allergen_ids.allergen_id')
    def _compute_allergen_summary_html(self):
        for rec in self:
            present = rec.allergen_ids.filtered(lambda a: a.status == 'present')
            traces = rec.allergen_ids.filtered(lambda a: a.status == 'traces')
            absent = rec.allergen_ids.filtered(lambda a: a.status == 'absent')
            parts = []
            if present or traces:
                parts.append(
                    '<div style="margin-bottom:14px;">'
                    '<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:.7px;color:#9ca3af;margin-bottom:8px;">Allergeni Presenti</div>'
                )
                for a in present:
                    name = (a.allergen_id.name or '').upper()
                    parts.append(
                        f'<span style="display:inline-block;background:#fee2e2;color:#cc0000;'
                        f'font-weight:700;padding:5px 14px;border-radius:20px;margin:3px;'
                        f'font-size:13px;border:1.5px solid #fca5a5;">{name}</span>'
                    )
                if traces:
                    parts.append(
                        '<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
                        'letter-spacing:.7px;color:#9ca3af;margin:10px 0 6px;">Può Contenere Tracce</div>'
                    )
                    for a in traces:
                        name = (a.allergen_id.name or '').upper()
                        parts.append(
                            f'<span style="display:inline-block;background:#fef3c7;color:#d97706;'
                            f'font-weight:600;padding:4px 12px;border-radius:20px;margin:3px;'
                            f'font-size:12px;border:1.5px solid #fcd34d;">{name}</span>'
                        )
                parts.append('</div>')
            if absent:
                parts.append(
                    '<div style="margin-top:8px;">'
                    '<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:.7px;color:#d1d5db;margin-bottom:6px;">Assenti / Non Rilevati</div>'
                )
                for a in absent:
                    name = a.allergen_id.name or ''
                    parts.append(
                        f'<span style="display:inline-block;background:#f3f4f6;color:#9ca3af;'
                        f'font-weight:500;padding:3px 10px;border-radius:20px;margin:2px;'
                        f'font-size:11px;border:1px solid #e5e7eb;">{name}</span>'
                    )
                parts.append('</div>')
            if not parts:
                rec.allergen_summary_html = (
                    '<p style="color:#9ca3af;font-style:italic;margin:0;">'
                    'Nessun allergene configurato. Usa &#8220;Analizza Allergeni da BoM&#8221; '
                    'per il rilevamento automatico.</p>'
                )
            else:
                rec.allergen_summary_html = ''.join(parts)

    def _analyze_allergens_sync(self):
        """Core allergen detection: keyword matching + component declared allergens."""
        keywords = self.env["cf.allergen.keyword"].search([])
        kw_map = {}
        for kw in keywords:
            kw_map.setdefault(kw.allergen_id.id, []).append(kw)

        # Collect declared allergens from component product templates
        comp_present = {}   # allergen_id -> set of product names
        comp_traces = {}    # allergen_id -> set of product names
        for line in self.bom_line_ids:
            line_tmpl = line.product_id.product_tmpl_id
            prod_name = line.product_id.name or ''
            for allergen in line_tmpl.x_allergen_present_ids:
                comp_present.setdefault(allergen.id, set()).add(prod_name)
            for allergen in line_tmpl.x_allergen_traces_ids:
                comp_traces.setdefault(allergen.id, set()).add(prod_name)

        allergens = self.env["cf.allergen"].search([])
        for allergen in allergens:
            found_status = 'absent'
            source_names = []

            # 1) Keyword matching
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

            # 2) Component declared allergens (allergen_ids on product.template)
            if allergen.id in comp_present:
                found_status = 'present'
                for name in comp_present[allergen.id]:
                    if name not in source_names:
                        source_names.append(name)

            # 3) Component "may contain" (allergen_may_contain_ids)
            if allergen.id in comp_traces and found_status == 'absent':
                found_status = 'traces'
                for name in comp_traces[allergen.id]:
                    if name not in source_names:
                        source_names.append(name)

            existing = self.allergen_ids.filtered(
                lambda a: a.allergen_id.id == allergen.id)
            vals = {
                'status': found_status,
                'source_ingredient': ", ".join(source_names) if source_names else False,
                'auto_detected': True,
            }
            if existing:
                if not existing[0].verified:
                    existing[0].write(vals)
            else:
                self.env["cf.recipe.allergen"].create({
                    'bom_id': self.id,
                    'allergen_id': allergen.id,
                    **vals,
                })
        return len(allergens)

    def action_analyze_allergens(self):
        self.ensure_one()
        n_allergens = self._analyze_allergens_sync()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Analisi completata',
                'message': f'Analizzati {n_allergens} allergeni su {len(self.bom_line_ids)} ingredienti.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_recompute_allergens_from_components(self):
        """Force recompute allergens from component product declarations."""
        self.ensure_one()
        # Reset non-verified auto-detected entries to trigger full recompute
        auto_entries = self.allergen_ids.filtered(
            lambda a: a.auto_detected and not a.verified)
        auto_entries.unlink()
        n_allergens = self._analyze_allergens_sync()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ricalcolo completato',
                'message': f'Allergeni ricalcolati da {len(self.bom_line_ids)} componenti ({n_allergens} allergeni analizzati).',
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

    # --- Nuovi campi dichiarazione manuale materia prima ---
    x_allergen_present_ids = fields.Many2many(
        "cf.allergen", "product_x_allergen_present_rel",
        "product_id", "allergen_id",
        string="Allergeni Presenti")
    x_allergen_traces_ids = fields.Many2many(
        "cf.allergen", "product_x_allergen_traces_rel",
        "product_id", "allergen_id",
        string="Allergeni in Tracce")

    # --- Allergeni da BOM (computed, readonly) ---
    x_allergen_from_bom_ids = fields.Many2many(
        "cf.allergen",
        string="Allergeni da BOM",
        compute="_compute_x_allergen_from_bom")
    x_allergen_from_bom_html = fields.Html(
        string="Allergeni da Distinta Base",
        compute="_compute_x_allergen_from_bom",
        sanitize=False)

    x_allergen_label_eu = fields.Text(
        string="Testo etichetta EU",
        compute="_compute_x_allergen_label_eu")

    allergen_check_state = fields.Selection([
        ("unchecked", "Non Verificato"),
        ("ok", "Verificato - Conforme"),
        ("alert", "ATTENZIONE - Allergeni non dichiarati"),
    ], string="Stato Allergeni", compute="_compute_allergen_check", store=True)
    allergen_alert_msg = fields.Text(
        "Dettaglio Alert", compute="_compute_allergen_check", store=True)

    @api.depends('bom_ids.allergen_ids', 'bom_ids.allergen_ids.status',
                 'bom_ids.allergen_ids.allergen_id', 'bom_ids.active')
    def _compute_x_allergen_from_bom(self):
        for rec in self:
            boms = rec.bom_ids.filtered(lambda b: b.active)
            bom_present = self.env["cf.allergen"]
            bom_traces = self.env["cf.allergen"]
            for bom in boms:
                for ra in bom.allergen_ids:
                    if ra.status == 'present':
                        bom_present |= ra.allergen_id
                    elif ra.status == 'traces':
                        bom_traces |= ra.allergen_id
            # Traces che sono già presenti non contano come tracce
            bom_traces = bom_traces - bom_present
            rec.x_allergen_from_bom_ids = bom_present | bom_traces
            # Badge HTML
            parts = []
            for a in bom_present:
                name = (a.name or '').upper()
                parts.append(
                    f'<span style="display:inline-block;background:#fee2e2;color:#cc0000;'
                    f'font-weight:700;padding:4px 12px;border-radius:20px;margin:3px;'
                    f'font-size:12px;border:1.5px solid #fca5a5;">{name}</span>')
            for a in bom_traces:
                name = (a.name or '').upper()
                parts.append(
                    f'<span style="display:inline-block;background:#fef3c7;color:#d97706;'
                    f'font-weight:600;padding:4px 12px;border-radius:20px;margin:3px;'
                    f'font-size:12px;border:1.5px solid #fcd34d;">{name}</span>')
            rec.x_allergen_from_bom_html = ''.join(parts) if parts else False

    @api.depends('x_allergen_present_ids', 'x_allergen_traces_ids',
                 'bom_ids.allergen_ids', 'bom_ids.allergen_ids.status',
                 'bom_ids.allergen_ids.allergen_id', 'bom_ids.active')
    def _compute_x_allergen_label_eu(self):
        for rec in self:
            # Collect BOM present/traces
            boms = rec.bom_ids.filtered(lambda b: b.active)
            bom_present = self.env["cf.allergen"]
            bom_traces = self.env["cf.allergen"]
            for bom in boms:
                for ra in bom.allergen_ids:
                    if ra.status == 'present':
                        bom_present |= ra.allergen_id
                    elif ra.status == 'traces':
                        bom_traces |= ra.allergen_id
            # Union: manual + BOM
            all_present = rec.x_allergen_present_ids | bom_present
            all_traces = (rec.x_allergen_traces_ids | bom_traces) - all_present
            present = all_present.mapped('name')
            traces = all_traces.mapped('name')
            parts = []
            if present:
                parts.append("Contiene: " + ", ".join(
                    n.upper() for n in present) + ".")
            if traces:
                parts.append("Può contenere tracce di: " + ", ".join(
                    n.upper() for n in traces) + ".")
            rec.x_allergen_label_eu = " ".join(parts) if parts else False

    def _get_keyword_matches(self):
        """Return cf.allergen recordset matched by keyword on product name."""
        self.ensure_one()
        keywords = self.env["cf.allergen.keyword"].search([])
        kw_map = {}
        for kw in keywords:
            kw_map.setdefault(kw.allergen_id.id, []).append(kw)
        product_name = (self.name or '').lower()
        matched = self.env["cf.allergen"]
        if not product_name:
            return matched
        for allergen in self.env["cf.allergen"].search([]):
            for kw in kw_map.get(allergen.id, []):
                k = kw.keyword.lower()
                if kw.match_type == "exact" and k == product_name:
                    matched |= allergen
                    break
                elif kw.match_type == "partial" and k in product_name:
                    matched |= allergen
                    break
                elif kw.match_type == "starts" and product_name.startswith(k):
                    matched |= allergen
                    break
        return matched

    def action_analyze_allergens_from_name(self):
        """Keyword matching on product name — adds to x_allergen_present_ids (union)."""
        self.ensure_one()
        found = self._get_keyword_matches()
        if found:
            self.x_allergen_present_ids = [(4, a.id) for a in found]
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Analisi da nome prodotto',
                'message': (
                    f'Trovati {len(found)} allergeni nel nome "{self.name}".'
                    if found else
                    f'Nessun allergene rilevato nel nome "{self.name}".'
                ),
                'type': 'success' if found else 'warning',
                'sticky': False,
            }
        }

    def action_add_suggested_allergens(self):
        """Add keyword-matched allergens missing from x_allergen_present_ids."""
        self.ensure_one()
        suggested = self._get_keyword_matches()
        missing = suggested - self.x_allergen_present_ids
        if missing:
            self.x_allergen_present_ids = [(4, a.id) for a in missing]
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Allergeni aggiunti',
                'message': f'Aggiunti: {", ".join(missing.mapped("name"))}' if missing else 'Nessun allergene da aggiungere.',
                'type': 'success' if missing else 'info',
                'sticky': False,
            }
        }

    def action_refresh_from_bom(self):
        """Re-analyze all active BOMs and refresh computed BOM allergens."""
        self.ensure_one()
        boms = self.bom_ids.filtered(lambda b: b.active)
        for bom in boms:
            bom._analyze_allergens_sync()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Aggiornamento da BOM completato',
                'message': f'Analizzate {len(boms)} distinte base.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.depends("x_allergen_present_ids", "name")
    def _compute_allergen_check(self):
        """Compare keyword matches on product name vs x_allergen_present_ids."""
        for tmpl in self:
            suggested = tmpl._get_keyword_matches()
            if not suggested:
                tmpl.allergen_check_state = "unchecked"
                tmpl.allergen_alert_msg = ""
                continue
            missing = suggested - tmpl.x_allergen_present_ids
            if missing:
                tmpl.allergen_check_state = "alert"
                names = ", ".join(missing.mapped("name"))
                tmpl.allergen_alert_msg = (
                    "Allergeni rilevati nel nome prodotto ma non dichiarati: %s"
                    % names
                )
            else:
                tmpl.allergen_check_state = "ok"
                tmpl.allergen_alert_msg = ""


class MrpBomLineAutoAnalyze(models.Model):
    _inherit = "mrp.bom.line"

    x_allergeni_display = fields.Html(
        compute="_compute_x_allergeni_display",
        string="Allergeni",
        sanitize=False,
    )

    @api.depends('product_id', 'bom_id.allergen_ids',
                 'bom_id.allergen_ids.status', 'bom_id.allergen_ids.source_ingredient')
    def _compute_x_allergeni_display(self):
        for line in self:
            tmpl = line.product_id.product_tmpl_id
            if not tmpl:
                line.x_allergeni_display = ''
                continue
            # Read from product declared allergens
            present_names = list(tmpl.x_allergen_present_ids.mapped('name'))
            traces_names = list(tmpl.x_allergen_traces_ids.mapped('name'))
            # Remove duplicates (traces already in present)
            traces_names = [n for n in traces_names if n not in present_names]
            parts = []
            if present_names:
                names = ', '.join(n.upper() for n in present_names)
                parts.append(
                    f'<span style="font-weight:700;color:#cc0000;">{names}</span>')
            if traces_names:
                names = ', '.join(n.upper() for n in traces_names)
                parts.append(
                    f'<span style="font-weight:600;color:#d97706;">(tracce: {names})</span>')
            line.x_allergeni_display = ' '.join(parts) if parts else ''

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        boms = lines.mapped('bom_id')
        for bom in boms:
            bom._analyze_allergens_sync()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'product_id' in vals or 'product_qty' in vals:
            boms = self.mapped('bom_id')
            for bom in boms:
                bom._analyze_allergens_sync()
        return res


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
