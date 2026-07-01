import uuid

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    fancyfood_token = fields.Char(string="Fancy Food Token", copy=False, index=True)
    fancyfood_event_ids = fields.One2many(
        "casafolino.fancyfood.event", "partner_id", string="Eventi Fancy Food",
    )
    fancyfood_open_count = fields.Integer(
        string="Aperture", compute="_compute_fancyfood_stats", store=True,
    )
    fancyfood_click_count = fields.Integer(
        string="Click catalogo", compute="_compute_fancyfood_stats", store=True,
    )
    fancyfood_logo_count = fields.Integer(
        string="Load logo", compute="_compute_fancyfood_stats", store=True,
    )
    fancyfood_event_count = fields.Integer(
        string="Eventi FF", compute="_compute_fancyfood_stats", store=True,
    )
    fancyfood_clicked = fields.Boolean(
        string="Ha cliccato il catalogo", compute="_compute_fancyfood_stats", store=True,
    )
    fancyfood_first_click = fields.Datetime(
        string="Primo click catalogo", compute="_compute_fancyfood_stats", store=True,
    )
    fancyfood_hot = fields.Boolean(
        string="Hot lead Fancy Food", compute="_compute_fancyfood_stats", store=True,
    )

    @api.depends("fancyfood_event_ids.event_type", "fancyfood_event_ids.create_date")
    def _compute_fancyfood_stats(self):
        for partner in self:
            events = partner.fancyfood_event_ids
            clicks = events.filtered(lambda e: e.event_type == "click")
            partner.fancyfood_open_count = len(events.filtered(lambda e: e.event_type == "open"))
            partner.fancyfood_click_count = len(clicks)
            partner.fancyfood_logo_count = len(events.filtered(lambda e: e.event_type == "logo"))
            partner.fancyfood_event_count = len(events)
            partner.fancyfood_clicked = bool(clicks)
            partner.fancyfood_first_click = min(clicks.mapped("create_date")) if clicks else False
            partner.fancyfood_hot = bool(clicks)

    def _ensure_fancyfood_token(self):
        for partner in self:
            if not partner.fancyfood_token:
                partner.fancyfood_token = uuid.uuid4().hex
        return True

    def _fancyfood_owner_user(self):
        self.ensure_one()
        antonio = self.env["res.users"].sudo().search(
            [("login", "=", "antonio@casafolino.com")], limit=1,
        )
        return self.user_id or antonio or self.env.ref("base.user_admin")

    def _fancyfood_register_click(self):
        """Called from the catalogue controller on a tokenized click."""
        self.ensure_one()
        summary = "Ha scaricato il catalogo — ricontattare"
        existing = self.env["mail.activity"].sudo().search(
            [
                ("res_model", "=", "res.partner"),
                ("res_id", "=", self.id),
                ("summary", "=", summary),
            ],
            limit=1,
        )
        if existing:
            return
        user = self._fancyfood_owner_user()
        self.sudo().activity_schedule(
            "mail.mail_activity_data_todo",
            summary=summary,
            note="Il contatto ha cliccato/scaricato il catalogo Fancy Food NY 2026.",
            user_id=user.id,
        )

    def action_send_fancyfood_mail(self):
        """Manual action: send the Fancy Food follow-up mail (EN or IT by lang)."""
        self._ensure_fancyfood_token()
        tmpl_en = self.env.ref(
            "casafolino_fancyfood.mail_template_fancyfood_en", raise_if_not_found=False,
        )
        tmpl_it = self.env.ref(
            "casafolino_fancyfood.mail_template_fancyfood_it", raise_if_not_found=False,
        )
        sent = 0
        skipped = 0
        for partner in self:
            if not partner.email:
                skipped += 1
                continue
            use_it = (partner.lang or "").startswith("it") and tmpl_it
            tmpl = tmpl_it if use_it else tmpl_en
            if not tmpl:
                skipped += 1
                continue
            tmpl.send_mail(partner.id, force_send=True)
            sent += 1
        message = "Mail Fancy Food inviata a %s contatto/i." % sent
        if skipped:
            message += " %s saltati (email mancante)." % skipped
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Fancy Food NY 2026",
                "message": message,
                "type": "success" if sent else "warning",
                "sticky": False,
            },
        }
