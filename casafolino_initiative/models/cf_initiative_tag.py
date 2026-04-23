from odoo import fields, models


class CfInitiativeTag(models.Model):
    _name = 'cf.initiative.tag'
    _description = 'Tag Iniziativa'
    _order = 'category, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, copy=False)
    color = fields.Integer()
    category = fields.Selection([
        ('fair', 'Fiera'),
        ('campaign', 'Campagna'),
        ('strategic', 'Strategico'),
        ('market', 'Mercato'),
    ])
    description = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Il codice tag deve essere univoco.'),
    ]
