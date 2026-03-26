# -*- coding: utf-8 -*-
import imaplib
import email
import email.header
import email.utils
import logging
import base64
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

IMAP_GMAIL = "imap.gmail.com"
IMAP_PORT = 993


class CfMailAccount(models.Model):
    _name = "cf.mail.account"
    _description = "Account Email CasaFolino"
    _order = "sequence asc, id asc"
    _rec_name = "display_name_custom"

    # ── IDENTITA ──
    display_name_custom = fields.Char(string="Nome Account", required=True,
        help="Es: Antonio, Export, Info CasaFolino")
    email_address = fields.Char(string="Indirizzo Email", required=True)
    account_type = fields.Selection([
        ("personal", "Personale"),
        ("shared", "Condiviso Team"),
    ], string="Tipo", default="personal", required=True)

    # ── AUTENTICAZIONE — riusa fetchmail_server di Odoo ──
    fetchmail_server_id = fields.Many2one(
        "fetchmail.server",
        string="Server IMAP Odoo",
        help="Collega al server IMAP gia configurato in Odoo con OAuth2 Gmail",
        ondelete="set null",
    )
    outgoing_mail_server_id = fields.Many2one(
        "ir.mail_server",
        string="Server SMTP Odoo",
        help="Collega al server SMTP gia configurato in Odoo",
        ondelete="set null",
    )

    # ── PERMESSI ──
    owner_id = fields.Many2one("res.users", string="Proprietario",
        default=lambda self: self.env.user)
    allowed_user_ids = fields.Many2many(
        "res.users",
        "cf_mail_account_user_rel",
        "account_id", "user_id",
        string="Utenti Autorizzati",
        help="Per account condivisi: chi puo vedere questa casella",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(default=0)

    # ── STATO SYNC ──
    last_sync = fields.Datetime(string="Ultima Sincronizzazione", readonly=True)
    email_count = fields.Integer(string="Email in Inbox", readonly=True)
    unread_count = fields.Integer(string="Non Lette", readonly=True)

    @api.constrains("email_address")
    def _check_email(self):
        for rec in self:
            if "@" not in (rec.email_address or ""):
                raise UserError("Indirizzo email non valido.")

    def _get_imap_connection(self):
        # Connessione IMAP usando le credenziali del fetchmail_server Odoo.
        self.ensure_one()
        if not self.fetchmail_server_id:
            raise UserError(
                "Nessun server IMAP configurato per %s. "
                "Vai in Impostazioni > Tecnico > Server Posta in Entrata e collega l account." % self.display_name_custom
            )
        srv = self.fetchmail_server_id
        try:
            if srv.is_ssl:
                conn = imaplib.IMAP4_SSL(srv.server, srv.port or 993)
            else:
                conn = imaplib.IMAP4(srv.server, srv.port or 143)

            # Odoo 18 Enterprise: usa google_gmail OAuth2 se configurato
            if hasattr(srv, "google_gmail_access_token") and srv.google_gmail_access_token:
                # Refresh token se scaduto
                if hasattr(srv, "_refresh_google_gmail_token"):
                    srv._refresh_google_gmail_token()
                auth_string = "user=%sauth=Bearer %s" % (
                    srv.user, srv.google_gmail_access_token
                )
                conn.authenticate("XOAUTH2", lambda x: auth_string)
            else:
                conn.login(srv.user, srv.password)
            return conn
        except Exception as e:
            raise UserError("Connessione IMAP fallita per %s: %s" % (self.display_name_custom, str(e)))

    def action_sync_inbox(self):
        # Sincronizza inbox — scarica ultimi 50 messaggi non ancora in DB.
        self.ensure_one()
        conn = self._get_imap_connection()
        try:
            conn.select("INBOX")
            # Cerca ultimi 7 giorni
            since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
            typ, data = conn.search(None, "SINCE", since_date)
            if typ != "OK":
                return
            msg_ids = data[0].split()
            # Prendi solo gli ultimi 100
            msg_ids = msg_ids[-100:]
            created = 0
            for num in reversed(msg_ids):
                typ, msg_data = conn.fetch(num, "(RFC822 FLAGS)")
                if typ != "OK":
                    continue
                raw_email = msg_data[0][1]
                flags = str(msg_data[0][0])
                is_read = "\Seen" in flags
                msg = email.message_from_bytes(raw_email)
                imap_uid = num.decode()
                # Evita duplicati
                existing = self.env["cf.mail.message"].search([
                    ("account_id", "=", self.id),
                    ("imap_uid", "=", imap_uid),
                ], limit=1)
                if existing:
                    continue
                self.env["cf.mail.message"].create(
                    self._parse_message(msg, imap_uid, is_read)
                )
                created += 1
            self.write({
                "last_sync": datetime.now(),
                "email_count": len(msg_ids),
                "unread_count": self.env["cf.mail.message"].search_count([
                    ("account_id", "=", self.id),
                    ("is_read", "=", False),
                    ("folder", "=", "INBOX"),
                ]),
            })
            _logger.info("Account %s: sincronizzati %d nuovi messaggi", self.display_name_custom, created)
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def _parse_message(self, msg, imap_uid, is_read):
        # Parsa un messaggio email e ritorna dict per cf.mail.message.
        def decode_header_value(value):
            if not value:
                return ""
            parts = email.header.decode_header(value)
            result = []
            for part, enc in parts:
                if isinstance(part, bytes):
                    result.append(part.decode(enc or "utf-8", errors="replace"))
                else:
                    result.append(part)
            return " ".join(result)

        subject = decode_header_value(msg.get("Subject", ""))
        from_raw = decode_header_value(msg.get("From", ""))
        to_raw = decode_header_value(msg.get("To", ""))
        cc_raw = decode_header_value(msg.get("Cc", ""))
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To", "")

        # Data
        date_raw = msg.get("Date", "")
        try:
            date_parsed = email.utils.parsedate_to_datetime(date_raw)
        except Exception:
            date_parsed = datetime.now()

        # Body
        body_plain = ""
        body_html = ""
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition", ""))
                if "attachment" in disp:
                    fname = part.get_filename() or "allegato"
                    attachments.append(fname)
                elif ctype == "text/plain" and not body_plain:
                    body_plain = part.get_payload(decode=True).decode("utf-8", errors="replace")
                elif ctype == "text/html" and not body_html:
                    body_html = part.get_payload(decode=True).decode("utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_plain = payload.decode("utf-8", errors="replace")

        return {
            "account_id": self.id,
            "imap_uid": imap_uid,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "subject": subject or "(Nessun oggetto)",
            "from_address": from_raw,
            "to_address": to_raw,
            "cc_address": cc_raw,
            "date": date_parsed,
            "body_plain": body_plain,
            "body_html": body_html,
            "is_read": is_read,
            "folder": "INBOX",
            "attachment_names": ", ".join(attachments) if attachments else False,
        }

    def action_mark_all_read(self):
        self.env["cf.mail.message"].search([
            ("account_id", "=", self.id),
            ("is_read", "=", False),
        ]).write({"is_read": True})

    @api.model
    def sync_all_accounts(self):
        # Cron: sincronizza tutti gli account attivi.
        accounts = self.search([("active", "=", True)])
        for acc in accounts:
            try:
                acc.action_sync_inbox()
            except Exception as e:
                _logger.warning("Sync fallita per account %s: %s", acc.display_name_custom, e)

    def _is_visible_to_user(self, user=None):
        # Controlla se l'account e visibile all'utente corrente.
        if user is None:
            user = self.env.user
        if self.account_type == "personal":
            return self.owner_id == user
        return user in self.allowed_user_ids or self.owner_id == user

    @api.model
    def get_my_accounts(self):
        # Ritorna gli account visibili all'utente corrente.
        all_accounts = self.search([("active", "=", True)])
        return all_accounts.filtered(lambda a: a._is_visible_to_user())
