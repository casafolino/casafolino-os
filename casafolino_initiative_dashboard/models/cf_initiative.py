from odoo import api, fields, models


class CfInitiative(models.Model):
    _inherit = 'cf.initiative'

    lavagna_enabled = fields.Boolean(
        string="Lavagna Attiva",
        default=False,
        help="Mostra il bottone 'Apri Lavagna' sulla form dell'iniziativa",
    )
    lavagna_swimlane_category = fields.Char(
        string="Categoria Tag Swimlane",
        help="Categoria di cf.initiative.tag usata per le corsie. Es: 'source' per ICE/CCIC.",
    )
    lavagna_swimlane_tag_ids = fields.Many2many(
        'cf.initiative.tag',
        'cf_initiative_lavagna_swimlane_rel',
        'initiative_id', 'tag_id',
        string="Tag Swimlane",
        help="Quali tag della categoria mostrare come corsie. Vuoto = tutti i tag della categoria",
    )
    lavagna_kpi_ids = fields.Many2many(
        'casafolino.dashboard.kpi',
        'cf_initiative_lavagna_kpi_rel',
        'initiative_id', 'kpi_id',
        string="KPI Lavagna",
    )
    lavagna_panels = fields.Char(
        string="Pannelli Attivi",
        default='kanban,todo,mail,activity',
        help="CSV dei pannelli abilitati: kanban, todo, mail, activity, docs, notes, calendar, shipments",
    )
    lavagna_task_count = fields.Integer(
        string="N. Task Totali",
        compute='_compute_lavagna_counts',
    )
    lavagna_lead_count = fields.Integer(
        string="N. Lead Collegati",
        compute='_compute_lavagna_counts',
    )

    @api.depends('project_ids')
    def _compute_lavagna_counts(self):
        for rec in self:
            rec.lavagna_task_count = self.env['project.task'].search_count([
                ('project_id.initiative_id', '=', rec.id)
            ])
            rec.lavagna_lead_count = self.env['crm.lead'].search_count([
                ('initiative_id', '=', rec.id)
            ])

    def action_open_lavagna(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'casafolino_lavagna',
            'name': f'Lavagna \u2014 {self.name}',
            'params': {'initiative_id': self.id},
        }

    @api.model
    def action_open_dashboard_wizard(self):
        """Launch the dashboard wizard from menu."""
        wizard = self.env['cf.initiative.dashboard.wizard'].create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Apri Nuova Iniziativa (Lavagna)',
            'res_model': 'cf.initiative.dashboard.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
