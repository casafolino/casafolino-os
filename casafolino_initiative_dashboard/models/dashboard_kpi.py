from odoo import fields, models


class CasafolinoDashboardKpi(models.Model):
    _name = 'casafolino.dashboard.kpi'
    _description = 'KPI Configurabile per Lavagna Iniziativa'
    _order = 'sequence, id'

    name = fields.Char(string="Nome KPI", required=True, translate=True)
    sequence = fields.Integer(default=10)
    target_model = fields.Selection([
        ('project.task', 'Task Progetto'),
        ('crm.lead', 'Lead CRM'),
        ('sale.order', 'Ordini Vendita'),
        ('stock.picking', 'Spedizioni'),
        ('mail.message', 'Messaggi Mail'),
    ], string="Modello Target", required=True, default='project.task')
    domain = fields.Char(
        string="Filtro (Domain)",
        required=True,
        default='[]',
        help="Domain Odoo applicato al modello target. "
             "Filtro [('initiative_id', '=', current_initiative)] aggiunto in runtime.",
    )
    icon = fields.Char(string="Icona FontAwesome", default="fa-tasks")
    color = fields.Char(string="Colore HEX", default="#875A7B")
    active = fields.Boolean(default=True)
