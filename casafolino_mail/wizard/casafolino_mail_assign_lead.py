import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CasafolinoMailAssignLeadWizard(models.TransientModel):
    _name = 'casafolino.mail.assign.lead.wizard'
    _description = 'Collega email a trattativa CRM'

    lead_id = fields.Many2one('crm.lead', string='Trattativa CRM', required=True)

    def action_assign(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return {'type': 'ir.actions.act_window_close'}

        messages = self.env['casafolino.mail.message'].browse(active_ids)

        # Scarica body per chi non lo ha
        messages._ensure_body_downloaded()

        for msg in messages.filtered(lambda m: m.body_downloaded and m.body_html):
            # Evita duplicati nel chatter del lead
            existing = self.env['mail.message'].search([
                ('message_id', '=', msg.message_id_rfc),
                ('res_id', '=', self.lead_id.id),
                ('model', '=', 'crm.lead'),
            ], limit=1)
            if existing:
                continue

            self.env['mail.message'].sudo().create({
                'model': 'crm.lead',
                'res_id': self.lead_id.id,
                'message_type': 'email',
                'subtype_id': self.env.ref('mail.mt_note').id,
                'body': msg.body_html,
                'subject': msg.subject,
                'email_from': msg.sender_email,
                'date': msg.email_date,
                'message_id': msg.message_id_rfc,
            })

        return {'type': 'ir.actions.act_window_close'}
