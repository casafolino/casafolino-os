import logging

from odoo import models, fields

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

    def _wake_thread(self):
        """Wake a snoozed thread."""
        self.ensure_one()
        self.thread_id.write({'is_snoozed': False})
        self.write({'active': False})
        _logger.info('[mail v3] Woke thread %s (snooze %s, type=%s)',
                     self.thread_id.id, self.id, self.snooze_type)
