import logging
from datetime import timedelta

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
    scheduled_send_at = fields.Datetime('Programma invio')
    template_id = fields.Many2one('casafolino.mail.template', string='Template')

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Apply template: render variables and prefill subject + body."""
        if not self.template_id:
            return
        # Find partner from in_reply_to or to_emails
        partner_id = False
        if self.in_reply_to_message_id and self.in_reply_to_message_id.partner_id:
            partner_id = self.in_reply_to_message_id.partner_id.id
        elif self.to_emails:
            first_email = self.to_emails.split(',')[0].strip().lower()
            partner = self.env['res.partner'].search([('email', '=ilike', first_email)], limit=1)
            partner_id = partner.id if partner else False

        thread_id = False
        if self.in_reply_to_message_id and self.in_reply_to_message_id.thread_id:
            thread_id = self.in_reply_to_message_id.thread_id.id

        if partner_id:
            Template = self.env['casafolino.mail.template']
            rendered = Template.render_template(self.template_id.id, partner_id, thread_id)
            self.subject = rendered.get('subject', '')
            self.body_html = rendered.get('body_html', '')
        else:
            self.subject = self.template_id.subject
            self.body_html = self.template_id.body_html

    def _get_sig_and_headers(self):
        """Get signature HTML and reply headers."""
        sig = self.env['casafolino.mail.signature'].search([
            ('account_id', '=', self.account_id.id),
            ('is_default', '=', True),
        ], limit=1)
        sig_html = sig.body_html if sig else ''
        in_reply_to = ''
        references = ''
        if self.in_reply_to_message_id:
            in_reply_to = self.in_reply_to_message_id.message_id_rfc or ''
            references = in_reply_to
        return sig_html, in_reply_to, references

    def action_send(self):
        """Invia via outbox queue con 10s undo window."""
        self.ensure_one()
        account = self.account_id
        if not account:
            return {'type': 'ir.actions.act_window_close'}

        sig_html, in_reply_to, references = self._get_sig_and_headers()

        now = fields.Datetime.now()
        undo_seconds = self.env.user.mv3_undo_send_seconds or 0

        outbox = self.env['casafolino.mail.outbox'].queue_send(
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
        if undo_seconds > 0:
            undo_until = now + timedelta(seconds=undo_seconds)
            outbox.write({'state': 'undoable', 'undo_until': undo_until})
        else:
            outbox.write({'state': 'queued'})

        _logger.info('[mail v3] Compose wizard queued email to %s (undoable)', self.to_emails)
        return {'type': 'ir.actions.act_window_close'}

    def action_schedule(self):
        """Programma invio a data specificata."""
        self.ensure_one()
        if not self.scheduled_send_at:
            return {'type': 'ir.actions.act_window_close'}

        sig_html, _, _ = self._get_sig_and_headers()

        draft_vals = {
            'account_id': self.account_id.id,
            'user_id': self.env.uid,
            'to_emails': self.to_emails or '',
            'cc_emails': self.cc_emails or '',
            'bcc_emails': self.bcc_emails or '',
            'subject': self.subject or '',
            'body_html': self.body_html or '',
            'in_reply_to_message_id': self.in_reply_to_message_id.id if self.in_reply_to_message_id else False,
            'scheduled_send_at': self.scheduled_send_at,
            'is_scheduled': True,
        }
        if self.attachment_ids:
            draft_vals['attachment_ids'] = [(6, 0, self.attachment_ids.ids)]

        self.env['casafolino.mail.draft'].create(draft_vals)
        _logger.info('[mail v3] Scheduled send for %s at %s', self.to_emails, self.scheduled_send_at)
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
