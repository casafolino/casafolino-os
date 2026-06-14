import logging
from datetime import timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailFollowupRule(models.Model):
    _name = 'casafolino.mail.followup.rule'
    _description = 'Auto follow-up rules for stale hot threads'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Trigger
    min_hotness = fields.Integer(default=70)
    no_reply_days = fields.Integer(default=7,
        help="No inbound reply for N days after last outbound")
    min_outbound_messages = fields.Integer(default=1)
    max_thread_age_days = fields.Integer(default=60)

    # Action
    action_type = fields.Selection([
        ('activity', 'Create Activity on Partner'),
        ('lead_activity', 'Create Activity on CRM Lead (if linked)'),
        ('email', 'Send notification email to assigned user'),
    ], default='activity')
    activity_type_id = fields.Many2one('mail.activity.type',
        default=lambda self: self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False))
    activity_summary = fields.Char(default='Follow-up thread caldo')
    activity_note = fields.Text(default='Thread con hotness alta senza reply. Valutare follow-up.')
    activity_user_field = fields.Selection([
        ('thread_user', 'User that last replied in thread'),
        ('partner_user', 'Partner account manager'),
        ('fixed', 'Fixed user'),
    ], default='thread_user')
    activity_user_id = fields.Many2one('res.users', string='Fixed user (if selected)')
    activity_deadline_days = fields.Integer(default=1, string='Deadline in N days from now')

    # Dedup
    skip_if_activity_last_days = fields.Integer(default=3,
        help="Skip thread if activity already created in last N days")

    # Stats
    executions_count = fields.Integer(compute='_compute_stats')
    last_run = fields.Datetime(readonly=True)

    def _compute_stats(self):
        for rule in self:
            rule.executions_count = 0  # placeholder — count from log

    def action_run_now(self):
        """Manual trigger."""
        self.ensure_one()
        count = self._run_rule()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Follow-up Checker',
                'message': f'{count} activity create.',
                'type': 'success',
                'sticky': False,
            },
        }

    def _run_rule(self):
        """Execute one follow-up rule. Returns count of activities created."""
        self.ensure_one()
        threads = self._find_stale_threads()
        created = 0

        for thread in threads:
            if self._has_recent_activity(thread):
                continue
            self._create_followup_action(thread)
            created += 1

        self.sudo().write({'last_run': fields.Datetime.now()})
        return created

    def _find_stale_threads(self):
        """Find threads matching this rule's stale criteria."""
        Thread = self.env['casafolino.mail.thread']
        Intel = self.env['casafolino.partner.intelligence']

        now = fields.Datetime.now()
        cutoff_date = now - timedelta(days=self.no_reply_days)
        min_create = now - timedelta(days=self.max_thread_age_days) if self.max_thread_age_days else False

        domain = [
            ('has_outbound', '=', True),
            ('last_message_date', '<=', cutoff_date),
        ]
        if min_create:
            domain.append(('first_message_date', '>=', min_create))

        threads = Thread.search(domain)

        result = Thread
        for thread in threads:
            # Check outbound count
            outbound_msgs = thread.message_ids.filtered(
                lambda m: m.direction == 'outbound' and not m.is_deleted)
            if len(outbound_msgs) < self.min_outbound_messages:
                continue

            # Check last message is outbound (no inbound reply)
            last_msg = thread.message_ids.filtered(
                lambda m: not m.is_deleted
            ).sorted('email_date', reverse=True)[:1]
            if last_msg and last_msg.direction != 'outbound':
                continue

            # Check partner hotness
            partners = thread.partner_ids
            has_hot_partner = False
            for partner in partners:
                intel = Intel.search([('partner_id', '=', partner.id)], limit=1)
                if intel and intel.hotness_score >= self.min_hotness:
                    has_hot_partner = True
                    break
            if not has_hot_partner:
                continue

            result |= thread

        return result

    def _has_recent_activity(self, thread):
        """Check if an activity was already created for this thread recently."""
        if not self.skip_if_activity_last_days:
            return False
        cutoff = fields.Datetime.now() - timedelta(days=self.skip_if_activity_last_days)
        partners = thread.partner_ids
        if not partners:
            return False
        Activity = self.env['mail.activity']
        count = Activity.search_count([
            ('res_model', '=', 'res.partner'),
            ('res_id', 'in', partners.ids),
            ('create_date', '>=', cutoff),
            ('summary', 'ilike', 'follow-up'),
        ])
        return count > 0

    def _create_followup_action(self, thread):
        """Create activity based on rule config."""
        partner = thread.partner_ids[:1]
        if not partner:
            return

        # Determine user
        user_id = self.env.uid
        if self.activity_user_field == 'thread_user':
            last_out = thread.message_ids.filtered(
                lambda m: m.direction == 'outbound' and not m.is_deleted
            ).sorted('email_date', reverse=True)[:1]
            if last_out and last_out.account_id and last_out.account_id.user_id:
                user_id = last_out.account_id.user_id.id
        elif self.activity_user_field == 'partner_user':
            if partner.user_id:
                user_id = partner.user_id.id
        elif self.activity_user_field == 'fixed' and self.activity_user_id:
            user_id = self.activity_user_id.id

        deadline = fields.Date.context_today(self) + timedelta(days=self.activity_deadline_days)

        # Determine target model/id
        res_model = 'res.partner'
        res_id = partner.id

        if self.action_type == 'lead_activity':
            lead = self.env['crm.lead'].search([
                ('cf_mail_thread_id', '=', thread.id),
                ('active', '=', True),
            ], limit=1)
            if lead:
                res_model = 'crm.lead'
                res_id = lead.id

        activity_type = self.activity_type_id
        if not activity_type:
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        try:
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get_id(res_model),
                'res_id': res_id,
                'activity_type_id': activity_type.id if activity_type else False,
                'summary': self.activity_summary or 'Follow-up thread caldo',
                'note': self.activity_note or '',
                'user_id': user_id,
                'date_deadline': deadline,
            })
        except Exception as e:
            _logger.warning("[followup] Activity create error: %s", e)

    @api.model
    def _cron_followup_check(self):
        """Cron 95: run all active follow-up rules."""
        rules = self.search([('active', '=', True)])
        total = 0
        for rule in rules:
            try:
                total += rule._run_rule()
            except Exception as e:
                _logger.error("[followup] Error in rule '%s': %s", rule.name, e)
        if total:
            _logger.info("[followup] Cron total: %d activities created", total)
