from odoo import api, fields, models

TASK_STATE_TO_ATOM = {
    '01_in_progress': 'in_progress',
    '03_approved': 'done',
    '1_done': 'done',
    '1_canceled': 'skipped',
}


class ProjectTask(models.Model):
    _inherit = 'project.task'

    initiative_id = fields.Many2one('cf.initiative', ondelete='set null', index=True,
                                    string='Iniziativa')
    cf_tag_ids = fields.Many2many('cf.initiative.tag', string='Tag Iniziativa')
    source_atom_line_id = fields.Many2one('cf.initiative.atom.line', readonly=True,
                                          string='Atomo origine')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('initiative_id') and not vals.get('cf_tag_ids'):
                initiative = self.env['cf.initiative'].browse(vals['initiative_id'])
                if initiative.tag_ids:
                    vals['cf_tag_ids'] = [(6, 0, initiative.tag_ids.ids)]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('initiative_id') and not vals.get('cf_tag_ids'):
            initiative = self.env['cf.initiative'].browse(vals['initiative_id'])
            if initiative.tag_ids:
                vals['cf_tag_ids'] = [(6, 0, initiative.tag_ids.ids)]
        res = super().write(vals)
        if 'state' in vals or 'stage_id' in vals:
            for task in self:
                if task.state in TASK_STATE_TO_ATOM:
                    atom_line = self.env['cf.initiative.atom.line'].search([
                        ('generated_model', '=', 'project.task'),
                        ('generated_res_id', '=', task.id),
                    ], limit=1)
                    if atom_line:
                        atom_line.state = TASK_STATE_TO_ATOM[task.state]
        return res
