import logging

from odoo import fields, models, tools

_logger = logging.getLogger(__name__)


class CasafolinoMailOrphanPartner(models.Model):
    _name = 'casafolino.mail.orphan.partner'
    _description = 'Buyer senza lead — partner con email ma senza opportunità CRM'
    _auto = False
    _order = 'priority desc, inbound_count_90d desc, last_inbound_date desc'

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char('Nome', readonly=True)
    partner_email = fields.Char('Email', readonly=True)
    country_id = fields.Many2one('res.country', string='Paese', readonly=True)
    inbound_count_90d = fields.Integer('IN 90gg', readonly=True)
    outbound_count_90d = fields.Integer('OUT 90gg', readonly=True)
    last_inbound_date = fields.Datetime('Ultimo IN', readonly=True)
    first_inbound_date = fields.Datetime('Primo IN', readonly=True)
    days_active = fields.Integer('Giorni attivi', readonly=True)
    has_reply = fields.Boolean('Risposto', readonly=True)
    priority = fields.Selection([
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
    ], string='Priorità', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH partner_mail_stats AS (
                    SELECT
                        m.partner_id,
                        COUNT(CASE WHEN m.direction = 'inbound' THEN 1 END) AS inbound_count_90d,
                        COUNT(CASE WHEN m.direction = 'outbound' THEN 1 END) AS outbound_count_90d,
                        MAX(CASE WHEN m.direction = 'inbound' THEN m.email_date END) AS last_inbound_date,
                        MIN(CASE WHEN m.direction = 'inbound' THEN m.email_date END) AS first_inbound_date
                    FROM casafolino_mail_message m
                    WHERE m.partner_id IS NOT NULL
                      AND m.state IN ('keep', 'auto_keep')
                      AND m.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '90 days'
                    GROUP BY m.partner_id
                    HAVING COUNT(CASE WHEN m.direction = 'inbound' THEN 1 END) > 0
                )
                SELECT
                    p.id AS id,
                    p.id AS partner_id,
                    p.name AS partner_name,
                    p.email AS partner_email,
                    p.country_id,
                    pms.inbound_count_90d,
                    pms.outbound_count_90d,
                    pms.last_inbound_date,
                    pms.first_inbound_date,
                    COALESCE(
                        EXTRACT(DAY FROM pms.last_inbound_date - pms.first_inbound_date)::INTEGER,
                        0
                    ) AS days_active,
                    COALESCE(pms.outbound_count_90d, 0) > 0 AS has_reply,
                    CASE
                        WHEN pms.inbound_count_90d >= 5
                            OR pms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
                        THEN 'hot'
                        WHEN pms.inbound_count_90d >= 2
                            OR pms.last_inbound_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
                        THEN 'warm'
                        ELSE 'cold'
                    END AS priority
                FROM res_partner p
                JOIN partner_mail_stats pms ON pms.partner_id = p.id
                WHERE NOT EXISTS (
                    SELECT 1 FROM crm_lead l
                    JOIN crm_stage s ON s.id = l.stage_id
                    WHERE l.partner_id = p.id
                      AND l.active = TRUE
                      AND l.type = 'opportunity'
                      AND COALESCE(s.is_won, FALSE) = FALSE
                )
                AND (p.email IS NULL OR p.email NOT ILIKE '%%@casafolino.com')
                AND p.id NOT IN (SELECT COALESCE(partner_id, 0) FROM res_users)
            )
        """ % self._table)

    def action_create_lead(self):
        """Crea un crm.lead per questo partner orfano e apre il form."""
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

    # ── Bulk Actions (F7 §3.6) ──────────────────────────────────────

    def action_bulk_ignore_sender(self):
        """Bulk: ignora tutti i mittenti selezionati (crea policy auto_discard)."""
        Policy = self.env['casafolino.mail.sender_policy'].sudo()
        Decision = self.env['casafolino.mail.sender.decision']
        Msg = self.env['casafolino.mail.message'].sudo()

        count = 0
        for orphan in self:
            email = (orphan.partner_email or '').lower().strip()
            if not email:
                continue

            # Skip se decisione già esiste
            existing = Decision.search([
                ('partner_id', '=', orphan.partner_id.id),
                ('active', '=', True),
            ], limit=1)
            if existing:
                continue

            # Crea policy
            policy = Policy.create({
                'name': 'Bulk ignora: %s' % email,
                'pattern_type': 'email_exact',
                'pattern_value': email,
                'action': 'auto_discard',
                'priority': 15,
                'notes': 'Bulk triage il %s da %s' % (
                    fields.Datetime.now().strftime('%Y-%m-%d'), self.env.user.name),
            })

            # Crea decisione
            Decision.create({
                'partner_id': orphan.partner_id.id,
                'sender_email': email,
                'decision': 'ignored_sender',
                'sender_policy_id': policy.id,
            })

            # Retroactive apply
            msgs = Msg.search([
                ('sender_email', '=ilike', email),
                ('state', 'in', ['new', 'review']),
                ('direction', '=', 'inbound'),
            ])
            if msgs:
                msgs.write({'state': 'auto_discard', 'policy_applied_id': policy.id})

            count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Ignora',
                'message': '%d mittenti ignorati.' % count,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_bulk_keep(self):
        """Bulk: tieni tutti i selezionati come contatti validi."""
        Decision = self.env['casafolino.mail.sender.decision']

        count = 0
        for orphan in self:
            existing = Decision.search([
                ('partner_id', '=', orphan.partner_id.id),
                ('active', '=', True),
            ], limit=1)
            if existing:
                continue

            Decision.create({
                'partner_id': orphan.partner_id.id,
                'sender_email': (orphan.partner_email or '').lower().strip(),
                'decision': 'kept',
                'notes': 'Bulk keep il %s da %s' % (
                    fields.Datetime.now().strftime('%Y-%m-%d'), self.env.user.name),
            })
            count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Tieni',
                'message': '%d contatti confermati validi.' % count,
                'type': 'success',
                'sticky': False,
            },
        }

    @staticmethod
    def _noreply_regex():
        """Pattern per mittenti noreply/automated."""
        import re
        return re.compile(
            r'^(noreply|no-reply|donotreply|mailer-daemon|postmaster|'
            r'info|news|newsletter|automated|notification)@',
            re.IGNORECASE)

    def action_bulk_autoclean_noreply(self):
        """Admin action: ignora tutti gli orfani con email noreply-like."""
        pattern = self._noreply_regex()
        noreply_orphans = self.search([]).filtered(
            lambda o: o.partner_email and pattern.match(o.partner_email))
        if noreply_orphans:
            return noreply_orphans.action_bulk_ignore_sender()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Auto-pulizia',
                'message': 'Nessun mittente noreply@ trovato.',
                'type': 'warning',
                'sticky': False,
            },
        }
