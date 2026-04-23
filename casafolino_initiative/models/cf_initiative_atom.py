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

    # F2: Generation configuration
    generate_on_create = fields.Boolean(
        default=True,
        help="Se True, al create atom_line genera oggetto Odoo automaticamente")
    subject_template = fields.Char(
        translate=True,
        help="Template inline per subject/name dell'oggetto generato")
    body_template = fields.Html(
        translate=True,
        help="Template inline per body/description")
    task_stage_default = fields.Many2one(
        'project.task.type',
        help="Stage default per project_task")
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        help="Tipo activity per mail_activity")
    sample_product_ids = fields.Many2many(
        'product.product',
        help="Prodotti default per sample picking")
    journal_id = fields.Many2one(
        'account.journal',
        help="Journal default per fatture generate")
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        help="Tipo picking default")

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Il codice atomo deve essere univoco.'),
    ]
