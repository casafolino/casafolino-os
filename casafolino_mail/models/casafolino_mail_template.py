import logging
import re

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

_VAR_RE = re.compile(r'\{\{(\w+)\}\}')


class CasafolinoMailTemplate(models.Model):
    _name = 'casafolino.mail.template'
    _description = 'Mail V3 templates with variables'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Char(help="Short description for selector")

    subject = fields.Char(required=True,
        help="Supports {{partner_name}}, {{partner_country}}, {{last_order_date}}, etc.")
    body_html = fields.Html(required=True, sanitize=True)

    language = fields.Selection([
        ('it_IT', 'Italiano'),
        ('en_US', 'English'),
        ('de_DE', 'Deutsch'),
        ('es_ES', 'Español'),
        ('fr_FR', 'Français'),
    ], default='it_IT')

    category = fields.Selection([
        ('follow_up', 'Follow-up'),
        ('sample_offer', 'Sample/Offer'),
        ('post_fair', 'Post-Fair'),
        ('quote', 'Quote'),
        ('reminder', 'Reminder'),
        ('generic', 'Generic'),
    ], default='generic')

    account_ids = fields.Many2many('casafolino.mail.account',
        'casafolino_mail_template_account_rel', 'template_id', 'account_id',
        help="Visible only when composing from these accounts. Empty = all accounts.")

    default_signature_id = fields.Many2one('casafolino.mail.signature')

    usage_count = fields.Integer(default=0)
    last_used = fields.Datetime()

    @api.model
    def render_template(self, template_id, partner_id, thread_id=None, context_extra=None):
        """Render template with variable substitution.
        Returns {subject: rendered, body_html: rendered}.
        """
        template = self.browse(template_id)
        if not template.exists():
            return {'subject': '', 'body_html': ''}

        partner = self.env['res.partner'].browse(partner_id)

        # Build variables dict
        variables = self._build_variables(partner, thread_id)
        if context_extra:
            variables.update(context_extra)

        rendered_subject = self._render_string(template.subject or '', variables)
        rendered_body = self._render_string(template.body_html or '', variables)

        # Log usage
        template.sudo().write({
            'usage_count': template.usage_count + 1,
            'last_used': fields.Datetime.now(),
        })

        return {'subject': rendered_subject, 'body_html': rendered_body}

    def _build_variables(self, partner, thread_id=None):
        """Build substitution variables dict."""
        from datetime import timedelta

        variables = {
            'partner_name': partner.name or '',
            'partner_first_name': (partner.name or '').split(' ')[0] if partner.name else '',
            'partner_country': partner.country_id.name if partner.country_id else '',
            'partner_city': partner.city or '',
            'partner_language': (partner.lang or '').split('_')[0].upper() if partner.lang else '',
            'sender_name': self.env.user.name or '',
            'sender_signature': '',
            'today_date': fields.Date.context_today(self).strftime('%d/%m/%Y'),
            'thread_subject': '',
        }

        # Last order info
        SaleOrder = self.env['sale.order']
        last_order = SaleOrder.search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
        ], order='date_order desc', limit=1)

        variables['last_order_date'] = (
            last_order.date_order.strftime('%d/%m/%Y') if last_order and last_order.date_order else 'mai'
        )
        variables['last_order_number'] = last_order.name if last_order else ''

        # Days since last contact
        Intel = self.env['casafolino.partner.intelligence']
        intel = Intel.search([('partner_id', '=', partner.id)], limit=1)
        if intel and intel.last_email_date:
            delta = fields.Datetime.now() - intel.last_email_date
            variables['days_since_last_contact'] = str(delta.days)
        else:
            variables['days_since_last_contact'] = '?'

        # Thread subject
        if thread_id:
            thread = self.env['casafolino.mail.thread'].browse(thread_id)
            if thread.exists():
                variables['thread_subject'] = thread.subject or ''

        # Sender signature
        sig = self.env['casafolino.mail.signature'].search([
            ('user_id', '=', self.env.uid),
            ('is_default', '=', True),
        ], limit=1)
        if sig:
            variables['sender_signature'] = sig.body_html or ''

        return variables

    @staticmethod
    def _render_string(template_str, variables):
        """Replace {{var}} with values. Unknown vars → empty string."""
        def replacer(match):
            key = match.group(1)
            return str(variables.get(key, ''))
        return _VAR_RE.sub(replacer, template_str or '')
