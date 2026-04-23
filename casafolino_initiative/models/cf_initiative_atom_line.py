from odoo import _, api, fields, models


GENERATED_MODELS = [
    ('project.task', 'Project Task'),
    ('mail.activity', 'Mail Activity'),
    ('crm.lead', 'CRM Lead'),
    ('sale.order', 'Sale Order'),
    ('stock.picking', 'Stock Picking'),
    ('account.move', 'Account Move'),
    ('mrp.production', 'MRP Production'),
]


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

    # F2: Generation tracking
    generated_model = fields.Char(readonly=True)
    generated_res_id = fields.Integer(readonly=True)
    generated_ref = fields.Reference(
        selection='_selection_target_model',
        compute='_compute_generated_ref', store=True, readonly=True)
    generation_state = fields.Selection([
        ('pending', 'Da Generare'),
        ('generated', 'Generato'),
        ('error', 'Errore'),
        ('manual', 'Manuale'),
    ], default='pending', readonly=True)
    generation_error = fields.Text(readonly=True)
    generated_at = fields.Datetime(readonly=True)

    @api.model
    def _selection_target_model(self):
        return GENERATED_MODELS

    @api.depends('generated_model', 'generated_res_id')
    def _compute_generated_ref(self):
        for line in self:
            if line.generated_model and line.generated_res_id:
                line.generated_ref = f'{line.generated_model},{line.generated_res_id}'
            else:
                line.generated_ref = False

    def action_generate(self):
        """Manual generation button for atoms with generate_on_create=False."""
        self.ensure_one()
        self.env['cf.initiative.atom.generator'].generate(self)

    def action_regenerate(self):
        """Retry generation for atoms in error state."""
        self.ensure_one()
        self.write({
            'generation_state': 'pending',
            'generation_error': False,
        })
        self.env['cf.initiative.atom.generator'].generate(self)
