from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
