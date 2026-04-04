from odoo import models, fields, api


class CfHaccpReceiptWizard(models.TransientModel):
    _name = 'cf.haccp.receipt.wizard'
    _description = 'Wizard Ricevimento Materie Prime HACCP'

    receipt_id = fields.Many2one('cf.haccp.receipt', string='Ricevimento', required=True)
    note = fields.Text('Note')

    def action_confirm(self):
        if self.receipt_id:
            self.receipt_id.write({'state': 'done'})
        return {'type': 'ir.actions.act_window_close'}
