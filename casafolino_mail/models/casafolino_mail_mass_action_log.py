import json
import logging
import uuid

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailMassActionLog(models.Model):
    _name = 'casafolino.mail.mass.action.log'
    _description = 'Mass Action Undo Log'
    _order = 'created_at desc'

    token = fields.Char('Token', required=True, index=True, default=lambda self: str(uuid.uuid4()))
    action_type = fields.Selection([
        ('move', 'Spostamento'),
        ('archive', 'Archiviazione'),
        ('trash', 'Cestinamento'),
        ('mark_read', 'Segna come letto'),
        ('dismiss', 'Dismetti mittenti'),
    ], string='Tipo azione', required=True)
    thread_ids = fields.Text('Thread IDs (JSON)', required=True)
    previous_state = fields.Text('Stato precedente (JSON)')
    user_id = fields.Many2one('res.users', string='Utente', required=True,
                              default=lambda self: self.env.uid)
    created_at = fields.Datetime('Creato il', default=fields.Datetime.now, required=True)
    expires_at = fields.Datetime('Scade il', required=True)

    @api.model
    def create_log(self, action_type, thread_ids, previous_state):
        """Create an undo log entry with 1h expiry. Returns token."""
        from datetime import timedelta
        now = fields.Datetime.now()
        log = self.create({
            'action_type': action_type,
            'thread_ids': json.dumps(thread_ids),
            'previous_state': json.dumps(previous_state),
            'expires_at': now + timedelta(hours=1),
        })
        return log.token

    def get_previous_state(self):
        """Parse and return the previous_state JSON."""
        self.ensure_one()
        try:
            return json.loads(self.previous_state or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_thread_ids(self):
        """Parse and return the thread_ids JSON list."""
        self.ensure_one()
        try:
            return json.loads(self.thread_ids or '[]')
        except (json.JSONDecodeError, TypeError):
            return []

    @api.model
    def _cron_cleanup_expired_logs(self):
        """Delete expired mass action logs. Runs every 30 min."""
        expired = self.search([('expires_at', '<', fields.Datetime.now())])
        count = len(expired)
        if count:
            expired.unlink()
            _logger.info("Cleanup mass action logs: %d expired entries deleted", count)
