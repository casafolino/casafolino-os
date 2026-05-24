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
        'name': 'lookup_knowledge',
        'description': 'Cerca informazioni approvate su CasaFolino, prodotti, formati, certificazioni, capacita produttiva, mercati e private label.',
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string'},
                'category': {
                    'type': 'string',
                    'enum': ['company', 'products', 'formats', 'certifications', 'operations', 'markets', 'services', 'guardrails'],
                },
            },
            'required': ['query'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'lookup_order_status',
        'description': 'Cerca lo stato di un ordine Odoo usando riferimento ordine, cliente, telefono o email.',
        'parameters': {
            'type': 'object',
            'properties': {
                'order_name': {'type': 'string'},
                'partner_id': {'type': 'integer'},
                'customer_name': {'type': 'string'},
                'phone': {'type': 'string'},
                'email': {'type': 'string'},
            },
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'create_call_note',
        'description': 'Crea una nota interna in Odoo collegata a chiamata, cliente o lead.',
        'parameters': {
            'type': 'object',
            'properties': {
                'call_id': {'type': 'integer'},
                'partner_id': {'type': 'integer'},
                'lead_id': {'type': 'integer'},
                'note': {'type': 'string'},
                'summary': {'type': 'string'},
            },
            'required': ['note'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'create_crm_lead',
        'description': 'Crea un lead/opportunita CRM da una chiamata commerciale o da una richiesta prodotto.',
        'parameters': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'partner_id': {'type': 'integer'},
                'contact_name': {'type': 'string'},
                'company_name': {'type': 'string'},
                'phone': {'type': 'string'},
                'email': {'type': 'string'},
                'country': {'type': 'string'},
                'interest': {'type': 'string'},
                'description': {'type': 'string'},
            },
            'required': ['name', 'interest'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'create_email_activity',
        'description': 'Crea una attivita email da preparare/inviare da un umano, senza inviare automaticamente email.',
        'parameters': {
            'type': 'object',
            'properties': {
                'partner_id': {'type': 'integer'},
                'lead_id': {'type': 'integer'},
                'email': {'type': 'string'},
                'subject': {'type': 'string'},
                'body': {'type': 'string'},
            },
            'required': ['subject', 'body'],
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
