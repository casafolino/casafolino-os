from odoo import api, fields, models
from odoo.exceptions import UserError


class CfInitiativeDashboardWizard(models.TransientModel):
    _name = 'cf.initiative.dashboard.wizard'
    _description = 'Wizard Apertura Nuova Iniziativa con Lavagna'

    # Navigation
    state = fields.Selection([
        ('family', 'Tipo Iniziativa'),
        ('config', 'Configurazione Lavagna'),
        ('details', 'Dettagli Progetto'),
        ('panels', 'Moduli Attivi'),
        ('done', 'Conferma'),
    ], default='family', required=True)

    # STEP 1: Famiglia
    family_id = fields.Many2one(
        'cf.initiative.family', string="Tipo Iniziativa",
        domain="[('active', '=', True)]",
    )
    variant_id = fields.Many2one(
        'cf.initiative.variant', string="Variante",
        domain="[('family_id', '=', family_id)]",
    )
    template_id = fields.Many2one(
        'casafolino.lavagna.template', string="Template Lavagna",
        domain="[('family_id', '=', family_id)]",
    )

    # STEP 2: Config lavagna
    swimlane_category = fields.Char(string="Categoria Swimlane")
    swimlane_tag_ids = fields.Many2many(
        'cf.initiative.tag',
        'dashboard_wizard_swimlane_rel',
        string="Tag Swimlane",
    )
    stage_names_csv = fields.Char(
        string="Stage (CSV)",
        help="Stage da creare nel progetto, separati da virgola",
    )
    kpi_ids = fields.Many2many(
        'casafolino.dashboard.kpi',
        'dashboard_wizard_kpi_rel',
        string="KPI",
    )

    # STEP 3: Dettagli
    name = fields.Char(string="Nome Iniziativa")
    partner_id = fields.Many2one('res.partner', string="Partner Principale")
    country_id = fields.Many2one('res.country', string="Paese")
    date_start = fields.Date(string="Data Inizio", default=fields.Date.context_today)
    date_end = fields.Date(string="Data Fine Prevista")
    user_ids = fields.Many2many(
        'res.users',
        'dashboard_wizard_users_rel',
        string="Membri Team",
        default=lambda self: [(6, 0, [self.env.user.id])],
    )
    market_tag_ids = fields.Many2many(
        'cf.initiative.tag',
        'dashboard_wizard_market_tags_rel',
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

    @api.onchange('family_id')
    def _onchange_family_id(self):
        if self.family_id:
            template = self.env['casafolino.lavagna.template'].search(
                [('family_id', '=', self.family_id.id), ('active', '=', True)],
                limit=1,
            )
            self.template_id = template.id if template else False
            # Reset variant when family changes
            self.variant_id = False
        else:
            self.template_id = False

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            t = self.template_id
            self.swimlane_category = t.swimlane_category
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

    def action_next(self):
        self.ensure_one()
        flow = ['family', 'config', 'details', 'panels', 'done']
        idx = flow.index(self.state)
        # Validation before advancing
        if self.state == 'family' and not self.family_id:
            raise UserError("Seleziona un tipo di iniziativa.")
        if self.state == 'family' and not self.variant_id:
            raise UserError("Seleziona una variante.")
        if idx < len(flow) - 1:
            self.state = flow[idx + 1]
        return self._reopen()

    def action_back(self):
        self.ensure_one()
        flow = ['family', 'config', 'details', 'panels', 'done']
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
        }

    def action_confirm(self):
        """Crea cf.initiative + project.project + stage + tag + apre la Lavagna."""
        self.ensure_one()
        if not self.name:
            raise UserError("Il nome dell'iniziativa e obbligatorio.")

        # Build panel CSV
        panels = []
        for p in ['kanban', 'todo', 'mail', 'activity', 'docs', 'notes', 'calendar', 'shipments']:
            if getattr(self, f'panel_{p}'):
                panels.append(p)
        panel_csv = ','.join(panels)

        # Merge tags
        all_tags = self.swimlane_tag_ids | self.market_tag_ids

        # 1. Create cf.initiative
        initiative_vals = {
            'name': self.name,
            'family_id': self.family_id.id,
            'variant_id': self.variant_id.id,
            'user_id': self.env.user.id,
            'tag_ids': [(6, 0, all_tags.ids)],
            'lavagna_enabled': True,
            'lavagna_swimlane_category': self.swimlane_category,
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
                    'fold': sname.lower() in ('lead crm', 'archiviati', 'chiuso', 'archived'),
                })
                stage_ids.append(stage.id)
            project.write({'type_ids': [(6, 0, stage_ids)]})

        # 4. Open Lavagna placeholder
        return initiative.action_open_lavagna()
