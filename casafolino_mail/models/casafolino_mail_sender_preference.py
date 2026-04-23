import logging
import uuid

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CasafolinoMailSenderPreference(models.Model):
    _name = 'casafolino.mail.sender_preference'
    _description = 'Preferenza mittente (keep/dismiss/pending)'
    _order = 'decided_at desc'

    email = fields.Char('Email mittente', required=True, index=True)
    account_id = fields.Many2one(
        'casafolino.mail.account', string='Account',
        required=True, ondelete='cascade', index=True)
    status = fields.Selection([
        ('pending', 'Da decidere'),
        ('kept', 'Tenuto'),
        ('dismissed', 'Dismesso'),
    ], string='Stato', default='pending', required=True, index=True)
    decided_at = fields.Datetime('Data decisione')
    decided_by_id = fields.Many2one('res.users', string='Deciso da')
    dismissed_email_count = fields.Integer('Email cancellate', default=0)
    last_dismissed_at = fields.Datetime('Ultima dismissione')
    undo_token = fields.Char('Token undo', index=True)

    _sql_constraints = [
        ('email_account_uniq', 'UNIQUE(email, account_id)',
         'Preference already exists for this sender/account pair.'),
    ]

    def action_keep(self):
        """Mark sender as kept."""
        self.ensure_one()
        self.write({
            'status': 'kept',
            'decided_at': fields.Datetime.now(),
            'decided_by_id': self.env.uid,
            'undo_token': False,
        })

    def action_dismiss(self):
        """Mark sender as dismissed, schedule cascade delete via one-shot cron."""
        self.ensure_one()
        token = str(uuid.uuid4())
        self.write({
            'status': 'dismissed',
            'decided_at': fields.Datetime.now(),
            'decided_by_id': self.env.uid,
            'last_dismissed_at': fields.Datetime.now(),
            'undo_token': token,
        })
        # Schedule cascade delete with 12s delay (undo window = 10s + buffer)
        from datetime import timedelta
        run_at = fields.Datetime.now() + timedelta(seconds=12)
        model_id = self.env['ir.model']._get_id(self._name)
        self.env['ir.cron'].sudo().create({
            'name': 'Dismiss cascade: %s' % self.email,
            'model_id': model_id,
            'state': 'code',
            'code': "model.browse(%d)._cascade_delete_emails()" % self.id,
            'active': True,
            'nextcall': run_at,
        })
        return token

    def action_cancel_dismiss(self, token):
        """Cancel dismissal if undo_token matches. Returns True on success."""
        self.ensure_one()
        if self.undo_token and self.undo_token == token:
            # Cancel scheduled cron
            cron = self.env['ir.cron'].sudo().search([
                ('name', '=', 'Dismiss cascade: %s' % self.email),
                ('active', '=', True),
            ], limit=1, order='id desc')
            if cron:
                cron.unlink()
            self.write({
                'status': 'pending',
                'undo_token': False,
                'decided_at': False,
                'decided_by_id': False,
            })
            return True
        return False

    def action_restore(self, recover_days=0):
        """Restore dismissed sender to kept."""
        self.ensure_one()
        self.write({
            'status': 'kept',
            'decided_at': fields.Datetime.now(),
            'decided_by_id': self.env.uid,
            'undo_token': False,
        })
        if recover_days and recover_days > 0:
            self._trigger_imap_recovery(recover_days)

    def _cascade_delete_emails(self):
        """Delete all emails from this sender in DB. Fast SQL."""
        self.ensure_one()
        if self.status != 'dismissed':
            _logger.info("Cascade skip: %s no longer dismissed", self.email)
            return
        cr = self.env.cr
        cr.execute("""
            DELETE FROM casafolino_mail_message
            WHERE sender_email = %s AND account_id = %s
            RETURNING id
        """, (self.email, self.account_id.id))
        deleted_ids = cr.fetchall()
        count = len(deleted_ids)
        self.write({'dismissed_email_count': count})
        _logger.info("Cascade delete: %d emails from %s", count, self.email)
        # Auto-disable this one-shot cron after execution
        cron = self.env['ir.cron'].sudo().search([
            ('name', '=', 'Dismiss cascade: %s' % self.email),
            ('active', '=', True),
        ], limit=1)
        if cron:
            cron.write({'active': False})

    def _trigger_imap_recovery(self, recover_days):
        """Trigger IMAP recovery for sender emails in the last N days."""
        _logger.info(
            "IMAP recovery requested: %s, %d days",
            self.email, recover_days)
        # Actual IMAP recovery would require connecting to IMAP server
        # and searching for emails FROM this sender SINCE (now - recover_days).
        # For now, log intent — full IMAP recovery is a future enhancement.
