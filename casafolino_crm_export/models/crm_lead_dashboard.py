from odoo import models, api


class CrmLeadDashboard(models.AbstractModel):
    _name = 'casafolino.crm.lead.dashboard'
    _description = "CRM Lead Dashboard Aggregator"

    @api.model
    def get_metrics(self, domain=None):
        """Return 4 KPI metrics for the list view header."""
        domain = domain or []
        Lead = self.env['crm.lead']

        base_domain = domain + [
            ('active', '=', True),
            ('stage_id.is_won', '=', False),
            ('probability', '!=', 0),
        ]

        open_leads = Lead.search_count(base_domain)

        leads = Lead.search(base_domain)
        pipeline_value = sum(leads.mapped('expected_revenue'))

        self.env.cr.execute("""
            SELECT
                COUNT(*) FILTER (WHERE s.is_won = true) AS won,
                COUNT(*) AS total
            FROM crm_lead l
            JOIN crm_stage s ON l.stage_id = s.id
            WHERE l.create_date >= NOW() - INTERVAL '90 days'
              AND l.active = true
        """)
        row = self.env.cr.fetchone()
        conversion_90d = round((row[0] / row[1]) * 100, 1) if row and row[1] > 0 else 0.0

        open_issues = Lead.search_count([
            ('active', '=', True),
            ('stage_id.is_won', '=', False),
            ('tag_ids.cf_category', '=', 'issue'),
        ])

        return {
            'open_leads': open_leads,
            'pipeline_value': pipeline_value,
            'conversion_90d': conversion_90d,
            'open_issues': open_issues,
        }
