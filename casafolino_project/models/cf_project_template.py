from odoo import models, fields


CF_PROJECT_TYPES = [
    ('sample_fair', 'Campionatura Fiera'),
    ('sample_client', 'Campionatura Cliente'),
    ('custom_label', 'Etichetta Personalizzata'),
    ('new_product', 'Lancio Nuovo Prodotto'),
    ('fair_prep', 'Preparazione Fiera'),
    ('strategic', 'Progetto Strategico'),
]

CF_WAITING_FOR = [
    ('none', 'Nessuno'),
    ('client', 'Cliente'),
    ('graphic', 'Grafico'),
    ('printer', 'Tipografia'),
    ('production', 'Produzione'),
    ('internal', 'Interno'),
    ('supplier', 'Fornitore'),
]


class CfProjectTemplate(models.Model):
    _name = 'cf.project.template'
    _description = 'Template Progetto CasaFolino'

    name = fields.Char(string="Nome Template", required=True)
    cf_project_type = fields.Selection(CF_PROJECT_TYPES, string="Tipo Progetto")
    task_template_ids = fields.One2many(
        'cf.project.task.template', 'template_id', string="Task del Template")
    active = fields.Boolean(default=True)
    description = fields.Html(string="Descrizione")


class CfProjectTaskTemplate(models.Model):
    _name = 'cf.project.task.template'
    _description = 'Task Template CasaFolino'
    _order = 'sequence'

    template_id = fields.Many2one(
        'cf.project.template', required=True, ondelete='cascade')
    name = fields.Char(string="Nome Task", required=True)
    sequence = fields.Integer(string="Ordine", default=10)
    relative_days = fields.Integer(
        string="Giorni Relativi alla Deadline",
        help="Es: -30 = 30 giorni prima della deadline progetto")
    default_user_id = fields.Many2one('res.users', string="Responsabile Default")
    cf_waiting_for = fields.Selection(CF_WAITING_FOR, string="In Attesa Di", default='none')
    description = fields.Html(string="Istruzioni")
    auto_activate_next = fields.Boolean(string="Attiva Successiva", default=True)
    stage_name = fields.Char(string="Stage Iniziale")
    checklist_template_ids = fields.One2many(
        'cf.project.checklist.template', 'task_template_id',
        string="Checklist Template")
    checklist_required = fields.Boolean(string="Checklist Obbligatoria", default=False)
