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

    @api.model
    def _cron_send_scheduled(self):
        """Cron ogni 5 min: invia draft programmati con scheduled_send_at <= now."""
        now = fields.Datetime.now()
        drafts = self.sudo().search([
            ('is_scheduled', '=', True),
            ('scheduled_send_at', '<=', now),
        ], order='scheduled_send_at asc', limit=20)

        if not drafts:
            return

        _logger.info("[send later] %d draft programmati da inviare", len(drafts))
        sent = 0
        for draft in drafts:
            try:
                result = draft.action_send()
                if result.get('success'):
                    sent += 1
                    _logger.info("[send later] Draft %s inviato (account %s, user %s)",
                                 draft.id, draft.account_id.name, draft.user_id.name)
                else:
                    _logger.warning("[send later] Draft %s invio fallito: %s",
                                    draft.id, result.get('error', ''))
            except Exception as e:
                _logger.error("[send later] Draft %s errore: %s", draft.id, e)
            self.env.cr.commit()

        _logger.info("[send later] Completato: %d/%d inviati", sent, len(drafts))

    def action_send(self):
        """Invia il draft tramite outbox queue (async SMTP)."""
        self.ensure_one()
        account = self.account_id
        if not account:
            _logger.error('[mail v3] Draft %s: no account', self.id)
            return {'success': False, 'error': 'Account non configurato'}

        try:
            outbox = self.env['casafolino.mail.outbox'].queue_send(
                account_id=account.id,
                to_emails=self.to_emails or '',
                subject=self.subject or '',
                body_html=self.body_html or '',
                cc_emails=self.cc_emails or '',
                bcc_emails=self.bcc_emails or '',
                signature_html=self.signature_id.body_html if self.signature_id else '',
                in_reply_to=self.in_reply_to_message_id.message_id_rfc if self.in_reply_to_message_id else '',
                attachment_ids=self.attachment_ids.ids or None,
                source_message_id=self.in_reply_to_message_id.id if self.in_reply_to_message_id else False,
            )
            _logger.info('[mail v3] Draft %s queued to outbox %s', self.id, outbox.id)
            self.unlink()
            return {'success': True, 'outbox_id': outbox.id}
        except Exception as e:
            _logger.error('[mail v3] Draft %s send failed: %s', self.id, e)
            return {'success': False, 'error': str(e)[:200]}

