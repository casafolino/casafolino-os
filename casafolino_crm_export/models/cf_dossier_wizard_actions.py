from odoo import _, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    def action_open_dossier_upsert_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Aggiorna Dossier 360"),
            "res_model": "cf.dossier.upsert.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "project.project",
                "active_id": self.id,
                "default_project_id": self.id,
            },
        }
