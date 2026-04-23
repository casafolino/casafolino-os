from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    initiative_id = fields.Many2one('cf.initiative', ondelete='set null', index=True,
                                    string='Iniziativa')
    cf_tag_ids = fields.Many2many('cf.initiative.tag', string='Tag Iniziativa')

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
        return super().write(vals)
