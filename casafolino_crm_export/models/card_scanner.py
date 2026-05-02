import base64
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

SIAL_TAG_NAME = 'SIAL_MONTREAL_2026'
SIAL_SOURCE_NAME = 'Fiera SIAL Canada 2026'


class CrmLeadCardScanner(models.Model):
    _inherit = 'crm.lead'

    card_image = fields.Binary('Business Card Image', attachment=True)
    card_image_filename = fields.Char('Card Image Filename')
    ai_extracted_data = fields.Text('AI Extracted Data')

    @api.model
    def create_from_card_scan(self, form_data, image_data, language='en_US', send_email=True):
        """Create partner + lead from card scan data, optionally send follow-up email."""
        # --- Partner ---
        partner_vals = {
            'name': ' '.join(filter(None, [
                form_data.get('first_name', ''),
                form_data.get('last_name', ''),
            ])).strip() or 'Contact SIAL',
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
            [('name', '=', SIAL_TAG_NAME)], limit=1,
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
            [('name', '=', SIAL_TAG_NAME)], limit=1,
        )
        utm_source = self.env['utm.source'].search(
            [('name', '=', SIAL_SOURCE_NAME)], limit=1,
        )

        lead_vals = {
            'name': f'Lead Fiera SIAL Canada 2026 — {company_name or partner.name}',
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
            email_sent = self._send_sial_followup(lead, partner, language, card_attachment)

        # --- Chatter log ---
        body = _(
            '<p><strong>Lead creato da Card Scanner SIAL Montreal 2026</strong></p>'
            '<p>Contatto: %(name)s<br/>Azienda: %(company)s<br/>'
            'Lingua email: %(lang)s<br/>Email inviata: %(sent)s</p>',
            name=partner.name,
            company=company_name or '-',
            lang='Français' if language == 'fr_FR' else 'English',
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

    def _send_sial_followup(self, lead, partner, language, card_attachment):
        """Send SIAL follow-up email with fair attachments."""
        ICP = self.env['ir.config_parameter'].sudo()
        template_xmlid = (
            'casafolino_crm_export.email_template_sial_montreal_fr'
            if language == 'fr_FR'
            else 'casafolino_crm_export.email_template_sial_montreal_en'
        )
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
            _logger.warning('SIAL email send failed for lead %s: %s', lead.id, e)
            try:
                lead.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary='Email follow-up da reinviare',
                    note=f'Invio automatico fallito: {e}',
                )
            except Exception:
                pass
            return False

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
