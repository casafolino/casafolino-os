from odoo import fields, models


class CrmLeadExt(models.Model):
    _inherit = 'crm.lead'

    cf_initiative_id = fields.Many2one(
        'cf.initiative', string='Lavagna iniziativa', index=True,
        ondelete='set null',
    )
