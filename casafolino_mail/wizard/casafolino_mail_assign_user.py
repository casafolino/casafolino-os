from odoo import models, fields


class CasafolinoMailAssignUserWizard(models.TransientModel):
    _name = 'casafolino.mail.assign.user.wizard'
    _description = 'Assegna responsabile a email selezionate'

    user_ids = fields.Many2many('res.users', string='Responsabili', required=True)

    def action_assign(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            messages = self.env['casafolino.mail.message'].browse(active_ids)
            # Aggiunge utenti senza sovrascrivere quelli esistenti
            for msg in messages:
                msg.assigned_user_ids = [(4, uid) for uid in self.user_ids.ids]
        return {'type': 'ir.actions.act_window_close'}
