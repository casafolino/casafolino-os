from odoo import fields, models


class CasaFolinoVoiceConsent(models.Model):
    _name = 'casafolino.voice.consent'
    _description = 'CasaFolino Voice AI Consent'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'write_date desc, id desc'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', tracking=True)
    phone = fields.Char(required=True, tracking=True)
    consent_outbound = fields.Boolean(string='Outbound consent', default=False, tracking=True)
    consent_source = fields.Selection([
        ('customer_request', 'Customer Request'),
        ('existing_relationship', 'Existing Relationship'),
        ('written_consent', 'Written Consent'),
        ('manual', 'Manual'),
    ], default='existing_relationship', required=True)
    consent_date = fields.Datetime()
    opt_out_date = fields.Datetime()
    opt_out_reason = fields.Text()
    notes = fields.Text()

    def action_opt_out(self):
        for consent in self:
            consent.write({
                'consent_outbound': False,
                'opt_out_date': fields.Datetime.now(),
                'opt_out_reason': consent.opt_out_reason or 'Opt-out richiesto dal cliente',
            })

