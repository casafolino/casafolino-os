from odoo import fields, models

ROLE_SELECTION = [
    ('commerciale', 'Commerciale'),
    ('backoffice', 'Backoffice'),
    ('produzione', 'Produzione'),
    ('logistica', 'Logistica'),
    ('etichette', 'Etichette'),
    ('amministrazione', 'Amministrazione'),
]


class CfInitiativeTemplateStage(models.Model):
    _name = 'cf.initiative.template.stage'
    _description = 'Fase Template Staffetta'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'cf.initiative.template', ondelete='cascade', required=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    role = fields.Selection(ROLE_SELECTION, string='Ruolo')
    default_user_id = fields.Many2one('res.users', string='Utente Default')
    task_names = fields.Text(string='Task predefiniti', help='Un task per riga')
    optional = fields.Boolean(default=False)
    require_feedback = fields.Boolean(default=False, string='Feedback obbligatorio')
    require_shipment = fields.Boolean(default=False, string='Richiede spedizione')
