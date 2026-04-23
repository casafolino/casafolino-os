from odoo import fields, models


class CfInitiativeAtomLine(models.Model):
    _name = 'cf.initiative.atom.line'
    _description = 'Istanza Atomo su Iniziativa'
    _order = 'sequence, id'

    initiative_id = fields.Many2one('cf.initiative', required=True, ondelete='cascade')
    atom_id = fields.Many2one('cf.initiative.atom', required=True, ondelete='restrict')
    user_id = fields.Many2one('res.users', string='Responsabile')
    date_deadline = fields.Date(string='Scadenza')
    state = fields.Selection([
        ('todo', 'Da Fare'),
        ('in_progress', 'In Corso'),
        ('done', 'Fatto'),
        ('skipped', 'Saltato'),
    ], default='todo')
    sequence = fields.Integer(default=10)
    note = fields.Text()
