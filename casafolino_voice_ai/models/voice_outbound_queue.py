from odoo import api, fields, models


class CasaFolinoVoiceOutboundQueue(models.Model):
    _name = 'casafolino.voice.outbound.queue'
    _description = 'CasaFolino Voice AI Outbound Queue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_at asc, id asc'

    name = fields.Char(default='New', copy=False, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    phone = fields.Char(required=True, tracking=True)
    reason = fields.Char(required=True, tracking=True)
    state = fields.Selection([
        ('queued', 'Queued'),
        ('ready', 'Ready'),
        ('calling', 'Calling'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('opt_out', 'Opt-out'),
        ('cancelled', 'Cancelled'),
        ('blocked', 'Blocked'),
    ], default='queued', tracking=True)
    scheduled_at = fields.Datetime(default=fields.Datetime.now, tracking=True)
    attempt_count = fields.Integer(default=0)
    max_attempts = fields.Integer(default=2)
    last_attempt_at = fields.Datetime()
    call_id = fields.Many2one('casafolino.voice.call', string='Last Call')
    agent_id = fields.Many2one('casafolino.voice.agent', domain=[('direction', '=', 'outbound')])
    consent_checked = fields.Boolean(default=False)
    blocked_reason = fields.Char()
    external_job_id = fields.Char(copy=False, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = sequence.next_by_code('casafolino.voice.outbound.queue') or 'VOICE-OUT'
        return super().create(vals_list)

    def _has_outbound_consent(self):
        self.ensure_one()
        consent = self.env['casafolino.voice.consent'].search([
            ('partner_id', '=', self.partner_id.id),
            ('phone', '=', self.phone),
            ('consent_outbound', '=', True),
        ], limit=1)
        return bool(consent)

    def action_check_ready(self):
        now = fields.Datetime.now()
        for job in self:
            vals = {'consent_checked': True}
            if job.attempt_count >= job.max_attempts:
                vals.update({'state': 'blocked', 'blocked_reason': 'Tentativi massimi raggiunti'})
            elif job.scheduled_at and job.scheduled_at > now:
                vals.update({'state': 'queued', 'blocked_reason': False})
            elif not job._has_outbound_consent():
                vals.update({'state': 'blocked', 'blocked_reason': 'Consenso outbound mancante'})
            else:
                vals.update({'state': 'ready', 'blocked_reason': False})
            job.write(vals)

    def action_mark_calling(self):
        for job in self:
            call = self.env['casafolino.voice.call'].create({
                'direction': 'outbound',
                'state': 'active',
                'partner_id': job.partner_id.id,
                'phone': job.phone,
                'agent_id': job.agent_id.id if job.agent_id else False,
                'outbound_queue_id': job.id,
            })
            job.write({
                'state': 'calling',
                'attempt_count': job.attempt_count + 1,
                'last_attempt_at': fields.Datetime.now(),
                'call_id': call.id,
            })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def cron_process_outbound_queue(self):
        jobs = self.search([
            ('state', 'in', ['queued', 'ready']),
            ('scheduled_at', '<=', fields.Datetime.now()),
        ], limit=25)
        jobs.action_check_ready()
        return True

    @api.model
    def get_next_ready_job_payload(self):
        job = self.search([('state', '=', 'ready')], limit=1)
        if not job:
            return {}
        agent = job.agent_id or self.env['casafolino.voice.agent'].search([
            ('direction', '=', 'outbound'),
            ('active', '=', True),
        ], limit=1)
        job.action_mark_calling()
        return {
            'job_id': job.id,
            'phone': job.phone,
            'partner_id': job.partner_id.id,
            'partner_name': job.partner_id.display_name,
            'reason': job.reason,
            'agent': agent.build_realtime_payload({
                'cliente': job.partner_id.display_name,
                'telefono': job.phone,
                'motivo': job.reason,
            }) if agent else {},
        }

