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
        users = group.users if group else self.env["res.users"]
        return users or self.env.user

    def _activity_exists(self, model_name, res_id, user, summary):
        model = self.env["ir.model"].sudo().search(
            [("model", "=", model_name)], limit=1,
        )
        if not model:
            return True
        return bool(self.env["mail.activity"].sudo().search([
            ("res_model_id", "=", model.id),
            ("res_id", "=", res_id),
            ("user_id", "=", user.id),
            ("summary", "=", summary),
        ], limit=1))

    def _schedule_activity_once(self, record, user, summary, note, deadline):
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type or self._activity_exists(record._name, record.id, user, summary):
            return
        self.env["mail.activity"].sudo().create({
            "res_model_id": self.env["ir.model"].sudo().search(
                [("model", "=", record._name)], limit=1,
            ).id,
            "res_id": record.id,
            "activity_type_id": activity_type.id,
            "summary": summary,
            "note": note,
            "user_id": user.id,
            "date_deadline": deadline,
        })

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
        log_oggi = self.env["cf.haccp.temperature.log"].sudo().search([
            ("date", "=", oggi),
        ], limit=1)
        if log_oggi and log_oggi.esito != "pending":
            return
        if not log_oggi:
            log_oggi = self.env["cf.haccp.temperature.log"].sudo().create({
                "date": oggi,
                "note": "Creato automaticamente dal reminder HACCP giornaliero.",
            })
        users = self._get_haccp_operators()
        summary = "Registro Temperature da compilare"
        for user in users:
            self._schedule_activity_once(
                log_oggi,
                user,
                summary,
                "Il registro temperature di oggi (%s) non e ancora stato compilato." % oggi,
                oggi,
            )
        self._send_telegram_message(
            "<b>CasaFolino HACCP</b>\n"
            "Registro Temperature NON compilato oggi (%s)" % oggi
        )

    @api.model
    def _send_sanification_reminders(self):
        oggi = datetime.now().date()
        daily_areas = ["zone1", "zone2", "zone3", "frigo", "attrezzature", "pavimenti"]
        missing_logs = self.env["cf.haccp.sanification.log"].sudo()
        for area in daily_areas:
            log = self.env["cf.haccp.sanification.log"].sudo().search([
                ("date", "=", oggi),
                ("area", "=", area),
            ], limit=1)
            if not log:
                log = self.env["cf.haccp.sanification.log"].sudo().create({
                    "date": oggi,
                    "area": area,
                    "frequenza": "giornaliera",
                    "note": "Creato automaticamente dal reminder HACCP giornaliero.",
                })
            if not log.eseguita:
                missing_logs |= log
        if not missing_logs:
            return
        users = self._get_haccp_operators()
        summary = "Registro Pulizie da compilare"
        for log in missing_logs:
            for user in users:
                self._schedule_activity_once(
                    log,
                    user,
                    summary,
                    "Il registro sanificazione di oggi (%s) non e ancora completo." % oggi,
                    oggi,
                )
        self._send_telegram_message(
            "<b>CasaFolino HACCP</b>\n"
            "Registro Pulizie NON completo oggi (%s)" % oggi
        )

    @api.model
    def _send_daily_reminders(self):
        self._send_temperature_reminders()
        self._send_sanification_reminders()

    @api.model
    def _send_weekly_document_reminders(self):
        self.env["cf.haccp.calibration"].sudo().send_expiring_alerts()
        self.env["cf.haccp.document"].sudo().send_expiry_alerts()
