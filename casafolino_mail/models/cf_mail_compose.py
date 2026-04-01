from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CfMailCompose(models.TransientModel):
    _name = 'cf.mail.compose'
    _description = 'Composizione Email CasaFolino'

    account_id = fields.Many2one(
        'cf.mail.account', string='Account mittente',
        required=True, domain=[('active', '=', True)],
        default=lambda self: self.env['cf.mail.account'].search([('active', '=', True)], limit=1),
    )
    to_address = fields.Char('A', required=True)
    cc_address = fields.Char('CC')
    bcc_address = fields.Char('BCC')
    subject = fields.Char('Oggetto', required=True)
    body_html = fields.Html('Corpo', default='')
    export_lead_id = fields.Many2one('cf.export.lead', string='Trattativa collegata')

    def action_send(self):
        self.ensure_one()
        result = self.env['cf.mail.message'].send_reply(
            account_id=self.account_id.id,
            to_address=self.to_address,
            cc_address=self.cc_address or '',
            bcc_address=self.bcc_address or '',
            subject=self.subject,
            body=self.body_html or '',
        )
        if result.get('success') and self.export_lead_id:
            msg = self.env['cf.mail.message'].browse(result['id'])
            msg.write({'lead_id': self.export_lead_id.id})
        return {'type': 'ir.actions.act_window_close'}
