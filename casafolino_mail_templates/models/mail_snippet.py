from odoo import fields, models


class MailSnippet(models.Model):
    _name = 'casafolino.mail.snippet'
    _description = 'Blocchi HTML riutilizzabili nei template email'
    _order = 'category, sequence, name'

    name = fields.Char(required=True)
    category = fields.Selection([
        ('opening', 'Apertura'),
        ('intro', 'Intro CasaFolino'),
        ('product', 'Categorie prodotto'),
        ('certifications', 'Certificazioni'),
        ('attachments', 'Box allegati'),
        ('cta', 'Call-to-action'),
        ('signature', 'Firma'),
        ('custom', 'Custom'),
    ], required=True, default='custom')
    sequence = fields.Integer(default=10)
    body_html = fields.Html(required=True, sanitize=False)
    description = fields.Char()
    language = fields.Selection([
        ('en', 'English'),
        ('fr', 'Français'),
        ('it', 'Italiano'),
        ('es', 'Español'),
        ('any', 'Qualsiasi'),
    ], default='any')
    is_active = fields.Boolean(default=True)
