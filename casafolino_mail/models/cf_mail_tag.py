from odoo import models, fields


class CfMailTag(models.Model):
    _name = 'cf.mail.tag'
    _description = 'Tag Email CasaFolino'

    name = fields.Char('Nome', required=True)
    color = fields.Char('Colore', default='#5A6E3A')
