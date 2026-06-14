import logging

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class CasafolinoMailLeadScore(models.Model):
    """Lead Scoring 0-100 cross-source per res.partner con attività email.

    Formula (v7.8.1):
        score = frequency (max 35) + recency (max 30) + engagement (max 20)
              + lead_bonus (max 10) + sentiment_bonus (max 5) + urgency_bonus (max 5)

    - frequency_score: LEAST(35, inbound_count_90d * 2) — 18 email = max
    - recency_score: 30/22/14/7/0 per fasce 3d/7d/14d/30d/90d
    - engagement_score: 20 dialogo, 15 buyer urgente senza risposta (5+ IN, 0 OUT), 12 risposto
    - lead_bonus: 10 se ha almeno un lead CRM aperto
    - sentiment_bonus: media AI sentiment (positive=5, neutral=2, negative=0, NULL=2)
    - urgency_bonus: 5 se ultimo IN < 3gg e mai risposto (0 OUT)

    Max teorico 105 ma combinatoriamente ~95. Tier: hot (80+), warm (50-79), cold (20-49), frozen (0-19)
    """
    _name = 'casafolino.mail.lead.score'
    _description = 'Lead Scoring 0-100 — buyer ranked per priorità commerciale'
    _auto = False
    _order = 'score desc, id'

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char('Nome', readonly=True)
    partner_email = fields.Char('Email', readonly=True)
    country_id = fields.Many2one('res.country', string='Paese', readonly=True)
    score = fields.Integer('Score', readonly=True)
    tier = fields.Selection([
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
        ('frozen', 'Frozen'),
    ], string='Tier', readonly=True)
    has_open_lead = fields.Boolean('Lead aperto', readonly=True)
    inbound_count_90d = fields.Integer('IN 90gg', readonly=True)
    outbound_count_90d = fields.Integer('OUT 90gg', readonly=True)
    last_inbound_date = fields.Datetime('Ultimo IN', readonly=True)
    frequency_score = fields.Integer('Freq.', readonly=True)
    recency_score = fields.Integer('Recency', readonly=True)
    engagement_score = fields.Integer('Engage.', readonly=True)
    lead_bonus = fields.Integer('Lead', readonly=True)
    sentiment_bonus = fields.Integer('Sentiment', readonly=True)
    urgency_bonus = fields.Integer('Urgency', readonly=True)
    rank = fields.Integer('Rank', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH mail_stats AS (
                    SELECT
                        m.partner_id,
                        COUNT(CASE WHEN m.direction = 'inbound' THEN 1 END) AS inbound_count_90d,
                        COUNT(CASE WHEN m.direction = 'outbound' THEN 1 END) AS outbound_count_90d,
                        MAX(CASE WHEN m.direction = 'inbound' THEN m.email_date END) AS last_inbound_date
                    FROM casafolino_mail_message m
                    WHERE m.partner_id IS NOT NULL
                      AND m.state IN ('keep', 'auto_keep')
                      AND m.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '90 days'
                    GROUP BY m.partner_id
                    HAVING COUNT(CASE WHEN m.direction = 'inbound' THEN 1 END) > 0
                ),
                lead_check AS (
                    SELECT DISTINCT l.partner_id, TRUE AS has_open_lead
                    FROM crm_lead l
                    JOIN crm_stage s ON s.id = l.stage_id
                    WHERE l.active = TRUE
                      AND l.type = 'opportunity'
                      AND COALESCE(s.is_won, FALSE) = FALSE
                      AND l.partner_id IS NOT NULL
                ),
                sentiment_avg AS (
                    SELECT
                        m.partner_id,
                        AVG(CASE
                            WHEN m.ai_sentiment = 'positive' THEN 5
                            WHEN m.ai_sentiment = 'neutral' THEN 2
                            WHEN m.ai_sentiment = 'negative' THEN 0
                            ELSE 2
                        END) AS avg_sent
                    FROM casafolino_mail_message m
                    WHERE m.partner_id IS NOT NULL
                      AND m.direction = 'inbound'
                      AND m.state IN ('keep', 'auto_keep')
                      AND m.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
                    GROUP BY m.partner_id
                ),
                scored AS (
                    SELECT
                        p.id AS partner_id,
                        p.name AS partner_name,
                        p.email AS partner_email,
                        p.country_id,
                        ms.inbound_count_90d,
                        ms.outbound_count_90d,
                        ms.last_inbound_date,
                        COALESCE(lc.has_open_lead, FALSE) AS has_open_lead,

                        -- frequency_score (max 35)
                        LEAST(35, ms.inbound_count_90d * 2) AS frequency_score,

                        -- recency_score (max 30)
                        CASE
                            WHEN ms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '3 days' THEN 30
                            WHEN ms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days' THEN 22
                            WHEN ms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '14 days' THEN 14
                            WHEN ms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days' THEN 7
                            ELSE 0
                        END AS recency_score,

                        -- engagement_score (max 20)
                        CASE
                            WHEN ms.outbound_count_90d >= 3 AND ms.inbound_count_90d >= 3 THEN 20
                            WHEN ms.outbound_count_90d >= 1 THEN 12
                            WHEN ms.inbound_count_90d >= 5 AND ms.outbound_count_90d = 0 THEN 15
                            ELSE 0
                        END AS engagement_score,

                        -- lead_bonus (max 10)
                        CASE WHEN COALESCE(lc.has_open_lead, FALSE) THEN 10 ELSE 0 END AS lead_bonus,

                        -- sentiment_bonus (max 5)
                        COALESCE(ROUND(sa.avg_sent)::INTEGER, 2) AS sentiment_bonus,

                        -- urgency_bonus (max 5)
                        CASE WHEN ms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '3 days'
                                  AND ms.outbound_count_90d = 0
                             THEN 5 ELSE 0
                        END AS urgency_bonus

                    FROM res_partner p
                    JOIN mail_stats ms ON ms.partner_id = p.id
                    LEFT JOIN lead_check lc ON lc.partner_id = p.id
                    LEFT JOIN sentiment_avg sa ON sa.partner_id = p.id
                    WHERE p.email IS NULL OR p.email NOT ILIKE '%%@casafolino.com'
                )
                SELECT
                    s.partner_id AS id,
                    s.partner_id,
                    s.partner_name,
                    s.partner_email,
                    s.country_id,
                    s.inbound_count_90d,
                    s.outbound_count_90d,
                    s.last_inbound_date,
                    s.has_open_lead,
                    s.frequency_score,
                    s.recency_score,
                    s.engagement_score,
                    s.lead_bonus,
                    s.sentiment_bonus,
                    s.urgency_bonus,
                    LEAST(100, s.frequency_score + s.recency_score + s.engagement_score
                     + s.lead_bonus + s.sentiment_bonus + s.urgency_bonus) AS score,
                    CASE
                        WHEN LEAST(100, s.frequency_score + s.recency_score + s.engagement_score
                              + s.lead_bonus + s.sentiment_bonus + s.urgency_bonus) >= 80 THEN 'hot'
                        WHEN LEAST(100, s.frequency_score + s.recency_score + s.engagement_score
                              + s.lead_bonus + s.sentiment_bonus + s.urgency_bonus) >= 50 THEN 'warm'
                        WHEN LEAST(100, s.frequency_score + s.recency_score + s.engagement_score
                              + s.lead_bonus + s.sentiment_bonus + s.urgency_bonus) >= 20 THEN 'cold'
                        ELSE 'frozen'
                    END AS tier,
                    ROW_NUMBER() OVER (
                        ORDER BY LEAST(100, s.frequency_score + s.recency_score + s.engagement_score
                                  + s.lead_bonus + s.sentiment_bonus + s.urgency_bonus) DESC
                    ) AS rank
                FROM scored s
            )
        """ % self._table)

    def action_open_emails(self):
        """Apre lista email filtrata per questo partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Email — %s' % self.partner_name,
            'res_model': 'casafolino.mail.message',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id),
                       ('state', 'in', ['keep', 'auto_keep'])],
        }

    def action_create_lead(self):
        """Crea un crm.lead per questo partner e apre il form."""
        self.ensure_one()
        stage = self.env['crm.stage'].search(
            [('is_won', '!=', True)], order='sequence', limit=1)
        lead = self.env['crm.lead'].create({
            'name': 'Lead da email: %s' % self.partner_name,
            'partner_id': self.partner_id.id,
            'email_from': self.partner_email or self.partner_id.email,
            'type': 'opportunity',
            'stage_id': stage.id if stage else False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead — %s' % self.partner_name,
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
            'target': 'current',
        }
