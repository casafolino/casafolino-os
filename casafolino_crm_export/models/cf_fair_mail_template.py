import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


LANGUAGES = [
    ('it_IT', 'Italiano'),
    ('en_US', 'English'),
    ('fr_FR', 'Français'),
    ('es_ES', 'Español'),
    ('de_DE', 'Deutsch'),
]


class CfFairMailTemplateFolder(models.Model):
    _name = 'cf.fair.mail.template.folder'
    _description = 'Cartella Template Mail Fiera'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class CfFairMailTemplate(models.Model):
    _name = 'cf.fair.mail.template'
    _description = 'Template Mail Fiera'
    _inherit = ['mail.thread']
    _order = 'fair_id, folder_id, name, language'

    name = fields.Char(required=True, tracking=True)
    folder_id = fields.Many2one(
        'cf.fair.mail.template.folder',
        string='Cartella',
        ondelete='set null',
    )
    fair_id = fields.Many2one(
        'cf.export.fair',
        string='Fiera',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    language = fields.Selection(LANGUAGES, string='Lingua', required=True, default='it_IT')
    subject = fields.Char(required=True, tracking=True)
    body_html = fields.Html(string='Corpo email', required=True)
    auto_send_on_card_scan = fields.Boolean(
        string='Invio automatico da scanner',
        default=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    translated_from_id = fields.Many2one(
        'cf.fair.mail.template',
        string='Tradotto da',
        ondelete='set null',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'cf_fair_mail_template_ir_attachment_rel',
        'template_id',
        'attachment_id',
        string='Allegati',
    )
    last_generated_translation = fields.Datetime(readonly=True)
    notes = fields.Text()

    @api.constrains('fair_id', 'language', 'auto_send_on_card_scan', 'active')
    def _check_unique_auto_template(self):
        for rec in self:
            if not rec.fair_id or not rec.language or not rec.auto_send_on_card_scan or not rec.active:
                continue
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('fair_id', '=', rec.fair_id.id),
                ('language', '=', rec.language),
                ('auto_send_on_card_scan', '=', True),
                ('active', '=', True),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'Esiste già un template attivo per questa fiera e lingua.'
                ))

    def action_generate_translations(self):
        for template in self:
            template._generate_translations()
        return True

    def _generate_translations(self):
        self.ensure_one()
        source = self
        targets = [
            ('en_US', 'English'),
            ('fr_FR', 'French'),
            ('es_ES', 'Spanish'),
            ('de_DE', 'German'),
        ]
        created = []
        for lang, label in targets:
            existing = self.search([
                ('fair_id', '=', source.fair_id.id),
                ('language', '=', lang),
                ('active', '=', True),
            ], limit=1)
            subject, body = self._translate_pair(source.subject, source.body_html, label)
            vals = {
                'name': '%s - %s' % (source.name, dict(LANGUAGES).get(lang, lang)),
                'folder_id': source.folder_id.id,
                'fair_id': source.fair_id.id,
                'language': lang,
                'subject': subject,
                'body_html': body,
                'auto_send_on_card_scan': source.auto_send_on_card_scan,
                'translated_from_id': source.id,
                'attachment_ids': [(6, 0, source.attachment_ids.ids)],
                'last_generated_translation': fields.Datetime.now(),
                'notes': source.notes,
            }
            if existing:
                existing.write(vals)
                created.append(existing.display_name)
            else:
                created.append(self.create(vals).display_name)
        self.message_post(
            body=_('Traduzioni generate/aggiornate: %s') % ', '.join(created),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def _translate_pair(self, subject, body_html, target_language):
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.groq_api_key', ''
        )
        if not api_key:
            raise UserError(_('Groq API key non configurata.'))

        prompt = (
            'Translate this CasaFolino fair follow-up email from Italian to %s.\n'
            'Preserve HTML tags, placeholders in braces such as {contact_name}, '
            '{company_name}, {fair_name}, and the business tone.\n'
            'Return ONLY valid JSON with keys "subject" and "body_html".\n\n'
            'Subject:\n%s\n\nBody HTML:\n%s'
        ) % (target_language, subject or '', body_html or '')
        resp = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': 'Bearer %s' % api_key,
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (CasaFolino Fair Template Translator)',
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You translate commercial email templates and return JSON only.',
                    },
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.1,
                'max_tokens': 2500,
            },
            timeout=45,
        )
        if not resp.ok:
            raise UserError(_('Traduzione Groq fallita: %s') % resp.text[:300])
        raw = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        import json
        import re

        match = re.search(r'\{[\s\S]*\}', raw or '')
        if not match:
            _logger.warning('Groq translation returned no JSON: %s', raw[:300])
            raise UserError(_('La traduzione AI non ha restituito JSON valido.'))
        data = json.loads(match.group())
        return data.get('subject') or subject, data.get('body_html') or body_html

    def render_for_lead(self, lead, partner):
        self.ensure_one()
        replacements = {
            '{contact_name}': partner.name or '',
            '{company_name}': partner.parent_id.name if partner.parent_id else (partner.name or ''),
            '{lead_name}': lead.name or '',
            '{fair_name}': self.fair_id.name or '',
            '{user_name}': self.env.user.name or '',
            '{user_email}': self.env.user.email or '',
        }
        subject = self.subject or ''
        body = self.body_html or ''
        for key, value in replacements.items():
            subject = subject.replace(key, value or '')
            body = body.replace(key, value or '')
        return subject, body
