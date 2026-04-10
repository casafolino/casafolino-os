from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CfMailMessageCrm(models.Model):
    _inherit = 'cf.mail.message'

    @api.model
    def create_lead_from_email(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return {'success': False, 'error': 'ID messaggio mancante'}
        try:
            msg = self.browse(int(message_id))
            if not msg.exists():
                return {'success': False, 'error': 'Messaggio non trovato'}
            partner = msg.partner_id
            if not partner and msg.from_address:
                partner = self.env['res.partner'].search([('email', '=', msg.from_address)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': msg.from_name or msg.from_address,
                        'email': msg.from_address,
                    })
                msg.write({'partner_id': partner.id})
            stage = self.env['crm.stage'].search([], order='sequence', limit=1)
            lead_vals = {
                'name': msg.subject or 'Lead da email',
                'partner_id': partner.id if partner else False,
                'stage_id': stage.id if stage else False,
                'description': (msg.body_text or '')[:500],
            }
            lead = self.env['crm.lead'].create(lead_vals)
            msg.write({'lead_id': lead.id})
            return {'success': True, 'lead_id': lead.id, 'lead_name': lead.name}
        except Exception as e:
            _logger.error('create_lead_from_email error: %s', e)
            return {'success': False, 'error': str(e)}
