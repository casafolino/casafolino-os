import logging
from datetime import timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailSnooze(models.Model):
    _name = 'casafolino.mail.snooze'
    _description = 'Thread snooze for later reappearance'
    _order = 'wake_at asc'

    thread_id = fields.Many2one('casafolino.mail.thread', required=True,
                                 ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', required=True,
                               default=lambda self: self.env.user)
    snooze_type = fields.Selection([
        ('until_date', 'Fino a data'),
        ('until_reply', 'Fino a risposta'),
        ('if_no_reply_by', 'Se non risponde entro'),
    ], required=True, default='until_date')
    wake_at = fields.Datetime(string='Risveglia il', index=True)
    deadline_days = fields.Integer(string='Giorni deadline', default=3)
    snoozed_at = fields.Datetime(string='Snoozed il', default=fields.Datetime.now)
    active = fields.Boolean(default=True, index=True)
    note = fields.Text(string='Nota privata')

    @api.model
    def _cron_check_snooze(self):
        """Check snooze conditions every 15 minutes and wake threads."""
        now = fields.Datetime.now()
        woken = 0

        # Type 1: until_date — NOW >= wake_at
        date_snoozes = self.search([
            ('active', '=', True),
            ('snooze_type', '=', 'until_date'),
            ('wake_at', '<=', now),
        ])
        for snooze in date_snoozes:
            snooze._wake_thread()
            woken += 1

        # Type 2: until_reply — new inbound message in thread after snooze
        reply_snoozes = self.search([
            ('active', '=', True),
            ('snooze_type', '=', 'until_reply'),
        ])
        for snooze in reply_snoozes:
            new_inbound = self.env['casafolino.mail.message'].search([
                ('thread_id', '=', snooze.thread_id.id),
                ('direction', '=', 'inbound'),
                ('email_date', '>', snooze.snoozed_at),
                ('is_deleted', '=', False),
            ], limit=1)
            if new_inbound:
                snooze._wake_thread()
                woken += 1

        # Type 3: if_no_reply_by — no inbound within deadline days
        noreply_snoozes = self.search([
            ('active', '=', True),
            ('snooze_type', '=', 'if_no_reply_by'),
        ])
        for snooze in noreply_snoozes:
            deadline = snooze.snoozed_at + timedelta(days=snooze.deadline_days)
            if now >= deadline:
                # Check if there was a reply
                new_inbound = self.env['casafolino.mail.message'].search([
                    ('thread_id', '=', snooze.thread_id.id),
                    ('direction', '=', 'inbound'),
                    ('email_date', '>', snooze.snoozed_at),
                    ('is_deleted', '=', False),
                ], limit=1)
                if not new_inbound:
                    snooze._wake_thread()
                    woken += 1
                else:
                    # Got a reply, just deactivate silently
                    snooze.write({'active': False})

        if woken:
            _logger.info('[mail v3] Snooze cron: woke %d threads', woken)

    def _wake_thread(self):
        """Wake a snoozed thread."""
        self.ensure_one()
        self.thread_id.write({'is_snoozed': False})
        self.write({'active': False})
        _logger.info('[mail v3] Woke thread %s (snooze %s, type=%s)',
                     self.thread_id.id, self.id, self.snooze_type)
