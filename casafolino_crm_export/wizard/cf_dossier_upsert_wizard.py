from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CfDossierUpsertWizard(models.TransientModel):
    _name = "cf.dossier.upsert.wizard"
    _description = "Crea o aggiorna Dossier 360"

    project_id = fields.Many2one(
        "project.project",
        string="Dossier da aggiornare",
        domain=[("cf_status_dossier", "!=", False)],
    )
    template_id = fields.Many2one("cf.dossier.template", string="Template")
    name = fields.Char(string="Nome dossier", required=True)

    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente esistente",
        domain=[("is_company", "=", True)],
    )
    create_partner = fields.Boolean(string="Crea nuovo cliente")
    new_partner_name = fields.Char(string="Nome nuovo cliente")
    country_id = fields.Many2one("res.country", string="Paese")
    buyer_name = fields.Char(string="Buyer / referente")
    buyer_email = fields.Char(string="Email referente")
    buyer_phone = fields.Char(string="Telefono referente")

    status = fields.Selection(
        [
            ("exploration", "Esplorativo"),
            ("active", "Attivo"),
            ("on_hold", "In pausa"),
            ("won", "Vinto / ricorrente"),
            ("closed", "Chiuso"),
        ],
        string="Stato dossier",
        default="active",
        required=True,
    )
    priority = fields.Selection(
        [
            ("low", "Bassa"),
            ("medium", "Media"),
            ("high", "Alta"),
        ],
        string="Priorita",
        default="medium",
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsabile",
        default=lambda self: self.env.user,
        required=True,
    )
    dossier_lang = fields.Selection(
        [
            ("it", "Italiano"),
            ("en", "English"),
            ("es", "Espanol"),
            ("fr", "Francais"),
            ("de", "Deutsch"),
            ("pt", "Portugues"),
            ("ar", "Arabo"),
            ("zh", "Cinese"),
        ],
        string="Lingua",
        default="en",
    )
    volume_target = fields.Float(string="Volume target")
    volume_unit = fields.Selection(
        [
            ("unit", "Unita"),
            ("cartoni", "Cartoni"),
            ("pallet", "Pallet"),
            ("kg", "Kg"),
            ("tonnellate", "Tonnellate"),
        ],
        string="Unita volume",
        default="unit",
    )
    margin_target = fields.Float(string="Margine target %")
    value_estimate = fields.Float(string="Valore stimato")
    incoterms = fields.Selection(
        [
            ("exw", "EXW"),
            ("fca", "FCA"),
            ("fob", "FOB"),
            ("cif", "CIF"),
            ("ddp", "DDP"),
        ],
        string="Incoterms",
    )
    payment_term = fields.Selection(
        [
            ("advance", "Anticipo 100%"),
            ("30_70", "30% advance / 70% balance"),
            ("50_50", "50/50"),
            ("lc", "LC at sight"),
            ("30_days", "30 giorni FM"),
            ("60_days", "60 giorni FM"),
            ("open_account", "Open account"),
        ],
        string="Pagamento",
    )
    certification_ids = fields.Many2many(
        "cf.export.certification",
        string="Certificazioni",
    )
    next_action = fields.Char(string="Prossima azione")
    next_action_date = fields.Date(string="Data prossima azione")
    internal_notes = fields.Text(string="Note interne")

    create_or_link_lead = fields.Boolean(
        string="Metti in pipeline",
        default=True,
        help="Crea o collega una opportunita CRM al dossier.",
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead esistente",
        domain=[("type", "in", ["lead", "opportunity"])],
    )
    lead_name = fields.Char(string="Titolo lead")
    stage_id = fields.Many2one("crm.stage", string="Fase pipeline")
    expected_revenue = fields.Monetary(string="Valore lead")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        project_id = (
            self.env.context.get("default_project_id")
            or self.env.context.get("active_id")
        )
        if self.env.context.get("active_model") == "project.project" and project_id:
            project = self.env["project.project"].browse(project_id).exists()
            if project:
                vals.update(self._defaults_from_project(project))
        if not vals.get("stage_id"):
            stage = self._default_pipeline_stage()
            if stage:
                vals["stage_id"] = stage.id
        if not vals.get("name"):
            vals["name"] = _("Nuovo dossier")
        return vals

    @api.model
    def _defaults_from_project(self, project):
        lead = project.cf_lead_ids[:1]
        return {
            "project_id": project.id,
            "template_id": project.cf_template_origin_id.id or False,
            "name": project.name,
            "partner_id": project.partner_id.id or False,
            "buyer_name": project.cf_buyer_id.name or False,
            "buyer_email": project.cf_buyer_id.email or False,
            "buyer_phone": project.cf_buyer_id.phone or project.cf_buyer_id.mobile or False,
            "status": project.cf_status_dossier or "active",
            "priority": project.cf_dossier_priority or "medium",
            "user_id": project.user_id.id or self.env.user.id,
            "dossier_lang": project.cf_dossier_lang or "en",
            "volume_target": project.cf_volume_target or 0,
            "volume_unit": project.cf_volume_unit or "unit",
            "margin_target": project.cf_margin_target or 0,
            "value_estimate": project.cf_dossier_value_estimate or 0,
            "incoterms": project.cf_incoterms or False,
            "payment_term": project.cf_payment_term or False,
            "certification_ids": [(6, 0, project.cf_certification_ids.ids)],
            "next_action": project.cf_next_action or False,
            "next_action_date": project.cf_next_action_date or False,
            "internal_notes": project.cf_internal_notes or False,
            "lead_id": lead.id or False,
            "lead_name": lead.name or project.name,
            "stage_id": lead.stage_id.id or False,
            "expected_revenue": lead.expected_revenue or project.cf_dossier_value_estimate or 0,
        }

    @api.onchange("template_id")
    def _onchange_template_id(self):
        tmpl = self.template_id
        if not tmpl:
            return
        self.dossier_lang = tmpl.default_lang or self.dossier_lang
        self.volume_unit = tmpl.default_volume_unit or self.volume_unit
        self.incoterms = tmpl.default_incoterms or self.incoterms
        self.payment_term = tmpl.default_payment_term or self.payment_term
        self.certification_ids = tmpl.default_certification_ids

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.create_partner = False
            self.country_id = self.partner_id.country_id
            if not self.name or self.name == _("Nuovo dossier"):
                self.name = self.partner_id.name
            if not self.lead_name:
                self.lead_name = self.name

    @api.onchange("new_partner_name")
    def _onchange_new_partner_name(self):
        if self.create_partner and self.new_partner_name:
            if not self.name or self.name == _("Nuovo dossier"):
                self.name = self.new_partner_name
            if not self.lead_name:
                self.lead_name = self.name

    @api.model
    def _default_pipeline_stage(self):
        return self.env.ref(
            "casafolino_crm_export.stage_negoziazione",
            raise_if_not_found=False,
        ) or self.env["crm.stage"].search([], order="sequence, id", limit=1)

    def _resolve_partner(self):
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        if not self.create_partner and not self.new_partner_name:
            return self.env["res.partner"]
        if not self.new_partner_name:
            raise UserError(_("Inserisci il nome del nuovo cliente."))
        partner = self.env["res.partner"].create(
            {
                "name": self.new_partner_name,
                "company_type": "company",
                "is_company": True,
                "country_id": self.country_id.id or False,
            }
        )
        return partner

    def _resolve_buyer(self, partner):
        self.ensure_one()
        if not self.buyer_name:
            return self.env["res.partner"]
        domain = [("name", "ilike", self.buyer_name)]
        if partner:
            domain.append(("parent_id", "=", partner.id))
        buyer = self.env["res.partner"].search(domain, limit=1)
        if buyer:
            buyer.write(
                {
                    "email": self.buyer_email or buyer.email,
                    "phone": self.buyer_phone or buyer.phone,
                }
            )
            return buyer
        return self.env["res.partner"].create(
            {
                "name": self.buyer_name,
                "parent_id": partner.id if partner else False,
                "company_type": "person",
                "email": self.buyer_email or False,
                "phone": self.buyer_phone or False,
                "function": "Buyer",
            }
        )

    def _project_vals(self, partner, buyer):
        self.ensure_one()
        return {
            "name": self.name,
            "partner_id": partner.id or False,
            "user_id": self.user_id.id,
            "cf_status_dossier": self.status or "active",
            "cf_dossier_priority": self.priority,
            "cf_template_origin_id": self.template_id.id or False,
            "cf_buyer_id": buyer.id or False,
            "cf_dossier_lang": self.dossier_lang or "en",
            "cf_volume_target": self.volume_target or 0,
            "cf_volume_unit": self.volume_unit or "unit",
            "cf_margin_target": self.margin_target or 0,
            "cf_dossier_value_estimate": self.value_estimate or 0,
            "cf_incoterms": self.incoterms or False,
            "cf_payment_term": self.payment_term or False,
            "cf_certification_ids": [(6, 0, self.certification_ids.ids)],
            "cf_next_action": self.next_action or False,
            "cf_next_action_date": self.next_action_date or False,
            "cf_internal_notes": self.internal_notes or False,
        }

    def _sync_primary_contact(self, project, partner, buyer):
        contact_partner = buyer or partner
        if not contact_partner:
            return
        existing = project.cf_contact_ids.filtered(
            lambda c: c.partner_id == contact_partner or c.is_primary
        )[:1]
        vals = {
            "project_id": project.id,
            "partner_id": contact_partner.id,
            "name": contact_partner.name,
            "email": contact_partner.email or self.buyer_email or "",
            "phone": contact_partner.phone or contact_partner.mobile or self.buyer_phone or "",
            "role": "commercial",
            "is_primary": True,
        }
        if existing:
            existing.write(vals)
        else:
            self.env["cf.project.contact"].create(vals)

    def _create_template_tasks(self, project):
        self.ensure_one()
        if not self.template_id:
            return
        Task = self.env["project.task"]
        for checkpoint in self.template_id.checkpoint_ids.sorted("sequence"):
            exists = Task.search(
                [
                    ("project_id", "=", project.id),
                    ("name", "=", checkpoint.name),
                ],
                limit=1,
            )
            if exists:
                continue
            Task.create(
                {
                    "name": checkpoint.name,
                    "project_id": project.id,
                    "description": checkpoint.description or "",
                    "sequence": checkpoint.sequence,
                }
            )

    def _sync_lead(self, project, partner):
        self.ensure_one()
        if not self.create_or_link_lead:
            return self.env["crm.lead"]
        lead = self.lead_id or project.cf_lead_ids[:1]
        vals = {
            "name": self.lead_name or project.name,
            "type": "opportunity",
            "partner_id": partner.id or False,
            "user_id": self.user_id.id,
            "cf_project_id": project.id,
            "stage_id": self.stage_id.id or self._default_pipeline_stage().id,
            "expected_revenue": self.expected_revenue or self.value_estimate or 0,
        }
        if lead:
            lead.write(vals)
        else:
            lead = self.env["crm.lead"].create(vals)
        return lead

    def action_apply(self):
        self.ensure_one()
        partner = self._resolve_partner()
        buyer = self._resolve_buyer(partner)
        vals = self._project_vals(partner, buyer)

        if self.project_id:
            project = self.project_id
            project.write(vals)
            message = _("Dossier aggiornato dal wizard Dossier 360.")
        else:
            project = self.env["project.project"].create(vals)
            message = _("Dossier creato dal wizard Dossier 360.")

        self._sync_primary_contact(project, partner, buyer)
        self._create_template_tasks(project)
        lead = self._sync_lead(project, partner)

        if lead:
            message += _(" Lead pipeline collegato: %s.") % lead.display_name
        project.message_post(body=message)

        return project.action_open_project_dashboard_360()
