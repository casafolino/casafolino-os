import imaplib
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CasafolinoMailAccount(models.Model):
    _name = 'casafolino.mail.account'
    _description = 'Account Email IMAP — Mail Hub'
    _order = 'name'

    name = fields.Char('Nome account', required=True)
    email_address = fields.Char('Indirizzo email', required=True)
    responsible_user_id = fields.Many2one('res.users', string='Responsabile triage',
                                          default=lambda self: self.env.uid)
    imap_host = fields.Char('IMAP Host', default='imap.gmail.com')
    imap_port = fields.Integer('IMAP Port', default=993)
    imap_password = fields.Char('App Password')
    imap_use_ssl = fields.Boolean('SSL', default=True)
    sent_folder = fields.Char('Cartella Sent', help='Auto-detected o manuale. Es. [Gmail]/Posta inviata')
    sync_start_date = fields.Date('Importa dal', default='2025-01-01')
    last_fetch_datetime = fields.Datetime('Ultimo fetch', readonly=True)
    last_fetch_uid = fields.Char('Ultimo UID processato', readonly=True)
    state = fields.Selection([
        ('draft', 'Bozza'),
        ('connected', 'Connesso'),
        ('error', 'Errore'),
    ], string='Stato', default='draft')
    error_message = fields.Text('Errore')
    active = fields.Boolean(default=True)
    fetch_inbox = fields.Boolean('Scarica INBOX', default=True)
    fetch_sent = fields.Boolean('Scarica Sent', default=True)

    # ── Connection helpers ────────────────────────────────────────────

    def _get_imap_connection(self):
        """Apre connessione IMAP SSL a Gmail."""
        self.ensure_one()
        try:
            if self.imap_use_ssl:
                imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                imap = imaplib.IMAP4(self.imap_host, self.imap_port)
            imap.login(self.email_address, self.imap_password)
            return imap
        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})
            raise UserError("Connessione IMAP fallita: %s" % e)

    def action_test_connection(self):
        """Testa la connessione e rileva la cartella Sent."""
        self.ensure_one()
        imap = self._get_imap_connection()

        # Rileva cartella sent
        status, folders = imap.list()
        sent_folder = None
        if status == 'OK':
            for folder in folders:
                decoded = folder.decode() if isinstance(folder, bytes) else folder
                if '\\Sent' in decoded:
                    parts = decoded.split('"')
                    if len(parts) >= 3:
                        sent_folder = parts[-2]
                    break

        imap.logout()

        vals = {'state': 'connected', 'error_message': False}
        if sent_folder:
            vals['sent_folder'] = sent_folder
        self.write(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'OK',
                'message': 'Connessione riuscita. Sent: %s' % (sent_folder or '(non rilevata)'),
                'type': 'success',
            },
        }

    def action_fetch_now(self):
        """Fetch manuale — placeholder per Step 2."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fetch',
                'message': 'Fetch engine non ancora implementato (Step 2).',
                'type': 'warning',
            },
        }
