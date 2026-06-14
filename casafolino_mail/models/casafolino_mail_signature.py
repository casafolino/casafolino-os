import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class CasafolinoMailSignature(models.Model):
    _name = 'casafolino.mail.signature'
    _description = 'Firma email — Mail V3'
    _order = 'name'

    name = fields.Char('Nome', required=True)
    account_id = fields.Many2one('casafolino.mail.account', string='Account',
                                  required=True, ondelete='cascade')
    body_html = fields.Html('Firma HTML', sanitize=False)
    is_default = fields.Boolean('Default', default=False)
    include_in_reply = fields.Boolean('Includi in risposte', default=True)
    include_in_forward = fields.Boolean('Includi in inoltro', default=True)

    @api.constrains('is_default', 'account_id')
    def _check_unique_default(self):
        for sig in self:
            if sig.is_default:
                others = self.search([
                    ('account_id', '=', sig.account_id.id),
                    ('is_default', '=', True),
                    ('id', '!=', sig.id),
                ])
                if others:
                    raise ValidationError(
                        'Solo una firma default per account. '
                        'Disattiva prima la firma "%s".' % others[0].name
                    )
