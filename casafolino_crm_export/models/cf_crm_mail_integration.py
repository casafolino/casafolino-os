# -*- coding: utf-8 -*-
# Integrazione CRM -> Mail
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CfExportLeadMail(models.Model):
    _inherit = "cf.export.lead"

    email_count = fields.Integer(
        string="Email", compute="_compute_email_count", store=False
    )
    last_email_date = fields.Datetime(
        string="Ultima Email", compute="_compute_email_count", store=False
    )

    def _compute_email_count(self):
        for rec in self:
            if self.env["ir.model"].search([("model", "=", "cf.mail.message")], limit=1):
                msgs = self.env["cf.mail.message"].search_count([
                    ("export_lead_id", "=", rec.id),
                ])
                rec.email_count = msgs
                last = self.env["cf.mail.message"].search([
                    ("export_lead_id", "=", rec.id),
                ], order="date desc", limit=1)
                rec.last_email_date = last.date if last else False
            else:
                rec.email_count = 0
                rec.last_email_date = False

    def action_view_emails(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Email — %s" % self.name,
            "res_model": "cf.mail.message",
            "view_mode": "list,form",
            "domain": [("export_lead_id", "=", self.id)],
            "context": {"default_export_lead_id": self.id},
        }

    def action_compose_email(self):
        self.ensure_one()
        account = self.env["cf.mail.account"].search([
            ("owner_id", "=", self.env.uid),
            ("active", "=", True),
        ], limit=1)
        return {
            "type": "ir.actions.act_window",
            "name": "Scrivi Email",
            "res_model": "cf.mail.compose",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_account_id": account.id if account else False,
                "default_to_address": self.partner_id.email or "",
                "default_subject": "Re: %s" % self.name,
                "default_export_lead_id": self.id,
            },
        }
