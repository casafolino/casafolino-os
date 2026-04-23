from odoo import fields, models


class CfInitiativeTemplate(models.Model):
    _name = 'cf.initiative.template'
    _description = 'Template Iniziativa (famiglia x variante -> atomi)'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    family_id = fields.Many2one('cf.initiative.family', required=True, ondelete='cascade')
    variant_id = fields.Many2one('cf.initiative.variant', required=True,
                                 domain="[('family_id', '=', family_id)]",
                                 ondelete='cascade')
    atom_ids = fields.Many2many('cf.initiative.atom', 'cf_initiative_template_atom_rel',
                                'template_id', 'atom_id', string='Atomi')
    description = fields.Text()

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Il codice template deve essere univoco.'),
        ('family_variant_uniq', 'unique(family_id, variant_id)',
         'Esiste già un template per questa combinazione famiglia/variante.'),
    ]
