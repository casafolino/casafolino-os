from odoo import fields, models


class CasaFolinoVoiceKnowledge(models.Model):
    _name = 'casafolino.voice.knowledge'
    _description = 'CasaFolino Voice AI Knowledge'
    _order = 'sequence, category, title'

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    category = fields.Selection([
        ('company', 'Company'),
        ('products', 'Products'),
        ('formats', 'Formats'),
        ('certifications', 'Certifications'),
        ('operations', 'Operations'),
        ('markets', 'Markets'),
        ('services', 'Services'),
        ('guardrails', 'Guardrails'),
    ], required=True, default='products')
    title = fields.Char(required=True)
    keywords = fields.Char(help='Comma-separated search keywords used by the voice agent.')
    content = fields.Text(required=True)
    source = fields.Char()

    def build_payload(self):
        return [{
            'id': item.id,
            'category': item.category,
            'title': item.title,
            'content': item.content,
            'source': item.source,
        } for item in self]
