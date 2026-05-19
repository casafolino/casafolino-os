from odoo import fields, models


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
    instructions = fields.Text(required=True)
    transfer_policy = fields.Text()
    max_turns = fields.Integer(default=12)
    allow_tools = fields.Boolean(default=True)

    def build_realtime_payload(self, extra_context=None):
        self.ensure_one()
        instructions = self.instructions or ''
        if extra_context:
            lines = ['Contesto operativo:']
            for key, value in extra_context.items():
                if value:
                    lines.append('- %s: %s' % (key, value))
            instructions = '%s\n\n%s' % (instructions, '\n'.join(lines))

        return {
            'type': 'realtime',
            'model': self.model,
            'voice': self.voice,
            'instructions': instructions,
            'metadata': {
                'agent_id': self.id,
                'agent_name': self.name,
                'direction': self.direction,
                'language': self.language,
            },
        }

