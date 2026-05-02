from odoo import api, fields, models


class MailTemplateTag(models.Model):
    _name = 'casafolino.mail.template.tag'
    _description = 'Tag per organizzare template email CasaFolino'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    color = fields.Integer(default=0)
    sequence = fields.Integer(default=10)
    description = fields.Char()
    is_fair_tag = fields.Boolean(string='Tag Fiera', default=False)
    template_count = fields.Integer(compute='_compute_template_count')

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'Tag nome deve essere univoco'),
    ]

    def _compute_template_count(self):
        for tag in self:
            tag.template_count = self.env['mail.template'].search_count(
                [('cf_tag_ids', 'in', tag.id)])
