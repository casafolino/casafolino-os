from odoo import fields, models


class CfInitiativeTag(models.Model):
    _inherit = 'cf.initiative.tag'

    category = fields.Selection(
        selection_add=[('source', 'Source / Canale Acquisizione')],
        ondelete={'source': 'set null'},
    )
