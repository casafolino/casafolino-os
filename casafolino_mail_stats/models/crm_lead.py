from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    mail_stats_total_sent = fields.Integer(
        'Email Inviate', compute='_compute_mail_stats', store=False)
    mail_stats_opened_count = fields.Integer(
        'Email Aperte', compute='_compute_mail_stats', store=False)
    mail_stats_clicked_count = fields.Integer(
        'Email Cliccate', compute='_compute_mail_stats', store=False)
    mail_stats_bounced_count = fields.Integer(
        'Email Bounced', compute='_compute_mail_stats', store=False)
    mail_stats_replied_count = fields.Integer(
        'Email Replied', compute='_compute_mail_stats', store=False)
    mail_stats_open_rate = fields.Float(
        'Open Rate %', compute='_compute_mail_stats', store=False)
    mail_stats_engagement_status = fields.Selection([
        ('cold', 'Cold'),
        ('warm', 'Warm'),
        ('hot', 'Hot'),
        ('replied', 'Replied'),
        ('bounced', 'Bounced'),
    ], string='Email Engagement', compute='_compute_mail_stats',
        search='_search_engagement_status', store=False)

    @api.depends('partner_id')
    def _compute_mail_stats(self):
        """Compute stats from partner's engagement data."""
        for lead in self:
            if lead.partner_id:
                eng = self.env['casafolino.mail.engagement'].search([
                    ('res_model', '=', 'res.partner'),
                    ('res_id', '=', lead.partner_id.id),
                ], limit=1)
            else:
                eng = None
            lead.mail_stats_total_sent = eng.total_sent if eng else 0
            lead.mail_stats_opened_count = eng.opened_count if eng else 0
            lead.mail_stats_clicked_count = eng.clicked_count if eng else 0
            lead.mail_stats_bounced_count = eng.bounced_count if eng else 0
            lead.mail_stats_replied_count = eng.replied_count if eng else 0
            lead.mail_stats_open_rate = eng.open_rate if eng else 0
            lead.mail_stats_engagement_status = eng.engagement_status if eng else False

    def _search_engagement_status(self, operator, value):
        engagements = self.env['casafolino.mail.engagement'].search([
            ('res_model', '=', 'res.partner'),
            ('engagement_status', operator, value),
        ])
        partner_ids = [e.res_id for e in engagements]
        return [('partner_id', 'in', partner_ids)]

    def action_view_email_traces(self):
        self.ensure_one()
        domain = []
        if self.partner_id:
            domain = [('model', '=', 'res.partner'), ('res_id', '=', self.partner_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Email Tracking — %s' % self.name,
            'res_model': 'mailing.trace',
            'view_mode': 'list,form',
            'domain': domain,
        }
