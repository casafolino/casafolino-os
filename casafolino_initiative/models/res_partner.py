from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    initiative_ids = fields.One2many('cf.initiative', 'partner_id', string='Dossier / Iniziative')
    initiative_count = fields.Integer(compute='_compute_initiative_count', string='Numero Dossier')

    @api.depends('initiative_ids')
    def _compute_initiative_count(self):
        for partner in self:
            partner.initiative_count = len(partner.initiative_ids)

    def action_view_initiatives(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dossier Cliente',
            'res_model': 'cf.initiative',
            'view_mode': 'kanban,list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id, 'default_name': f'Dossier {self.name}'},
        }

    def action_create_master_dossier(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('casafolino_initiative.action_cf_initiative_wizard')
        action['context'] = {
            'default_partner_id': self.id,
            'default_name': f'Dossier {self.name}',
            'default_step': '1_family'
        }
        return action
