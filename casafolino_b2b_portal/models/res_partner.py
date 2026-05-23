# -*- coding: utf-8 -*-
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

    def action_cf_b2b_approve(self):
        portal_group = self.env.ref("base.group_portal")
        for partner in self:
            email = partner.email_normalized or partner.email
            if not email:
                raise UserError(_("Imposta una email prima di approvare il cliente B2B."))
            partner.cf_b2b_status = "approved"
            user = self.env["res.users"].sudo().search([("login", "=", email)], limit=1)
            if not user:
                user = self.env["res.users"].sudo().create(
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
            partner.message_post(body=_("Cliente B2B approvato. Accesso portale attivato per %s.") % email)
        return True

    def action_cf_b2b_suspend(self):
        self.write({"cf_b2b_status": "suspended"})
        return True
