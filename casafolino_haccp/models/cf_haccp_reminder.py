# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from odoo import models, api

_logger = logging.getLogger(__name__)


class CfHaccpReminder(models.Model):
    _name = "cf.haccp.reminder"
    _description = "Gestione Reminder HACCP"

    def _get_haccp_operators(self):
        group = self.env.ref(
            "casafolino_haccp.group_haccp_operator", raise_if_not_found=False,
        )
        return group.users if group else self.env["res.users"]

    def _send_telegram_message(self, message):
        ICP = self.env["ir.config_parameter"].sudo()
        token = ICP.get_param("cf_haccp.telegram_bot_token", "")
        chat_id = ICP.get_param("cf_haccp.telegram_chat_id", "")
        if not token or not chat_id:
            return
        try:
            import requests
            requests.post(
                "https://api.telegram.org/bot%s/sendMessage" % token,
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=5,
            )
        except Exception:
            _logger.warning("HACCP Telegram: invio fallito", exc_info=True)

    @api.model
    def _send_temperature_reminders(self):
        oggi = datetime.now().date()
        logs_oggi = self.env["cf.haccp.temperature.log"].sudo().search([
            ("date", ">=", str(oggi)),
        ])
        if logs_oggi:
            return
        users = self._get_haccp_operators()
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return
        temp_model_id = self.env["ir.model"].sudo().search(
            [("model", "=", "cf.haccp.temperature.log")], limit=1,
        )
        if not temp_model_id:
            return
        existing = self.env["cf.haccp.temperature.log"].sudo().search([], limit=1)
        res_id = existing.id if existing else False
        if not res_id:
            return
        for user in users:
            self.env["mail.activity"].sudo().create({
                "res_model_id": temp_model_id.id,
                "res_id": res_id,
                "activity_type_id": activity_type.id,
                "summary": "Registro Temperature da compilare",
                "note": "Il registro temperature di oggi (%s) non e ancora stato compilato." % oggi,
                "user_id": user.id,
                "date_deadline": oggi,
            })
        self._send_telegram_message(
            "<b>CasaFolino HACCP</b>\n"
            "Registro Temperature NON compilato oggi (%s)" % oggi
        )

    @api.model
    def _send_sanification_reminders(self):
        oggi = datetime.now().date()
        logs_oggi = self.env["cf.haccp.sanification.log"].sudo().search([
            ("date", ">=", str(oggi)),
        ])
        if logs_oggi:
            return
        users = self._get_haccp_operators()
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return
        san_model_id = self.env["ir.model"].sudo().search(
            [("model", "=", "cf.haccp.sanification.log")], limit=1,
        )
        if not san_model_id:
            return
        existing = self.env["cf.haccp.sanification.log"].sudo().search([], limit=1)
        res_id = existing.id if existing else False
        if not res_id:
            return
        for user in users:
            self.env["mail.activity"].sudo().create({
                "res_model_id": san_model_id.id,
                "res_id": res_id,
                "activity_type_id": activity_type.id,
                "summary": "Registro Pulizie da compilare",
                "note": "Il registro sanificazione di oggi (%s) non e ancora stato compilato." % oggi,
                "user_id": user.id,
                "date_deadline": oggi,
            })
        self._send_telegram_message(
            "<b>CasaFolino HACCP</b>\n"
            "Registro Pulizie NON compilato oggi (%s)" % oggi
        )
