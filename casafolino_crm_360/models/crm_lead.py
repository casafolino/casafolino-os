from odoo import models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def action_open_project_360(self):
        self.ensure_one()
        project = self.cf_project_id
        if not project:
            vals = {
                "name": self.partner_id.name or self.name or "Dossier commerciale",
                "partner_id": self.partner_id.id if self.partner_id else False,
                "user_id": self.user_id.id or self.env.user.id,
            }
            if "cf_status_dossier" in self.env["project.project"]._fields:
                vals["cf_status_dossier"] = "exploration"
            project = self.env["project.project"].create(vals)
            self.cf_project_id = project.id
        return project.action_open_project_dashboard_360()
