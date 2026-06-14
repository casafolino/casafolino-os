import logging

from odoo import SUPERUSER_ID
from odoo.api import Environment

_logger = logging.getLogger(__name__)


OFFICIAL_SIGNATURE_HTML = """
<table cellpadding="0" cellspacing="0" style="font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:1.45;color:#2f3328;margin-top:8px;">
  <tr>
    <td style="border-left:3px solid #5A6E3A;padding-left:12px;">
      <div style="font-size:15px;font-weight:700;color:#27311f;">{name}</div>
      <div style="color:#6b6f62;margin-bottom:8px;">{role} - CasaFolino Srl Societ&agrave; Benefit</div>
      <div><a href="mailto:{email}" style="color:#5A6E3A;text-decoration:none;">{email}</a></div>
      <div><a href="https://casafolino.com" style="color:#5A6E3A;text-decoration:none;">casafolino.com</a></div>
      <div style="color:#6b6f62;">Via Prunia, 1 - 88046 Lamezia Terme (CZ), Italy</div>
      <div style="color:#6b6f62;">Artigiani del gusto dal 1962</div>
    </td>
  </tr>
</table>
"""

ROLE_BY_EMAIL = {
    'antonio@casafolino.com': 'CEO',
    'martina.sinopoli@casafolino.com': 'Commercial Back Office',
    'josefina.lazzaro@casafolino.com': 'Export Manager',
}

TEMPLATES = [
    {
        'name': 'Catalogo allegato',
        'language': 'it_IT',
        'sequence': 1,
        'subject': 'Catalogo CasaFolino',
        'description': 'Invia il catalogo senza listino prezzi.',
        'default_attachment_policy': 'catalog',
        'body_html': """
<p>Buongiorno {{partner_first_name}},</p>
<p>le invio in allegato il catalogo CasaFolino con la nostra selezione prodotti.</p>
<p>Resto a disposizione per approfondire formati, disponibilit&agrave; e soluzioni pi&ugrave; adatte al vostro mercato.</p>
<p>Cordiali saluti,</p>
""",
    },
    {
        'name': 'Catalogue attached',
        'language': 'en_US',
        'sequence': 2,
        'subject': 'CasaFolino catalogue',
        'description': 'Send the catalogue without price list.',
        'default_attachment_policy': 'catalog',
        'body_html': """
<p>Dear {{partner_first_name}},</p>
<p>please find attached the CasaFolino catalogue with our product selection.</p>
<p>I remain available to discuss formats, availability and the most suitable options for your market.</p>
<p>Best regards,</p>
""",
    },
    {
        'name': 'Catalogo + listino prezzi',
        'language': 'it_IT',
        'sequence': 3,
        'subject': 'Catalogo e listino prezzi CasaFolino',
        'description': 'Invia catalogo e listino prezzi.',
        'default_attachment_policy': 'catalog_price_list',
        'body_html': """
<p>Buongiorno {{partner_first_name}},</p>
<p>le invio in allegato il catalogo CasaFolino e il listino prezzi aggiornato.</p>
<p>Se desidera, possiamo valutare insieme la selezione pi&ugrave; adatta per il vostro canale e preparare una proposta dedicata.</p>
<p>Cordiali saluti,</p>
""",
    },
    {
        'name': 'Catalogue + price list',
        'language': 'en_US',
        'sequence': 4,
        'subject': 'CasaFolino catalogue and price list',
        'description': 'Send catalogue and price list.',
        'default_attachment_policy': 'catalog_price_list',
        'body_html': """
<p>Dear {{partner_first_name}},</p>
<p>please find attached the CasaFolino catalogue and updated price list.</p>
<p>If useful, we can review the best selection for your channel and prepare a dedicated proposal.</p>
<p>Best regards,</p>
""",
    },
]


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})
    _ensure_official_signatures(env)
    _ensure_composer_templates(env)
    _logger.info("[V19] Composer catalogue templates and official signatures seeded")


def _ensure_official_signatures(env):
    Account = env['casafolino.mail.account'].sudo()
    Signature = env['casafolino.mail.signature'].sudo()

    for account in Account.search([('active', '=', True)]):
        email = (account.email_address or account.responsible_user_id.login or '').strip().lower()
        if not email:
            continue
        name = account.responsible_user_id.name or account.name or email
        role = ROLE_BY_EMAIL.get(email, 'CasaFolino Team')
        body_html = OFFICIAL_SIGNATURE_HTML.format(name=name, role=role, email=email)

        signature = Signature.search([
            ('account_id', '=', account.id),
            ('name', '=', 'Firma ufficiale CasaFolino'),
        ], limit=1)
        other_defaults = Signature.search([
            ('account_id', '=', account.id),
            ('is_default', '=', True),
            ('id', '!=', signature.id if signature else 0),
        ])
        if other_defaults:
            other_defaults.write({'is_default': False})

        vals = {
            'name': 'Firma ufficiale CasaFolino',
            'account_id': account.id,
            'body_html': body_html,
            'is_default': True,
            'include_in_reply': True,
            'include_in_forward': True,
        }
        if signature:
            signature.write(vals)
        else:
            Signature.create(vals)

        if account.signature_html != body_html:
            account.write({'signature_html': body_html})


def _ensure_composer_templates(env):
    Template = env['casafolino.mail.template'].sudo()
    for vals in TEMPLATES:
        template = Template.search([
            ('name', '=', vals['name']),
            ('language', '=', vals['language']),
        ], limit=1)
        data = dict(vals)
        data.setdefault('category', 'generic')
        if template:
            template.write(data)
        else:
            Template.create(data)
