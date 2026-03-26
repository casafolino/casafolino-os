# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CfMailMessage(models.Model):
    _name = "cf.mail.message"
    _description = "Messaggio Email CasaFolino"
    _order = "date desc, id desc"
    _rec_name = "subject"

    account_id = fields.Many2one("cf.mail.account", required=True, ondelete="cascade")
    imap_uid = fields.Char(string="IMAP UID", index=True)
    message_id = fields.Char(string="Message-ID", index=True)
    in_reply_to = fields.Char(string="In-Reply-To")
    thread_id = fields.Char(string="Thread ID", index=True)

    # ── HEADER ──
    subject = fields.Char(string="Oggetto")
    from_address = fields.Char(string="Da")
    to_address = fields.Char(string="A")
    cc_address = fields.Char(string="CC")
    date = fields.Datetime(string="Data")

    # ── CORPO ──
    body_plain = fields.Text(string="Testo")
    body_html = fields.Html(string="HTML", sanitize=True)
    attachment_names = fields.Char(string="Allegati")

    # ── STATO ──
    folder = fields.Char(string="Cartella", default="INBOX", index=True)
    is_read = fields.Boolean(string="Letta", default=False, index=True)
    is_starred = fields.Boolean(string="Preferita", default=False)
    is_archived = fields.Boolean(string="Archiviata", default=False)
    direction = fields.Selection([
        ("in", "Ricevuta"),
        ("out", "Inviata"),
    ], default="in")

    # ── COLLEGAMENTO CRM ──
    export_lead_id = fields.Many2one(
        "cf.export.lead",
        string="Trattativa Export",
        ondelete="set null",
    )
    partner_id = fields.Many2one("res.partner", string="Contatto Odoo")

    # ── RISPOSTA ──
    replied = fields.Boolean(string="Risposto", default=False)

    def action_mark_read(self):
        for rec in self:
            rec.is_read = True
            rec._sync_flag_to_imap("\Seen", add=True)

    def action_mark_unread(self):
        for rec in self:
            rec.is_read = False
            rec._sync_flag_to_imap("\Seen", add=False)

    def action_star(self):
        for rec in self:
            rec.is_starred = not rec.is_starred
            flag = "\Flagged"
            rec._sync_flag_to_imap(flag, add=rec.is_starred)

    def action_archive_message(self):
        for rec in self:
            rec.is_archived = True
            rec._sync_flag_to_imap("\Deleted", add=False)

    def _sync_flag_to_imap(self, flag, add=True):
        # Sincronizza flag su server IMAP (bidirezionale).
        if not self.imap_uid or not self.account_id.fetchmail_server_id:
            return
        try:
            conn = self.account_id._get_imap_connection()
            conn.select(self.folder or "INBOX")
            op = "+FLAGS" if add else "-FLAGS"
            conn.store(self.imap_uid, op, flag)
            conn.logout()
        except Exception as e:
            _logger.warning("Sync IMAP flag fallita per msg %s: %s", self.id, e)

    def action_link_to_crm(self):
        # Apre wizard per collegare email a trattativa Export.
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Collega a Trattativa",
            "res_model": "cf.export.lead",
            "view_mode": "list,form",
            "target": "new",
        }

    def action_reply(self):
        # Apre composer per risposta.
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Rispondi",
            "res_model": "cf.mail.compose",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_account_id": self.account_id.id,
                "default_to_address": self.from_address,
                "default_subject": "Re: %s" % (self.subject or ""),
                "default_in_reply_to": self.message_id,
                "default_reply_to_msg_id": self.id,
            },
        }

    def action_forward(self):
        # Apre composer per inoltro.
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Inoltra",
            "res_model": "cf.mail.compose",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_account_id": self.account_id.id,
                "default_subject": "Fwd: %s" % (self.subject or ""),
                "default_body_html": "<br/><br/>--- Messaggio originale ---<br/>%s" % (self.body_html or self.body_plain or ""),
            },
        }

    @api.model
    def get_inbox_messages(self, account_id, folder="INBOX", limit=50, offset=0, only_unread=False):
        # API per UI: ritorna messaggi paginati per account e cartella.
        domain = [
            ("account_id", "=", account_id),
            ("folder", "=", folder),
            ("is_archived", "=", False),
        ]
        if only_unread:
            domain.append(("is_read", "=", False))
        messages = self.search(domain, limit=limit, offset=offset)
        return messages.read([
            "id", "subject", "from_address", "to_address", "date",
            "is_read", "is_starred", "replied", "attachment_names",
            "export_lead_id",
        ])


class CfMailCompose(models.TransientModel):
    _name = "cf.mail.compose"
    _description = "Composer Email CasaFolino"

    account_id = fields.Many2one("cf.mail.account", string="Da Account", required=True)
    to_address = fields.Char(string="A", required=True)
    cc_address = fields.Char(string="CC")
    bcc_address = fields.Char(string="BCC")
    subject = fields.Char(string="Oggetto", required=True)
    body_html = fields.Html(string="Corpo")
    in_reply_to = fields.Char(string="In-Reply-To")
    reply_to_msg_id = fields.Many2one("cf.mail.message", string="Risposta a")
    export_lead_id = fields.Many2one("cf.export.lead", string="Collega a Trattativa")

    def action_send(self):
        # Invia email usando il server SMTP configurato in Odoo.
        self.ensure_one()
        acc = self.account_id
        if not acc.outgoing_mail_server_id:
            from odoo.exceptions import UserError
            raise UserError(
                "Nessun server SMTP configurato per %s. "
                "Vai in Impostazioni > Tecnico > Server Posta in Uscita." % acc.display_name_custom
            )
        # Usa mail.mail di Odoo per l'invio (gestisce OAuth2 automaticamente)
        mail_values = {
            "subject": self.subject,
            "body_html": self.body_html or "",
            "email_from": acc.email_address,
            "email_to": self.to_address,
            "email_cc": self.cc_address or "",
            "mail_server_id": acc.outgoing_mail_server_id.id,
        }
        if self.in_reply_to:
            mail_values["headers"] = {"In-Reply-To": self.in_reply_to}

        mail = self.env["mail.mail"].create(mail_values)
        mail.send()

        # Salva in DB come messaggio inviato
        self.env["cf.mail.message"].create({
            "account_id": acc.id,
            "subject": self.subject,
            "from_address": acc.email_address,
            "to_address": self.to_address,
            "cc_address": self.cc_address or "",
            "body_html": self.body_html,
            "date": fields.Datetime.now(),
            "folder": "Sent",
            "is_read": True,
            "direction": "out",
            "export_lead_id": self.export_lead_id.id if self.export_lead_id else False,
        })

        # Marca come risposto il messaggio originale
        if self.reply_to_msg_id:
            self.reply_to_msg_id.replied = True

        return {"type": "ir.actions.act_window_close"}
