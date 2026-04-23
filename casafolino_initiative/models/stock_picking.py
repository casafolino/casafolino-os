from odoo import api, fields, models

PICKING_STATE_TO_ATOM = {
    'draft': 'in_progress',
    'waiting': 'in_progress',
    'confirmed': 'in_progress',
    'assigned': 'in_progress',
    'done': 'done',
    'cancel': 'skipped',
}
PICKING_CRITICAL_FIELDS = {'state'}


class StockPicking(models.Model):
    _inherit = 'stock.picking'

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
        if not PICKING_CRITICAL_FIELDS.intersection(vals):
            return res
        for picking in self:
            if picking.state in PICKING_STATE_TO_ATOM:
                atom_line = self.env['cf.initiative.atom.line'].search([
                    ('generated_model', '=', 'stock.picking'),
                    ('generated_res_id', '=', picking.id),
                ], limit=1)
                if atom_line:
                    atom_line.state = PICKING_STATE_TO_ATOM[picking.state]
        return res
