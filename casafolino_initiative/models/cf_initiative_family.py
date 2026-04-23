from odoo import fields, models


class CfInitiativeFamily(models.Model):
    _name = 'cf.initiative.family'
    _description = 'Famiglia Iniziativa'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    description = fields.Text(translate=True)
    icon = fields.Char(help='FontAwesome icon class, es. fa-handshake-o')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    variant_ids = fields.One2many('cf.initiative.variant', 'family_id', string='Varianti')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Il codice famiglia deve essere univoco.'),
    ]
