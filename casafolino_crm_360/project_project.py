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
        return {
            "type": "ir.actions.client",
            "tag": "casafolino_crm_export.project_dashboard",
            "name": "Vista 360° — %s" % self.display_name,
            "target": "current",
            "context": {
                "active_id": self.id,
                "active_model": "project.project",
                "default_project_id": self.id,
            },
        }
