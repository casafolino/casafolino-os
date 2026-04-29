from odoo import api, fields, models
from odoo.exceptions import UserError


class CfInitiativeDashboardWizard(models.TransientModel):
    _name = 'cf.initiative.dashboard.wizard'
    _description = 'Wizard Apri Nuova Iniziativa (Lavagna)'

    state = fields.Selection([
        ('family', 'Tipo Iniziativa'),
        ('scenario', 'Scenario Lavagna'),
        ('details', 'Dettagli Iniziativa'),
        ('panels', 'Moduli Attivi'),
        ('done', 'Conferma'),
    ], default='family', required=True)

    # STEP 1: Famiglia (card visuali)
    family_id = fields.Many2one(
        'cf.initiative.family',
        string="Tipo Iniziativa",
        required=True,
        domain="[('active', '=', True)]",
    )

    # STEP 2: Scenario (card visuali)
    scenario_id = fields.Many2one(
        'casafolino.lavagna.template',
        string="Scenario",
        domain="[('family_id', '=', family_id), ('active', '=', True)]",
    )
    scenario_description = fields.Text(
        related='scenario_id.description',
        readonly=True,
    )
    scenario_stage_preview = fields.Char(
        related='scenario_id.suggested_stage_names',
        readonly=True,
        string="Stage Pipeline",
    )

    # Auto-popolato da scenario, modificabile
    swimlane_category = fields.Char(string="Categoria Swimlane")
    swimlane_tag_ids = fields.Many2many(
        'cf.initiative.tag',
        'wizard_dashboard_swimlane_rel',
        string="Tag Swimlane",
    )
    stage_names_csv = fields.Char(string="Stage Pipeline (CSV)")
    kpi_ids = fields.Many2many(
        'casafolino.dashboard.kpi',
        'wizard_dashboard_kpi_rel',
        string="KPI",
    )

    # STEP 3: Dettagli iniziativa
    name = fields.Char(string="Nome Iniziativa")
    partner_id = fields.Many2one('res.partner', string="Partner Principale")
    country_id = fields.Many2one('res.country', string="Paese")
    date_start = fields.Date(string="Data Inizio", default=fields.Date.context_today)
    date_end = fields.Date(string="Data Fine Prevista")
    user_ids = fields.Many2many(
        'res.users',
        'wizard_dashboard_users_rel',
        string="Membri Team",
        default=lambda self: [(6, 0, [self.env.user.id])],
    )
    market_tag_ids = fields.Many2many(
        'cf.initiative.tag',
        'wizard_dashboard_market_tags_rel',
        string="Tag Mercato/Strategici",
        domain="[('category', 'in', ['market', 'strategic'])]",
    )

    # STEP 4: Pannelli
    panel_kanban = fields.Boolean(string="Lavagna Kanban", default=True)
    panel_todo = fields.Boolean(string="To-Do List", default=True)
    panel_mail = fields.Boolean(string="Comunicazioni Mail", default=True)
    panel_activity = fields.Boolean(string="Timeline Attivita", default=True)
    panel_docs = fields.Boolean(string="Documenti", default=False)
    panel_notes = fields.Boolean(string="Note Interne", default=False)
    panel_calendar = fields.Boolean(string="Scadenze Calendario", default=False)
    panel_shipments = fields.Boolean(string="Spedizioni Campioni", default=False)

    # ============= ONCHANGE =============

    @api.onchange('family_id')
    def _onchange_family_id(self):
        self.scenario_id = False
        self._reset_scenario_fields()

    @api.onchange('scenario_id')
    def _onchange_scenario_id(self):
        if self.scenario_id:
            t = self.scenario_id
            self.swimlane_category = t.swimlane_category or ''
            self.swimlane_tag_ids = [(6, 0, t.suggested_swimlane_tag_ids.ids)]
            self.stage_names_csv = t.suggested_stage_names
            self.kpi_ids = [(6, 0, t.default_kpi_ids.ids)]
            panels = (t.default_panels or '').split(',')
            self.panel_kanban = 'kanban' in panels
            self.panel_todo = 'todo' in panels
            self.panel_mail = 'mail' in panels
            self.panel_activity = 'activity' in panels
            self.panel_docs = 'docs' in panels
            self.panel_notes = 'notes' in panels
            self.panel_calendar = 'calendar' in panels
            self.panel_shipments = 'shipments' in panels
        else:
            self._reset_scenario_fields()

    def _reset_scenario_fields(self):
        self.swimlane_category = ''
        self.swimlane_tag_ids = [(5, 0, 0)]
        self.stage_names_csv = False
        self.kpi_ids = [(5, 0, 0)]

    # ============= NAVIGATION =============

    def action_next(self):
        flow = ['family', 'scenario', 'details', 'panels', 'done']
        idx = flow.index(self.state)
        if self.state == 'family' and not self.family_id:
            raise UserError("Seleziona un tipo di iniziativa per continuare.")
        if self.state == 'scenario' and not self.scenario_id:
            raise UserError("Seleziona uno scenario per continuare.")
        if self.state == 'details' and not self.name:
            raise UserError("Inserisci il nome dell'iniziativa.")
        if idx < len(flow) - 1:
            self.state = flow[idx + 1]
        return self._reopen()

    def action_back(self):
        flow = ['family', 'scenario', 'details', 'panels', 'done']
        idx = flow.index(self.state)
        if idx > 0:
            self.state = flow[idx - 1]
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cf.initiative.dashboard.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def _get_default_variant(self):
        """
        Default variant for cf.initiative (user never sees this):
        1. Variant with code matching family standard (OC_STANDARD, CE_STANDARD, etc.)
        2. Fallback: first variant for the family
        3. Fallback: first variant overall
        """
        Variant = self.env['cf.initiative.variant']
        family_code = self.family_id.code or ''
        # Try family-specific standard
        variant = Variant.search([
            ('code', '=', f'{family_code}_STANDARD'),
        ], limit=1)
        if variant:
            return variant
        # Fallback: first for family
        variant = Variant.search([
            ('family_id', '=', self.family_id.id),
        ], limit=1, order='sequence, id')
        if variant:
            return variant
        # Fallback: any variant
        return Variant.search([], limit=1)

    # ============= CONFIRM & CREATE =============

    def action_confirm(self):
        self.ensure_one()
        if not self.name:
            raise UserError("Il nome dell'iniziativa e obbligatorio.")

        # Build panel CSV
        panels = []
        for p in ['kanban', 'todo', 'mail', 'activity', 'docs', 'notes', 'calendar', 'shipments']:
            if getattr(self, f'panel_{p}'):
                panels.append(p)
        panel_csv = ','.join(panels)

        # Default variant in background (user never sees it)
        variant = self._get_default_variant()
        if not variant:
            raise UserError(
                "Nessuna variante disponibile. Configurare almeno una "
                "cf.initiative.variant prima di creare iniziative."
            )

        # Merge tags
        all_tags = self.swimlane_tag_ids | self.market_tag_ids

        # 1. Create cf.initiative
        initiative_vals = {
            'name': self.name,
            'family_id': self.family_id.id,
            'variant_id': variant.id,
            'user_id': self.env.user.id,
            'tag_ids': [(6, 0, all_tags.ids)],
            'lavagna_enabled': True,
            'lavagna_swimlane_category': self.swimlane_category or '',
            'lavagna_swimlane_tag_ids': [(6, 0, self.swimlane_tag_ids.ids)],
            'lavagna_kpi_ids': [(6, 0, self.kpi_ids.ids)],
            'lavagna_panels': panel_csv,
        }
        if self.partner_id:
            initiative_vals['partner_id'] = self.partner_id.id
        if self.date_start:
            initiative_vals['date_start'] = self.date_start
        if self.date_end:
            initiative_vals['date_end'] = self.date_end

        initiative = self.env['cf.initiative'].create(initiative_vals)

        # 2. Create project.project linked to initiative
        project_vals = {
            'name': self.name,
            'initiative_id': initiative.id,
            'privacy_visibility': 'followers',
            'user_id': self.env.user.id,
        }
        project = self.env['project.project'].create(project_vals)

        # Add team members as followers
        if self.user_ids:
            partner_ids = self.user_ids.mapped('partner_id').ids
            project.message_subscribe(partner_ids=partner_ids)

        # 3. Create project stages
        if self.stage_names_csv:
            stage_names = [s.strip() for s in self.stage_names_csv.split(',') if s.strip()]
            stage_ids = []
            for i, sname in enumerate(stage_names):
                stage = self.env['project.task.type'].create({
                    'name': sname,
                    'sequence': (i + 1) * 10,
                    'fold': sname.lower() in (
                        'lead crm', 'archiviati', 'chiuso', 'archived', 'archive', 'archiviato',
                    ),
                })
                stage_ids.append(stage.id)
            project.write({'type_ids': [(6, 0, stage_ids)]})

        # 4. Open Lavagna
        return initiative.action_open_lavagna()
