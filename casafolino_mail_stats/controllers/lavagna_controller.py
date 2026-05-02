import logging
from odoo import http
from odoo.http import request

from odoo.addons.casafolino_initiative_dashboard.controllers.lavagna_controller import LavagnaController

_logger = logging.getLogger(__name__)


class LavagnaControllerMailStats(LavagnaController):
    """Extend Lavagna data endpoint to include email performance stats."""

    def get_lavagna_data(self, initiative_id, **kwargs):
        result = super().get_lavagna_data(initiative_id, **kwargs)
        if isinstance(result, dict) and 'error' not in result:
            result['email_stats'] = self._get_email_stats(initiative_id)
        return result

    def _get_email_stats(self, initiative_id):
        """Compute email performance stats for the initiative."""
        try:
            show = request.env['ir.config_parameter'].sudo().get_param(
                'casafolino.mail_stats.show_in_lavagna', 'True')
            if show.lower() != 'true':
                return None

            request.env.cr.execute("""
                SELECT
                    COUNT(*) AS total_sent,
                    COUNT(*) FILTER (WHERE trace_status IN ('open', 'reply')) AS opened,
                    COUNT(*) FILTER (WHERE links_click_datetime IS NOT NULL) AS clicked,
                    COUNT(*) FILTER (WHERE trace_status = 'reply') AS replied,
                    COUNT(*) FILTER (WHERE trace_status = 'bounce') AS bounced,
                    CASE WHEN COUNT(*) > 0
                         THEN ROUND((COUNT(*) FILTER (WHERE trace_status IN ('open', 'reply')))::numeric / COUNT(*) * 100, 1)
                         ELSE 0 END AS open_rate,
                    CASE WHEN COUNT(*) > 0
                         THEN ROUND((COUNT(*) FILTER (WHERE links_click_datetime IS NOT NULL))::numeric / COUNT(*) * 100, 1)
                         ELSE 0 END AS click_rate
                FROM mailing_trace
                WHERE create_date >= NOW() - INTERVAL '30 days'
                  AND trace_status NOT IN ('cancel', 'error')
            """)
            row = request.env.cr.dictfetchone()

            # Top 5 most engaged partners
            request.env.cr.execute("""
                SELECT e.res_id, p.name, e.engagement_status, e.opened_count, e.total_sent
                FROM casafolino_mail_engagement e
                JOIN res_partner p ON p.id = e.res_id AND e.res_model = 'res.partner'
                WHERE e.engagement_status IN ('hot', 'replied')
                ORDER BY e.opened_count DESC
                LIMIT 5
            """)
            top_engaged = [
                {'id': r[0], 'name': r[1], 'status': r[2],
                 'opens': r[3], 'sent': r[4]}
                for r in request.env.cr.fetchall()
            ]

            return {
                'total_sent': row['total_sent'],
                'opened': row['opened'],
                'clicked': row['clicked'],
                'replied': row['replied'],
                'bounced': row['bounced'],
                'open_rate': float(row['open_rate']),
                'click_rate': float(row['click_rate']),
                'top_engaged': top_engaged,
            }
        except Exception as e:
            _logger.warning("Error computing email stats for lavagna: %s", e)
            return None
