from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    cf360_sale_order_ids = fields.One2many(
        "sale.order",
        "cf_project_id",
        string="Ordini collegati",
        readonly=True,
    )

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
