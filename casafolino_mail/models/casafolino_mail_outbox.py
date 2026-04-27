import json
import logging
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailOutbox(models.Model):
    _name = 'casafolino.mail.outbox'
    _description = 'Async SMTP Queue'
    _order = 'priority desc, create_date asc'

    account_id = fields.Many2one('casafolino.mail.account', string='Account',
                                  required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Mittente',
                               default=lambda self: self.env.uid)
    to_emails = fields.Text('Destinatari', required=True)
    cc_emails = fields.Text('CC')
    bcc_emails = fields.Text('BCC')
    subject = fields.Char('Oggetto')
    body_html = fields.Html('Body HTML', sanitize=False)
    signature_html = fields.Html('Firma', sanitize=False)
    in_reply_to = fields.Char('In-Reply-To')
    references = fields.Char('References')
    attachment_ids = fields.Many2many('ir.attachment',
        'casafolino_mail_outbox_attachment_rel',
        'outbox_id', 'attachment_id', string='Allegati')
    priority = fields.Selection([
        ('0', 'Normale'), ('1', 'Alta'),
    ], string='Priorita', default='0')
    state = fields.Selection([
        ('queued', 'In coda'),
        ('undoable', 'Annullabile'),
        ('sending', 'Invio in corso'),
        ('sent', 'Inviato'),
        ('error', 'Errore'),
    ], string='Stato', default='queued', index=True)
    undo_until = fields.Datetime('Annullabile fino a')
    error_message = fields.Text('Errore')
    retry_count = fields.Integer('Tentativi', default=0)
    max_retries = fields.Integer('Max tentativi', default=3)
    sent_at = fields.Datetime('Inviato il')
    message_id_rfc = fields.Char('Message-ID generato')
    source_message_id = fields.Many2one('casafolino.mail.message',
        string='Messaggio originale', ondelete='set null',
        help='Se risposta, link al messaggio originale')

    @api.model
    def queue_send(self, account_id, to_emails, subject, body_html,
                   cc_emails='', bcc_emails='', signature_html='',
                   in_reply_to='', references='', attachment_ids=None,
                   priority='0', source_message_id=False):
        """Queue an email for async sending. Returns outbox record."""
        vals = {
            'account_id': account_id,
            'to_emails': to_emails,
            'cc_emails': cc_emails or '',
            'bcc_emails': bcc_emails or '',
            'subject': subject or '',
            'body_html': body_html or '',
            'signature_html': signature_html or '',
            'in_reply_to': in_reply_to or '',
            'references': references or '',
            'priority': priority,
            'state': 'queued',
            'source_message_id': source_message_id,
        }
        if attachment_ids:
            vals['attachment_ids'] = [(6, 0, attachment_ids)]

        rec = self.create(vals)
        _logger.info("[outbox] Queued email to %s (id=%s)", to_emails, rec.id)
        return rec

    # ── SMTP Send ────────────────────────────────────────────────────

    def _send_smtp(self):
        """Send this outbox item via SMTP. Updates state."""
        self.ensure_one()
        account = self.account_id

        if not account or account.state != 'connected':
            self.write({'state': 'error', 'error_message': 'Account non connesso'})
            return False

        self.write({'state': 'sending'})

        try:
            # Build MIME message
            msg = MIMEMultipart('mixed')
            msg['From'] = account.email_address
            msg['To'] = self.to_emails
            if self.cc_emails:
                msg['Cc'] = self.cc_emails
            msg['Subject'] = self.subject or ''

            if self.in_reply_to:
                msg['In-Reply-To'] = self.in_reply_to
            if self.references:
                msg['References'] = self.references

            # Generate Message-ID
            import uuid
            message_id = '<%s@casafolino.com>' % uuid.uuid4().hex[:16]
            msg['Message-ID'] = message_id

            # Body with signature
            full_body = self.body_html or ''
            if self.signature_html:
                full_body += '<br/><br/>--<br/>' + self.signature_html
            msg.attach(MIMEText(full_body, 'html', 'utf-8'))

            # Attachments
            for att in self.attachment_ids:
                part = MIMEApplication(att.raw or b'', Name=att.name)
                part['Content-Disposition'] = 'attachment; filename="%s"' % att.name
                msg.attach(part)

            # Collect all recipients
            all_to = [e.strip() for e in (self.to_emails or '').split(',') if e.strip()]
            all_cc = [e.strip() for e in (self.cc_emails or '').split(',') if e.strip()]
            all_bcc = [e.strip() for e in (self.bcc_emails or '').split(',') if e.strip()]
            recipients = all_to + all_cc + all_bcc

            if not recipients:
                self.write({'state': 'error', 'error_message': 'Nessun destinatario'})
                return False

            # Send via SMTP
            context = ssl.create_default_context()
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls(context=context)
                server.login(account.email_address, account.imap_password)
                server.sendmail(account.email_address, recipients, msg.as_string())

            # IMAP APPEND to Sent folder
            self._imap_append_sent(account, msg)

            # Create casafolino.mail.message record for outbound tracking
            self._create_outbound_message(account, message_id)

            self.write({
                'state': 'sent',
                'sent_at': fields.Datetime.now(),
                'message_id_rfc': message_id,
                'error_message': False,
            })
            _logger.info("[outbox] Sent id=%s to %s", self.id, self.to_emails)
            return True

        except Exception as e:
            retry = self.retry_count + 1
            state = 'error' if retry >= self.max_retries else 'queued'
            self.write({
                'state': state,
                'retry_count': retry,
                'error_message': str(e)[:500],
            })
            _logger.error("[outbox] Send error id=%s (attempt %d): %s",
                          self.id, retry, e)
            return False

    def _imap_append_sent(self, account, mime_msg):
        """Append sent email to IMAP Sent folder."""
        if not account.sent_folder:
            return
        try:
            imap = account._get_imap_connection()
            import time
            imap_time = time.strftime('%d-%b-%Y %H:%M:%S +0000')
            imap.append(
                '"%s"' % account.sent_folder,
                '\\Seen',
                imap_time.encode(),
                mime_msg.as_bytes(),
            )
            imap.logout()
        except Exception as e:
            _logger.warning("[outbox] IMAP append error: %s", e)

    def _create_outbound_message(self, account, message_id):
        """Create casafolino.mail.message record for the sent email."""
        try:
            self.env['casafolino.mail.message'].create({
                'account_id': account.id,
                'message_id_rfc': message_id,
                'direction': 'outbound',
                'sender_email': account.email_address,
                'sender_name': account.name,
                'recipient_emails': self.to_emails,
                'cc_emails': self.cc_emails or '',
                'subject': self.subject,
                'email_date': fields.Datetime.now(),
                'body_html': self.body_html,
                'body_downloaded': True,
                'state': 'keep',
                'fetch_state': 'done',
                'is_read': True,
                'imap_flags_synced': True,
                'partner_id': self._find_partner_for_recipients(),
                'match_type': 'exact' if self._find_partner_for_recipients() else 'none',
            })
        except Exception as e:
            _logger.warning("[outbox] Create outbound msg error: %s", e)

    def _find_partner_for_recipients(self):
        """Find partner matching first To recipient."""
        if not self.to_emails:
            return False
        first_to = self.to_emails.split(',')[0].strip().lower()
        if not first_to:
            return False
        partner = self.env['res.partner'].search(
            [('email', '=ilike', first_to)], limit=1)
        return partner.id if partner else False

    # ── Cron: process queue ──────────────────────────────────────────

    @api.model
    def _cron_process_outbox(self):
        """Process queued emails. Runs every 2 minutes."""
        now = fields.Datetime.now()

        # Transition undoable → queued when undo window expires
        expired_undo = self.search([
            ('state', '=', 'undoable'),
            ('undo_until', '<=', now),
        ])
        if expired_undo:
            expired_undo.write({'state': 'queued'})

        items = self.search([
            ('state', '=', 'queued'),
        ], order='priority desc, create_date asc', limit=20)

        sent = 0
        errors = 0
        for item in items:
            try:
                if item._send_smtp():
                    sent += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                _logger.error("[outbox] Cron error id=%s: %s", item.id, e)
            self.env.cr.commit()

        if sent or errors:
            _logger.info("[outbox] Cron: %d sent, %d errors", sent, errors)

