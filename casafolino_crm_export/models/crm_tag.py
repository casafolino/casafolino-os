from odoo import fields, models


class CrmTag(models.Model):
    _inherit = 'crm.tag'

    cf_category = fields.Selection([
        ('geo', 'Geografica'),
        ('fair', 'Fiera'),
        ('product', 'Prodotto'),
        ('channel', 'Canale'),
    ], string='Categoria CF')
