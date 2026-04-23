from odoo import fields, models


class CfInitiativeAtom(models.Model):
    _name = 'cf.initiative.atom'
    _description = 'Atomo Iniziativa (catalogo)'
    _order = 'sequence, code'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, copy=False)
    description = fields.Text(translate=True)
    default_user_id = fields.Many2one('res.users')
    default_duration_days = fields.Integer(default=1)
    email_template_id = fields.Many2one('mail.template')
    odoo_object_type = fields.Selection([
        ('none', 'Nessuno'),
        ('project_task', 'Project Task'),
        ('mail_activity', 'Mail Activity'),
        ('crm_lead', 'CRM Lead'),
        ('sale_order', 'Sale Order'),
        ('stock_picking', 'Stock Picking'),
        ('account_move', 'Account Move'),
        ('mrp_production', 'MRP Production'),
    ], default='none')
    is_core = fields.Boolean()
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Il codice atomo deve essere univoco.'),
    ]
