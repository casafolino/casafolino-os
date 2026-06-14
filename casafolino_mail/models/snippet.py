from odoo import api, fields, models


class CasafolinoMailSnippet(models.Model):
    _name = 'casafolino.mail.snippet'
    _description = 'Snippet risposte multilingua'
    _order = 'category, language, name'

    name = fields.Char('Titolo', required=True)
    code = fields.Char('Codice', required=True)
    category = fields.Selection([
        ('listino', 'Listino / Prezzi'),
        ('campioni', 'Campioni'),
        ('moq', 'MOQ / Palletizzazione'),
        ('certificazioni', 'Certificazioni'),
        ('follow_up', 'Follow-up'),
        ('ringraziamento', 'Ringraziamento'),
        ('documenti', 'Documenti richiesti'),
        ('altro', 'Altro'),
    ], string='Categoria', required=True)
    language = fields.Selection([
        ('it', 'Italiano'),
        ('en', 'English'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
        ('es', 'Español'),
    ], string='Lingua', required=True)
    subject = fields.Char('Oggetto email suggerito')
    body = fields.Text('Testo snippet', required=True)
    active = fields.Boolean(default=True)
    usage_count = fields.Integer('Utilizzi', readonly=True, default=0)
    last_used = fields.Datetime('Ultimo utilizzo', readonly=True)
    notes = fields.Text('Note interne')

    _sql_constraints = [
        ('code_language_unique', 'UNIQUE(code, language)',
         'Esiste già uno snippet con questo codice e lingua.'),
    ]

    def _render_snippet(self, partner=None, user=None):
        """Sostituisce placeholder nel body con dati reali."""
        self.ensure_one()
        text = self.body or ''
        replacements = {
            '{our_name}': 'CasaFolino',
        }
        if partner:
            replacements['{partner_name}'] = partner.name or '{partner_name}'
            replacements['{partner_company}'] = (
                partner.parent_id.name if partner.parent_id else partner.name
            ) or '{partner_company}'
        if user:
            replacements['{my_name}'] = user.name or '{my_name}'
            account = self.env['casafolino.mail.account'].search([
                ('responsible_user_id', '=', user.id),
                ('signature_html', '!=', False),
            ], limit=1)
            if account and account.signature_html:
                # Strip HTML for plain text signature
                import re
                sig = re.sub(r'<[^>]+>', '', account.signature_html)
                sig = re.sub(r'\s+', ' ', sig).strip()
                replacements['{my_signature}'] = sig
            else:
                replacements['{my_signature}'] = user.name or '{my_signature}'
        for key, val in replacements.items():
            text = text.replace(key, val)
        return text

    def action_increment_usage(self):
        """Incrementa contatore uso."""
        self.ensure_one()
        self.write({
            'usage_count': self.usage_count + 1,
            'last_used': fields.Datetime.now(),
        })
