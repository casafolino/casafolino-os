from odoo import models, fields


class CrmLeadBulkChangeOwnerWizard(models.TransientModel):
    _name = 'crm.lead.bulk.change.owner.wizard'
    _description = "Bulk Change Owner"

    user_id = fields.Many2one('res.users', string='Nuovo Owner', required=True)
    lead_ids = fields.Many2many('crm.lead', string='Lead selezionati')

    def action_confirm(self):
        self.lead_ids.write({'user_id': self.user_id.id})
        return {'type': 'ir.actions.act_window_close'}


class CrmLeadBulkChangeStageWizard(models.TransientModel):
    _name = 'crm.lead.bulk.change.stage.wizard'
    _description = "Bulk Change Stage"

    stage_id = fields.Many2one('crm.stage', string='Nuovo Stage', required=True)
    lead_ids = fields.Many2many('crm.lead', string='Lead selezionati')

    def action_confirm(self):
        self.lead_ids.write({'stage_id': self.stage_id.id})
        return {'type': 'ir.actions.act_window_close'}
