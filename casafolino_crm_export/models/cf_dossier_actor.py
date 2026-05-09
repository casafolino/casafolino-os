from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CfDossierActor(models.Model):
    _name = 'cf.dossier.actor'
    _description = 'Network e Commissioni Dossier'
    _order = 'sequence, id'

    project_id = fields.Many2one(
        'project.project', string='Dossier',
        ondelete='cascade', required=True, index=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Contatto esterno',
    )
    user_id = fields.Many2one(
        'res.users', string='Operatore interno',
    )

    role = fields.Selection([
        ('broker', 'Broker'),
        ('referrer', 'Segnalatore'),
        ('agent', 'Agente'),
        ('co_responsible', 'Co-responsabile interno'),
        ('back_office', 'Supporto back office'),
        ('consultant', 'Consulente'),
        ('other', 'Altro'),
    ], string='Ruolo', required=True)

    commission_basis = fields.Selection([
        ('revenue', '% su Fatturato'),
        ('margin', '% su Margine'),
        ('quantity', 'EUR per Unita venduta'),
        ('fixed', 'Importo fisso'),
        ('none', 'Nessuna commissione'),
    ], string='Base commissione', default='none', required=True)

    commission_value = fields.Float(
        'Valore commissione',
        help='Significato dipende da basis: % se revenue/margin, EUR/unita se quantity, EUR fisso se fixed',
    )
    commission_currency_id = fields.Many2one(
        'res.currency', string='Valuta',
        default=lambda self: self.env.company.currency_id,
    )

    notes = fields.Text('Note')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    @api.constrains('partner_id', 'user_id')
    def _check_one_actor(self):
        for rec in self:
            if not rec.partner_id and not rec.user_id:
                raise ValidationError(
                    'Specifica un contatto esterno o un operatore interno.')
            if rec.partner_id and rec.user_id:
                raise ValidationError(
                    'Specifica solo uno tra contatto esterno e operatore interno, non entrambi.')
