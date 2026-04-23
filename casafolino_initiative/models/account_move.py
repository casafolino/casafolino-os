from odoo import api, fields, models

MOVE_STATE_TO_ATOM = {
    'draft': 'in_progress',
    'posted': 'done',
    'cancel': 'skipped',
}
MOVE_CRITICAL_FIELDS = {'state'}


class AccountMove(models.Model):
    _inherit = 'account.move'

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
        if not MOVE_CRITICAL_FIELDS.intersection(vals):
            return res
        for move in self:
            if move.move_type == 'out_invoice' and move.state in MOVE_STATE_TO_ATOM:
                atom_line = self.env['cf.initiative.atom.line'].search([
                    ('generated_model', '=', 'account.move'),
                    ('generated_res_id', '=', move.id),
                ], limit=1)
                if atom_line:
                    atom_line.state = MOVE_STATE_TO_ATOM[move.state]
        return res
