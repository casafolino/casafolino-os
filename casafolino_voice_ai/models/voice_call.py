from odoo import api, fields, models


class CasaFolinoVoiceCall(models.Model):
    _name = 'casafolino.voice.call'
    _description = 'CasaFolino Voice AI Call'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'started_at desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], required=True, default='inbound', tracking=True)
    state = fields.Selection([
        ('new', 'New'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('transferred', 'Transferred'),
    ], default='new', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    phone = fields.Char(tracking=True)
    agent_id = fields.Many2one('casafolino.voice.agent', tracking=True)
    outbound_queue_id = fields.Many2one('casafolino.voice.outbound.queue', string='Outbound Job')
    external_call_id = fields.Char(index=True, copy=False)
    started_at = fields.Datetime(default=fields.Datetime.now, tracking=True)
    ended_at = fields.Datetime(tracking=True)
    duration_seconds = fields.Integer()
    outcome = fields.Selection([
        ('resolved', 'Resolved'),
        ('callback_requested', 'Callback Requested'),
        ('transferred', 'Transferred'),
        ('not_available', 'Not Available'),
        ('opt_out', 'Opt-out'),
        ('failed', 'Failed'),
        ('other', 'Other'),
    ], tracking=True)
    summary = fields.Text()
    next_action = fields.Text()
    transcript = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = sequence.next_by_code('casafolino.voice.call') or 'VOICE-CALL'
        return super().create(vals_list)

    def action_mark_completed(self):
        for call in self:
            call.write({
                'state': 'completed',
                'ended_at': fields.Datetime.now(),
            })

    def action_transfer(self):
        for call in self:
            call.write({
                'state': 'transferred',
                'outcome': 'transferred',
                'ended_at': fields.Datetime.now(),
            })

    def action_create_callback_activity(self):
        for call in self:
            if not call.partner_id:
                continue
            call.partner_id.activity_schedule(
                'mail.mail_activity_data_call',
                summary='Richiamare cliente da chiamata AI',
                note=call.summary or call.next_action or 'Richiamata richiesta dal centralino AI.',
            )

