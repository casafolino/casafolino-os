# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CfMailSenderRule(models.Model):
    """Regola per mittente email: keep (scarica tutta la storia) o exclude (ignora sempre)."""
    _name = "cf.mail.sender.rule"
    _description = "Regola Mittente Email"
    _rec_name = "email"
    _order = "action, email"

    email = fields.Char(
        string="Email Mittente",
        required=True,
        index=True,
    )
    action = fields.Selection(
        [("keep", "Tieni (sync storica)"), ("exclude", "Escludi (ignora sempre)")],
        string="Azione",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contatto",
        ondelete="set null",
    )
    full_sync_done = fields.Boolean(
        string="Sync storica completata",
        default=False,
        help="True quando tutta la storia di questo mittente è stata scaricata.",
    )
    message_count = fields.Integer(
        string="Email in archivio",
        compute="_compute_message_count",
    )

    _sql_constraints = [
        ("email_unique", "UNIQUE(email)", "Esiste già una regola per questo indirizzo email."),
    ]

    @api.depends("email")
    def _compute_message_count(self):
        for rec in self:
            if rec.email:
                rec.message_count = self.env["cf.mail.message"].search_count(
                    [("from_address", "ilike", rec.email)]
                )
            else:
                rec.message_count = 0

    # ── API per OWL / RPC ──────────────────────────────────────────────────

    @api.model
    def get_rules(self):
        """Ritorna tutte le regole serializzate per il frontend."""
        rules = self.search([])
        return [
            {
                "id": r.id,
                "email": r.email,
                "action": r.action,
                "partner_id": r.partner_id.id if r.partner_id else False,
                "partner_name": r.partner_id.name if r.partner_id else "",
                "full_sync_done": r.full_sync_done,
                "message_count": r.message_count,
            }
            for r in rules
        ]

    @api.model
    def set_rule(self, email, action, trigger_sync=False):
        """
        Crea o aggiorna una regola per il mittente.
        Se action=='exclude' elimina tutte le email di quel mittente.
        Se action=='keep' e trigger_sync=True, pianifica sync storica.
        """
        email = (email or "").strip().lower()
        if not email:
            raise UserError("Indirizzo email non valido.")
        if action not in ("keep", "exclude"):
            raise UserError("Azione non valida.")

        partner = self.env["res.partner"].search([("email", "ilike", email)], limit=1)
        existing = self.search([("email", "=", email)], limit=1)

        if existing:
            existing.write({
                "action": action,
                "partner_id": partner.id if partner else False,
                "full_sync_done": False,
            })
            rule = existing
        else:
            rule = self.create({
                "email": email,
                "action": action,
                "partner_id": partner.id if partner else False,
            })

        if action == "exclude":
            # Elimina tutte le email di questo mittente
            msgs = self.env["cf.mail.message"].search([("from_address", "ilike", email)])
            count = len(msgs)
            msgs.unlink()
            _logger.info("Sender rule EXCLUDE %s: deleted %d messages", email, count)

        elif action == "keep" and trigger_sync:
            # Triggera sync storica per tutti gli account
            accounts = self.env["cf.mail.account"].search([("imap_enabled", "=", True)])
            accounts._sync_sender_history(email)
            rule.write({"full_sync_done": True})

        return {"success": True, "rule_id": rule.id, "action": action}

    @api.model
    def delete_rule(self, rule_id):
        """Elimina una regola mittente."""
        rule = self.browse(int(rule_id))
        if not rule.exists():
            raise UserError("Regola non trovata.")
        rule.unlink()
        return {"success": True}
