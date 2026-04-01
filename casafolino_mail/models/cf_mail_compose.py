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
