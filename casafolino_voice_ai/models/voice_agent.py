from odoo import fields, models


VOICE_AI_TOOL_SCHEMAS = [
    {
        'type': 'function',
        'name': 'lookup_customer',
        'description': 'Cerca un cliente CasaFolino per numero di telefono, nome o email.',
        'parameters': {
            'type': 'object',
            'properties': {
                'phone': {'type': 'string'},
                'name': {'type': 'string'},
                'email': {'type': 'string'},
            },
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'create_callback',
        'description': 'Crea una attivita di richiamata su un cliente o contatto.',
        'parameters': {
            'type': 'object',
            'properties': {
                'call_id': {'type': 'integer'},
                'partner_id': {'type': 'integer'},
                'customer_name': {'type': 'string'},
                'phone': {'type': 'string'},
                'reason': {'type': 'string'},
                'urgency': {'type': 'string', 'enum': ['low', 'normal', 'high']},
            },
            'required': ['phone', 'reason'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'record_call_outcome',
        'description': 'Registra esito, riepilogo e prossima azione della chiamata.',
        'parameters': {
            'type': 'object',
            'properties': {
                'call_id': {'type': 'integer'},
                'outcome': {
                    'type': 'string',
                    'enum': ['resolved', 'callback_requested', 'transferred', 'not_available', 'opt_out', 'failed', 'other'],
                },
                'summary': {'type': 'string'},
                'next_action': {'type': 'string'},
                'detected_language': {'type': 'string'},
            },
            'required': ['call_id', 'outcome', 'summary'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'opt_out_customer',
        'description': 'Registra opt-out del cliente da futuri follow-up vocali.',
        'parameters': {
            'type': 'object',
            'properties': {
                'partner_id': {'type': 'integer'},
                'phone': {'type': 'string'},
                'reason': {'type': 'string'},
            },
            'required': ['phone'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'transfer_to_human',
        'description': 'Richiede trasferimento o presa in carico umana.',
        'parameters': {
            'type': 'object',
            'properties': {
                'call_id': {'type': 'integer'},
                'department': {'type': 'string', 'enum': ['commerciale', 'assistenza', 'amministrazione', 'generale']},
                'reason': {'type': 'string'},
            },
            'required': ['reason'],
            'additionalProperties': False,
        },
    },
]


class CasaFolinoVoiceAgent(models.Model):
    _name = 'casafolino.voice.agent'
    _description = 'CasaFolino Voice AI Agent'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'direction, name'

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], required=True, default='inbound', tracking=True)
    model = fields.Char(default='gpt-realtime-2', required=True)
    voice = fields.Char(default='marin', required=True)
    language = fields.Char(default='it-IT', required=True)
    persona = fields.Text()
    first_message = fields.Char()
    instructions = fields.Text(required=True)
    success_criteria = fields.Text()
    guardrails = fields.Text()
    language_policy = fields.Text()
    tool_policy = fields.Text()
    transfer_policy = fields.Text()
    closing_policy = fields.Text()
    max_turns = fields.Integer(default=12)
    allow_tools = fields.Boolean(default=True)
    temperature = fields.Float(default=0.4)

    def _compose_instructions(self, extra_context=None):
        self.ensure_one()
        sections = [
            ('Ruolo', self.persona),
            ('Prima frase', self.first_message),
            ('Istruzioni operative', self.instructions),
            ('Policy lingua', self.language_policy),
            ('Criteri di successo', self.success_criteria),
            ('Uso strumenti', self.tool_policy),
            ('Escalation', self.transfer_policy),
            ('Guardrail', self.guardrails),
            ('Chiusura chiamata', self.closing_policy),
        ]
        chunks = []
        for title, body in sections:
            if body:
                chunks.append('%s:\n%s' % (title, body))
        if extra_context:
            lines = ['Contesto operativo:']
            for key, value in extra_context.items():
                if value:
                    lines.append('- %s: %s' % (key, value))
            chunks.append('\n'.join(lines))
        return '\n\n'.join(chunks)

    def build_realtime_payload(self, extra_context=None):
        self.ensure_one()
        payload = {
            'type': 'realtime',
            'model': self.model,
            'voice': self.voice,
            'instructions': self._compose_instructions(extra_context=extra_context),
            'temperature': self.temperature,
            'metadata': {
                'agent_id': self.id,
                'agent_name': self.name,
                'direction': self.direction,
                'language': self.language,
            },
        }
        if self.allow_tools:
            payload['tools'] = VOICE_AI_TOOL_SCHEMAS
            payload['tool_choice'] = 'auto'
        return payload
