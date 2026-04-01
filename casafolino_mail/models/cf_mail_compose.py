# -*- coding: utf-8 -*-
from odoo import models, fields


class CfMailCompose(models.TransientModel):
    _name = "cf.mail.compose"
    _description = "Composizione Email CasaFolino"

    account_id = fields.Many2one("cf.mail.account", string="Account Mittente")
    message_id = fields.Many2one("cf.mail.message", string="Messaggio Originale")
    to_address = fields.Char(string="A")
    cc_address = fields.Char(string="Cc")
    bcc_address = fields.Char(string="Ccn")
    subject = fields.Char(string="Oggetto")
    body_html = fields.Html(string="Corpo")
    compose_mode = fields.Selection([
        ("new", "Nuovo"),
        ("reply", "Rispondi"),
        ("forward", "Inoltra"),
    ], default="new")

    def action_send(self):
        self.ensure_one()
        result = self.env['cf.mail.message'].send_reply(
            account_id=self.account_id.id if self.account_id else None,
            to_address=self.to_address or '',
            cc_address=self.cc_address or '',
            bcc_address=self.bcc_address or '',
            subject=self.subject or '',
            body=self.body_html or '',
            message_id=self.message_id.id if hasattr(self, 'message_id') and self.message_id else None,
        )
        return {'type': 'ir.actions.act_window_close'}

