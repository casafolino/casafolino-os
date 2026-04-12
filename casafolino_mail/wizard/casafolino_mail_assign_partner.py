from odoo import models, fields


class CasafolinoMailAssignPartnerWizard(models.TransientModel):
    _name = 'casafolino.mail.assign.partner.wizard'
    _description = 'Assegna contatto a email selezionate'

    partner_id = fields.Many2one('res.partner', string='Contatto', required=True)

    def action_assign(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            messages = self.env['casafolino.mail.message'].browse(active_ids)
            messages.write({
                'partner_id': self.partner_id.id,
                'match_type': 'manual',
            })
        return {'type': 'ir.actions.act_window_close'}
