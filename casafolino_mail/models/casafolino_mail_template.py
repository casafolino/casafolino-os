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
        """Build substitution variables dict (25+ variables)."""
        from datetime import date as dt_date

        today = fields.Date.context_today(self)

        variables = {
            # ── Partner base ──
            'partner_name': partner.name or '',
            'partner_first_name': (partner.name or '').split(' ')[0] if partner.name else '',
            'partner_country': partner.country_id.name if partner.country_id else '',
            'partner_city': partner.city or '',
            'partner_language': (partner.lang or '').split('_')[0].upper() if partner.lang else '',
            # ── Partner extra (F8) ──
            'partner_full_address': self._fmt_address(partner),
            'partner_vat': partner.vat or '',
            'partner_company_type': 'Azienda' if partner.is_company else 'Persona',
            'partner_time_zone': partner.tz or '',
            # ── Sender ──
            'sender_name': self.env.user.name or '',
            'sender_signature': '',
            # ── Dates ──
            'today_date': today.strftime('%d/%m/%Y'),
            # ── Thread ──
            'thread_subject': '',
            'thread_message_count': '0',
            'thread_first_email_date': '',
            'thread_attachment_count': '0',
        }

        # ── Last order info ──
        SaleOrder = self.env['sale.order']
        last_order = SaleOrder.search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
        ], order='date_order desc', limit=1)

        variables['last_order_date'] = (
            last_order.date_order.strftime('%d/%m/%Y') if last_order and last_order.date_order else 'mai'
        )
        variables['last_order_number'] = last_order.name if last_order else ''

        # ── Sales extra (F8) ──
        year_start = dt_date(today.year, 1, 1)
        ytd_orders = SaleOrder.search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', year_start),
        ])
        variables['total_orders_ytd'] = str(len(ytd_orders))
        variables['total_revenue_ytd'] = '{:,.0f}'.format(
            sum(o.amount_total for o in ytd_orders)) if ytd_orders else '0'

        # Top product
        top_product = ''
        try:
            groups = self.env['sale.report'].read_group(
                domain=[('partner_id', '=', partner.id), ('state', 'in', ['sale', 'done'])],
                fields=['product_id', 'product_uom_qty:sum'],
                groupby=['product_id'],
                orderby='product_uom_qty desc',
                limit=1,
            )
            if groups and groups[0].get('product_id'):
                top_product = groups[0]['product_id'][1]
        except Exception:
            pass
        variables['top_product'] = top_product

        # ── Days/months since last contact ──
        Intel = self.env['casafolino.partner.intelligence']
        intel = Intel.search([('partner_id', '=', partner.id)], limit=1)
        if intel and intel.last_email_date:
            delta = fields.Datetime.now() - intel.last_email_date
            variables['days_since_last_contact'] = str(delta.days)
            variables['months_since_last_contact'] = str(delta.days // 30)
        else:
            variables['days_since_last_contact'] = '?'
            variables['months_since_last_contact'] = '?'

        # ── Thread variables ──
        if thread_id:
            thread = self.env['casafolino.mail.thread'].browse(thread_id)
            if thread.exists():
                variables['thread_subject'] = thread.subject or ''
                variables['thread_message_count'] = str(thread.message_count or 0)
                variables['thread_first_email_date'] = (
                    thread.first_message_date.strftime('%d/%m/%Y')
                    if thread.first_message_date else ''
                )
                att_count = self.env['ir.attachment'].search_count([
                    ('res_model', '=', 'casafolino.mail.message'),
                    ('res_id', 'in', thread.message_ids.ids),
                ]) if thread.message_ids else 0
                variables['thread_attachment_count'] = str(att_count)

        # ── Account extra (F8) ──
        account = self.env['casafolino.mail.account'].search([
            ('responsible_user_id', '=', self.env.uid),
            ('active', '=', True),
        ], limit=1)
        variables['account_email'] = account.email_address if account else ''

        sig = self.env['casafolino.mail.signature'].search([
            ('account_id', '=', account.id if account else 0),
            ('is_default', '=', True),
        ], limit=1)
        if sig:
            variables['sender_signature'] = sig.body_html or ''
            variables['account_signature_name'] = sig.name or ''
        else:
            variables['account_signature_name'] = ''

        # Account manager (CRM salesperson)
        manager_name = ''
        try:
            lead = self.env['crm.lead'].sudo().search([
                ('partner_id', '=', partner.id),
                ('active', '=', True),
            ], order='create_date desc', limit=1)
            if lead and lead.user_id:
                manager_name = lead.user_id.name or ''
        except Exception:
            pass
        variables['account_manager_name'] = manager_name

        # ── Current season (F8) ──
        month = today.month
        if month in (3, 4, 5):
            variables['current_season'] = 'primavera'
        elif month in (6, 7, 8):
            variables['current_season'] = 'estate'
        elif month in (9, 10, 11):
            variables['current_season'] = 'autunno'
        else:
            variables['current_season'] = 'inverno'

        return variables

    @staticmethod
    def _fmt_address(partner):
        """Format partner address as single line."""
        parts = []
        if partner.street:
            parts.append(partner.street)
        if partner.city:
            parts.append(partner.city)
        if partner.state_id:
            parts.append(partner.state_id.name)
        if partner.country_id:
            parts.append(partner.country_id.name)
        return ', '.join(parts)

    @staticmethod
    def _render_string(template_str, variables):
        """Replace {{var}} with values. Unknown vars → empty string."""
        def replacer(match):
            key = match.group(1)
            return str(variables.get(key, ''))
        return _VAR_RE.sub(replacer, template_str or '')
