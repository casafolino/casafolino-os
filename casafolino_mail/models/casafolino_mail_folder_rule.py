import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CasafolinoMailFolderRule(models.Model):
    _name = 'casafolino.mail.folder.rule'
    _description = 'Regola smistamento cartella'
    _order = 'sequence, id'

    name = fields.Char('Nome regola', required=True)
    folder_id = fields.Many2one(
        'casafolino.mail.folder', string='Cartella destinazione',
        required=True, ondelete='cascade')
    account_id = fields.Many2one(
        'casafolino.mail.account', string='Account',
        related='folder_id.account_id', store=True, index=True)
    active = fields.Boolean('Attiva', default=True)
    sequence = fields.Integer('Priorita', default=10)

    # Conditions (AND logic)
    sender_email = fields.Char('Email mittente (esatto)')
    sender_domain = fields.Char('Dominio mittente')
    subject_contains = fields.Char('Oggetto contiene')
    has_attachments = fields.Selection([
        ('any', 'Qualsiasi'),
        ('yes', 'Si'),
        ('no', 'No'),
    ], string='Allegati', default='any')

    # Actions
    mark_as_read = fields.Boolean('Segna come letta', default=False)

    @api.constrains('sender_email', 'sender_domain', 'subject_contains')
    def _check_at_least_one_condition(self):
        for rule in self:
            if not rule.sender_email and not rule.sender_domain and not rule.subject_contains:
                raise ValidationError(
                    "Almeno una condizione tra Email mittente, Dominio mittente "
                    "e Oggetto contiene deve essere valorizzata.")

    def _matches_message(self, message_data):
        """Check if a message matches this rule.

        Args:
            message_data: dict with keys: sender_email, subject, has_attachments
                          OR a casafolino.mail.message recordset (single).
        Returns:
            True if all non-empty conditions match.
        """
        self.ensure_one()

        if isinstance(message_data, dict):
            sender = (message_data.get('sender_email') or '').lower().strip()
            subject = message_data.get('subject') or ''
            has_att = message_data.get('has_attachments', False)
        else:
            sender = (message_data.sender_email or '').lower().strip()
            subject = message_data.subject or ''
            has_att = bool(message_data.attachment_ids) if message_data.body_downloaded else False

        # sender_email: exact match
        if self.sender_email:
            if sender != self.sender_email.lower().strip():
                return False

        # sender_domain: domain match
        if self.sender_domain:
            domain = self.sender_domain.lower().strip()
            sender_domain = sender.split('@')[-1] if '@' in sender else ''
            if sender_domain != domain:
                return False

        # subject_contains: case-insensitive substring
        if self.subject_contains:
            if self.subject_contains.lower() not in subject.lower():
                return False

        # has_attachments
        if self.has_attachments == 'yes' and not has_att:
            return False
        if self.has_attachments == 'no' and has_att:
            return False

        return True

    def action_test_rule(self):
        """Test rule against last 50 messages of the account. Returns count."""
        self.ensure_one()
        messages = self.env['casafolino.mail.message'].search([
            ('account_id', '=', self.account_id.id),
            ('is_deleted', '=', False),
        ], limit=50, order='email_date desc')

        matched = sum(1 for m in messages if self._matches_message(m))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test regola',
                'message': 'Regola "%s": %d messaggi su %d corrispondono.' % (
                    self.name, matched, len(messages)),
                'type': 'info',
                'sticky': False,
            },
        }
