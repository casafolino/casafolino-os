from odoo import fields, models


class CasafolinoLavagnaTemplate(models.Model):
    _name = 'casafolino.lavagna.template'
    _description = 'Template Lavagna per Famiglia Iniziativa'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    family_id = fields.Many2one('cf.initiative.family', required=True, ondelete='cascade')
    description = fields.Text()

    swimlane_category = fields.Char(
        string="Categoria Swimlane",
        help="Es: 'source' per OC, 'fair' per EV",
    )
    suggested_swimlane_tag_ids = fields.Many2many(
        'cf.initiative.tag',
        'lavagna_template_swimlane_rel',
        string="Tag Swimlane Suggeriti",
    )
    suggested_stage_names = fields.Char(
        string="Stage Suggeriti (CSV)",
        help="Stage del progetto separati da virgola. "
             "Es: 'Scouting,Campionatura,Appuntamenti,Incontri,Lead CRM'",
    )
    default_kpi_ids = fields.Many2many(
        'casafolino.dashboard.kpi',
        'lavagna_template_kpi_rel',
        string="KPI Default",
    )
    default_panels = fields.Char(
        string="Pannelli Default",
        default='kanban,todo,mail,activity',
    )
    active = fields.Boolean(default=True)
