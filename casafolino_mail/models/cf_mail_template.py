from odoo import models, fields, api


class CfMailTemplate(models.Model):
    _name = 'cf.mail.template'
    _description = 'Template Email CasaFolino'
    _order = 'category, name'

    name = fields.Char('Nome template', required=True)
    subject = fields.Char('Oggetto')
    body_html = fields.Html('Corpo', sanitize=False)
    language = fields.Selection([
        ('it', 'Italiano'), ('en', 'English'), ('de', 'Deutsch'),
        ('fr', 'Francais'), ('es', 'Espanol'),
    ], string='Lingua', default='it')
    category = fields.Selection([
        ('followup', 'Follow-up'), ('intro', 'Presentazione'),
        ('offer', 'Offerta'), ('sample', 'Campionatura'),
        ('general', 'Generale'),
    ], string='Categoria', default='general')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'cf_mail_template_attachment_rel',
        'template_id', 'attachment_id', string='Allegati di default')
    user_id = fields.Many2one('res.users', string='Creato da',
                               default=lambda self: self.env.uid)
    active = fields.Boolean(default=True)

    @api.model
    def get_templates(self, *args, **kw):
        """Ritorna template raggruppati per categoria."""
        templates = self.search([('active', '=', True)], order='category, name')
        result = []
        for t in templates:
            atts = []
            for a in t.attachment_ids:
                atts.append({
                    'id': a.id,
                    'name': a.name,
                    'mimetype': a.mimetype or '',
                    'size': len(a.datas or b'') if a.datas else 0,
                })
            result.append({
                'id': t.id,
                'name': t.name,
                'subject': t.subject or '',
                'body_html': t.body_html or '',
                'language': t.language or '',
                'category': t.category or 'general',
                'attachments': atts,
            })
        return result
