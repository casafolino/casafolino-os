from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    voice_consent_ids = fields.One2many('casafolino.voice.consent', 'partner_id', string='Voice AI Consents')
    voice_call_ids = fields.One2many('casafolino.voice.call', 'partner_id', string='Voice AI Calls')
    voice_outbound_queue_ids = fields.One2many('casafolino.voice.outbound.queue', 'partner_id', string='Voice AI Follow-ups')
    voice_ai_language = fields.Selection([
        ('auto', 'Ask / Auto-detect'),
        ('it-IT', 'Italian'),
        ('en-US', 'English'),
        ('fr-FR', 'French'),
        ('es-ES', 'Spanish'),
        ('de-DE', 'German'),
    ], string='Voice AI language', default='auto')
    voice_outbound_consent = fields.Boolean(
        string='Voice outbound consent',
        compute='_compute_voice_outbound_consent',
        store=False,
    )

    def _compute_voice_outbound_consent(self):
        for partner in self:
            partner.voice_outbound_consent = any(partner.voice_consent_ids.filtered('consent_outbound'))

    def action_voice_ai_enqueue_followup(self):
        self.ensure_one()
        phone = self.phone or self.mobile
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuovo follow-up vocale AI',
            'res_model': 'casafolino.voice.outbound.queue',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.id,
                'default_phone': phone,
                'default_reason': 'Follow-up cliente',
                'default_language': self.voice_ai_language or 'auto',
            },
        }
