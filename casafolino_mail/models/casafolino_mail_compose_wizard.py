import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailComposeWizard(models.TransientModel):
    _name = 'casafolino.mail.compose.wizard'
    _description = 'Composizione email — Mail V3'

    account_id = fields.Many2one('casafolino.mail.account', string='Account',
                                  required=True)
    to_emails = fields.Char('A', required=True)
    cc_emails = fields.Char('CC')
    bcc_emails = fields.Char('BCC')
    subject = fields.Char('Oggetto')
    body_html = fields.Html('Corpo', sanitize=False)
    attachment_ids = fields.Many2many('ir.attachment',
                                      'casafolino_mail_compose_wiz_att_rel',
                                      'wizard_id', 'attachment_id',
                                      string='Allegati')
    in_reply_to_message_id = fields.Many2one('casafolino.mail.message',
                                              string='In risposta a',
                                              ondelete='set null')

    def action_send(self):
        """Invia via outbox queue."""
        self.ensure_one()
        account = self.account_id
        if not account:
            return {'type': 'ir.actions.act_window_close'}

        # Signature
        sig = self.env['casafolino.mail.signature'].search([
            ('account_id', '=', account.id),
            ('is_default', '=', True),
        ], limit=1)
        sig_html = sig.body_html if sig else ''

        # In-Reply-To header
        in_reply_to = ''
        references = ''
        if self.in_reply_to_message_id:
            in_reply_to = self.in_reply_to_message_id.message_id_rfc or ''
            references = in_reply_to

        self.env['casafolino.mail.outbox'].queue_send(
            account_id=account.id,
            to_emails=self.to_emails or '',
            subject=self.subject or '',
            body_html=self.body_html or '',
            cc_emails=self.cc_emails or '',
            bcc_emails=self.bcc_emails or '',
            signature_html=sig_html,
            in_reply_to=in_reply_to,
            references=references,
            attachment_ids=self.attachment_ids.ids if self.attachment_ids else None,
            source_message_id=self.in_reply_to_message_id.id if self.in_reply_to_message_id else False,
        )

        _logger.info('[mail v3] Compose wizard queued email to %s', self.to_emails)
        return {'type': 'ir.actions.act_window_close'}

    def action_save_draft(self):
        """Salva come bozza."""
        self.ensure_one()
        draft_vals = {
            'account_id': self.account_id.id,
            'user_id': self.env.uid,
            'to_emails': self.to_emails or '',
            'cc_emails': self.cc_emails or '',
            'bcc_emails': self.bcc_emails or '',
            'subject': self.subject or '',
            'body_html': self.body_html or '',
            'in_reply_to_message_id': self.in_reply_to_message_id.id if self.in_reply_to_message_id else False,
        }
        if self.attachment_ids:
            draft_vals['attachment_ids'] = [(6, 0, self.attachment_ids.ids)]

        self.env['casafolino.mail.draft'].create(draft_vals)
        _logger.info('[mail v3] Draft saved for %s', self.to_emails)
        return {'type': 'ir.actions.act_window_close'}
