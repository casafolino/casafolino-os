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
    scheduled_send_at = fields.Datetime('Invio programmato')
    is_scheduled = fields.Boolean('Programmato', default=False, index=True)
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
    def _cron_scheduled_send(self):
        """Send scheduled drafts when their time arrives. Runs every minute."""
        now = fields.Datetime.now()
        drafts = self.search([
            ('is_scheduled', '=', True),
            ('scheduled_send_at', '<=', now),
        ])
        sent = 0
        for draft in drafts:
            try:
                # Convert to outbox
                outbox = self.env['casafolino.mail.outbox'].queue_send(
                    account_id=draft.account_id.id,
                    to_emails=draft.to_emails or '',
                    subject=draft.subject or '',
                    body_html=draft.body_html or '',
                    cc_emails=draft.cc_emails or '',
                    bcc_emails=draft.bcc_emails or '',
                    signature_html=draft.signature_id.body_html if draft.signature_id else '',
                    in_reply_to=draft.in_reply_to_message_id.message_id_rfc if draft.in_reply_to_message_id else '',
                    attachment_ids=draft.attachment_ids.ids or None,
                    source_message_id=draft.in_reply_to_message_id.id if draft.in_reply_to_message_id else False,
                )
                draft.write({'is_scheduled': False})
                sent += 1
            except Exception as e:
                _logger.error('[mail v3] Scheduled send error draft %s: %s', draft.id, e)
            self.env.cr.commit()
        if sent:
            _logger.info('[mail v3] Scheduled send cron: dispatched %d drafts', sent)

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
