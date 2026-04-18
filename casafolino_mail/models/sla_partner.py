import logging

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class CasafolinoMailSlaPartner(models.Model):
    _name = 'casafolino.mail.sla.partner'
    _description = 'SLA Dashboard Buyer — per partner con lead aperti'
    _auto = False
    _order = 'days_of_silence desc'

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char(related='partner_id.name', string='Nome', readonly=True)
    open_leads_count = fields.Integer('Lead aperti', readonly=True)
    last_in_date = fields.Datetime('Ultimo IN', readonly=True)
    last_out_date = fields.Datetime('Ultimo OUT', readonly=True)
    days_of_silence = fields.Integer('Silenzio (gg)', readonly=True)
    avg_our_response_hours = fields.Float('Ns risposta (h)', readonly=True, digits=(10, 1))
    avg_their_response_hours = fields.Float('Loro risposta (h)', readonly=True, digits=(10, 1))
    in_count_30d = fields.Integer('IN 30gg', readonly=True)
    out_count_30d = fields.Integer('OUT 30gg', readonly=True)
    sla_status = fields.Selection([
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ], string='Stato SLA', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH partners_with_leads AS (
                    SELECT
                        p.id AS partner_id,
                        COUNT(DISTINCT l.id) AS open_leads_count
                    FROM res_partner p
                    JOIN crm_lead l ON l.partner_id = p.id
                        AND l.active = TRUE
                        AND l.type = 'opportunity'
                    JOIN crm_stage s ON s.id = l.stage_id
                        AND s.is_won = FALSE
                    GROUP BY p.id
                ),
                msg_stats AS (
                    SELECT
                        m.partner_id,
                        MAX(CASE WHEN m.direction = 'inbound' THEN m.email_date END) AS last_in_date,
                        MAX(CASE WHEN m.direction = 'outbound' THEN m.email_date END) AS last_out_date,
                        COUNT(CASE WHEN m.direction = 'inbound'
                                    AND m.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
                              THEN 1 END) AS in_count_30d,
                        COUNT(CASE WHEN m.direction = 'outbound'
                                    AND m.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
                              THEN 1 END) AS out_count_30d
                    FROM casafolino_mail_message m
                    WHERE m.partner_id IS NOT NULL
                      AND m.state IN ('keep', 'auto_keep')
                    GROUP BY m.partner_id
                ),
                our_response AS (
                    SELECT
                        inb.partner_id,
                        AVG(EXTRACT(EPOCH FROM (outb.email_date - inb.email_date)) / 3600.0)
                            AS avg_hours
                    FROM casafolino_mail_message inb
                    JOIN LATERAL (
                        SELECT outb2.email_date
                        FROM casafolino_mail_message outb2
                        WHERE outb2.partner_id = inb.partner_id
                          AND outb2.direction = 'outbound'
                          AND outb2.state IN ('keep', 'auto_keep')
                          AND outb2.email_date > inb.email_date
                        ORDER BY outb2.email_date ASC
                        LIMIT 1
                    ) outb ON TRUE
                    WHERE inb.direction = 'inbound'
                      AND inb.state IN ('keep', 'auto_keep')
                      AND inb.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
                      AND inb.partner_id IS NOT NULL
                    GROUP BY inb.partner_id
                ),
                their_response AS (
                    SELECT
                        outb.partner_id,
                        AVG(EXTRACT(EPOCH FROM (inb.email_date - outb.email_date)) / 3600.0)
                            AS avg_hours
                    FROM casafolino_mail_message outb
                    JOIN LATERAL (
                        SELECT inb2.email_date
                        FROM casafolino_mail_message inb2
                        WHERE inb2.partner_id = outb.partner_id
                          AND inb2.direction = 'inbound'
                          AND inb2.state IN ('keep', 'auto_keep')
                          AND inb2.email_date > outb.email_date
                        ORDER BY inb2.email_date ASC
                        LIMIT 1
                    ) inb ON TRUE
                    WHERE outb.direction = 'outbound'
                      AND outb.state IN ('keep', 'auto_keep')
                      AND outb.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
                      AND outb.partner_id IS NOT NULL
                    GROUP BY outb.partner_id
                )
                SELECT
                    pwl.partner_id AS id,
                    pwl.partner_id,
                    pwl.open_leads_count,
                    ms.last_in_date,
                    ms.last_out_date,
                    COALESCE(
                        EXTRACT(DAY FROM (NOW() AT TIME ZONE 'UTC') - ms.last_in_date)::INTEGER,
                        9999
                    ) AS days_of_silence,
                    ROUND(oresp.avg_hours::NUMERIC, 1) AS avg_our_response_hours,
                    ROUND(tresp.avg_hours::NUMERIC, 1) AS avg_their_response_hours,
                    COALESCE(ms.in_count_30d, 0) AS in_count_30d,
                    COALESCE(ms.out_count_30d, 0) AS out_count_30d,
                    CASE
                        WHEN COALESCE(
                            EXTRACT(DAY FROM (NOW() AT TIME ZONE 'UTC') - ms.last_in_date)::INTEGER,
                            9999) >= 7
                            OR COALESCE(oresp.avg_hours, 9999) > 168
                        THEN 'critical'
                        WHEN COALESCE(
                            EXTRACT(DAY FROM (NOW() AT TIME ZONE 'UTC') - ms.last_in_date)::INTEGER,
                            9999) >= 3
                            OR COALESCE(oresp.avg_hours, 9999) > 72
                        THEN 'warning'
                        ELSE 'ok'
                    END AS sla_status
                FROM partners_with_leads pwl
                LEFT JOIN msg_stats ms ON ms.partner_id = pwl.partner_id
                LEFT JOIN our_response oresp ON oresp.partner_id = pwl.partner_id
                LEFT JOIN their_response tresp ON tresp.partner_id = pwl.partner_id
            )
        """ % self._table)

    def action_open_emails(self):
        """Apre lista email filtrata per questo partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Email — %s' % self.partner_id.name,
            'res_model': 'casafolino.mail.message',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.partner_id.id),
                       ('state', 'in', ['keep', 'auto_keep'])],
            'context': {'default_partner_id': self.partner_id.id},
        }
