from odoo import fields, models


class CfInitiativeVariant(models.Model):
    _name = 'cf.initiative.variant'
    _description = 'Variante Iniziativa'
    _order = 'family_id, sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    family_id = fields.Many2one('cf.initiative.family', required=True, ondelete='cascade')
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Il codice variante deve essere univoco.'),
    ]
