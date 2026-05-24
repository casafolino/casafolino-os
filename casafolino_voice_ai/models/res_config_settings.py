from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    voice_ai_public_base_url = fields.Char(
        string='Public Base URL',
        config_parameter='casafolino_voice_ai.public_base_url',
        help='Public Odoo URL used by the telephony bridge and OpenAI webhooks.',
    )
    voice_ai_webhook_token = fields.Char(
        string='Webhook Token',
        config_parameter='casafolino_voice_ai.webhook_token',
        help='Bearer token required by Voice AI bridge endpoints. Leave empty only during local testing.',
    )
    voice_ai_openai_api_key = fields.Char(
        string='OpenAI API Key',
        config_parameter='casafolino_voice_ai.openai_api_key',
        groups='base.group_system',
    )
    voice_ai_openai_realtime_model = fields.Char(
        string='Realtime Model',
        default='gpt-realtime-2',
        config_parameter='casafolino_voice_ai.openai_realtime_model',
    )
    voice_ai_openai_voice = fields.Char(
        string='Realtime Voice',
        default='marin',
        config_parameter='casafolino_voice_ai.openai_voice',
    )
    voice_ai_human_transfer_uri = fields.Char(
        string='Human Transfer URI',
        config_parameter='casafolino_voice_ai.human_transfer_uri',
        help='SIP or tel URI used when the assistant must transfer to a human.',
    )
    voice_ai_allow_outbound = fields.Boolean(
        string='Allow Outbound Calls',
        config_parameter='casafolino_voice_ai.allow_outbound',
    )
    voice_ai_require_token = fields.Boolean(
        string='Require Token',
        config_parameter='casafolino_voice_ai.require_token',
        default=True,
        help='When enabled, all operational Voice AI endpoints require Authorization: Bearer <token>.',
    )

