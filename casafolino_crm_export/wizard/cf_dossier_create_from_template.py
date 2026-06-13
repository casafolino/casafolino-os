from odoo import models, fields, api


class CfDossierCreateFromTemplate(models.TransientModel):
    _name = 'cf.dossier.create.from.template'
    _description = 'Crea Dossier da Template'

    template_id = fields.Many2one(
        'cf.dossier.template', string='Template',
        required=True,
    )
    name = fields.Char('Nome Dossier', required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente')

    def action_create(self):
        self.ensure_one()
        tmpl = self.template_id

        # Create project
        project_vals = {
            'name': self.name,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'cf_status_dossier': 'exploration',
            'cf_template_origin_id': tmpl.id,
            'cf_dossier_lang': tmpl.default_lang or 'en',
            'cf_volume_unit': tmpl.default_volume_unit or 'unit',
            'cf_incoterms': tmpl.default_incoterms or False,
            'cf_payment_term': tmpl.default_payment_term or False,
        }

        # Certifications
        if tmpl.default_certification_ids:
            project_vals['cf_certification_ids'] = [(6, 0, tmpl.default_certification_ids.ids)]

        project = self.env['project.project'].create(project_vals)

        # Create tasks from checkpoints
        Task = self.env['project.task']
        for cp in tmpl.checkpoint_ids.sorted('sequence'):
            Task.create({
                'name': cp.name,
                'project_id': project.id,
                'description': cp.description or '',
                'sequence': cp.sequence,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'casafolino_crm_export.project_dashboard',
            'name': 'Vista 360° — %s' % project.name,
            'target': 'current',
            'context': {
                'active_id': project.id,
                'active_model': 'project.project',
                'default_project_id': project.id,
            },
        }
