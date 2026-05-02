from odoo import fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    cf_probability_default = fields.Float(
        string='Probabilità Default (%)',
        help='Probabilità assegnata automaticamente al lead quando entra in questo stage.',
    )
