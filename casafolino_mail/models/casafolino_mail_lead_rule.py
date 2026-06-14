import logging
from datetime import timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailLeadRule(models.Model):
    _name = 'casafolino.mail.lead.rule'
    _description = 'Rules for auto-linking email conversations to CRM leads'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Trigger conditions (AND)
    min_outbound_messages = fields.Integer(default=3,
        help="Minimum outbound messages in thread")
    min_thread_age_days = fields.Integer(default=0,
        help="Thread must be at least N days old")
    max_thread_age_days = fields.Integer(default=30,
        help="Thread must not be older than N days")
    min_hotness = fields.Integer(default=40,
        help="Partner hotness must be >= this")
    require_subject_keywords = fields.Char(
        help="Comma-separated keywords (any match) in subject or body. Leave empty for no filter.")
    exclude_partners_with_open_lead = fields.Boolean(default=True)
    exclude_internal_domains = fields.Char(
        default='casafolino.com,casafolino.it',
        help="Comma-separated domains to exclude from auto-link (internal emails).")

    # Output config
    sales_team_id = fields.Many2one('crm.team')
    user_id = fields.Many2one('res.users', string='Assigned to')
    stage_id = fields.Many2one('crm.stage')
    tag_ids = fields.Many2many('crm.tag', 'casafolino_mail_lead_rule_tag_rel',
                                'rule_id', 'tag_id')
    estimated_revenue = fields.Float(default=0.0)

    # Stats
    lead_created_count = fields.Integer(compute='_compute_stats')

    def _compute_stats(self):
        Lead = self.env['crm.lead']
        for rule in self:
            rule.lead_created_count = Lead.search_count([
                ('cf_mail_lead_rule_id', '=', rule.id),
            ])

    def action_run_now(self):
        """Manual trigger — run this rule immediately."""
        self.ensure_one()
        count = self._run_rule()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Auto-link Lead',
                'message': f'{count} lead creati.',
                'type': 'success',
                'sticky': False,
            },
        }

    def _run_rule(self):
        """Execute one rule: find matching threads, create leads. Returns count."""
        self.ensure_one()
        Thread = self.env['casafolino.mail.thread']
        Lead = self.env['crm.lead']
        Intel = self.env['casafolino.partner.intelligence']
        Feedback = self.env['casafolino.partner.intelligence.feedback']

        now = fields.Datetime.now()
        min_date = now - timedelta(days=self.max_thread_age_days) if self.max_thread_age_days else False
        max_date = now - timedelta(days=self.min_thread_age_days) if self.min_thread_age_days else False

        # Base domain: threads with outbound messages
        domain = [('has_outbound', '=', True)]
        if min_date:
            domain.append(('first_message_date', '>=', min_date))
        if max_date:
            domain.append(('first_message_date', '<=', max_date))

        threads = Thread.search(domain)

        keywords = []
        if self.require_subject_keywords:
            keywords = [k.strip().lower() for k in self.require_subject_keywords.split(',') if k.strip()]

        internal_domains = set()
        if self.exclude_internal_domains:
            internal_domains = {d.strip().lower() for d in self.exclude_internal_domains.split(',') if d.strip()}

        # F6.5: exclude partners with ignored/discarded decisions or policies
        excluded_partner_ids = set(self._get_excluded_partner_ids())
        if excluded_partner_ids:
            _logger.info('[cron 94] Rule %s: %d partners excluded (ignored/discarded)',
                         self.name, len(excluded_partner_ids))

        created = 0
        source = self._get_or_create_source()

        for thread in threads:
            # Check outbound count
            outbound_count = len(thread.message_ids.filtered(
                lambda m: m.direction == 'outbound' and not m.is_deleted))
            if outbound_count < self.min_outbound_messages:
                continue

            # Get partner(s) from thread
            partners = thread.partner_ids
            if not partners:
                continue

            for partner in partners:
                # F6.5: skip ignored/discarded partners
                if partner.id in excluded_partner_ids:
                    continue

                # Skip internal domains (e.g. @casafolino.com)
                if internal_domains and partner.email:
                    partner_domain = (partner.email or '').split('@')[-1].lower().strip()
                    if partner_domain in internal_domains:
                        continue

                # Check hotness
                intel = Intel.search([('partner_id', '=', partner.id)], limit=1)
                hotness = intel.hotness_score if intel else 0
                if hotness < self.min_hotness:
                    continue

                # Check keyword match
                if keywords:
                    subject_lower = (thread.subject or '').lower()
                    if not any(kw in subject_lower for kw in keywords):
                        continue

                # Dedup: skip if partner already has open lead
                if self.exclude_partners_with_open_lead:
                    existing = Lead.search_count([
                        ('partner_id', '=', partner.id),
                        ('stage_id.is_won', '=', False),
                        ('active', '=', True),
                    ])
                    if existing:
                        continue

                # Also skip if this thread already generated a lead
                existing_thread_lead = Lead.search_count([
                    ('cf_mail_thread_id', '=', thread.id),
                ])
                if existing_thread_lead:
                    continue

                # Create lead
                lead_name = "[Auto] " + (thread.subject or 'Conversazione')[:60]
                description = self._build_lead_description(thread)

                lead_vals = {
                    'name': lead_name,
                    'partner_id': partner.id,
                    'description': description,
                    'source_id': source.id,
                    'expected_revenue': self.estimated_revenue,
                    'cf_mail_thread_id': thread.id,
                    'cf_auto_created': True,
                    'cf_mail_lead_rule_id': self.id,
                }
                if self.sales_team_id:
                    lead_vals['team_id'] = self.sales_team_id.id
                if self.user_id:
                    lead_vals['user_id'] = self.user_id.id
                if self.stage_id:
                    lead_vals['stage_id'] = self.stage_id.id
                if self.tag_ids:
                    lead_vals['tag_ids'] = [(6, 0, self.tag_ids.ids)]

                Lead.create(lead_vals)
                created += 1

                # Log feedback
                try:
                    Feedback.create({
                        'partner_id': partner.id,
                        'user_id': self.env.uid,
                        'action_type': 'auto_lead_created',
                        'hotness_at_action': hotness,
                        'context_json': f'{{"rule_id": {self.id}, "thread_id": {thread.id}}}',
                    })
                except Exception as e:
                    _logger.warning("[lead rule] Feedback log error: %s", e)

        _logger.info("[lead rule] Rule '%s' created %d leads", self.name, created)
        return created

    def _build_lead_description(self, thread):
        """Build HTML description from last 3 messages."""
        msgs = thread.message_ids.filtered(
            lambda m: not m.is_deleted
        ).sorted('email_date', reverse=True)[:3]

        parts = []
        for msg in msgs:
            direction = '→' if msg.direction == 'outbound' else '←'
            date_str = msg.email_date.strftime('%d/%m/%Y') if msg.email_date else ''
            sender = msg.sender_name or msg.sender_email or ''
            snippet = (msg.body_text or msg.subject or '')[:200]
            parts.append(f"<p><b>{direction} {sender}</b> ({date_str})<br/>{snippet}</p>")

        return ''.join(parts) or '<p>Thread email attivo</p>'

    def _get_or_create_source(self):
        """Get or create utm.source 'Mail V3 Auto-link'."""
        Source = self.env['utm.source']
        source = Source.search([('name', '=', 'Mail V3 Auto-link')], limit=1)
        if not source:
            source = Source.create({'name': 'Mail V3 Auto-link'})
        return source

    def _get_excluded_partner_ids(self):
        """Partner esclusi da auto-link: hanno decisione ignore o policy discard."""
        Decision = self.env['casafolino.mail.sender.decision'].sudo()
        ignored_decisions = Decision.search([
            ('active', '=', True),
            ('decision', 'in', ['ignored_sender', 'ignored_domain']),
        ])
        ignored_ids = ignored_decisions.mapped('partner_id').ids

        Policy = self.env['casafolino.mail.sender_policy'].sudo()
        discard_policies = Policy.search([
            ('active', '=', True),
            ('action', '=', 'auto_discard'),
        ])

        discard_ids = []
        if discard_policies:
            Partner = self.env['res.partner'].sudo()
            for policy in discard_policies:
                if policy.pattern_type == 'domain':
                    val = policy.pattern_value.replace('*', '%')
                    partners = Partner.search([('email', '=ilike', val)])
                    discard_ids.extend(partners.ids)

        return list(set(ignored_ids + discard_ids))

    @api.model
    def _cron_auto_link_leads(self):
        """Cron 94: run all active lead rules."""
        rules = self.search([('active', '=', True)])
        total = 0
        for rule in rules:
            try:
                total += rule._run_rule()
            except Exception as e:
                _logger.error("[lead rule] Error in rule '%s': %s", rule.name, e)
        if total:
            _logger.info("[lead rule] Cron total: %d leads created", total)
