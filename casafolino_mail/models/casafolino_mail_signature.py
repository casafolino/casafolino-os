import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


OFFICIAL_SIGNATURE_NAME = 'Firma ufficiale CasaFolino'

ROLE_BY_EMAIL = {
    'antonio@casafolino.com': 'CEO &amp; Founder',
    'martina.sinopoli@casafolino.com': 'Commercial Back Office',
    'josefina.lazzaro@casafolino.com': 'Export Manager',
}

PHONE_BY_EMAIL = {
    'antonio@casafolino.com': '+39 335 166 5306',
    'martina.sinopoli@casafolino.com': '+39 392 8123 582',
}


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

    @api.model
    def _official_signature_html(self, account):
        """Return the brand signature used by the F8 composer."""
        email = (account.email_address or account.responsible_user_id.email or '').strip().lower()
        name = account.responsible_user_id.name or account.name or email
        role = ROLE_BY_EMAIL.get(email, 'CasaFolino Team')
        phone = PHONE_BY_EMAIL.get(email, '+39 0968 1945080')
        return """
<table cellpadding="0" cellspacing="0" border="0" style="font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:1.45;color:#2C2C2A;margin-top:8px;">
  <tr>
    <td style="padding-right:16px;font-family:Georgia,serif;font-style:italic;font-size:22px;color:#6B4A1E;line-height:1.1;white-space:nowrap;">
      CasaFolino<br/><span style="font-size:10px;letter-spacing:4px;font-style:normal;">1962</span>
    </td>
    <td style="border-left:1px solid #E5E5E5;padding-left:16px;">
      <div style="font-size:15px;font-weight:700;color:#27311f;">{name}</div>
      <div style="color:#888780;margin-bottom:6px;">{role} - CasaFolino Srl Societ&agrave; Benefit</div>
      <div style="color:#888780;">{phone} &middot; <a href="mailto:{email}" style="color:#5A6E3A;text-decoration:none;">{email}</a> &middot; <a href="https://casafolino.com" style="color:#5A6E3A;text-decoration:none;">casafolino.com</a></div>
      <div style="color:#888780;">Via Prunia, 1 - 88046 Lamezia Terme (CZ), Italy</div>
      <div style="color:#6B4A1E;font-size:12px;margin-top:4px;">Artigiani del gusto dal 1962</div>
    </td>
  </tr>
</table>
""".format(name=name, role=role, phone=phone, email=email)

    @api.model
    def _ensure_official_for_account(self, account):
        if not account:
            return False
        body_html = self._official_signature_html(account)
        signature = self.search([
            ('account_id', '=', account.id),
            ('name', '=', OFFICIAL_SIGNATURE_NAME),
        ], limit=1)
        other_defaults = self.search([
            ('account_id', '=', account.id),
            ('is_default', '=', True),
            ('id', '!=', signature.id if signature else 0),
        ])
        if other_defaults:
            other_defaults.write({'is_default': False})
        vals = {
            'name': OFFICIAL_SIGNATURE_NAME,
            'account_id': account.id,
            'body_html': body_html,
            'is_default': True,
            'include_in_reply': True,
            'include_in_forward': True,
        }
        if signature:
            signature.write(vals)
        else:
            signature = self.create(vals)
        if account.signature_html != body_html:
            account.write({'signature_html': body_html})
        return signature
