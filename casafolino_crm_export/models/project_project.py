from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    cf_managed_by_id = fields.Many2one(
        comodel_name='res.partner',
        domain="[('cf_partner_role', '=', 'agent')]",
        string='Agente',
        index=True,
        tracking=True,
    )

    cf_status_dossier = fields.Selection(
        selection=[
            ('exploration', 'Esplorativo'),
            ('active', 'Attivo'),
            ('on_hold', 'In pausa'),
            ('won', 'Vinto / ricorrente'),
            ('closed', 'Chiuso'),
        ],
        string='Status dossier',
        default='exploration',
        index=True,
        tracking=True,
    )

    cf_dossier_priority = fields.Selection(
        selection=[
            ('low', 'Bassa'),
            ('medium', 'Media'),
            ('high', 'Alta'),
        ],
        string='Priorità dossier',
        default='medium',
    )

    cf_dossier_value_estimate = fields.Float(
        string='Valore stimato dossier',
    )

    cf_open_issues_count = fields.Integer(
        compute='_compute_cf_dossier_stats',
        string='Reclami aperti',
    )

    cf_last_activity_date = fields.Datetime(
        compute='_compute_cf_dossier_stats',
        string='Ultima attività',
    )

    cf_lead_count = fields.Integer(
        compute='_compute_cf_dossier_stats',
        string='Lead/quotazioni',
    )

    @api.depends('partner_id')
    def _compute_cf_dossier_stats(self):
        if not self.ids:
            for p in self:
                p.cf_open_issues_count = 0
                p.cf_last_activity_date = False
                p.cf_lead_count = 0
            return

        # Lead counts
        self.env.cr.execute("""
            SELECT cf_project_id, COUNT(*)
            FROM crm_lead
            WHERE cf_project_id IN %s AND active = true
            GROUP BY cf_project_id
        """, (tuple(self.ids),))
        lead_counts = dict(self.env.cr.fetchall())

        # Last activity
        self.env.cr.execute("""
            SELECT cf_project_id, MAX(write_date)
            FROM crm_lead
            WHERE cf_project_id IN %s AND active = true
            GROUP BY cf_project_id
        """, (tuple(self.ids),))
        last_dates = dict(self.env.cr.fetchall())

        # Open issues
        self.env.cr.execute("""
            SELECT l.cf_project_id, COUNT(*)
            FROM crm_lead l
            JOIN crm_tag_rel ctr ON ctr.lead_id = l.id
            JOIN crm_tag t ON t.id = ctr.tag_id
            WHERE l.cf_project_id IN %s
              AND l.active = true
              AND t.cf_category = 'issue'
            GROUP BY l.cf_project_id
        """, (tuple(self.ids),))
        issue_counts = dict(self.env.cr.fetchall())

        for project in self:
            project.cf_lead_count = lead_counts.get(project.id, 0)
            project.cf_last_activity_date = last_dates.get(project.id) or project.write_date
            project.cf_open_issues_count = issue_counts.get(project.id, 0)
