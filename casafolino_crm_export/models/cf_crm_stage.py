from odoo import fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    cf_probability_default = fields.Float(
        string='Probabilità Default (%)',
        help='Probabilità assegnata automaticamente al lead quando entra in questo stage.',
    )
    cf_rotting_threshold = fields.Integer(
        string='Soglia Rotting (giorni)',
        default=14,
        help='Giorni massimi in questa fase prima che il lead sia considerato in ritardo.',
    )
    cf_requires_sample = fields.Boolean(
        string='Richiede Campione',
        help='Se attivo, non è possibile passare a questa fase senza un campione collegato.',
    )
    cf_requires_sale_order = fields.Boolean(
        string='Richiede Ordine di Vendita',
        help='Se attivo, non è possibile passare a questa fase senza un ordine di vendita collegato.',
    )
