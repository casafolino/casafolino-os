import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailCreateLead(models.TransientModel):
    _name = 'casafolino.mail.create.lead.wizard'
    _description = 'Crea Lead da Email'

    message_id = fields.Many2one(
        'casafolino.mail.message', string='Email', required=True, ondelete='cascade')
    name = fields.Char('Nome lead', required=True)
    partner_id = fields.Many2one('res.partner', string='Contatto')
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.uid)
    stage_id = fields.Many2one(
        'crm.stage', string='Stage', domain="[('team_id', '=', team_id)]")
    team_id = fields.Many2one('crm.team', string='Pipeline')
    expected_revenue = fields.Monetary('Ricavo atteso', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    priority = fields.Selection([
        ('0', 'Normale'), ('1', 'Bassa'), ('2', 'Alta'), ('3', 'Molto alta'),
    ], string='Priorità', default='1')
    tag_ids = fields.Many2many('crm.tag', string='Tag')
    description = fields.Text('Note')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        msg_id = self.env.context.get('default_message_id')
        if msg_id:
            msg = self.env['casafolino.mail.message'].browse(msg_id)
            if msg.exists():
                res['name'] = msg.subject or 'Email da %s' % msg.sender_email
                res['partner_id'] = msg.partner_id.id if msg.partner_id else False
                res['description'] = (msg.body_plain or msg.snippet or '')[:3000]
                # Find Export CRM team and its "New" stage
                team = self.env['crm.team'].search([
                    ('name', 'ilike', 'Export')], limit=1)
                if team:
                    res['team_id'] = team.id
                    stage = self.env['crm.stage'].search([
                        ('team_id', '=', team.id),
                        ('name', 'ilike', 'New'),
                    ], limit=1)
                    if not stage:
                        stage = self.env['crm.stage'].search([
                            ('team_id', '=', team.id),
                        ], order='sequence', limit=1)
                    if stage:
                        res['stage_id'] = stage.id
        return res

    def action_create_lead(self):
        """Crea crm.lead e collega all'email."""
        self.ensure_one()
        msg = self.message_id

        lead_vals = {
            'name': self.name,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'email_from': msg.sender_email,
            'user_id': self.user_id.id if self.user_id else False,
            'team_id': self.team_id.id if self.team_id else False,
            'stage_id': self.stage_id.id if self.stage_id else False,
            'expected_revenue': self.expected_revenue,
            'priority': self.priority,
            'tag_ids': [(6, 0, self.tag_ids.ids)] if self.tag_ids else False,
            'description': self.description,
            'source_email_id': msg.id,
        }

        # UTM source "Email"
        try:
            lead_vals['source_id'] = self.env.ref('utm.utm_source_email').id
        except Exception:
            pass

        lead = self.env['crm.lead'].create(lead_vals)
        msg.write({
            'lead_id': lead.id,
            'state': 'keep',
            'triage_user_id': self.env.user.id,
            'triage_date': fields.Datetime.now(),
        })

        _logger.info("Lead %s created from email %s", lead.id, msg.id)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Lead creato',
                'message': 'Lead "%s" creato con successo' % self.name,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
