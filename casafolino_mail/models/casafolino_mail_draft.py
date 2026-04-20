import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailDraft(models.Model):
    _name = 'casafolino.mail.draft'
    _description = 'Bozza email — Mail V3'
    _order = 'write_date desc'

    account_id = fields.Many2one('casafolino.mail.account', string='Account',
                                  required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Utente', required=True,
                               default=lambda self: self.env.uid)
    in_reply_to_message_id = fields.Many2one('casafolino.mail.message',
                                              string='In risposta a',
                                              ondelete='set null')
    to_emails = fields.Text('A')
    cc_emails = fields.Text('CC')
    bcc_emails = fields.Text('BCC')
    subject = fields.Char('Oggetto')
    body_html = fields.Html('Corpo', sanitize=False)
    attachment_ids = fields.Many2many('ir.attachment',
                                      'casafolino_mail_draft_attachment_rel',
                                      'draft_id', 'attachment_id',
                                      string='Allegati')
    signature_id = fields.Many2one('casafolino.mail.signature', string='Firma',
                                    ondelete='set null')
    scheduled_send_at = fields.Datetime('Invio programmato')  # F5
    auto_saved_at = fields.Datetime('Ultimo salvataggio auto')

    def action_autosave(self):
        """Aggiorna timestamp autosave."""
        self.write({'auto_saved_at': fields.Datetime.now()})

    def action_send(self):
        """Invia il draft tramite SMTP dell'account associato."""
        self.ensure_one()
        account = self.account_id
        if not account:
            _logger.error('[mail v3] Draft %s: no account', self.id)
            return {'success': False, 'error': 'Account non configurato'}

        try:
            new_msg = account._smtp_send(self)
            _logger.info('[mail v3] Draft %s sent, message %s', self.id, new_msg.id)
            return {'success': True, 'message_id': new_msg.id}
        except Exception as e:
            _logger.error('[mail v3] Draft %s send failed: %s', self.id, e)
            return {'success': False, 'error': str(e)[:200]}

    @api.model
    def _cron_cleanup_old_drafts(self):
        """Elimina bozze non modificate da oltre 30 giorni."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(days=30)
        old_drafts = self.search([
            ('write_date', '<', cutoff),
        ])
        count = len(old_drafts)
        if old_drafts:
            old_drafts.unlink()
        _logger.info('[mail v3] Cleaned up %d old drafts', count)
