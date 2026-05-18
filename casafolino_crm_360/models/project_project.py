from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProjectProject(models.Model):
    _inherit = "project.project"

    cf360_sale_order_ids = fields.One2many(
        "sale.order",
        "cf_project_id",
        string="Ordini collegati",
        readonly=True,
    )
    cf360_mail_ids = fields.Many2many(
        "casafolino.mail.message",
        compute="_compute_cf360_mail_ids",
        string="Mail 360",
    )
    cf360_mail_count = fields.Integer(
        compute="_compute_cf360_mail_ids",
        string="Mail",
    )
    cf360_task_count = fields.Integer(
        compute="_compute_cf360_counts",
        string="Sottoprogetti",
    )
    cf360_document_count = fields.Integer(
        compute="_compute_cf360_counts",
        string="Documenti",
    )

    @api.depends("task_ids", "cf_dossier_attachment_ids")
    def _compute_cf360_counts(self):
        for project in self:
            project.cf360_task_count = len(project.task_ids)
            project.cf360_document_count = len(project.cf_dossier_attachment_ids)

    @api.depends("partner_id")
    def _compute_cf360_mail_ids(self):
        Mail = self.env["casafolino.mail.message"]
        for project in self:
            domain = [("cf_project_id", "=", project.id)]
            if project.partner_id:
                domain = ["|", ("cf_project_id", "=", project.id), ("partner_id", "=", project.partner_id.id)]
            mails = Mail.search(domain, order="email_date desc", limit=200)
            project.cf360_mail_ids = mails
            project.cf360_mail_count = len(mails)

    def _cf360_get_or_create_lavagna_initiative(self):
        self.ensure_one()
        initiative = self.initiative_id
        if not initiative:
            family = self.env["cf.initiative.family"].search([], order="sequence, id", limit=1)
            variant_domain = [("family_id", "=", family.id)] if family else []
            variant = self.env["cf.initiative.variant"].search(
                variant_domain, order="sequence, id", limit=1
            )
            if not family or not variant:
                raise UserError(
                    _(
                        "Non posso creare la Lavagna: mancano famiglia o variante "
                        "delle iniziative."
                    )
                )
            initiative = self.env["cf.initiative"].create(
                {
                    "name": self.name,
                    "family_id": family.id,
                    "variant_id": variant.id,
                    "partner_id": self.partner_id.id or False,
                    "user_id": self.user_id.id or self.env.user.id,
                    "state": "in_progress",
                    "lavagna_enabled": True,
                    "lavagna_panels": "kanban,todo,mail,activity,docs,notes,calendar",
                }
            )
            self.write({"initiative_id": initiative.id})

        updates = {}
        if not initiative.lavagna_enabled:
            updates["lavagna_enabled"] = True
        if not initiative.lavagna_panels:
            updates["lavagna_panels"] = "kanban,todo,mail,activity,docs,notes,calendar"
        if updates:
            initiative.write(updates)
        return initiative

    def action_open_project_dashboard_360(self):
        self.ensure_one()
        view = self.env.ref("casafolino_crm_360.view_project_project_form_crm360")
        return {
            "type": "ir.actions.act_window",
            "name": "Vista 360 - %s" % self.display_name,
            "res_id": self.id,
            "view_mode": "form",
            "res_model": "project.project",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "current",
            "context": {
                "active_id": self.id,
                "active_model": "project.project",
            },
        }

    def action_open_lavagna_360(self):
        initiative = self._cf360_get_or_create_lavagna_initiative()
        return initiative.action_open_lavagna()

    def action_open_mails_360(self):
        self.ensure_one()
        domain = [("cf_project_id", "=", self.id)]
        if self.partner_id:
            domain = ["|", ("cf_project_id", "=", self.id), ("partner_id", "=", self.partner_id.id)]
        return {
            "type": "ir.actions.act_window",
            "name": _("Mail - %s") % self.display_name,
            "res_model": "casafolino.mail.message",
            "view_mode": "list,form",
            "domain": domain,
            "context": {
                "default_cf_project_id": self.id,
                "default_partner_id": self.partner_id.id if self.partner_id else False,
            },
        }

    def action_open_tasks_360(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sottoprogetti - %s") % self.display_name,
            "res_model": "project.task",
            "view_mode": "list,kanban,form",
            "domain": [("project_id", "=", self.id)],
            "context": {
                "default_project_id": self.id,
                "active_id": self.id,
                "active_model": "project.project",
            },
        }

    def action_open_documents_360(self):
        self.ensure_one()
        domain = [
            "|",
            "&",
            ("res_model", "=", "project.project"),
            ("res_id", "=", self.id),
            "&",
            ("res_model", "=", "res.partner"),
            ("res_id", "=", self.partner_id.id if self.partner_id else 0),
        ]
        return {
            "type": "ir.actions.act_window",
            "name": _("Documenti - %s") % self.display_name,
            "res_model": "ir.attachment",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"default_res_model": "project.project", "default_res_id": self.id},
        }
