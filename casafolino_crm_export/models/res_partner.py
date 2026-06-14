from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    cf_dossiers_count = fields.Integer(
        compute='_compute_cf_dossiers_count', string='Dossier',
    )
    cf_sample_count = fields.Integer(
        compute='_compute_cf_sample_metrics', string='Campionature',
    )
    cf_open_sample_count = fields.Integer(
        compute='_compute_cf_sample_metrics', string='Campionature aperte',
    )
    cf_sample_ids = fields.Many2many(
        'cf.export.sample',
        compute='_compute_cf_sample_ids',
        string='Campionature cliente',
    )

    cf_partner_role = fields.Selection(
        selection=[
            ('customer', 'Cliente'),
            ('agent', 'Agente / Canale'),
            ('prospect', 'Prospect'),
            ('internal', 'Interno CasaFolino'),
            ('supplier', 'Fornitore'),
            ('other', 'Altro'),
        ],
        string='Ruolo CasaFolino',
        default='other',
        index=True,
        tracking=True,
    )

    cf_managed_by_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='cf_partner_managed_by_rel',
        column1='partner_id',
        column2='agent_id',
        domain="[('cf_partner_role', '=', 'agent')]",
        string='Gestito da agenti',
    )

    cf_origin_introducer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Presentato da',
        index=True,
    )

    cf_managed_partners_count = fields.Integer(
        compute='_compute_cf_managed_counts',
        string='Partner gestiti',
    )
    cf_managed_projects_count = fields.Integer(
        compute='_compute_cf_managed_counts',
        string='Progetti gestiti',
    )

    @api.depends('cf_partner_role')
    def _compute_cf_managed_counts(self):
        agents = self.filtered(lambda p: p.cf_partner_role == 'agent')
        non_agents = self - agents
        for p in non_agents:
            p.cf_managed_partners_count = 0
            p.cf_managed_projects_count = 0
        if not agents or not agents.ids:
            return
        self.env.cr.execute("""
            SELECT agent_id, COUNT(DISTINCT partner_id)
            FROM cf_partner_managed_by_rel
            WHERE agent_id IN %s
            GROUP BY agent_id
        """, (tuple(agents.ids),))
        partner_counts = dict(self.env.cr.fetchall())
        self.env.cr.execute("""
            SELECT cf_managed_by_id, COUNT(*)
            FROM project_project
            WHERE cf_managed_by_id IN %s AND active = true
            GROUP BY cf_managed_by_id
        """, (tuple(agents.ids),))
        project_counts = dict(self.env.cr.fetchall())
        for agent in agents:
            agent.cf_managed_partners_count = partner_counts.get(agent.id, 0)
            agent.cf_managed_projects_count = project_counts.get(agent.id, 0)

    def _compute_cf_dossiers_count(self):
        Project = self.env['project.project']
        for p in self:
            commercial = p.commercial_partner_id or p
            p.cf_dossiers_count = Project.search_count([
                '|',
                ('partner_id', '=', commercial.id),
                ('partner_id.commercial_partner_id', '=', commercial.id),
            ])

    def _compute_cf_sample_metrics(self):
        Sample = self.env['cf.export.sample']
        for p in self:
            commercial = p.commercial_partner_id or p
            domain = [
                '|',
                ('partner_id', '=', commercial.id),
                ('partner_id.commercial_partner_id', '=', commercial.id),
            ]
            p.cf_sample_count = Sample.search_count(domain)
            p.cf_open_sample_count = Sample.search_count(domain + [
                ('state', 'not in', ['feedback_ok', 'feedback_ko', 'no_feedback']),
            ])

    def _compute_cf_sample_ids(self):
        Sample = self.env['cf.export.sample']
        for p in self:
            commercial = p.commercial_partner_id or p
            p.cf_sample_ids = Sample.search([
                '|',
                ('partner_id', '=', commercial.id),
                ('partner_id.commercial_partner_id', '=', commercial.id),
            ], order='create_date desc', limit=50)

    def action_view_cf_dossiers(self):
        self.ensure_one()
        commercial = self.commercial_partner_id or self
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dossier %s') % self.name,
            'res_model': 'project.project',
            'view_mode': 'kanban,list,form',
            'domain': [
                '|',
                ('partner_id', '=', commercial.id),
                ('partner_id.commercial_partner_id', '=', commercial.id),
            ],
        }

    def action_view_cf_samples(self):
        self.ensure_one()
        commercial = self.commercial_partner_id or self
        return {
            'type': 'ir.actions.act_window',
            'name': _('Campionature %s') % self.name,
            'res_model': 'cf.export.sample',
            'view_mode': 'kanban,list,form',
            'domain': [
                '|',
                ('partner_id', '=', commercial.id),
                ('partner_id.commercial_partner_id', '=', commercial.id),
            ],
            'context': {
                'default_partner_id': self.id,
                'search_default_open': 1,
            },
        }

    def action_create_cf_sample(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nuova campionatura cliente'),
            'res_model': 'cf.export.sample',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_partner_id': self.id},
        }

    def action_compose_email_f8(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'casafolino_mail.compose_f8',
            'context': {
                'default_partner_email': self.email or '',
                'default_partner_id': self.id,
                'default_thread_id': self.id,
                'default_thread_model': 'res.partner',
            },
        }
