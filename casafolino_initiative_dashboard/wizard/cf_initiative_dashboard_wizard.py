import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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

    # Recovery mode: configure existing initiative
    recovery_initiative_id = fields.Many2one(
        'cf.initiative',
        string="Iniziativa da Configurare (recovery)",
    )

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
    panel_activity = fields.Boolean(string="Timeline Attività", default=True)
    panel_docs = fields.Boolean(string="Documenti", default=False)
    panel_notes = fields.Boolean(string="Note Interne", default=False)
    panel_calendar = fields.Boolean(string="Scadenze Calendario", default=False)
    panel_shipments = fields.Boolean(string="Spedizioni Campioni", default=False)

    # ============= DEFAULT GET (recovery mode) =============

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if ctx.get('recovery_initiative_id'):
            init = self.env['cf.initiative'].browse(ctx['recovery_initiative_id'])
            if init.exists():
                res['recovery_initiative_id'] = init.id
                res['name'] = init.name
                res['family_id'] = init.family_id.id if init.family_id else False
                res['state'] = 'scenario'
        return res

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
        # Recovery mode: skip details step (name already set)
        if self.recovery_initiative_id and self.state == 'scenario':
            self.state = 'panels'
            return self._reopen()
        if idx < len(flow) - 1:
            self.state = flow[idx + 1]
        return self._reopen()

    def action_back(self):
        flow = ['family', 'scenario', 'details', 'panels', 'done']
        idx = flow.index(self.state)
        # Recovery mode: from panels go back to scenario (skip details)
        if self.recovery_initiative_id and self.state == 'panels':
            self.state = 'scenario'
            return self._reopen()
        if idx > 0:
            self.state = flow[idx - 1]
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apri Nuova Iniziativa (Lavagna)',
            'res_model': 'cf.initiative.dashboard.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def _get_default_variant(self):
        Variant = self.env['cf.initiative.variant']
        family_code = self.family_id.code or ''
        variant = Variant.search([
            ('code', '=', f'{family_code}_STANDARD'),
        ], limit=1)
        if variant:
            return variant
        variant = Variant.search([
            ('family_id', '=', self.family_id.id),
        ], limit=1, order='sequence, id')
        if variant:
            return variant
        return Variant.search([], limit=1)

    def _read_scenario_defaults(self):
        """Read defaults from scenario (source of truth for M2M fields)."""
        scenario = self.scenario_id
        swimlane_category = self.swimlane_category or scenario.swimlane_category or ''
        swimlane_tags = self.swimlane_tag_ids or scenario.suggested_swimlane_tag_ids
        kpis = self.kpi_ids or scenario.default_kpi_ids
        stages_csv = self.stage_names_csv or scenario.suggested_stage_names

        panels = []
        for p in ['kanban', 'todo', 'mail', 'activity', 'docs', 'notes', 'calendar', 'shipments']:
            if getattr(self, f'panel_{p}'):
                panels.append(p)
        panel_csv = ','.join(panels) if panels else (scenario.default_panels or 'kanban,todo,mail,activity')

        return swimlane_category, swimlane_tags, kpis, stages_csv, panel_csv

    # ============= CONFIRM & CREATE =============

    def action_confirm(self):
        self.ensure_one()
        if not self.scenario_id:
            raise UserError("Devi selezionare uno scenario per la Lavagna.")

        if self.recovery_initiative_id:
            return self._action_confirm_recovery()

        if not self.name:
            raise UserError("Il nome dell'iniziativa è obbligatorio.")

        swimlane_category, swimlane_tags, kpis, stages_csv, panel_csv = self._read_scenario_defaults()

        variant = self._get_default_variant()
        if not variant:
            raise UserError(
                "Nessuna variante disponibile. Configurare almeno una "
                "cf.initiative.variant prima di creare iniziative."
            )

        all_tags = swimlane_tags | self.market_tag_ids

        initiative = None
        project = None

        try:
            # 1. Create cf.initiative
            initiative_vals = {
                'name': self.name,
                'family_id': self.family_id.id,
                'variant_id': variant.id,
                'user_id': self.env.user.id,
                'tag_ids': [(6, 0, all_tags.ids)],
                'lavagna_enabled': True,
                'lavagna_swimlane_category': swimlane_category,
                'lavagna_swimlane_tag_ids': [(6, 0, swimlane_tags.ids)],
                'lavagna_kpi_ids': [(6, 0, kpis.ids)],
                'lavagna_panels': panel_csv,
            }
            for field_name, value in [
                ('partner_id', self.partner_id.id if self.partner_id else False),
                ('country_id', self.country_id.id if self.country_id else False),
                ('date_start', self.date_start),
                ('date_end', self.date_end),
            ]:
                if value and field_name in self.env['cf.initiative']._fields:
                    initiative_vals[field_name] = value

            initiative = self.env['cf.initiative'].create(initiative_vals)
            _logger.info("[Wizard] Created initiative id=%s name=%s", initiative.id, initiative.name)

            # 2. Create project
            project = self.env['project.project'].create({
                'name': self.name,
                'initiative_id': initiative.id,
                'privacy_visibility': 'followers',
                'user_id': self.env.user.id,
            })
            _logger.info("[Wizard] Created project id=%s for initiative %s", project.id, initiative.id)

            # Add followers
            if self.user_ids:
                partner_ids = self.user_ids.mapped('partner_id').ids
                project.message_subscribe(partner_ids=partner_ids)

            # 3. Create stages
            self._create_stages(project, stages_csv)

            return initiative.action_open_lavagna()

        except Exception as e:
            _logger.error("[Wizard] FATAL during creation: %s", e, exc_info=True)
            raise UserError(f"Errore durante la creazione dell'iniziativa: {e}")

    def _action_confirm_recovery(self):
        """Configure existing initiative with scenario/stages/project."""
        init = self.recovery_initiative_id
        swimlane_category, swimlane_tags, kpis, stages_csv, panel_csv = self._read_scenario_defaults()

        # Update lavagna fields on existing initiative
        init.write({
            'lavagna_enabled': True,
            'lavagna_swimlane_category': swimlane_category,
            'lavagna_swimlane_tag_ids': [(6, 0, swimlane_tags.ids)],
            'lavagna_kpi_ids': [(6, 0, kpis.ids)],
            'lavagna_panels': panel_csv,
            'tag_ids': [(4, t.id) for t in (swimlane_tags | self.market_tag_ids)],
        })
        _logger.info("[Wizard Recovery] Updated initiative id=%s", init.id)

        # Create project if missing
        project = self.env['project.project'].search(
            [('initiative_id', '=', init.id)], limit=1)
        if not project:
            project = self.env['project.project'].create({
                'name': init.name,
                'initiative_id': init.id,
                'privacy_visibility': 'followers',
                'user_id': self.env.user.id,
            })
            _logger.info("[Wizard Recovery] Created project id=%s", project.id)

        # Create stages if missing
        if not project.type_ids:
            self._create_stages(project, stages_csv)

        return init.action_open_lavagna()

    def _create_stages(self, project, stages_csv):
        """Create project stages from CSV string."""
        if not stages_csv:
            return
        stage_names = [s.strip() for s in stages_csv.split(',') if s.strip()]
        stage_ids = []
        for i, sname in enumerate(stage_names):
            stage = self.env['project.task.type'].create({
                'name': sname,
                'sequence': (i + 1) * 10,
                'fold': sname.lower() in (
                    'lead crm', 'archiviati', 'chiuso', 'archived',
                    'archive', 'archiviato', 'operativo',
                ),
            })
            stage_ids.append(stage.id)
        project.write({'type_ids': [(6, 0, stage_ids)]})
        _logger.info("[Wizard] Created %d stages for project %s", len(stage_ids), project.id)
