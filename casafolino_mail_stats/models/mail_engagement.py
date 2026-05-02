import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailEngagement(models.Model):
    _name = 'casafolino.mail.engagement'
    _description = 'Cache aggregazione tracking email per partner/lead'
    _rec_name = 'res_id'

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    total_sent = fields.Integer(default=0)
    opened_count = fields.Integer(default=0)
    clicked_count = fields.Integer(default=0)
    bounced_count = fields.Integer(default=0)
    replied_count = fields.Integer(default=0)
    last_open_date = fields.Datetime()
    last_click_date = fields.Datetime()
    open_rate = fields.Float(digits=(5, 2))
    engagement_status = fields.Selection([
        ('cold', 'Cold'),
        ('warm', 'Warm'),
        ('hot', 'Hot'),
        ('replied', 'Replied'),
        ('bounced', 'Bounced'),
    ], default='cold', index=True)
    last_update = fields.Datetime(default=fields.Datetime.now)

    _sql_constraints = [
        ('unique_res', 'UNIQUE(res_model, res_id)', 'One entry per record'),
    ]

    def init(self):
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_mailing_trace_res_model_status
            ON mailing_trace(res_id, model, trace_status)
        """)

    @api.model
    def _rebuild_cache_full(self):
        """Cron: ricostruisce tutta la cache da mailing.trace."""
        _logger.info("casafolino.mail.engagement: rebuilding full cache")
        self.env.cr.execute("""
            INSERT INTO casafolino_mail_engagement
                (res_model, res_id, total_sent, opened_count, clicked_count,
                 bounced_count, replied_count, last_open_date, last_click_date,
                 open_rate, engagement_status, last_update,
                 create_uid, create_date, write_uid, write_date)
            SELECT
                model AS res_model,
                res_id,
                COUNT(*) AS total_sent,
                COUNT(*) FILTER (WHERE trace_status IN ('open', 'reply')) AS opened_count,
                COUNT(*) FILTER (WHERE links_click_datetime IS NOT NULL) AS clicked_count,
                COUNT(*) FILTER (WHERE trace_status = 'bounce') AS bounced_count,
                COUNT(*) FILTER (WHERE trace_status = 'reply') AS replied_count,
                MAX(open_datetime) AS last_open_date,
                MAX(links_click_datetime) AS last_click_date,
                CASE WHEN COUNT(*) > 0
                     THEN (COUNT(*) FILTER (WHERE trace_status IN ('open', 'reply')))::float / COUNT(*) * 100
                     ELSE 0 END AS open_rate,
                CASE
                    WHEN COUNT(*) FILTER (WHERE trace_status = 'reply') > 0 THEN 'replied'
                    WHEN COUNT(*) > 0 AND COUNT(*) FILTER (WHERE trace_status = 'bounce') = COUNT(*) THEN 'bounced'
                    WHEN COUNT(*) FILTER (WHERE trace_status IN ('open', 'reply')) >= 3
                         AND MAX(open_datetime) >= NOW() - INTERVAL '7 days' THEN 'hot'
                    WHEN COUNT(*) FILTER (WHERE trace_status IN ('open', 'reply')) >= 1
                         AND MAX(open_datetime) >= NOW() - INTERVAL '30 days' THEN 'warm'
                    ELSE 'cold'
                END AS engagement_status,
                NOW(), 1, NOW(), 1, NOW()
            FROM mailing_trace
            WHERE res_id IS NOT NULL AND model IS NOT NULL
              AND trace_status NOT IN ('cancel', 'error')
            GROUP BY model, res_id
            ON CONFLICT (res_model, res_id) DO UPDATE SET
                total_sent = EXCLUDED.total_sent,
                opened_count = EXCLUDED.opened_count,
                clicked_count = EXCLUDED.clicked_count,
                bounced_count = EXCLUDED.bounced_count,
                replied_count = EXCLUDED.replied_count,
                last_open_date = EXCLUDED.last_open_date,
                last_click_date = EXCLUDED.last_click_date,
                open_rate = EXCLUDED.open_rate,
                engagement_status = EXCLUDED.engagement_status,
                last_update = NOW(),
                write_date = NOW()
        """)
        _logger.info("casafolino.mail.engagement: cache rebuild complete")

    @api.model
    def _rebuild_cache_partial(self, keys):
        """Aggiorna cache per una lista di (model, res_id) specifici."""
        if not keys:
            return
        for model, res_id in keys:
            self.env.cr.execute("""
                SELECT
                    COUNT(*) AS total_sent,
                    COUNT(*) FILTER (WHERE trace_status IN ('open', 'reply')) AS opened_count,
                    COUNT(*) FILTER (WHERE links_click_datetime IS NOT NULL) AS clicked_count,
                    COUNT(*) FILTER (WHERE trace_status = 'bounce') AS bounced_count,
                    COUNT(*) FILTER (WHERE trace_status = 'reply') AS replied_count,
                    MAX(open_datetime) AS last_open_date,
                    MAX(links_click_datetime) AS last_click_date
                FROM mailing_trace
                WHERE model = %s AND res_id = %s
                  AND trace_status NOT IN ('cancel', 'error')
            """, (model, res_id))
            row = self.env.cr.dictfetchone()
            if not row or row['total_sent'] == 0:
                self.search([('res_model', '=', model), ('res_id', '=', res_id)]).unlink()
                continue
            total = row['total_sent']
            opened = row['opened_count']
            clicked = row['clicked_count']
            bounced = row['bounced_count']
            replied = row['replied_count']
            last_open = row['last_open_date']
            open_rate = (opened / total * 100) if total else 0
            if replied > 0:
                status = 'replied'
            elif total > 0 and bounced == total:
                status = 'bounced'
            elif opened >= 3 and last_open and (fields.Datetime.now() - last_open).days <= 7:
                status = 'hot'
            elif opened >= 1 and last_open and (fields.Datetime.now() - last_open).days <= 30:
                status = 'warm'
            else:
                status = 'cold'
            existing = self.search([('res_model', '=', model), ('res_id', '=', res_id)], limit=1)
            vals = {
                'total_sent': total,
                'opened_count': opened,
                'clicked_count': clicked,
                'bounced_count': bounced,
                'replied_count': replied,
                'last_open_date': last_open,
                'last_click_date': row['last_click_date'],
                'open_rate': open_rate,
                'engagement_status': status,
                'last_update': fields.Datetime.now(),
            }
            if existing:
                existing.write(vals)
            else:
                vals.update({'res_model': model, 'res_id': res_id})
                self.create(vals)

    @api.model
    def _check_hot_leads_activity(self):
        """Crea activity su lead collegati per partner hot/replied."""
        auto_activity = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.mail_stats.auto_activity', 'True')
        if auto_activity.lower() != 'true':
            return
        hot_partners = self.search([
            ('res_model', '=', 'res.partner'),
            ('engagement_status', 'in', ('hot', 'replied')),
        ])
        for eng in hot_partners:
            leads = self.env['crm.lead'].search([
                ('partner_id', '=', eng.res_id),
                ('active', '=', True),
                ('stage_id.is_won', '=', False),
            ], limit=1)
            if not leads:
                continue
            lead = leads[0]
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
                ('summary', 'ilike', 'lead caldo'),
                ('date_deadline', '>=', fields.Date.today()),
            ], limit=1)
            if existing:
                continue
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get('crm.lead').id,
                'res_id': lead.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_call').id,
                'summary': '📞 Call lead caldo — email engagement %s' % eng.engagement_status,
                'user_id': lead.user_id.id or self.env.uid,
                'date_deadline': fields.Date.today() + __import__('datetime').timedelta(days=1),
            })
