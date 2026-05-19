from odoo import api, fields, models


ROUTE_ACTIONS = [
    ('agent', 'AI Agent'),
    ('ivr', 'IVR Menu'),
    ('queue', 'Queue'),
    ('voicemail', 'Voicemail'),
    ('external', 'External Number'),
    ('callback', 'Callback Request'),
    ('hangup', 'Hangup'),
]


class CasaFolinoVoiceNumber(models.Model):
    _name = 'casafolino.voice.number'
    _description = 'CasaFolino Voice Number'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True)
    phone_number = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    provider = fields.Selection([
        ('ehiweb', 'Ehiweb / VivaVox'),
        ('twilio', 'Twilio'),
        ('telnyx', 'Telnyx'),
        ('other', 'Other'),
    ], default='ehiweb', required=True)
    default_agent_id = fields.Many2one('casafolino.voice.agent', domain=[('direction', '=', 'inbound')])
    default_routing_rule_id = fields.Many2one('casafolino.voice.routing.rule')
    notes = fields.Text()


class CasaFolinoVoiceSchedule(models.Model):
    _name = 'casafolino.voice.schedule'
    _description = 'CasaFolino Voice Business Hours'
    _order = 'name'

    name = fields.Char(required=True)
    timezone = fields.Char(default='Europe/Rome', required=True)
    line_ids = fields.One2many('casafolino.voice.schedule.line', 'schedule_id', string='Opening Hours')

    def is_open_now(self):
        self.ensure_one()
        now = fields.Datetime.context_timestamp(self.with_context(tz=self.timezone), fields.Datetime.now())
        weekday = str(now.weekday())
        hour = now.hour + (now.minute / 60.0)
        for line in self.line_ids.filtered(lambda item: item.dayofweek == weekday and item.active):
            if line.hour_from <= hour < line.hour_to:
                return True
        return False


class CasaFolinoVoiceScheduleLine(models.Model):
    _name = 'casafolino.voice.schedule.line'
    _description = 'CasaFolino Voice Business Hours Line'
    _order = 'dayofweek, hour_from'

    schedule_id = fields.Many2one('casafolino.voice.schedule', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], required=True)
    hour_from = fields.Float(required=True, default=9.0)
    hour_to = fields.Float(required=True, default=18.0)


class CasaFolinoVoiceQueue(models.Model):
    _name = 'casafolino.voice.queue'
    _description = 'CasaFolino Voice Queue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    strategy = fields.Selection([
        ('ring_all', 'Ring All'),
        ('round_robin', 'Round Robin'),
        ('least_recent', 'Least Recent'),
        ('manual', 'Manual Dispatch'),
    ], default='ring_all', required=True)
    user_ids = fields.Many2many('res.users', string='Members')
    timeout_seconds = fields.Integer(default=25)
    max_wait_seconds = fields.Integer(default=120)
    overflow_action = fields.Selection(ROUTE_ACTIONS, default='voicemail')
    overflow_agent_id = fields.Many2one('casafolino.voice.agent')
    overflow_external_number = fields.Char()
    greeting = fields.Text()

    def build_queue_payload(self):
        self.ensure_one()
        return {
            'type': 'queue',
            'queue_id': self.id,
            'queue_name': self.name,
            'strategy': self.strategy,
            'timeout_seconds': self.timeout_seconds,
            'max_wait_seconds': self.max_wait_seconds,
            'members': [{'id': user.id, 'name': user.name} for user in self.user_ids],
            'overflow': {
                'action': self.overflow_action,
                'agent_id': self.overflow_agent_id.id if self.overflow_agent_id else None,
                'external_number': self.overflow_external_number,
            },
        }


class CasaFolinoVoiceIvrMenu(models.Model):
    _name = 'casafolino.voice.ivr.menu'
    _description = 'CasaFolino Voice IVR Menu'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    prompt = fields.Text(required=True)
    repeat_prompt = fields.Text()
    max_attempts = fields.Integer(default=2)
    timeout_seconds = fields.Integer(default=6)
    option_ids = fields.One2many('casafolino.voice.ivr.option', 'menu_id', string='Options')
    fallback_action = fields.Selection(ROUTE_ACTIONS, default='agent')
    fallback_agent_id = fields.Many2one('casafolino.voice.agent', domain=[('direction', '=', 'inbound')])
    fallback_queue_id = fields.Many2one('casafolino.voice.queue')
    fallback_external_number = fields.Char()

    def build_ivr_payload(self):
        self.ensure_one()
        return {
            'type': 'ivr',
            'ivr_id': self.id,
            'ivr_name': self.name,
            'prompt': self.prompt,
            'repeat_prompt': self.repeat_prompt,
            'max_attempts': self.max_attempts,
            'timeout_seconds': self.timeout_seconds,
            'options': [option.build_option_payload() for option in self.option_ids.sorted('digit')],
            'fallback': {
                'action': self.fallback_action,
                'agent_id': self.fallback_agent_id.id if self.fallback_agent_id else None,
                'queue_id': self.fallback_queue_id.id if self.fallback_queue_id else None,
                'external_number': self.fallback_external_number,
            },
        }


class CasaFolinoVoiceIvrOption(models.Model):
    _name = 'casafolino.voice.ivr.option'
    _description = 'CasaFolino Voice IVR Option'
    _order = 'menu_id, digit'

    menu_id = fields.Many2one('casafolino.voice.ivr.menu', required=True, ondelete='cascade')
    digit = fields.Selection([
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
    ], required=True)
    label = fields.Char(required=True)
    action = fields.Selection(ROUTE_ACTIONS, default='agent', required=True)
    agent_id = fields.Many2one('casafolino.voice.agent')
    queue_id = fields.Many2one('casafolino.voice.queue')
    external_number = fields.Char()
    callback_reason = fields.Char()

    def build_option_payload(self):
        self.ensure_one()
        return {
            'digit': self.digit,
            'label': self.label,
            'action': self.action,
            'agent_id': self.agent_id.id if self.agent_id else None,
            'queue_id': self.queue_id.id if self.queue_id else None,
            'external_number': self.external_number,
            'callback_reason': self.callback_reason,
        }


class CasaFolinoVoiceRoutingRule(models.Model):
    _name = 'casafolino.voice.routing.rule'
    _description = 'CasaFolino Voice Routing Rule'
    _order = 'sequence, name'

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    number_id = fields.Many2one('casafolino.voice.number', string='Called Number')
    caller_contains = fields.Char(help='Optional caller phone fragment to match.')
    schedule_id = fields.Many2one('casafolino.voice.schedule', string='Business Hours')
    when = fields.Selection([
        ('always', 'Always'),
        ('open', 'During Business Hours'),
        ('closed', 'After Hours'),
    ], default='always', required=True)
    action = fields.Selection(ROUTE_ACTIONS, default='agent', required=True)
    agent_id = fields.Many2one('casafolino.voice.agent')
    ivr_menu_id = fields.Many2one('casafolino.voice.ivr.menu')
    queue_id = fields.Many2one('casafolino.voice.queue')
    external_number = fields.Char()
    voicemail_email = fields.Char()
    callback_reason = fields.Char()

    def _matches(self, caller_phone=None, called_number=None):
        self.ensure_one()
        if self.number_id and called_number and self.number_id.phone_number != called_number:
            return False
        if self.caller_contains and caller_phone and self.caller_contains not in caller_phone:
            return False
        if self.when == 'always' or not self.schedule_id:
            return True
        is_open = self.schedule_id.is_open_now()
        return (self.when == 'open' and is_open) or (self.when == 'closed' and not is_open)

    def build_route_payload(self):
        self.ensure_one()
        payload = {
            'rule_id': self.id,
            'rule_name': self.name,
            'action': self.action,
        }
        if self.action == 'agent' and self.agent_id:
            payload['agent'] = self.agent_id.build_realtime_payload()
        elif self.action == 'ivr' and self.ivr_menu_id:
            payload['ivr'] = self.ivr_menu_id.build_ivr_payload()
        elif self.action == 'queue' and self.queue_id:
            payload['queue'] = self.queue_id.build_queue_payload()
        elif self.action == 'external':
            payload['external_number'] = self.external_number
        elif self.action == 'voicemail':
            payload['voicemail_email'] = self.voicemail_email
        elif self.action == 'callback':
            payload['callback_reason'] = self.callback_reason
        return payload

    @api.model
    def resolve_inbound_route(self, caller_phone=None, called_number=None):
        rules = self.search([('active', '=', True)])
        for rule in rules:
            if rule._matches(caller_phone=caller_phone, called_number=called_number):
                return rule
        return self.browse()

