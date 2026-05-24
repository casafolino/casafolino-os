# -*- coding: utf-8 -*-
from urllib.parse import urlsplit, urlunsplit

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    cf_b2b_status = fields.Selection(
        [
            ("none", "Non B2B"),
            ("pending", "In attesa"),
            ("approved", "Approvato"),
            ("suspended", "Sospeso"),
        ],
        string="Stato B2B",
        default="none",
        tracking=True,
    )
    cf_b2b_category = fields.Selection(
        [
            ("restaurant", "Ristorante"),
            ("grocery", "Gastronomia / Retail"),
            ("hotel", "Hotel"),
            ("distributor", "Distributore"),
            ("other", "Altro"),
        ],
        string="Categoria B2B",
    )
    cf_b2b_vat_code = fields.Char(string="P.IVA B2B")
    cf_b2b_sdi_pec = fields.Char(string="SDI / PEC")
    cf_b2b_google_place_id = fields.Char(string="Google Place ID")
    cf_b2b_google_place_types = fields.Char(string="Google Place types")
    cf_b2b_source = fields.Selection(
        [
            ("ecommerce", "B2B Ecommerce"),
            ("company", "B2B Company"),
            ("manual", "Manuale"),
        ],
        string="Origine B2B",
        default="manual",
        tracking=True,
    )
    cf_b2b_requested_at = fields.Datetime(string="Richiesta B2B", default=fields.Datetime.now, tracking=True)
    cf_b2b_approved_at = fields.Datetime(string="Approvazione B2B", tracking=True)

    def _cf_b2b_default_email_from(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            "casafolino_b2b.email_from",
            "CasaFolino B2B <antonio@casafolino.com>",
        )

    def _cf_b2b_base_url(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            "casafolino_b2b.portal_base_url",
            "https://b2b.casafolino.com",
        ).rstrip("/")

    def _cf_b2b_signup_url(self):
        self.ensure_one()
        url = self._get_signup_url()
        base_url = self._cf_b2b_base_url()
        if not url:
            return base_url
        if url.startswith("/"):
            return f"{base_url}{url}"
        base = urlsplit(base_url)
        parsed = urlsplit(url)
        return urlunsplit((base.scheme, base.netloc, parsed.path, parsed.query, parsed.fragment))

    def _cf_b2b_send_template(self, xmlid, email_values=None):
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template:
            return False
        values = dict(email_values or {})
        values.setdefault("email_from", self._cf_b2b_default_email_from())
        for partner in self:
            if not partner.email and not values.get("email_to"):
                continue
            template.sudo().send_mail(partner.id, force_send=True, email_values=values)
        return True

    def action_cf_b2b_send_pending_notifications(self):
        notify_email = self.env["ir.config_parameter"].sudo().get_param(
            "casafolino_b2b.notification_email",
            "antonio@casafolino.com",
        )
        self._cf_b2b_send_template("casafolino_b2b_portal.mail_template_b2b_request_received")
        if notify_email:
            self._cf_b2b_send_template(
                "casafolino_b2b_portal.mail_template_b2b_internal_pending",
                email_values={"email_to": notify_email},
            )
        return True

    def action_cf_b2b_approve(self):
        portal_group = self.env.ref("base.group_portal")
        for partner in self:
            email = partner.email_normalized or partner.email
            if not email:
                raise UserError(_("Imposta una email prima di approvare il cliente B2B."))
            partner.cf_b2b_status = "approved"
            user = self.env["res.users"].sudo().search([("login", "=", email)], limit=1)
            if not user:
                user = self.env["res.users"].sudo().with_context(
                    no_reset_password=True,
                    mail_create_nosubscribe=True,
                    mail_create_nolog=True,
                ).create(
                    {
                        "name": partner.name,
                        "login": email,
                        "email": email,
                        "partner_id": partner.id,
                        "groups_id": [(6, 0, [portal_group.id])],
                    }
                )
            elif portal_group not in user.groups_id:
                user.sudo().write({"groups_id": [(4, portal_group.id)]})
            partner.sudo().signup_prepare(signup_type="reset")
            partner.cf_b2b_approved_at = fields.Datetime.now()
            partner._cf_b2b_send_template("casafolino_b2b_portal.mail_template_b2b_approved")
            partner.message_post(body=_("Cliente B2B approvato. Accesso portale attivato per %s.") % email)
        return True

    def action_cf_b2b_suspend(self):
        self.write({"cf_b2b_status": "suspended"})
        return True
