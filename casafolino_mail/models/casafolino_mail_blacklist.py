from odoo import models, fields, api


class CasafolinoMailBlacklist(models.Model):
    _name = 'casafolino.mail.blacklist'
    _description = 'Blacklist Email — Mail Hub'
    _order = 'type, value'

    type = fields.Selection([
        ('domain', 'Dominio'),
        ('email', 'Email'),
    ], string='Tipo', required=True, default='domain')
    value = fields.Char('Valore', required=True,
                         help='Dominio (es. linkedin.com) o indirizzo email completo')
    notes = fields.Text('Note')

    _sql_constraints = [
        ('value_unique', 'unique(type, value)', 'Questo valore è già in blacklist.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('value'):
                vals['value'] = vals['value'].lower().strip()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('value'):
            vals['value'] = vals['value'].lower().strip()
        return super().write(vals)

    @api.model
    def is_blacklisted(self, email_address):
        """Controlla se un indirizzo o il suo dominio è in blacklist."""
        email_lower = email_address.lower().strip()
        domain = email_lower.split('@')[1] if '@' in email_lower else ''
        return bool(self.search([
            '|',
            '&', ('type', '=', 'email'), ('value', '=', email_lower),
            '&', ('type', '=', 'domain'), ('value', '=', domain),
        ], limit=1))
