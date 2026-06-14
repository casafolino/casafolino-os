import logging
from datetime import timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailResponseMetric(models.TransientModel):
    _name = 'casafolino.mail.response.metric'
    _description = 'Response time analytics (computed on-the-fly)'

    @api.model
    def get_analytics(self, days=30, account_ids=None):
        """Compute response time analytics for the team."""
        now = fields.Datetime.now()
        cutoff = now - timedelta(days=days)

        Message = self.env['casafolino.mail.message']

        # Build base domain
        base_domain = [
            ('state', 'in', ['keep', 'auto_keep']),
            ('is_deleted', '=', False),
            ('email_date', '>=', cutoff),
        ]
        if account_ids:
            base_domain.append(('account_id', 'in', account_ids))

        # Per-account stats
        accounts = self.env['casafolino.mail.account'].search([('active', '=', True)])
        if account_ids:
            accounts = accounts.filtered(lambda a: a.id in account_ids)

        account_stats = []
        for acc in accounts:
            acc_domain = base_domain + [('account_id', '=', acc.id)]
            inbound = Message.search_count(acc_domain + [('direction', '=', 'inbound')])
            outbound = Message.search_count(acc_domain + [('direction', '=', 'outbound')])

            # Average response time: find inbound→outbound pairs in same thread
            avg_response_hours = self._compute_avg_response_time(acc.id, cutoff)

            account_stats.append({
                'account_id': acc.id,
                'account_name': acc.name or acc.email_address,
                'inbound_count': inbound,
                'outbound_count': outbound,
                'total': inbound + outbound,
                'avg_response_hours': round(avg_response_hours, 1),
            })

        # Top 10 partners by email volume
        cr = self.env.cr
        partner_domain_sql = ""
        params = [cutoff]
        if account_ids:
            partner_domain_sql = " AND m.account_id = ANY(%s)"
            params.append(account_ids)

        cr.execute("""
            SELECT m.partner_id, p.name, COUNT(*) as email_count,
                   MAX(m.email_date) as last_email
            FROM casafolino_mail_message m
            JOIN res_partner p ON p.id = m.partner_id
            WHERE m.state IN ('keep', 'auto_keep')
              AND m.is_deleted = false
              AND m.email_date >= %s
              AND m.partner_id IS NOT NULL
              """ + partner_domain_sql + """
            GROUP BY m.partner_id, p.name
            ORDER BY email_count DESC
            LIMIT 10
        """, params)
        top_partners = [
            {
                'partner_id': r[0],
                'partner_name': r[1] or '',
                'email_count': r[2],
                'last_email': str(r[3])[:10] if r[3] else '',
            }
            for r in cr.fetchall()
        ]

        # Overall totals
        total_inbound = sum(a['inbound_count'] for a in account_stats)
        total_outbound = sum(a['outbound_count'] for a in account_stats)

        # Thread stats
        Thread = self.env['casafolino.mail.thread']
        thread_domain = [('last_message_date', '>=', cutoff)]
        if account_ids:
            thread_domain.append(('account_id', 'in', account_ids))
        active_threads = Thread.search_count(thread_domain)
        archived_threads = Thread.search_count(thread_domain + [('is_archived', '=', True)])

        # Hot partners followed
        intel_domain = [('hotness_tier', 'in', ['hot', 'warm'])]
        hot_count = self.env['casafolino.partner.intelligence'].search_count(intel_domain)

        return {
            'period_days': days,
            'account_stats': account_stats,
            'top_partners': top_partners,
            'total_inbound': total_inbound,
            'total_outbound': total_outbound,
            'active_threads': active_threads,
            'archived_threads': archived_threads,
            'hot_partners': hot_count,
        }

    def _compute_avg_response_time(self, account_id, cutoff):
        """Compute average response time for an account.

        Finds inbound messages, then looks for first outbound reply in same thread.
        """
        cr = self.env.cr
        cr.execute("""
            WITH inbound_msgs AS (
                SELECT id, thread_id, email_date
                FROM casafolino_mail_message
                WHERE account_id = %s
                  AND direction = 'inbound'
                  AND state IN ('keep', 'auto_keep')
                  AND is_deleted = false
                  AND email_date >= %s
                  AND thread_id IS NOT NULL
            ),
            first_reply AS (
                SELECT DISTINCT ON (i.id)
                    i.id as inbound_id,
                    EXTRACT(EPOCH FROM (o.email_date - i.email_date)) / 3600.0 as hours
                FROM inbound_msgs i
                JOIN casafolino_mail_message o
                    ON o.thread_id = i.thread_id
                   AND o.direction = 'outbound'
                   AND o.email_date > i.email_date
                   AND o.is_deleted = false
                ORDER BY i.id, o.email_date ASC
            )
            SELECT AVG(hours) FROM first_reply WHERE hours > 0 AND hours < 720
        """, (account_id, cutoff))
        result = cr.fetchone()
        return result[0] if result and result[0] else 0.0
