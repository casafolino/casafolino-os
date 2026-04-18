from odoo import api, fields, models


class CasafolinoMailSnippetPicker(models.TransientModel):
    _name = 'casafolino.mail.snippet.picker'
    _description = 'Selettore snippet per risposta email'

    message_id = fields.Many2one('casafolino.mail.message', string='Email')
    language = fields.Selection([
        ('it', 'Italiano'),
        ('en', 'English'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
        ('es', 'Español'),
    ], string='Lingua', default='it', required=True)
    category = fields.Selection([
        ('listino', 'Listino / Prezzi'),
        ('campioni', 'Campioni'),
        ('moq', 'MOQ / Palletizzazione'),
        ('certificazioni', 'Certificazioni'),
        ('follow_up', 'Follow-up'),
        ('ringraziamento', 'Ringraziamento'),
        ('documenti', 'Documenti richiesti'),
        ('altro', 'Altro'),
    ], string='Categoria')
    snippet_id = fields.Many2one('casafolino.mail.snippet', string='Snippet',
        domain="[('language', '=', language), ('active', '=', True)]")
    preview = fields.Text('Anteprima', compute='_compute_preview', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        msg_id = self.env.context.get('active_id')
        if msg_id:
            msg = self.env['casafolino.mail.message'].browse(msg_id)
            if msg.exists():
                res['message_id'] = msg.id
                if msg.ai_language and msg.ai_language in ('it', 'en', 'de', 'fr', 'es'):
                    res['language'] = msg.ai_language
        return res

    @api.depends('snippet_id', 'message_id')
    def _compute_preview(self):
        for rec in self:
            if rec.snippet_id:
                partner = rec.message_id.partner_id if rec.message_id else None
                rec.preview = rec.snippet_id._render_snippet(
                    partner=partner, user=self.env.user)
            else:
                rec.preview = ''

    def action_copy_and_close(self):
        """Incrementa contatore e ritorna azione clipboard JS."""
        self.ensure_one()
        if not self.snippet_id:
            return {'type': 'ir.actions.act_window_close'}
        self.snippet_id.action_increment_usage()
        rendered = self.preview or self.snippet_id.body
        return {
            'type': 'ir.actions.client',
            'tag': 'casafolino_mail.copy_snippet',
            'params': {'text': rendered},
        }
