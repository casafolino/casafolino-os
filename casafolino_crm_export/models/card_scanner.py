import base64
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

FAIR_TAG_NAME = 'TUTTOFOOD_2026'
FAIR_SOURCE_NAME = 'Fiera TUTTOFOOD Milano 2026'
FAIR_LEAD_PREFIX = 'Lead Fiera TUTTOFOOD Milano 2026'
FAIR_XMLID = 'casafolino_crm_export.cf_export_fair_tuttofood_2026'
LANG_FALLBACK = 'en_US'


class CrmLeadCardScanner(models.Model):
    _inherit = 'crm.lead'

    card_image = fields.Binary('Business Card Image', attachment=True)
    card_image_filename = fields.Char('Card Image Filename')
    ai_extracted_data = fields.Text('AI Extracted Data')

    @api.model
    def create_from_card_scan(self, form_data, image_data, language='en_US', send_email=True, fair_id=None):
        """Create partner + lead from card scan data, optionally send follow-up email."""
        fair = self._get_card_scan_fair(fair_id)
        fair_name = fair.name if fair else 'Fiera'
        fair_tag_name = self._fair_tag_name(fair) if fair else FAIR_TAG_NAME
        fair_source_name = 'Fiera %s' % fair_name if fair else FAIR_SOURCE_NAME
        lead_prefix = 'Lead %s' % fair_name if fair else FAIR_LEAD_PREFIX

        # --- Partner ---
        partner_vals = {
            'name': ' '.join(filter(None, [
                form_data.get('first_name', ''),
                form_data.get('last_name', ''),
            ])).strip() or 'Contatto %s' % fair_name,
            'email': form_data.get('email') or False,
            'phone': form_data.get('phone') or False,
            'mobile': form_data.get('mobile') or False,
            'function': form_data.get('job_title') or False,
            'website': form_data.get('website') or False,
            'street': form_data.get('address') or False,
            'city': form_data.get('city') or False,
            'is_company': False,
        }

        # Company as parent
        company_name = form_data.get('company')
        if company_name:
            parent = self.env['res.partner'].search(
                [('name', '=ilike', company_name), ('is_company', '=', True)],
                limit=1,
            )
            if not parent:
                parent = self.env['res.partner'].create({
                    'name': company_name,
                    'is_company': True,
                })
            partner_vals['parent_id'] = parent.id

        # Country
        country_code = form_data.get('country_code') or ''
        if country_code:
            country = self.env['res.country'].search(
                [('code', '=ilike', country_code)], limit=1,
            )
            if country:
                partner_vals['country_id'] = country.id

        # Partner category tag
        category = self.env['res.partner.category'].search(
            [('name', '=', fair_tag_name)], limit=1,
        )
        if category:
            partner_vals['category_id'] = [(4, category.id)]

        # Check existing partner by email
        partner = False
        if partner_vals.get('email'):
            partner = self.env['res.partner'].search(
                [('email', '=ilike', partner_vals['email'])], limit=1,
            )
        if partner:
            partner.write({k: v for k, v in partner_vals.items() if v and k != 'category_id'})
            if category:
                partner.write({'category_id': [(4, category.id)]})
        else:
            partner = self.env['res.partner'].create(partner_vals)

        # --- Lead ---
        crm_tag = self.env['crm.tag'].search(
            [('name', '=', fair_tag_name)], limit=1,
        )
        utm_source = self.env['utm.source'].search(
            [('name', '=', fair_source_name)], limit=1,
        )
        stage = self._get_first_pipeline_stage()

        lead_vals = {
            'name': f'{lead_prefix} - {company_name or partner.name}',
            'partner_id': partner.id,
            'contact_name': partner.name,
            'partner_name': company_name or '',
            'email_from': partner.email,
            'phone': partner.phone,
            'mobile': partner.mobile,
            'type': 'opportunity',
            'ai_extracted_data': str(form_data),
        }
        if crm_tag:
            lead_vals['tag_ids'] = [(4, crm_tag.id)]
        if utm_source:
            lead_vals['source_id'] = utm_source.id
        if fair:
            lead_vals['cf_fair_id'] = fair.id
        if stage:
            lead_vals['stage_id'] = stage.id

        lead = self.create(lead_vals)

        # --- Card image attachment ---
        card_attachment = False
        if image_data:
            card_attachment = self.env['ir.attachment'].create({
                'name': f'business_card_{partner.name}.jpg',
                'type': 'binary',
                'datas': image_data,
                'res_model': 'crm.lead',
                'res_id': lead.id,
                'mimetype': 'image/jpeg',
            })
            lead.card_image = image_data

        # --- Send email ---
        email_sent = False
        if send_email and partner.email:
            email_sent = self._send_fair_followup(lead, partner, language, card_attachment, fair)

        # --- Chatter log ---
        lang_label = {
            'it_IT': 'Italiano',
            'fr_FR': 'Français',
            'en_US': 'English',
            'es_ES': 'Español',
            'de_DE': 'Deutsch',
        }.get(language, language or '-')
        body = _(
            '<p><strong>Lead creato da Card Scanner %(fair)s</strong></p>'
            '<p>Contatto: %(name)s<br/>Azienda: %(company)s<br/>'
            'Lingua email: %(lang)s<br/>Email inviata: %(sent)s</p>',
            fair=fair_name,
            name=partner.name,
            company=company_name or '-',
            lang=lang_label,
            sent='Sì' if email_sent else 'No',
        )
        lead.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')

        return {
            'success': True,
            'lead_id': lead.id,
            'lead_name': lead.name,
            'partner_id': partner.id,
            'email_sent': email_sent,
        }

    def _send_fair_followup(self, lead, partner, language, card_attachment, fair=None):
        """Send TUTTOFOOD follow-up email with fair attachments."""
        template = self._get_fair_mail_template(fair, language)
        if template:
            return self._send_configured_fair_template(
                lead, partner, language, card_attachment, template,
            )
        return self._send_legacy_tuttofood_followup(lead, partner, language, card_attachment)

    def _send_configured_fair_template(self, lead, partner, language, card_attachment, template):
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            subject, body_html = template.render_for_lead(lead, partner)
            mail_vals = {
                'subject': subject,
                'body_html': body_html,
                'email_to': partner.email,
                'recipient_ids': [(4, partner.id)],
                'model': 'crm.lead',
                'res_id': lead.id,
                'auto_delete': False,
            }
            if self.env.user.email_formatted:
                mail_vals['email_from'] = self.env.user.email_formatted
            cc_email = ICP.get_param('casafolino.crm_export.fair_cc_email', '')
            if cc_email:
                mail_vals['email_cc'] = cc_email

            mail = self.env['mail.mail'].create(mail_vals)
            attachment_ids = template.attachment_ids.ids + self._get_fair_attachment_ids()
            if card_attachment:
                attachment_ids.append(card_attachment.id)
            if attachment_ids:
                mail.attachment_ids = [(4, aid) for aid in attachment_ids]
            mail.send()
            lead.message_post(
                body=_(
                    'Email automatica inviata con template "%(template)s" (%(lang)s).',
                    template=template.name,
                    lang=language,
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            return True
        except Exception as e:
            _logger.warning('Fair template email send failed for lead %s: %s', lead.id, e)
            self._schedule_failed_email_activity(lead, e)
            return False

    def _send_legacy_tuttofood_followup(self, lead, partner, language, card_attachment):
        """Legacy fallback for the original TUTTOFOOD mail.template records."""
        ICP = self.env['ir.config_parameter'].sudo()
        template_by_language = {
            'it_IT': 'casafolino_crm_export.email_template_tuttofood_2026_it',
            'fr_FR': 'casafolino_crm_export.email_template_tuttofood_2026_fr',
            'en_US': 'casafolino_crm_export.email_template_tuttofood_2026_en',
        }
        template_xmlid = template_by_language.get(
            language, 'casafolino_crm_export.email_template_tuttofood_2026_en')
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            _logger.warning('Mail template %s not found', template_xmlid)
            return False

        try:
            mail_id = template.send_mail(lead.id, force_send=False)
            mail = self.env['mail.mail'].browse(mail_id)

            # CC
            cc_email = ICP.get_param('casafolino.crm_export.fair_cc_email', '')
            if cc_email:
                mail.email_cc = cc_email

            # Set sender to current user
            if self.env.user.email_formatted:
                mail.email_from = self.env.user.email_formatted

            # Fair document attachments
            attachment_ids = self._get_fair_attachment_ids()
            if card_attachment:
                attachment_ids.append(card_attachment.id)
            if attachment_ids:
                mail.attachment_ids = [(4, aid) for aid in attachment_ids]

            mail.send()
            return True
        except Exception as e:
            _logger.warning('TUTTOFOOD email send failed for lead %s: %s', lead.id, e)
            self._schedule_failed_email_activity(lead, e)
            return False

    def _get_card_scan_fair(self, fair_id=None):
        if fair_id:
            fair = self.env['cf.export.fair'].browse(int(fair_id))
            if fair.exists():
                return fair
        fair = self.env.ref(FAIR_XMLID, raise_if_not_found=False)
        if fair:
            return fair
        return self.env['cf.export.fair'].search([
            ('state', 'in', ['active', 'followup', 'confirmed']),
        ], order='date_start desc, id desc', limit=1)

    def _get_fair_mail_template(self, fair, language):
        if not fair:
            return False
        Template = self.env['cf.fair.mail.template']
        languages = [language, LANG_FALLBACK, 'it_IT']
        for lang in [l for i, l in enumerate(languages) if l and l not in languages[:i]]:
            template = Template.search([
                ('fair_id', '=', fair.id),
                ('language', '=', lang),
                ('auto_send_on_card_scan', '=', True),
                ('active', '=', True),
            ], limit=1)
            if template:
                return template
        return False

    def _get_first_pipeline_stage(self):
        return self.env['crm.stage'].search([], order='sequence, id', limit=1)

    def _fair_tag_name(self, fair):
        if not fair:
            return FAIR_TAG_NAME
        base = (fair.name or '').upper()
        return ''.join(ch if ch.isalnum() else '_' for ch in base).strip('_')[:60]

    def _schedule_failed_email_activity(self, lead, error):
        try:
            lead.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Email follow-up da reinviare',
                note=f'Invio automatico fallito: {error}',
            )
        except Exception:
            pass

    @api.model
    def _get_fair_attachment_ids(self):
        """Get ir.attachment IDs for configured fair documents."""
        ICP = self.env['ir.config_parameter'].sudo()
        attachment_ids = []
        for param in ['fair_attachment_catalog', 'fair_attachment_company_profile']:
            doc_id = ICP.get_param(f'casafolino.crm_export.{param}', '')
            if doc_id:
                try:
                    doc = self.env['documents.document'].browse(int(doc_id))
                    if doc.exists() and doc.attachment_id:
                        attachment_ids.append(doc.attachment_id.id)
                except (ValueError, TypeError):
                    pass
        return attachment_ids
