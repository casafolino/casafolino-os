import logging
from email.utils import getaddresses
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'googlemail.com',
    'yahoo.com', 'yahoo.it', 'yahoo.fr', 'yahoo.de', 'yahoo.es', 'yahoo.co.uk',
    'hotmail.com', 'hotmail.it', 'hotmail.fr', 'hotmail.de', 'hotmail.es',
    'outlook.com', 'outlook.it', 'outlook.fr', 'outlook.de',
    'live.com', 'live.it', 'msn.com',
    'libero.it', 'tiscali.it', 'virgilio.it', 'alice.it', 'tin.it',
    'icloud.com', 'me.com', 'mac.com',
    'aol.com',
    'gmx.de', 'gmx.at', 'gmx.com', 'gmx.net',
    'web.de', 't-online.de',
    'protonmail.com', 'proton.me',
    'pec.it',
}


class CrmLeadPipelineControl(models.Model):
    _inherit = 'crm.lead'

    cf_pc_mail_count = fields.Integer(string='Email operative', compute='_compute_cf_pc_counts')
    cf_pc_quote_count = fields.Integer(string='Quotazioni aperte', compute='_compute_cf_pc_counts')
    cf_pc_task_count = fields.Integer(string='Task dossier', compute='_compute_cf_pc_counts')

    def _compute_cf_pc_counts(self):
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        Sale = self.env['sale.order']
        Task = self.env['project.task']
        has_opportunity = 'opportunity_id' in Sale._fields
        for lead in self:
            lead.cf_pc_mail_count = Mail.search_count([
                ('lead_id', '=', lead.id),
                ('is_deleted', '=', False),
            ]) if Mail else 0
            lead.cf_pc_quote_count = Sale.search_count([
                ('opportunity_id', '=', lead.id),
                ('state', 'in', ['draft', 'sent']),
            ]) if has_opportunity else 0
            project = getattr(lead, 'cf_project_id', False)
            lead.cf_pc_task_count = Task.search_count([
                ('project_id', '=', project.id),
            ]) if project else 0

    def action_cf_pc_open_followup(self):
        return self._cf_pc_open_dashboard('followup')

    def action_cf_pc_open_inbox(self):
        return self._cf_pc_open_dashboard('inbox')

    def action_cf_pc_promote_dossier(self):
        self.ensure_one()
        return self.env['cf.pipeline.control'].lead_quick_action(self.id, 'dossier')

    def action_cf_pc_new_task(self):
        self.ensure_one()
        return self.env['cf.pipeline.control'].lead_quick_action(self.id, 'task')

    def action_cf_pc_open_quotes(self):
        self.ensure_one()
        Sale = self.env['sale.order']
        domain = [('opportunity_id', '=', self.id)] if 'opportunity_id' in Sale._fields else [('partner_id', '=', self.partner_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotazioni lead',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_opportunity_id': self.id,
            },
        }

    def _cf_pc_open_dashboard(self, default_view):
        return {
            'type': 'ir.actions.client',
            'name': 'Console CRM',
            'tag': 'casafolino_pipeline_control',
            'target': 'current',
            'context': {'default_view': default_view},
        }

    def action_open_project_360(self):
        """Legacy CRM Export button: keep it useful, but route to the dossier."""
        self.ensure_one()
        project = getattr(self, 'cf_project_id', False)
        if not project and hasattr(self, '_ensure_project_360'):
            project = self._ensure_project_360()
        if project:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Dossier',
                'res_model': 'project.project',
                'res_id': project.id,
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
            }
        return self.action_cf_pc_promote_dossier()


class ProjectProjectPipelineControl(models.Model):
    _inherit = 'project.project'

    cf360_continent = fields.Selection(
        [
            ('europe', 'Europa'),
            ('north_america', 'Nord America'),
            ('south_america', 'Sud America'),
            ('asia', 'Asia'),
            ('africa', 'Africa'),
            ('oceania', 'Oceania'),
            ('other', 'Altro'),
        ],
        compute='_compute_cf360_continent',
        store=True,
        string='Continente',
        index=True,
    )
    cf360_sale_order_ids = fields.One2many(
        'sale.order',
        'cf_project_id',
        string='Ordini collegati',
        readonly=True,
    )
    cf360_mail_count = fields.Integer(
        compute='_compute_cf360_mail_count',
        string='Mail dossier',
    )
    cf360_task_count = fields.Integer(
        compute='_compute_cf360_counts',
        string='Task dossier',
    )
    cf360_document_count = fields.Integer(
        compute='_compute_cf360_counts',
        string='Documenti',
    )

    @api.depends('partner_id.country_id.code')
    def _compute_cf360_continent(self):
        europe = {
            'AD', 'AL', 'AT', 'BA', 'BE', 'BG', 'BY', 'CH', 'CY', 'CZ', 'DE',
            'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'HU', 'IE', 'IS',
            'IT', 'LI', 'LT', 'LU', 'LV', 'MC', 'MD', 'ME', 'MK', 'MT', 'NL',
            'NO', 'PL', 'PT', 'RO', 'RS', 'RU', 'SE', 'SI', 'SK', 'SM', 'UA',
            'VA', 'XK',
        }
        north_america = {'CA', 'MX', 'US'}
        south_america = {
            'AR', 'BO', 'BR', 'CL', 'CO', 'EC', 'FK', 'GY', 'PE', 'PY', 'SR',
            'UY', 'VE',
        }
        asia = {
            'AE', 'AF', 'AM', 'AZ', 'BD', 'BH', 'BN', 'BT', 'CN', 'GE', 'HK',
            'ID', 'IL', 'IN', 'IQ', 'IR', 'JO', 'JP', 'KG', 'KH', 'KP', 'KR',
            'KW', 'KZ', 'LA', 'LB', 'LK', 'MM', 'MN', 'MO', 'MY', 'NP', 'OM',
            'PH', 'PK', 'QA', 'SA', 'SG', 'SY', 'TH', 'TJ', 'TM', 'TR', 'TW',
            'UZ', 'VN', 'YE',
        }
        africa = {
            'AO', 'BF', 'BI', 'BJ', 'BW', 'CD', 'CF', 'CG', 'CI', 'CM', 'CV',
            'DJ', 'DZ', 'EG', 'ER', 'ET', 'GA', 'GH', 'GM', 'GN', 'GQ', 'GW',
            'KE', 'KM', 'LR', 'LS', 'LY', 'MA', 'MG', 'ML', 'MR', 'MU', 'MW',
            'MZ', 'NA', 'NE', 'NG', 'RE', 'RW', 'SC', 'SD', 'SL', 'SN', 'SO',
            'SS', 'ST', 'SZ', 'TD', 'TG', 'TN', 'TZ', 'UG', 'ZA', 'ZM', 'ZW',
        }
        oceania = {'AU', 'FJ', 'FM', 'NC', 'NZ', 'PG', 'SB', 'VU', 'WS'}
        for project in self:
            code = (project.partner_id.country_id.code or '').upper()
            if code in europe:
                project.cf360_continent = 'europe'
            elif code in north_america:
                project.cf360_continent = 'north_america'
            elif code in south_america:
                project.cf360_continent = 'south_america'
            elif code in asia:
                project.cf360_continent = 'asia'
            elif code in africa:
                project.cf360_continent = 'africa'
            elif code in oceania:
                project.cf360_continent = 'oceania'
            else:
                project.cf360_continent = 'other' if code else False

    @api.depends('task_ids', 'cf_dossier_attachment_ids')
    def _compute_cf360_counts(self):
        for project in self:
            project.cf360_task_count = len(project.task_ids)
            project.cf360_document_count = len(getattr(project, 'cf_dossier_attachment_ids', []))

    def _compute_cf360_mail_count(self):
        for project in self:
            project.cf360_mail_count = 0

    def action_open_project_dashboard_360(self):
        """Legacy project button: the active operational view is now the dossier form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dossier',
            'res_model': 'project.project',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _cf360_get_or_create_lavagna_initiative(self):
        self.ensure_one()
        initiative = getattr(self, 'initiative_id', False)
        if initiative:
            return initiative
        Family = self.env['cf.initiative.family']
        Variant = self.env['cf.initiative.variant']
        family = Family.search([], order='sequence, id', limit=1)
        variant_domain = [('family_id', '=', family.id)] if family else []
        variant = Variant.search(variant_domain, order='sequence, id', limit=1)
        if not family or not variant:
            raise UserError('Non posso creare la Lavagna: mancano famiglia o variante delle iniziative.')
        initiative = self.env['cf.initiative'].create({
            'name': self.name,
            'family_id': family.id,
            'variant_id': variant.id,
            'partner_id': self.partner_id.id or False,
            'user_id': self.user_id.id or self.env.user.id,
            'state': 'in_progress',
            'lavagna_enabled': True,
            'lavagna_panels': 'kanban,todo,mail,activity,docs,notes,calendar',
        })
        self.write({'initiative_id': initiative.id})
        return initiative

    def action_open_lavagna_360(self):
        initiative = self._cf360_get_or_create_lavagna_initiative()
        return initiative.action_open_lavagna()

    def action_open_mails_360(self):
        self.ensure_one()
        if hasattr(self, 'action_open_dossier_mails'):
            return self.action_open_dossier_mails()
        return self.env['cf.pipeline.control'].record_quick_action('project.project', self.id, 'open')

    def action_open_tasks_360(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Task dossier - %s' % self.display_name,
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_quick_task_360(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuova task dossier',
            'res_model': 'project.task',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_name': self.cf_next_action or 'Nuova attività dossier',
            },
        }

    def action_schedule_followup_360(self):
        self.ensure_one()
        return self.env['cf.pipeline.control'].record_quick_action(
            'project.project', self.id, 'followup7')

    def action_reply_last_email_f8(self):
        self.ensure_one()
        partner = self.partner_id
        partner_email = partner.email if partner else ''
        subject = '[%s] ' % (self.name or '')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Scrivi email',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'project.project',
                'default_res_ids': [self.id],
                'default_composition_mode': 'comment',
                'default_partner_ids': [partner.id] if partner else [],
                'default_subject': subject,
                'default_body': '<p>Buongiorno,</p><p>le rispondo in merito al dossier <strong>%s</strong>.</p><p></p>' % (self.name or ''),
                'default_email_to': partner_email,
            },
        }

    def action_open_documents_360(self):
        self.ensure_one()
        partner_id = self.partner_id.id if self.partner_id else 0
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documenti dossier - %s' % self.display_name,
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [
                '|',
                '&', ('res_model', '=', 'project.project'), ('res_id', '=', self.id),
                '&', ('res_model', '=', 'res.partner'), ('res_id', '=', partner_id),
            ],
            'context': {'default_res_model': 'project.project', 'default_res_id': self.id},
        }

    def action_upload_document_360(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Allega documento',
            'res_model': 'ir.attachment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'project.project',
                'default_res_id': self.id,
            },
        }


class CfPipelineControl(models.AbstractModel):
    _name = 'cf.pipeline.control'
    _description = 'CasaFolino Pipeline Control data provider'

    @api.model
    def get_dashboard_data(self, fair_id=False):
        today = fields.Date.context_today(self)
        user = self.env.user
        fair_id = self._normalize_fair_id(fair_id)
        return {
            'kpis': self._safe_section('kpis', lambda: self._get_kpis(today, user), []),
            'discipline': self._safe_section('discipline', lambda: self._get_pipeline_discipline(today), {'kpis': [], 'rows': []}),
            'lanes': self._safe_section('lanes', lambda: self._get_control_lanes(today, user), []),
            'b2b_registrations': self._safe_section('b2b_registrations', lambda: self._get_b2b_registration_data(today), {'kpis': [], 'rows': []}),
            'followup': self._safe_section('followup', lambda: self._get_followup_data(today, user), {'kpis': [], 'columns': [], 'routes': [], 'timeline': []}),
            'post_fair': self._safe_section('post_fair', lambda: self._get_post_fair_data(today, fair_id), {'kpis': [], 'columns': [], 'timeline': [], 'fair_options': []}),
            'pipeline': self._safe_section('pipeline', lambda: self._get_pipeline_data(today), []),
            'inbox': self._safe_section('inbox', lambda: self._get_inbox_data(user), {'kpis': [], 'distribution_stats': [], 'to_reply': [], 'waiting_customer': []}),
            'dossiers': self._safe_section('dossiers', lambda: self._get_dossier_data(today), []),
        }

    @api.model
    def mass_archive(self, message_ids):
        msgs = self.env['casafolino.mail.message'].browse([int(mid) for mid in message_ids]).exists()
        if msgs:
            msgs.action_archive()
        return True

    @api.model
    def mass_link_lead(self, message_ids, lead_id):
        msgs = self.env['casafolino.mail.message'].browse([int(mid) for mid in message_ids]).exists()
        lead = self.env['crm.lead'].browse(int(lead_id)).exists()
        if msgs and lead:
            msgs.write({'lead_id': lead.id})
            for msg in msgs:
                if msg.partner_id and not lead.partner_id:
                    lead.partner_id = msg.partner_id
        return True

    @api.model
    def quick_create_partner(self, message_id):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return False
        if msg.partner_id:
            return True
        partner = self.env['res.partner'].create({
            'name': msg.sender_name or msg.sender_email.split('@')[0],
            'email': msg.sender_email,
        })
        msg.write({'partner_id': partner.id})
        return True

    @api.model
    def mail_policy_action(self, message_id, policy_action):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return self._notify('Email non trovata', 'Il thread non e piu disponibile.', 'warning')

        sender_email = (msg.sender_email or '').lower().strip()
        sender_domain = (msg.sender_domain or '').lower().strip()
        if not sender_email:
            return self._notify('Mittente mancante', 'Non posso creare una regola senza email mittente.', 'warning')

        if policy_action == 'keep_domain':
            if not sender_domain:
                return self._notify('Dominio mancante', 'Non posso creare una regola dominio per questo mittente.', 'warning')
            if sender_domain in FREE_EMAIL_DOMAINS:
                result = self._apply_mail_sender_policy(msg, 'keep_sender')
                result['params']['message'] = (
                    'Dominio pubblico %s: ho tenuto solo il mittente %s.'
                    % (sender_domain, sender_email)
                )
                return result
            return self._apply_mail_sender_policy(msg, 'keep_domain')

        if policy_action == 'keep_sender':
            return self._apply_mail_sender_policy(msg, 'keep_sender')

        if policy_action == 'discard_domain':
            if not sender_domain:
                return self._notify('Dominio mancante', 'Non posso scartare per dominio questo mittente.', 'warning')
            if sender_domain in FREE_EMAIL_DOMAINS:
                result = self._apply_mail_sender_policy(msg, 'discard_sender')
                result['params']['message'] = (
                    'Dominio pubblico %s: ho scartato solo il mittente %s.'
                    % (sender_domain, sender_email)
                )
                return result
            return self._apply_mail_sender_policy(msg, 'discard_domain')

        if policy_action == 'discard_sender':
            return self._apply_mail_sender_policy(msg, 'discard_sender')

        return self._notify('Azione non disponibile', policy_action, 'warning')

    def _apply_mail_sender_policy(self, msg, policy_action):
        Policy = self.env['casafolino.mail.sender_policy'].sudo()
        sender_email = (msg.sender_email or '').lower().strip()
        sender_domain = (msg.sender_domain or '').lower().strip()
        now = fields.Datetime.now()

        is_domain = policy_action.endswith('_domain')
        is_keep = policy_action.startswith('keep')
        pattern_type = 'domain' if is_domain else 'email_exact'
        pattern_value = sender_domain if is_domain else sender_email
        policy_target = sender_domain if is_domain else sender_email
        action = 'auto_keep' if is_keep else 'auto_discard'
        state = 'auto_keep' if is_keep else 'auto_discard'
        policy_label = 'Auto-keep' if is_keep else 'Auto-discard'

        policy = Policy.search([
            ('pattern_type', '=', pattern_type),
            ('pattern_value', '=', pattern_value),
            ('action', '=', action),
        ], limit=1)
        if not policy:
            policy = Policy.create({
                'name': '%s Console CRM: %s' % (policy_label, policy_target),
                'pattern_type': pattern_type,
                'pattern_value': pattern_value,
                'action': action,
                'priority': 85 if is_keep else 90,
                'auto_create_partner': bool(is_keep),
                'default_owner_id': self.env.user.id if is_keep else False,
                'notes': 'Creata da Console CRM il %s da %s' % (
                    fields.Date.today(), self.env.user.name),
            })

        domain = [('direction', '=', 'inbound')]
        if is_domain:
            domain.append(('sender_domain', '=ilike', sender_domain))
        else:
            domain.append(('sender_email', '=ilike', sender_email))

        if is_keep:
            domain.append(('state', 'in', ['new', 'review', 'discard', 'auto_discard']))
            vals = {
                'state': state,
                'policy_applied_id': policy.id,
                'is_archived': False,
                'is_deleted': False,
                'triage_user_id': self.env.user.id,
                'triage_date': now,
            }
        else:
            domain.append(('state', 'in', ['new', 'review', 'keep', 'auto_keep']))
            vals = {
                'state': state,
                'policy_applied_id': policy.id,
                'is_archived': True,
                'is_deleted': True,
                'triage_user_id': self.env.user.id,
                'triage_date': now,
            }

        messages = self.env['casafolino.mail.message'].sudo().search(domain)
        if messages:
            messages.write(vals)
            if is_keep:
                for record in messages:
                    self._resolve_or_create_partner_from_message(
                        record,
                        create_company=is_domain,
                        create_participants=is_domain,
                    )

        title = 'Regola creata'
        verb = 'tenute' if is_keep else 'scartate'
        target = 'dominio %s' % sender_domain if is_domain else 'mittente %s' % sender_email
        return self._notify(
            title,
            '%s email %s per %s.' % (len(messages), verb, target),
            'success',
            reload=True,
        )

    def _resolve_or_create_partner_from_message(self, msg, create_company=False, create_participants=False):
        sender_email = (msg.sender_email or '').lower().strip()
        if not sender_email:
            return False
        sender_domain = (msg.sender_domain or '').lower().strip()
        company = False
        if create_company and sender_domain and sender_domain not in FREE_EMAIL_DOMAINS:
            company = self._resolve_or_create_company_from_domain(sender_domain)

        partner = self.env['res.partner'].sudo().search([
            ('email', '=ilike', sender_email),
        ], limit=1)
        if not partner:
            partner = self.env['res.partner'].sudo().create({
                'name': msg.sender_name or sender_email.split('@')[0],
                'email': sender_email,
                'parent_id': company.id if company else False,
                'type': 'contact',
            })
        elif company and not partner.parent_id and not partner.is_company:
            partner.write({'parent_id': company.id})
        msg.sudo().write({'partner_id': partner.id, 'match_type': 'exact'})

        if create_participants and company:
            self._resolve_message_participants(msg, company, sender_domain)
        return partner

    def _resolve_or_create_company_from_domain(self, domain):
        Partner = self.env['res.partner'].sudo()
        company = Partner.search([
            ('is_company', '=', True),
            '|',
            ('website', 'ilike', domain),
            ('email', 'ilike', '@' + domain),
        ], limit=1)
        if company:
            return company

        domain_root = domain.split('.')[0].replace('-', ' ').replace('_', ' ')
        company_name = ' '.join(part.capitalize() for part in domain_root.split() if part) or domain
        return Partner.create({
            'name': company_name,
            'is_company': True,
            'website': 'https://%s' % domain,
            'email': 'info@%s' % domain,
        })

    def _resolve_message_participants(self, msg, company, domain):
        participants = self._extract_message_participants(msg)
        Partner = self.env['res.partner'].sudo()
        for name, email in participants:
            if not email or '@' not in email:
                continue
            email = email.lower().strip()
            if email.split('@')[-1] != domain:
                continue
            partner = Partner.search([('email', '=ilike', email)], limit=1)
            if partner:
                if not partner.parent_id and not partner.is_company:
                    partner.write({'parent_id': company.id})
                continue
            Partner.create({
                'name': name or email.split('@')[0],
                'email': email,
                'parent_id': company.id,
                'type': 'contact',
            })

    def _extract_message_participants(self, msg):
        raw_addresses = []
        if msg.sender_email:
            raw_addresses.append('%s <%s>' % (msg.sender_name or '', msg.sender_email))
        if msg.recipient_emails:
            raw_addresses.append(msg.recipient_emails)
        if getattr(msg, 'cc_emails', False):
            raw_addresses.append(msg.cc_emails)
        seen = set()
        participants = []
        for name, email in getaddresses(raw_addresses):
            email = (email or '').lower().strip()
            if not email or email in seen:
                continue
            seen.add(email)
            participants.append(((name or '').strip(), email))
        return participants

    @api.model
    def search_context_records(self, category, query, limit=5):
        if not query or len(query) < 2:
            return []
        
        if category == 'partner':
            domain = ['|', ('name', 'ilike', query), ('email', 'ilike', query)]
            recs = self.env['res.partner'].search(domain, limit=limit)
            return [{'id': r.id, 'name': r.name, 'email': r.email or ''} for r in recs]
            
        elif category == 'lead':
            domain = ['|', ('name', 'ilike', query), ('partner_id.name', 'ilike', query), ('active', 'in', [True, False])]
            recs = self.env['crm.lead'].search(domain, limit=limit)
            return [{
                'id': r.id,
                'name': r.name,
                'stage_name': r.stage_id.name if r.stage_id else '',
                'expected_revenue': r.expected_revenue or 0.0,
            } for r in recs]
            
        elif category == 'dossier':
            domain = ['|', ('name', 'ilike', query), ('partner_id.name', 'ilike', query)]
            recs = self.env['project.project'].search(domain, limit=limit)
            return [{
                'id': r.id,
                'name': r.name,
                'partner_name': r.partner_id.name if r.partner_id else '',
                'status': dict(r._fields['cf_status_dossier'].selection).get(r.cf_status_dossier, r.cf_status_dossier) if 'cf_status_dossier' in r._fields and r.cf_status_dossier else '',
            } for r in recs]
            
        return []

    @api.model
    def get_message_context_info(self, message_id):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return {
                'has_partner': False,
                'partner': None,
                'suggested_partners': [],
                'leads': [],
                'dossiers': [],
                'quotes': []
            }

        partner = msg.partner_id
        partner_details = None
        suggested_partners = []

        if partner:
            score_rec = self.env['casafolino.mail.lead.score'].search([('partner_id', '=', partner.id)], limit=1)
            score = score_rec.score if score_rec else 0
            tier = score_rec.tier if score_rec else 'frozen'
            partner_details = {
                'id': partner.id,
                'name': partner.name,
                'email': partner.email,
                'phone': partner.phone or '',
                'mobile': partner.mobile or '',
                'score': score,
                'tier': tier.upper(),
            }
        else:
            if msg.sender_domain:
                generic_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com', 'mail.com', 'protonmail.com', 'libero.it', 'virgilio.it', 'tiscali.it', 'alice.it'}
                if msg.sender_domain not in generic_domains:
                    domain_partners = self.env['res.partner'].search([
                        ('email', '=ilike', '%%@' + msg.sender_domain),
                    ], limit=5)
                    for dp in domain_partners:
                        suggested_partners.append({
                            'id': dp.id,
                            'name': dp.name,
                            'email': dp.email or '',
                        })

        # Fetch CRM Leads
        Lead = self.env['crm.lead']
        lead_domain = [('active', '=', True), ('type', '=', 'opportunity')]
        if partner:
            lead_domain.append(('partner_id', '=', partner.id))
        leads_recs = Lead.search(lead_domain, order='create_date desc, id desc', limit=5)
        leads_list = []
        for l in leads_recs:
            score = 0
            if 'cf_lead_score' in Lead._fields:
                score = l.cf_lead_score
            elif 'lead_score' in Lead._fields:
                score = l.lead_score
            leads_list.append({
                'id': l.id,
                'name': l.name,
                'stage_name': l.stage_id.name if l.stage_id else '',
                'expected_revenue': l.expected_revenue or 0.0,
                'create_date': self._date_label(l.create_date),
                'score': score,
            })

        # Fetch Projects/Dossiers
        Project = self.env['project.project']
        project_domain = self._active_project_domain()
        if partner:
            project_domain = ['|', ('partner_id', '=', partner.id), ('cf_lead_ids.partner_id', '=', partner.id)] + project_domain
        project_recs = Project.search(project_domain, order='write_date desc, id desc', limit=5)
        projects_list = []
        for p in project_recs:
            tasks = self.env['project.task'].search([('project_id', '=', p.id)], limit=80)
            overdue_tasks = tasks.filtered(lambda task: self._is_overdue(task.date_deadline))
            projects_list.append({
                'id': p.id,
                'name': p.name,
                'status': self._project_status(p),
                'blocker': self._project_blocker_label(p),
                'task_count': len(tasks),
                'overdue_count': len(overdue_tasks),
                'target_date': self._date_label(getattr(p, 'cf_target_date', False) or getattr(p, 'date', False)),
                'partner_name': self._project_partner_name(p),
                'departments': self._project_departments(p),
            })

        # Fetch Active Quotes/Sale Orders
        Sale = self.env['sale.order']
        sale_domain = [('state', 'in', ['draft', 'sent'])]
        if partner:
            sale_domain.append(('partner_id', '=', partner.id))
        sale_recs = Sale.search(sale_domain, order='write_date desc, id desc', limit=5)
        sales_list = []
        for s in sale_recs:
            sales_list.append({
                'id': s.id,
                'name': s.name,
                'amount_total': s.amount_total or 0.0,
                'state_label': dict(Sale._fields['state'].selection).get(s.state, s.state) if s.state else '',
                'date_order': self._date_label(s.date_order),
                'validity_date': self._date_label(s.validity_date) if 'validity_date' in Sale._fields else '',
            })

        return {
            'has_partner': bool(partner),
            'partner': partner_details,
            'suggested_partners': suggested_partners,
            'leads': leads_list,
            'dossiers': projects_list,
            'quotes': sales_list,
        }

    @api.model
    def link_partner_to_message(self, message_id, partner_id):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        partner = self.env['res.partner'].browse(int(partner_id)).exists()
        if msg and partner:
            msg.write({'partner_id': partner.id, 'match_type': 'manual'})
            if msg.lead_id and not msg.lead_id.partner_id:
                msg.lead_id.write({'partner_id': partner.id})
            return True
        return False

    @api.model
    def link_lead_to_message(self, message_id, lead_id):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        lead = self.env['crm.lead'].browse(int(lead_id)).exists()
        if msg and lead:
            msg.write({'lead_id': lead.id})
            if lead.partner_id and not msg.partner_id:
                msg.write({'partner_id': lead.partner_id.id, 'match_type': 'manual'})
            elif msg.partner_id and not lead.partner_id:
                lead.write({'partner_id': msg.partner_id.id})
            return True
        return False

    @api.model
    def link_dossier_to_message(self, message_id, project_id):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        project = self.env['project.project'].browse(int(project_id)).exists()
        if msg and project:
            msg.action_position_to_project(project.id)
            return True
        return False

    @api.model
    def generate_ai_draft(self, message_id, instruction=''):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return {'success': False, 'error': 'Email non trovata'}

        original_body = msg.body_plain or msg.snippet or ''
        
        system_instruction = (
            "You are an expert sales assistant for CasaFolino, an Italian artisan gourmet food company.\n"
            "Your task is to write a highly professional, polite, and helpful email reply to the customer's email.\n"
            "Write the reply in the same language as the customer's email (typically Italian or English).\n"
            "Do NOT include any email subject or headers. Output ONLY the email body text in HTML format. Keep paragraphs clean using <p> tags. Do not put markdown placeholders. Keep it elegant."
        )

        user_prompt = (
            f"Customer email sender: {msg.sender_name or 'Customer'} <{msg.sender_email or ''}>\n"
            f"Customer email subject: {msg.subject or '(no subject)'}\n"
            f"Customer email body:\n\"\"\"\n{original_body[:3000]}\n\"\"\"\n\n"
        )
        
        if instruction:
            user_prompt += f"USER INSTRUCTIONS for the reply: {instruction}\n\n"
        else:
            user_prompt += "Write a friendly, professional response acknowledging receipt and addressing any questions in the email.\n\n"

        user_prompt += "Draft Response (HTML):"

        try:
            draft = self.env['cf.gemini.client']._call_gemini_raw(system_instruction, user_prompt)
            if not draft:
                return {'success': False, 'error': 'Gemini ha restituito una bozza vuota'}
            
            if '```' in draft:
                import re
                draft = re.sub(r'^```\w*\n?', '', draft)
                draft = re.sub(r'\n?```$', '', draft)
                draft = draft.strip()

            return {
                'success': True,
                'draft': draft,
                'sender_email': msg.sender_email,
                'subject': f"Re: {msg.subject}" if msg.subject and not msg.subject.startswith('Re:') else msg.subject or 'Re: Email'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @api.model
    def send_ai_reply(self, message_id, body, to_address=False, subject=False):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return {'success': False, 'error': 'Email non trovata'}

        to_addr = to_address or msg.sender_email
        sub = subject or (f"Re: {msg.subject}" if msg.subject and not msg.subject.startswith('Re:') else msg.subject or 'Re: Email')

        try:
            res = msg.send_reply(
                message_id=msg.id,
                to_address=to_addr,
                subject=sub,
                body=body,
                account_id=msg.account_id.id if msg.account_id else False
            )
            if isinstance(res, dict) and not res.get('success', True):
                return {'success': False, 'error': res.get('error', 'Invio fallito')}
            
            msg.write({'is_read': True, 'state': 'keep'})
            return {'success': True}
        except Exception as e:
            _logger.exception("SMTP Send Error: %s", e)
            return {'success': False, 'error': str(e)}

    @api.model
    def cleanup_legacy_entrypoints(self):
        """Keep one visible operational cockpit and hide obsolete 360 entrypoints."""
        refs_to_disable = [
            'casafolino_crm_360.menu_crm360_root',
            'casafolino_crm_export.menu_cf_projects_360',
            'casafolino_pipeline_control.menu_cf_pipeline_control',
            'casafolino_pipeline_control.menu_cf_pipeline_root_control',
            'casafolino_pipeline_control.menu_cf_pipeline_root_inbox',
            'casafolino_pipeline_control.menu_cf_pipeline_root_followup',
            'casafolino_pipeline_control.menu_cf_pipeline_root_post_fair',
            'casafolino_pipeline_control.menu_cf_pipeline_root_pipeline',
            'casafolino_pipeline_control.menu_cf_pipeline_root_dossiers',
            'casafolino_pipeline_control.menu_cf_pipeline_inbox',
            'casafolino_pipeline_control.menu_cf_pipeline_followup',
            'casafolino_pipeline_control.menu_cf_pipeline_post_fair',
            'casafolino_pipeline_control.menu_cf_pipeline_pipeline',
            'casafolino_pipeline_control.menu_cf_pipeline_dossiers',
            'casafolino_b2b_portal.menu_cf_b2b_control_room',
            'casafolino_crm_360.crm_lead_form_crm360_button',
            'casafolino_crm_360.crm_lead_form_premium_crm360_button',
            'casafolino_crm_360.view_project_project_form_crm360',
            'casafolino_crm_360.view_project_project_list_crm360',
            'casafolino_pipeline_control.view_crm_lead_premium_legacy_360_to_dossier',
            'casafolino_pipeline_control.view_crm_lead_standard_legacy_360_to_dossier',
            'casafolino_pipeline_control.view_project_form_legacy_360_to_dossier',
        ]
        for xmlid in refs_to_disable:
            record = self.env.ref(xmlid, raise_if_not_found=False)
            if record and 'active' in record._fields:
                record.write({'active': False})

        console_action = self.env.ref('casafolino_pipeline_control.action_cf_pipeline_control', raise_if_not_found=False)
        console_menu = self.env.ref('casafolino_pipeline_control.menu_cf_pipeline_control_root', raise_if_not_found=False)
        home_action = self.env.ref('casafolino_home.action_scrivania_commerciale', raise_if_not_found=False)
        home_menu = self.env.ref('casafolino_home.menu_cf_home_root', raise_if_not_found=False)
        if home_action and home_menu:
            home_menu.write({
                'name': 'Sala Controllo',
                'action': 'ir.actions.client,%s' % home_action.id,
                'active': True,
            })
        if console_action and console_menu:
            console_menu.write({
                'name': 'Console CRM',
                'action': 'ir.actions.client,%s' % console_action.id,
                'active': not bool(home_action),
            })
            child_menus = self.env['ir.ui.menu'].sudo().search([
                ('parent_id', '=', console_menu.id),
                ('active', '=', True),
            ])
            if child_menus:
                child_menus.write({'active': False})
            self.env.cr.execute(
                "UPDATE ir_ui_menu SET active = false WHERE parent_id = %s",
                (console_menu.id,),
            )

        desk_menu = self.env.ref('casafolino_mail.menu_mail_v3_root', raise_if_not_found=False)
        if console_action and desk_menu:
            desk_menu.write({
                'name': 'Console CRM',
                'action': 'ir.actions.client,%s' % console_action.id,
                'active': not bool(home_action),
            })

        action = self.env.ref('casafolino_crm_export.action_project_dashboard_360', raise_if_not_found=False)
        if action and action._name == 'ir.actions.client':
            action.write({
                'name': 'Dossier / Progetti',
                'tag': 'casafolino_pipeline_control',
                'target': 'current',
                'context': "{'default_view': 'dossiers'}",
            })

        old_action = self.env.ref('casafolino_crm_360.action_crm360_dossiers', raise_if_not_found=False)
        if old_action and old_action._name == 'ir.actions.act_window':
            old_action.write({
                'name': 'Dossier / Progetti',
                'res_model': 'project.project',
                'view_mode': 'list,form',
                'domain': "[('cf_status_dossier', '!=', False)]",
                'context': "{'default_cf_status_dossier': 'exploration'}",
            })
        return True

    def _normalize_fair_id(self, fair_id):
        if not fair_id:
            return False
        try:
            return int(fair_id)
        except (TypeError, ValueError):
            _logger.warning("Ignoring invalid fair_id for Pipeline Control: %s", fair_id)
            return False

    def _safe_section(self, name, func, fallback):
        try:
            return func()
        except Exception:
            _logger.exception("Pipeline Control section %s failed", name)
            return fallback

    def _get_pipeline_discipline(self, today):
        Lead = self.env['crm.lead']
        base_domain = [
            ('type', '=', 'opportunity'),
            ('active', '=', True),
            ('stage_id.fold', '=', False),
        ]
        missing_followup_domain = base_domain + [('cf_date_next_followup', '=', False)]
        overdue_followup_domain = base_domain + [('cf_date_next_followup', '<', today)]
        missing_partner_domain = base_domain + [('partner_id', '=', False)]
        missing_dossier_domain = base_domain + [('cf_project_id', '=', False)]

        missing_followup = Lead.search(
            missing_followup_domain,
            order='expected_revenue desc, write_date desc, id desc',
            limit=10,
        )
        rows = []
        for lead in missing_followup:
            item = self._format_lead_item(lead, today)
            item['issue'] = 'Manca prossima azione'
            item['suggested_action'] = 'Pianifica oggi'
            rows.append(item)

        return {
            'kpis': [
                {
                    'key': 'missing_followup',
                    'label': 'Senza prossima azione',
                    'value': Lead.search_count(missing_followup_domain),
                    'hint': 'Lead aperti da pianificare',
                    'tone': 'red',
                },
                {
                    'key': 'overdue_followup',
                    'label': 'Follow-up scaduti',
                    'value': Lead.search_count(overdue_followup_domain),
                    'hint': 'Da recuperare prima',
                    'tone': 'amber',
                },
                {
                    'key': 'missing_partner',
                    'label': 'Senza cliente',
                    'value': Lead.search_count(missing_partner_domain),
                    'hint': 'Da collegare ad anagrafica',
                    'tone': 'blue',
                },
                {
                    'key': 'missing_dossier',
                    'label': 'Senza dossier',
                    'value': Lead.search_count(missing_dossier_domain),
                    'hint': 'Lead non promossi a progetto',
                    'tone': 'green',
                },
            ],
            'rows': rows,
        }

    def _get_kpis(self, today, user):
        Lead = self.env['crm.lead']
        Sample = self.env['cf.export.sample']
        Project = self.env['project.project']

        inbox_threads, _waiting_threads = self._get_latest_commercial_threads(user)
        followup_domain = self._lead_followup_domain(today)
        hot_domain = self._hot_lead_domain()
        samples_domain = self._sample_feedback_overdue_domain(today)
        blocked_domain = self._blocked_project_domain()

        return [
            {
                'key': 'to_reply',
                'label': 'Inbox',
                'value': len(inbox_threads),
                'hint': 'Mail inbound da lavorare',
                'tone': 'red',
            },
            {
                'key': 'followups',
                'label': 'Follow-up oggi',
                'value': Lead.search_count(followup_domain),
                'hint': 'Lead con prossima azione scaduta',
                'tone': 'amber',
            },
            {
                'key': 'hot_leads',
                'label': 'Clienti caldi',
                'value': Lead.search_count(hot_domain),
                'hint': 'Priorità alta o valore stimato',
                'tone': 'green',
            },
            {
                'key': 'sample_feedback',
                'label': 'Campioni scaduti',
                'value': Sample.search_count(samples_domain),
                'hint': 'Feedback atteso non ricevuto',
                'tone': 'red',
            },
            {
                'key': 'blocked_dossiers',
                'label': 'Dossier bloccati',
                'value': Project.search_count(blocked_domain),
                'hint': 'Semaforo rosso/giallo o in pausa',
                'tone': 'amber',
            },
            {
                'key': 'open_quotes',
                'label': 'Quotazioni aperte',
                'value': self.env['sale.order'].search_count([
                    ('state', 'in', ['draft', 'sent']),
                ]),
                'hint': 'Preventivi da seguire',
                'tone': 'blue',
            },
        ]

    def _get_followup_data(self, today, user):
        Lead = self.env['crm.lead']
        week_end = today + timedelta(days=7)
        base = [('type', '=', 'opportunity'), ('active', '=', True)]
        if user and not user.has_group('base.group_system'):
            base.append(('user_id', 'in', [False, user.id]))

        date_field = 'cf_date_next_followup' if 'cf_date_next_followup' in Lead._fields else 'date_deadline'
        overdue_domain = base + [(date_field, '<=', today)]
        week_domain = base + [(date_field, '>', today), (date_field, '<=', week_end)]
        no_plan_domain = base + [(date_field, '=', False)]
        hot_domain = self._hot_lead_domain()
        if user and not user.has_group('base.group_system'):
            hot_domain = hot_domain + [('user_id', 'in', [False, user.id])]

        overdue = Lead.search(overdue_domain, order='%s asc, expected_revenue desc, id desc' % date_field, limit=12)
        week = Lead.search(week_domain, order='%s asc, expected_revenue desc, id desc' % date_field, limit=12)
        no_plan = Lead.search(no_plan_domain, order='create_date desc, id desc', limit=12)
        hot = Lead.search(hot_domain, order='expected_revenue desc, create_date desc', limit=12)
        waiting_leads = self._waiting_customer_leads(user)

        return {
            'kpis': [
                {'label': 'Scaduti / oggi', 'value': Lead.search_count(overdue_domain), 'hint': 'Prossima azione entro oggi'},
                {'label': 'Prossimi 7 giorni', 'value': Lead.search_count(week_domain), 'hint': 'Follow-up pianificati'},
                {'label': 'Da pianificare', 'value': Lead.search_count(no_plan_domain), 'hint': 'Lead senza prossima azione'},
                {'label': 'In attesa cliente', 'value': len(waiting_leads), 'hint': 'Ultimo segnale outbound'},
            ],
            'columns': [
                self._followup_column('Scaduti / oggi', overdue, today, 'red'),
                self._followup_column('Prossimi 7 giorni', week, today, 'amber'),
                self._followup_column('Da pianificare', no_plan, today, 'blue'),
                self._followup_column('Clienti caldi', hot, today, 'green'),
            ],
            'routes': self._followup_routes(today, user),
            'timeline': self._followup_timeline(overdue | week | no_plan | waiting_leads, today),
        }

    def _followup_routes(self, today, user):
        inbox, waiting = self._get_latest_commercial_threads(user)
        signal_items = [
            self._format_followup_lead_item(msg.lead_id, today) if msg.lead_id else self._format_mail_item(msg)
            for msg in inbox[:8]
        ]
        quotes = self._open_quotes()
        samples = self.env['cf.export.sample'].search([
            ('state', 'not in', ['feedback_ok', 'feedback_ko', 'no_feedback']),
        ], order='date_feedback_expected asc, create_date desc', limit=8)
        dossiers = self.env['project.project'].search(self._active_project_domain(), order='write_date desc, id desc', limit=8)
        return [
            {
                'title': 'Inbound / nuove risposte',
                'count': len(inbox),
                'tone': 'red',
                'items': signal_items,
                'empty': 'Nessuna risposta inbound',
            },
            {
                'title': 'Quotazioni aperte',
                'count': len(quotes),
                'tone': 'blue',
                'items': [self._format_quote_item(order) for order in quotes[:8]],
                'empty': 'Nessuna quotazione aperta',
            },
            {
                'title': 'Campionature',
                'count': len(samples),
                'tone': 'amber',
                'items': [self._format_sample_item(sample, today) for sample in samples[:8]],
                'empty': 'Nessuna campionatura attiva',
            },
            {
                'title': 'Dossier / progetti',
                'count': len(dossiers),
                'tone': 'green',
                'items': [self._format_project_item(project) for project in dossiers[:8]],
                'empty': 'Nessun dossier attivo',
            },
        ]

    def _waiting_customer_leads(self, user):
        _inbox, waiting = self._get_latest_commercial_threads(user)
        lead_ids = [msg.lead_id.id for msg in waiting if msg.lead_id]
        return self.env['crm.lead'].browse(lead_ids).exists()

    def _followup_column(self, title, leads, today, tone):
        return {
            'title': title,
            'count': len(leads),
            'tone': tone,
            'items': [self._format_followup_lead_item(lead, today) for lead in leads[:8]],
        }

    def _followup_timeline(self, leads, today):
        rows = [self._format_followup_timeline_row(lead, today) for lead in leads[:40]]
        rows.sort(key=lambda row: (not row['is_overdue'], row['next_action'] or '9999-12-31', row['value'] * -1))
        return rows[:20]

    def _get_control_lanes(self, today, user):
        Lead = self.env['crm.lead']
        Project = self.env['project.project']

        inbox_threads, _waiting_threads = self._get_latest_commercial_threads(user)
        to_reply = inbox_threads[:6]
        followup_domain = self._lead_followup_domain(today)
        hot_domain = self._hot_lead_domain()
        blocked_domain = self._blocked_project_domain()
        followups = Lead.search(self._lead_followup_domain(today), order='cf_date_next_followup asc, date_deadline asc, id desc', limit=6)
        hot = Lead.search(self._hot_lead_domain(), order='expected_revenue desc, create_date desc', limit=6)
        blocked = Project.search(self._blocked_project_domain(), limit=6)

        return [
            {
                'key': 'to_reply',
                'title': 'Tocca a noi',
                'tone': 'red',
                'count': len(inbox_threads),
                'items': [self._format_mail_item(msg) for msg in to_reply],
            },
            {
                'key': 'followups',
                'title': 'Follow-up oggi',
                'tone': 'amber',
                'count': Lead.search_count(followup_domain),
                'items': [self._format_lead_item(lead, today) for lead in followups],
            },
            {
                'key': 'hot',
                'title': 'Clienti caldi',
                'tone': 'green',
                'count': Lead.search_count(hot_domain),
                'items': [self._format_lead_item(lead, today) for lead in hot],
            },
            {
                'key': 'blocked',
                'title': 'Bloccati',
                'tone': 'red',
                'count': Project.search_count(blocked_domain),
                'items': [self._format_project_item(project) for project in blocked],
            },
        ]

    def _get_b2b_registration_data(self, today):
        Partner = self.env['res.partner'].sudo()
        if 'cf_b2b_status' not in Partner._fields:
            return {'kpis': [], 'rows': []}

        base_domain = [('cf_b2b_status', '!=', 'none')]
        pending_domain = [('cf_b2b_status', '=', 'pending')]
        approved_domain = [('cf_b2b_status', '=', 'approved')]
        suspended_domain = [('cf_b2b_status', '=', 'suspended')]
        requested_field = 'cf_b2b_requested_at' if 'cf_b2b_requested_at' in Partner._fields else 'create_date'
        rows = Partner.search(base_domain, order='%s desc, id desc' % requested_field, limit=12)

        today_start = fields.Datetime.to_datetime(today)
        today_domain = base_domain + [(requested_field, '>=', today_start)]
        approved_today_domain = approved_domain
        if 'cf_b2b_approved_at' in Partner._fields:
            approved_today_domain = approved_domain + [('cf_b2b_approved_at', '>=', today_start)]

        return {
            'kpis': [
                {
                    'key': 'pending',
                    'label': 'Da approvare',
                    'value': Partner.search_count(pending_domain),
                    'hint': 'Registrazioni in attesa',
                    'tone': 'amber',
                },
                {
                    'key': 'today',
                    'label': 'Registrazioni oggi',
                    'value': Partner.search_count(today_domain),
                    'hint': 'Nuove richieste B2B',
                    'tone': 'blue',
                },
                {
                    'key': 'approved',
                    'label': 'Approvati',
                    'value': Partner.search_count(approved_domain),
                    'hint': 'Account B2B attivi',
                    'tone': 'green',
                },
                {
                    'key': 'approved_today',
                    'label': 'Approvati oggi',
                    'value': Partner.search_count(approved_today_domain),
                    'hint': 'Conversioni odierne',
                    'tone': 'green',
                },
                {
                    'key': 'suspended',
                    'label': 'Sospesi',
                    'value': Partner.search_count(suspended_domain),
                    'hint': 'Accessi bloccati',
                    'tone': 'red',
                },
            ],
            'rows': [self._format_b2b_registration_row(partner) for partner in rows],
        }

    def _format_b2b_registration_row(self, partner):
        source_labels = dict(partner._fields['cf_b2b_source'].selection) if 'cf_b2b_source' in partner._fields else {}
        category_labels = dict(partner._fields['cf_b2b_category'].selection) if 'cf_b2b_category' in partner._fields else {}
        status_labels = dict(partner._fields['cf_b2b_status'].selection)
        requested_at = partner.cf_b2b_requested_at if 'cf_b2b_requested_at' in partner._fields else partner.create_date
        approved_at = partner.cf_b2b_approved_at if 'cf_b2b_approved_at' in partner._fields else False
        return {
            'id': partner.id,
            'model': 'res.partner',
            'res_id': partner.id,
            'name': partner.display_name,
            'email': partner.email or '',
            'phone': partner.phone or partner.mobile or '',
            'vat': partner.cf_b2b_vat_code or partner.vat or '',
            'status': partner.cf_b2b_status or '',
            'status_label': status_labels.get(partner.cf_b2b_status, partner.cf_b2b_status or ''),
            'source_label': source_labels.get(partner.cf_b2b_source, partner.cf_b2b_source or '') if 'cf_b2b_source' in partner._fields else '',
            'category_label': category_labels.get(partner.cf_b2b_category, partner.cf_b2b_category or '') if 'cf_b2b_category' in partner._fields else '',
            'requested_at': self._format_datetime_short(requested_at),
            'approved_at': self._format_datetime_short(approved_at),
            'salesperson': partner.user_id.name if partner.user_id else '',
        }

    def _format_datetime_short(self, value):
        if not value:
            return ''
        dt_value = fields.Datetime.to_datetime(value)
        if not dt_value:
            return ''
        localized = fields.Datetime.context_timestamp(self, dt_value)
        return localized.strftime('%d/%m %H:%M')

    def _get_post_fair_data(self, today, fair_id=False):
        Fair = self.env['cf.export.fair']
        fair_options = self._get_fair_options()
        fair = Fair.browse(int(fair_id)).exists() if fair_id else Fair
        if not fair:
            fair = Fair.search([], limit=1)
        if not fair:
            return {
                'fair': False,
                'kpis': [],
                'columns': [],
                'timeline': [],
                'fair_options': fair_options,
            }

        leads = fair.lead_ids
        mail_stats = self._mail_stats_by_lead(leads.ids)
        replied = leads.filtered(lambda lead: mail_stats.get(lead.id, {}).get('inbound', 0) > 0)
        first_followup = leads.filtered(lambda lead: mail_stats.get(lead.id, {}).get('outbound', 0) >= 1 or bool(lead.cf_date_last_contact))
        second_followup = leads.filtered(lambda lead: mail_stats.get(lead.id, {}).get('outbound', 0) >= 2)
        third_followup = leads.filtered(lambda lead: mail_stats.get(lead.id, {}).get('outbound', 0) >= 3)
        quoted = leads.filtered(lambda lead: lead.expected_revenue and lead.expected_revenue > 0)
        samples = self.env['cf.export.sample'].search([('lead_id', 'in', leads.ids)]) if leads else self.env['cf.export.sample']
        dossiers = leads.filtered(lambda lead: bool(lead.cf_project_id))
        no_reply = leads.filtered(lambda lead: mail_stats.get(lead.id, {}).get('inbound', 0) == 0)
        date_field = 'cf_date_next_followup' if 'cf_date_next_followup' in self.env['crm.lead']._fields else 'date_deadline'
        due_today = leads.filtered(lambda lead: bool(lead[date_field]) and fields.Date.to_date(lead[date_field]) == today)
        overdue = leads.filtered(lambda lead: bool(lead[date_field]) and fields.Date.to_date(lead[date_field]) < today)
        no_plan = leads.filtered(lambda lead: not lead[date_field])
        no_outbound = no_reply.filtered(lambda lead: mail_stats.get(lead.id, {}).get('outbound', 0) == 0 and not lead.cf_date_last_contact)
        followup_1 = no_reply.filtered(lambda lead: mail_stats.get(lead.id, {}).get('outbound', 0) == 1 or (lead.cf_date_last_contact and mail_stats.get(lead.id, {}).get('outbound', 0) == 0))
        followup_2 = no_reply.filtered(lambda lead: mail_stats.get(lead.id, {}).get('outbound', 0) == 2)
        followup_3 = no_reply.filtered(lambda lead: mail_stats.get(lead.id, {}).get('outbound', 0) >= 3)

        def pct(part, total):
            return round((part / total) * 100) if total else 0

        return {
            'fair': {
                'id': fair.id,
                'name': fair.name,
                'date': self._fair_date_range(fair),
                'location': ', '.join(self._compact([fair.location, fair.country_id.name if fair.country_id else False])),
                'state': dict(fair._fields['state'].selection).get(fair.state, fair.state) if fair.state else '',
            },
            'fair_options': fair_options,
            'kpis': [
                {'label': 'Lead raccolti', 'value': len(leads), 'hint': 'Trattative collegate'},
                {'label': 'Da fare oggi', 'value': len(due_today), 'hint': 'Prossima azione oggi'},
                {'label': 'In ritardo', 'value': len(overdue), 'hint': 'Follow-up scaduti'},
                {'label': 'Da pianificare', 'value': len(no_plan), 'hint': 'Senza prossima azione'},
                {'label': 'Follow-up 1', 'value': len(first_followup), 'hint': '%s%% del totale' % pct(len(first_followup), len(leads))},
                {'label': 'Follow-up 2', 'value': len(second_followup), 'hint': '%s%% del totale' % pct(len(second_followup), len(leads))},
                {'label': 'Follow-up 3', 'value': len(third_followup), 'hint': '%s%% del totale' % pct(len(third_followup), len(leads))},
                {'label': 'Response rate', 'value': '%s%%' % pct(len(replied), len(leads)), 'hint': '%s risposte su %s lead' % (len(replied), len(leads))},
                {'label': 'Quotazioni', 'value': len(quoted), 'hint': 'Con valore atteso'},
                {'label': 'Campionature', 'value': len(samples), 'hint': 'Standard/custom'},
                {'label': 'Dossier', 'value': len(dossiers), 'hint': 'Lead promossi'},
            ],
            'columns': [
                self._fair_column('Da fare oggi', due_today, today, mail_stats),
                self._fair_column('In ritardo', overdue, today, mail_stats),
                self._fair_column('Da contattare', no_outbound, today, mail_stats),
                self._fair_column('Follow-up 1', followup_1, today, mail_stats),
                self._fair_column('Follow-up 2', followup_2, today, mail_stats),
                self._fair_column('Follow-up 3+', followup_3, today, mail_stats),
                self._fair_column('Ha risposto', replied, today),
            ],
            'timeline': self._fair_timeline(leads, mail_stats, today),
        }

    def _get_fair_options(self):
        fairs = self.env['cf.export.fair'].search([], order='date_start desc, id desc', limit=20)
        return [{
            'id': fair.id,
            'name': fair.name,
            'date': self._fair_date_range(fair),
            'state': dict(fair._fields['state'].selection).get(fair.state, fair.state) if fair.state else '',
        } for fair in fairs]

    def _mail_stats_by_lead(self, lead_ids):
        stats = {lead_id: {'inbound': 0, 'outbound': 0, 'last_date': False} for lead_id in lead_ids}
        if not lead_ids:
            return stats
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        if not Mail:
            return stats
        messages = Mail.search([
            ('lead_id', 'in', lead_ids),
            ('is_deleted', '=', False),
        ], order='email_date desc, id desc', limit=2000)
        for msg in messages:
            bucket = stats.setdefault(msg.lead_id.id, {'inbound': 0, 'outbound': 0, 'last_date': False})
            direction = msg.direction_computed or msg.direction
            if direction == 'inbound':
                bucket['inbound'] += 1
            elif direction == 'outbound':
                bucket['outbound'] += 1
            if not bucket['last_date'] and msg.email_date:
                bucket['last_date'] = msg.email_date
        return stats

    def _fair_timeline(self, leads, mail_stats, today):
        rows = []
        for lead in leads:
            stats = mail_stats.get(lead.id, {})
            rows.append({
                'id': lead.id,
                'model': lead._name,
                'res_id': lead.id,
                'title': lead.partner_id.display_name if lead.partner_id else lead.name,
                'subtitle': lead.name,
                'stage': lead.stage_id.name if lead.stage_id else '',
                'owner': lead.user_id.name if lead.user_id else '',
                'last_contact': self._date_label(stats.get('last_date') or lead.cf_date_last_contact or lead.create_date),
                'next_action': self._date_label(lead.cf_date_next_followup or lead.date_deadline),
                'is_overdue': bool((lead.cf_date_next_followup or lead.date_deadline) and fields.Date.to_date(lead.cf_date_next_followup or lead.date_deadline) <= today),
                'outbound': stats.get('outbound', 0),
                'inbound': stats.get('inbound', 0),
                'value': lead.expected_revenue or 0,
            })
        rows.sort(key=lambda row: (not row['is_overdue'], row['next_action'] or '9999-12-31', row['last_contact'] or ''), reverse=False)
        return rows[:18]

    def _lead_ids_with_mail(self, lead_ids):
        if not lead_ids:
            return set()
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        if not Mail:
            return set()
        groups = Mail.read_group(
            [('lead_id', 'in', lead_ids), ('direction_computed', '=', 'inbound')],
            ['lead_id'],
            ['lead_id'],
        )
        return {group['lead_id'][0] for group in groups if group.get('lead_id')}

    def _get_pipeline_data(self, today):
        Lead = self.env['crm.lead']
        stages = self.env['crm.stage'].search([], order='sequence asc, id asc', limit=8)
        columns = []
        for stage in stages:
            leads = Lead.search([('stage_id', '=', stage.id)], order='expected_revenue desc, create_date desc', limit=5)
            columns.append({
                'id': stage.id,
                'title': stage.name,
                'count': Lead.search_count([('stage_id', '=', stage.id)]),
                'items': [self._format_lead_item(lead, today) for lead in leads],
            })
        return columns

    def _get_inbox_data(self, user):
        if 'casafolino.mail.message' not in self.env:
            return self._empty_inbox_data()
        inbox, waiting = self._get_latest_commercial_threads(user)
        rows_to_reply = [self._format_mail_row(msg) for msg in inbox[:24]]
        rows_waiting = [self._format_mail_row(msg) for msg in waiting[:24]]
        all_rows = rows_to_reply + rows_waiting

        # Weekly AI category distribution stats for the visual dashboard
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=7)
        self.env.cr.execute("""
            SELECT ai_category, COUNT(*)
            FROM casafolino_mail_message
            WHERE email_date >= %s AND is_deleted = False AND ai_category IS NOT NULL
            GROUP BY ai_category
        """, [cutoff])
        
        distribution = {}
        total_counted = 0
        for cat, count in self.env.cr.fetchall():
            distribution[cat] = count
            total_counted += count
            
        stats_list = []
        for cat in ['commerciale', 'admin', 'fornitore', 'newsletter', 'interno', 'personale', 'spam']:
            count = distribution.get(cat, 0)
            percentage = int(count / total_counted * 100) if total_counted > 0 else 0
            stats_list.append({
                'category': cat,
                'label': cat.title(),
                'count': count,
                'percentage': percentage,
            })

        return {
            'kpis': [
                {'label': 'Tocca a noi', 'value': len(inbox), 'hint': 'Ultimo messaggio inbound o azione richiesta'},
                {'label': 'Tocca al cliente', 'value': len(waiting), 'hint': 'Ultimo messaggio outbound'},
                {'label': 'Senza lead', 'value': len([row for row in all_rows if not row.get('lead_id')]), 'hint': 'Da collegare alla pipeline CRM'},
                {'label': 'Urgenti', 'value': len([row for row in all_rows if row.get('urgency') == 'high']), 'hint': 'AI urgenza alta'},
            ],
            'distribution_stats': stats_list,
            'to_reply': rows_to_reply,
            'waiting_customer': rows_waiting,
        }

    def _empty_inbox_data(self):
        return {
            'kpis': [
                {'label': 'Tocca a noi', 'value': 0, 'hint': 'Mail V2 disinstallata'},
                {'label': 'Tocca al cliente', 'value': 0, 'hint': 'Usa attivita e chatter Odoo'},
                {'label': 'Senza lead', 'value': 0, 'hint': 'Nessuna inbox custom attiva'},
                {'label': 'Urgenti', 'value': 0, 'hint': 'Nessuna urgenza email custom'},
            ],
            'distribution_stats': [],
            'to_reply': [],
            'waiting_customer': [],
        }

    @api.model
    def mail_quick_action(self, message_id, quick_action):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return self._notify('Email non trovata', 'Il thread non e piu disponibile.', 'warning')

        if quick_action == 'open':
            return self._open_record(msg, 'Email')
        if quick_action == 'open_thread':
            if msg.thread_id:
                return self._open_record(msg.thread_id, 'Thread email')
            return self._open_record(msg, 'Email')
        if quick_action == 'reply':
            return self._reply_from_message(msg)
        if quick_action == 'templates':
            return self._open_mail_templates()
        if quick_action == 'materials':
            return self._open_mail_materials(msg)
        if quick_action == 'attach_material':
            return self._attach_material_from_message(msg)
        if quick_action == 'open_lead':
            if msg.lead_id:
                return self._open_record(msg.lead_id, 'Lead')
            return msg.action_create_lead()
        if quick_action == 'create_lead':
            return msg.action_create_lead()
        if quick_action == 'create_dossier':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Crea dossier da email',
                'res_model': 'cf.pipeline.create.dossier.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_message_id': msg.id},
                'reload': True,
            }
        if quick_action == 'link_lead':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Collega email a lead',
                'res_model': 'cf.pipeline.link.lead.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_message_id': msg.id},
                'reload': True,
            }
        if quick_action == 'task':
            return self._new_task_from_message(msg)
        if quick_action == 'quote':
            return self._new_quote_from_message(msg)
        if quick_action == 'sample':
            return self._new_sample_from_message(msg)
        if quick_action == 'snooze':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Posticipa thread',
                'res_model': 'cf.pipeline.snooze.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_message_id': msg.id},
                'reload': True,
            }
        if quick_action == 'archive':
            msg.action_archive()
            return self._notify('Thread archiviato', 'La conversazione e stata rimossa dalla Console CRM.', reload=True)
        return self._notify('Azione non disponibile', quick_action, 'warning')

    def _open_mail_templates(self):
        action = self.env.ref('casafolino_mail.action_casafolino_mail_template', raise_if_not_found=False)
        if not action:
            return self._notify('Template non disponibili', 'Installa o aggiorna casafolino_mail.', 'warning')
        result = action.sudo().read()[0]
        result['target'] = 'current'
        return result

    def _open_mail_materials(self, msg=None):
        action = self.env.ref('casafolino_mail.action_casafolino_mail_material', raise_if_not_found=False)
        if not action:
            return self._notify('Materiali non disponibili', 'Installa o aggiorna casafolino_mail.', 'warning')
        result = action.sudo().read()[0]
        result['name'] = 'Materiali commerciali'
        raw_context = result.get('context') or {}
        context = safe_eval(raw_context) if isinstance(raw_context, str) else dict(raw_context)
        if msg:
            context.update({
                'default_message_id': msg.id,
                'active_message_id': msg.id,
                'default_partner_id': msg.partner_id.id if msg.partner_id else False,
                'default_lead_id': msg.lead_id.id if msg.lead_id else False,
            })
        result['context'] = context
        result['target'] = 'current'
        return result

    def _attach_material_from_message(self, msg):
        if 'casafolino.mail.material.picker.wizard' not in self.env:
            return self._notify('Materiali non disponibili', 'Aggiorna casafolino_mail.', 'warning')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Allega materiale',
            'res_model': 'casafolino.mail.material.picker.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_message_id': msg.id,
                'active_message_id': msg.id,
            },
        }

    @api.model
    def lead_quick_action(self, lead_id, quick_action):
        lead = self.env['crm.lead'].browse(int(lead_id)).exists()
        if not lead:
            return self._notify('Lead non trovato', 'La trattativa non e piu disponibile.', 'warning')

        if quick_action == 'open':
            return self._open_record(lead, 'Lead')
        if quick_action == 'email' and hasattr(lead, 'action_compose_email_f8'):
            return lead.action_compose_email_f8()
        if quick_action == 'followup7':
            if hasattr(lead, 'action_schedule_followup'):
                lead.action_schedule_followup()
            else:
                lead.write({'date_deadline': fields.Date.context_today(self) + timedelta(days=7)})
            return self._notify('Follow-up pianificato', 'Prossima azione tra 7 giorni.', reload=True)
        if quick_action == 'sample':
            return self._new_sample_from_lead(lead)
        if quick_action == 'quote':
            return self._new_quote_from_lead(lead)
        if quick_action == 'task':
            return self._new_task_from_lead(lead)
        if quick_action == 'today':
            date_field = 'cf_date_next_followup' if 'cf_date_next_followup' in lead._fields else 'date_deadline'
            lead.write({date_field: fields.Date.context_today(self)})
            return self._notify('Follow-up messo a oggi', 'La trattativa rientra nella lista scaduti / oggi.', reload=True)
        if quick_action == 'dossier':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Promuovi a dossier',
                'res_model': 'cf.pipeline.promote.dossier.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_lead_id': lead.id},
                'reload': True,
            }
        return self._notify('Azione non disponibile', quick_action, 'warning')

    @api.model
    def plan_fair_followups(self, fair_id=False):
        fair = self.env['cf.export.fair'].browse(int(fair_id)).exists() if fair_id else self.env['cf.export.fair']
        if not fair:
            return self._notify('Fiera richiesta', 'Seleziona prima una fiera.', 'warning')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pianifica follow-up fiera',
            'res_model': 'cf.pipeline.plan.fair.followup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_fair_id': fair.id},
            'reload': True,
        }

    @api.model
    def record_quick_action(self, model, res_id, quick_action):
        allowed_models = {
            'sale.order': 'Quotazione',
            'cf.export.sample': 'Campionatura',
            'project.project': 'Dossier',
            'project.task': 'Task',
        }
        if model not in allowed_models:
            return self._notify('Azione non disponibile', model, 'warning')
        record = self.env[model].browse(int(res_id)).exists()
        if not record:
            return self._notify('%s non trovato' % allowed_models[model], 'Il record non e piu disponibile.', 'warning')
        if quick_action == 'open':
            return self._open_record(record, allowed_models[model])
        if model == 'project.project' and quick_action == 'email' and hasattr(record, 'action_compose_email_f8'):
            return record.action_compose_email_f8()
        if model == 'project.project' and quick_action == 'reply' and hasattr(record, 'action_reply_last_email_f8'):
            return record.action_reply_last_email_f8()
        if quick_action == 'task':
            return self._new_operational_task(record)
        if quick_action == 'followup7':
            return self._new_followup_task(record, fields.Date.context_today(self) + timedelta(days=7))
        if quick_action == 'today':
            return self._new_followup_task(record, fields.Date.context_today(self))
        return self._notify('Azione non disponibile', quick_action, 'warning')

    def _get_latest_commercial_threads(self, user):
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        if not Mail:
            return [], []

        def latest_per_thread(messages):
            latest_by_thread = {}
            for msg in messages:
                key = msg.thread_key or (msg.partner_id.id and 'partner:%s' % msg.partner_id.id) or msg.sender_email or msg.subject or msg.id
                if key not in latest_by_thread:
                    latest_by_thread[key] = msg
            return list(latest_by_thread.values())

        Mail = Mail.sudo()
        base_domain = [
            ('is_archived', '=', False),
            ('is_deleted', '=', False),
            '|',
            ('thread_id', '=', False),
            ('thread_id.is_snoozed', '=', False),
        ]
        to_reply_domain = base_domain + [
            ('state', 'in', ['new', 'review', 'keep', 'auto_keep', 'auto_attached']),
            '|',
            ('direction_computed', '=', 'inbound'),
            '&',
            ('direction_computed', '=', False),
            ('direction', '=', 'inbound'),
        ]
        action_required_domain = base_domain + [
            ('ai_action_required', '=', True),
            ('state', 'in', ['new', 'review', 'keep', 'auto_keep', 'auto_attached']),
        ]
        waiting_domain = base_domain + [
            ('state', 'in', ['keep', 'auto_keep', 'auto_attached']),
            '|',
            ('direction_computed', '=', 'outbound'),
            '&',
            ('direction_computed', '=', False),
            ('direction', '=', 'outbound'),
        ]

        to_reply = latest_per_thread(Mail.search(to_reply_domain, order='email_date desc, id desc', limit=500))
        known_reply_ids = {msg.id for msg in to_reply}
        for msg in latest_per_thread(Mail.search(action_required_domain, order='email_date desc, id desc', limit=200)):
            if msg.id not in known_reply_ids:
                to_reply.append(msg)
                known_reply_ids.add(msg.id)
        waiting = latest_per_thread(Mail.search(waiting_domain, order='email_date desc, id desc', limit=500))
        return to_reply, waiting

    def _get_dossier_data(self, today):
        Project = self.env['project.project']
        projects = Project.search(self._active_project_domain(), order='write_date desc, id desc', limit=16)
        return [self._format_project_detail(project, today) for project in projects]

    def _mail_to_reply_domain(self, user):
        domain = [
            ('direction_computed', '=', 'inbound'),
            ('is_archived', '=', False),
            ('is_deleted', '=', False),
            ('state', 'in', ['new', 'review', 'keep', 'auto_keep', 'auto_attached']),
            '|',
            ('thread_id', '=', False),
            ('thread_id.is_snoozed', '=', False),
        ]
        if user and not user.has_group('base.group_system'):
            domain = ['|', ('assigned_user_ids', '=', False), ('assigned_user_ids', 'in', user.ids)] + domain
        return domain

    def _mail_waiting_customer_domain(self, user):
        domain = [
            ('direction_computed', '=', 'outbound'),
            ('is_archived', '=', False),
            ('is_deleted', '=', False),
            ('state', 'in', ['keep', 'auto_keep', 'auto_attached']),
            '|',
            ('thread_id', '=', False),
            ('thread_id.is_snoozed', '=', False),
        ]
        if user and not user.has_group('base.group_system'):
            domain = ['|', ('assigned_user_ids', '=', False), ('assigned_user_ids', 'in', user.ids)] + domain
        return domain

    def _lead_followup_domain(self, today):
        domain = [('type', '=', 'opportunity'), ('active', '=', True)]
        if 'cf_date_next_followup' in self.env['crm.lead']._fields:
            domain.append(('cf_date_next_followup', '<=', today))
        else:
            domain.append(('date_deadline', '<=', today))
        return domain

    def _hot_lead_domain(self):
        fields_map = self.env['crm.lead']._fields
        base = [('type', '=', 'opportunity'), ('active', '=', True)]
        priority_field = fields_map.get('casafolino_signals_priority')
        if priority_field and priority_field.store:
            return base + ['|', ('casafolino_signals_priority', '=', 'hot'), ('expected_revenue', '>', 0)]
        return base + [('expected_revenue', '>', 0)]

    def _sample_feedback_overdue_domain(self, today):
        return [
            ('date_feedback_expected', '<=', today),
            ('state', 'not in', ['feedback_ok', 'feedback_ko', 'no_feedback']),
        ]

    def _blocked_project_domain(self):
        Project = self.env['project.project']
        fields_map = Project._fields
        domain = []
        if 'cf_traffic_light' in fields_map:
            domain = ['|', ('cf_traffic_light', 'in', ['red', 'yellow']), ('cf_tasks_blocked', '>', 0)]
        elif 'cf_status_dossier' in fields_map:
            domain = [('cf_status_dossier', 'in', ['on_hold', 'active'])]
        else:
            domain = [('active', '=', True)]
        return domain

    def _active_project_domain(self):
        Project = self.env['project.project']
        if 'cf_status_dossier' in Project._fields:
            return [('cf_status_dossier', 'in', ['exploration', 'active', 'on_hold'])]
        return [('active', '=', True)]

    def _open_quotes(self):
        Sale = self.env['sale.order']
        domain = [('state', 'in', ['draft', 'sent'])]
        return Sale.search(domain, order='validity_date asc, write_date desc, id desc', limit=24)

    def _fair_column(self, title, leads, today, mail_stats=None):
        return {
            'title': title,
            'count': len(leads),
            'items': [self._format_fair_lead_item(lead, today, mail_stats or {}) for lead in leads[:8]],
        }

    def _format_fair_lead_item(self, lead, today, mail_stats):
        item = self._format_lead_item(lead, today)
        stats = mail_stats.get(lead.id, {})
        item['badges'] = self._compact(item.get('badges', []) + [
            '%s out' % stats.get('outbound', 0) if stats.get('outbound') else False,
            '%s in' % stats.get('inbound', 0) if stats.get('inbound') else False,
        ])
        return item

    def _fair_date_range(self, fair):
        start = self._date_label(fair.date_start)
        end = self._date_label(fair.date_end)
        if start and end and start != end:
            return '%s - %s' % (start, end)
        return end or start or ''

    def _format_mail_item(self, msg):
        partner = msg.partner_id
        lead = msg.lead_id
        return {
            'id': msg.id,
            'model': msg._name,
            'title': partner.display_name if partner else (msg.sender_name or msg.sender_email or 'Email senza partner'),
            'subtitle': msg.subject or 'Senza oggetto',
            'meta': self._date_label(msg.email_date),
            'tone': 'red' if msg.ai_urgency == 'high' or msg.ai_action_required else 'amber',
            'badges': self._compact([
                'tocca a noi',
                msg.ai_category,
                msg.ai_language,
                lead.stage_id.name if lead and lead.stage_id else False,
            ]),
            'res_id': msg.id,
        }

    def _format_mail_row(self, msg):
        item = self._format_mail_item(msg)
        
        # Deduplication matching suggestion for incoming email not linked to partner
        suggested_partner = False
        if not msg.partner_id and msg.sender_domain:
            generic_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com', 'mail.com', 'protonmail.com', 'libero.it', 'virgilio.it', 'tiscali.it', 'alice.it'}
            if msg.sender_domain not in generic_domains:
                domain_partner = self.env['res.partner'].search([
                    ('is_company', '=', True),
                    '|',
                    ('website', 'ilike', msg.sender_domain),
                    ('email', '=ilike', '%%@' + msg.sender_domain),
                ], limit=1)
                if domain_partner:
                    suggested_partner = {
                        'id': domain_partner.id,
                        'name': domain_partner.name,
                    }

        item.update({
            'lead': msg.lead_id.display_name if msg.lead_id else '',
            'lead_id': msg.lead_id.id if msg.lead_id else False,
            'partner_id': msg.partner_id.id if msg.partner_id else False,
            'suggested_partner': suggested_partner,
            'thread_id': msg.thread_id.id if msg.thread_id else False,
            'owner': ', '.join(msg.assigned_user_ids.mapped('name')) or '',
            'snippet': msg.snippet or '',
            'can_sample': bool(msg.lead_id),
            'account': msg.account_id.display_name if msg.account_id else '',
            'direction': msg.direction_computed or msg.direction or '',
            'urgency': msg.ai_urgency or '',
            'category': msg.ai_category or '',
            'language': msg.ai_language or '',
            'needs_action': bool(msg.ai_action_required),
            'thread_count': msg.thread_id.message_count if msg.thread_id else 1,
            'suggested_action': self._mail_suggested_action(msg),
        })
        return item

    def _mail_suggested_action(self, msg):
        if not msg.lead_id:
            return 'Collega lead'
        if msg.direction_computed == 'inbound' or msg.ai_action_required:
            return 'Rispondi'
        return 'Attendi risposta'

    def _open_record(self, record, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': record._name,
            'res_id': record.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _reply_from_message(self, msg):
        partner = msg.partner_id
        partner_email = partner.email if partner else (msg.sender_email or '')
        account = msg.account_id or self.env['casafolino.mail.account'].search([
            ('responsible_user_id', '=', self.env.user.id),
            ('active', '=', True),
        ], limit=1)
        return {
            'type': 'ir.actions.client',
            'name': 'Rispondi',
            'tag': 'casafolino_mail.compose_f8',
            'context': {
                'default_mode': 'reply',
                'default_account_id': account.id if account else False,
                'default_partner_email': partner_email,
                'default_subject': 'Re: %s' % (msg.subject or ''),
                'default_partner_id': partner.id if partner else False,
                'default_thread_id': msg.id,
                'default_thread_model': 'casafolino.mail.message',
            },
        }

    def _new_task_from_message(self, msg):
        lead = msg.lead_id
        project = getattr(lead, 'cf_project_id', False) if lead else False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuova task commerciale',
            'res_model': 'project.task',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_name': msg.subject or 'Follow-up commerciale',
                'default_project_id': project.id if project else False,
                'default_partner_id': msg.partner_id.id if msg.partner_id else False,
                'default_description': msg.snippet or '',
            },
        }

    def _new_task_from_lead(self, lead):
        project = getattr(lead, 'cf_project_id', False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuova task commerciale',
            'res_model': 'project.task',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_name': 'Follow-up: %s' % (lead.name or lead.display_name),
                'default_project_id': project.id if project else False,
                'default_partner_id': lead.partner_id.id if lead.partner_id else False,
            },
        }

    def _new_operational_task(self, record):
        partner = self._record_partner(record)
        project = record if record._name == 'project.project' else getattr(record, 'project_id', False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuova task operativa',
            'res_model': 'project.task',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_name': self._task_title_for_record(record),
                'default_project_id': project.id if project else False,
                'default_partner_id': partner.id if partner else False,
                'default_description': self._task_description_for_record(record),
            },
        }

    def _new_followup_task(self, record, deadline):
        action = self._new_operational_task(record)
        action['name'] = 'Pianifica follow-up'
        action['context'] = dict(action['context'], default_date_deadline=deadline)
        return action

    def _new_quote_from_message(self, msg):
        partner = msg.partner_id or msg.lead_id.partner_id
        return self._new_quote_action(partner, msg.lead_id, msg.subject or '')

    def _new_quote_from_lead(self, lead):
        return self._new_quote_action(lead.partner_id, lead, lead.name or '')

    def _new_quote_action(self, partner, lead, origin):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuova quotazione',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'context': {
                'default_partner_id': partner.id if partner else False,
                'default_opportunity_id': lead.id if lead else False,
                'default_origin': origin,
            },
        }

    def _new_sample_from_message(self, msg):
        if not msg.lead_id:
            return self._notify('Lead richiesto', 'Collega o crea prima una trattativa CRM.', 'warning')
        return self._new_sample_from_lead(msg.lead_id)

    def _new_sample_from_lead(self, lead):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuova campionatura',
            'res_model': 'cf.export.sample',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_lead_id': lead.id},
        }

    def _record_partner(self, record):
        return getattr(record, 'partner_id', False) or getattr(record, 'cf_partner_id', False)

    def _task_title_for_record(self, record):
        if record._name == 'sale.order':
            return 'Follow-up quotazione: %s' % (record.name or record.display_name)
        if record._name == 'cf.export.sample':
            return 'Sollecito feedback campione: %s' % (record.display_name or getattr(record, 'reference', ''))
        if record._name == 'project.project':
            return 'Prossima azione dossier: %s' % (record.name or record.display_name)
        return 'Task operativa: %s' % (record.display_name or record.id)

    def _task_description_for_record(self, record):
        if record._name == 'sale.order':
            return 'Verificare stato quotazione, prossima decisione cliente e possibilita ordine.'
        if record._name == 'cf.export.sample':
            return 'Verificare feedback campionatura, eventuali note qualita/logistica e prossima azione commerciale.'
        if record._name == 'project.project':
            return 'Aggiornare stato reparto, blocchi, prossima decisione e owner.'
        return ''

    def _notify(self, title, message, notification_type='success', reload=False):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notification_type,
                'sticky': False,
            },
            'reload': reload,
        }

    def _format_lead_item(self, lead, today):
        partner = lead.partner_id
        next_date = lead.cf_date_next_followup if 'cf_date_next_followup' in lead._fields else lead.date_deadline
        overdue = bool(next_date and next_date <= today)
        badges = [
            lead.stage_id.name if lead.stage_id else False,
            self._lead_origin_label(lead),
            partner.country_id.code if partner and partner.country_id else False,
            'follow-up oggi' if overdue else False,
            'dossier' if getattr(lead, 'cf_project_id', False) else False,
        ]
        if 'casafolino_signals_priority' in lead._fields and lead.casafolino_signals_priority:
            badges.append(lead.casafolino_signals_priority)
        return {
            'id': lead.id,
            'model': lead._name,
            'title': partner.display_name if partner else lead.name,
            'subtitle': lead.name,
            'meta': self._date_label(next_date) if next_date else 'Nessuna prossima azione',
            'value': lead.expected_revenue or 0,
            'tone': 'red' if overdue else 'green' if lead.expected_revenue else 'blue',
            'badges': self._compact(badges),
            'res_id': lead.id,
        }

    def _format_followup_lead_item(self, lead, today):
        item = self._format_lead_item(lead, today)
        item['owner'] = lead.user_id.name if lead.user_id else ''
        item['origin'] = self._lead_origin_label(lead)
        return item

    def _format_followup_timeline_row(self, lead, today):
        next_date = lead.cf_date_next_followup if 'cf_date_next_followup' in lead._fields else lead.date_deadline
        overdue = bool(next_date and fields.Date.to_date(next_date) <= today)
        return {
            'id': lead.id,
            'model': lead._name,
            'res_id': lead.id,
            'title': lead.partner_id.display_name if lead.partner_id else lead.name,
            'subtitle': lead.name,
            'origin': self._lead_origin_label(lead),
            'stage': lead.stage_id.name if lead.stage_id else '',
            'owner': lead.user_id.name if lead.user_id else '',
            'next_action': self._date_label(next_date),
            'is_overdue': overdue,
            'value': lead.expected_revenue or 0,
        }

    def _lead_origin_label(self, lead):
        if 'cf_fair_id' in lead._fields and lead.cf_fair_id:
            return 'Fiera'
        if 'source_email_id' in lead._fields and lead.source_email_id:
            return 'Email'
        if lead.source_id:
            return lead.source_id.name
        return 'Manuale'

    def _format_project_item(self, project):
        return {
            'id': project.id,
            'model': project._name,
            'title': project.name,
            'subtitle': self._project_partner_name(project),
            'meta': self._project_blocker_label(project),
            'tone': 'red',
            'badges': self._compact([
                self._project_status(project),
                self._project_blocker_label(project),
            ]),
            'res_id': project.id,
        }

    def _format_quote_item(self, order):
        partner = order.partner_id
        validity = getattr(order, 'validity_date', False)
        overdue = bool(validity and fields.Date.to_date(validity) <= fields.Date.context_today(self))
        return {
            'id': order.id,
            'model': order._name,
            'title': partner.display_name if partner else order.name,
            'subtitle': order.name,
            'meta': self._date_label(validity) if validity else 'Senza scadenza offerta',
            'value': order.amount_total or 0,
            'tone': 'red' if overdue else 'blue',
            'badges': self._compact([
                dict(order._fields['state'].selection).get(order.state, order.state) if order.state else False,
                order.user_id.name if order.user_id else False,
                'scade oggi' if overdue else False,
            ]),
            'res_id': order.id,
        }

    def _format_sample_item(self, sample, today):
        deadline = sample.date_feedback_expected
        overdue = bool(deadline and fields.Date.to_date(deadline) <= today)
        lead = sample.lead_id
        partner = sample.partner_id
        return {
            'id': sample.id,
            'model': sample._name,
            'title': partner.display_name if partner else sample.reference,
            'subtitle': lead.name if lead else sample.reference,
            'meta': self._date_label(deadline) if deadline else 'Feedback non pianificato',
            'value': 0,
            'tone': 'red' if overdue else 'amber',
            'badges': self._compact([
                dict(sample._fields['state'].selection).get(sample.state, sample.state) if sample.state else False,
                'feedback atteso' if deadline else False,
                'scaduto' if overdue else False,
            ]),
            'res_id': sample.id,
        }

    def _format_project_detail(self, project, today):
        tasks = self.env['project.task'].search([('project_id', '=', project.id)], limit=80)
        overdue_tasks = tasks.filtered(lambda task: self._is_overdue(task.date_deadline))
        partner = getattr(project, 'partner_id', False) or getattr(project, 'cf_partner_id', False)
        
        financials = self._get_dossier_financials(partner)
        
        subprojects = []
        if 'cf_child_project_ids' in project._fields:
            for sub in project.cf_child_project_ids:
                sub_tasks = self.env['project.task'].search([('project_id', '=', sub.id)], limit=40)
                sub_overdue = sub_tasks.filtered(lambda t: self._is_overdue(t.date_deadline))
                subprojects.append({
                    'id': sub.id,
                    'name': sub.name,
                    'project_type': sub.cf_project_type,
                    'project_type_label': dict(sub._fields['cf_project_type'].selection).get(sub.cf_project_type, sub.cf_project_type) if sub.cf_project_type else '',
                    'status': self._project_status(sub),
                    'blocker': self._project_blocker_label(sub),
                    'task_count': len(sub_tasks),
                    'overdue_count': len(sub_overdue),
                    'target_date': self._date_label(getattr(sub, 'cf_target_date', False) or getattr(sub, 'date', False)),
                    'departments': self._project_departments(sub),
                })

        return {
            'id': project.id,
            'model': project._name,
            'res_id': project.id,
            'name': project.name,
            'partner': self._project_partner_name(project),
            'partner_id': partner.id if partner else False,
            'partner_email': partner.email if partner else '',
            'partner_phone': partner.phone if partner else '',
            'status': self._project_status(project),
            'blocker': self._project_blocker_label(project),
            'next_action': project.cf_next_action if 'cf_next_action' in project._fields else '',
            'continent': project.cf360_continent if 'cf360_continent' in project._fields else '',
            'continent_label': self._project_continent_label(project),
            'target_date': self._date_label(getattr(project, 'cf_target_date', False) or getattr(project, 'date', False)),
            'task_count': len(tasks),
            'overdue_count': len(overdue_tasks),
            'departments': self._project_departments(project),
            'financials': financials,
            'subprojects': subprojects,
        }

    def _project_departments(self, project):
        tasks = self.env['project.task'].search([('project_id', '=', project.id)], limit=40)
        buckets = {
            'commerciale': [],
            'back office': [],
            'produzione': [],
            'logistica': [],
            'qualita': [],
        }
        for task in tasks:
            label = (task.name or '').lower()
            key = 'back office'
            if any(word in label for word in ['produzione', 'ricetta', 'campione']):
                key = 'produzione'
            elif any(word in label for word in ['logistica', 'spedizione', 'tracking']):
                key = 'logistica'
            elif any(word in label for word in ['qualita', 'allergeni', 'certificat', 'etichetta']):
                key = 'qualita'
            elif any(word in label for word in ['cliente', 'prezzo', 'quotazione', 'commerciale']):
                key = 'commerciale'
            buckets[key].append({
                'id': task.id,
                'name': task.name,
                'is_overdue': self._is_overdue(task.date_deadline),
                'assignee': ', '.join(task.user_ids.mapped('name')) if 'user_ids' in task._fields else '',
            })
        return [{'name': name.title(), 'tasks': tasks[:4]} for name, tasks in buckets.items()]

    def _is_overdue(self, value):
        if not value:
            return False
        deadline = fields.Date.to_date(value)
        return bool(deadline and deadline < fields.Date.context_today(self))

    def _project_partner_name(self, project):
        partner = getattr(project, 'partner_id', False) or getattr(project, 'cf_partner_id', False)
        return partner.display_name if partner else ''

    def _project_continent_label(self, project):
        if 'cf360_continent' not in project._fields or not project.cf360_continent:
            return ''
        return dict(project._fields['cf360_continent'].selection).get(
            project.cf360_continent, project.cf360_continent)

    def _project_status(self, project):
        if 'cf_traffic_light' in project._fields and project.cf_traffic_light:
            return project.cf_traffic_light
        if 'cf_status_dossier' in project._fields and project.cf_status_dossier:
            return dict(project._fields['cf_status_dossier'].selection).get(project.cf_status_dossier, project.cf_status_dossier)
        return ''

    def _project_blocker_label(self, project):
        if 'cf_main_blocker' in project._fields and project.cf_main_blocker:
            return dict(project._fields['cf_main_blocker'].selection).get(project.cf_main_blocker, project.cf_main_blocker)
        if 'cf_tasks_blocked' in project._fields and project.cf_tasks_blocked:
            return '%s task bloccate' % project.cf_tasks_blocked
        if 'cf_next_action' in project._fields and project.cf_next_action:
            return project.cf_next_action
        return 'Da verificare'

    def _date_label(self, value):
        if not value:
            return ''
        if isinstance(value, str):
            return value[:10]
        return fields.Date.to_string(value) if not hasattr(value, 'hour') else fields.Datetime.to_string(value)[:16]

    def _compact(self, values):
        return [value for value in values if value]

    def _get_dossier_financials(self, partner):
        if not partner:
            return {
                'revenue_total': 0.0,
                'quotes_total': 0.0,
                'exposure': 0.0,
                'monthly_purchases': [],
            }

        invoices = self.env['account.move'].search([
            ('partner_id', 'child_of', partner.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
        ])
        revenue_total = sum(inv.amount_total_signed for inv in invoices)

        sales = self.env['sale.order'].search([
            ('partner_id', 'child_of', partner.id),
            ('state', 'in', ['draft', 'sent']),
        ])
        quotes_total = sum(so.amount_total for so in sales)
        exposure = partner.credit or 0.0

        from collections import defaultdict
        import datetime

        monthly_data = defaultdict(float)
        today_dt = datetime.date.today()
        months = []
        for i in range(5, -1, -1):
            d = today_dt - datetime.timedelta(days=i * 30)
            month_key = d.strftime('%Y-%m')
            month_label = d.strftime('%b')
            months.append((month_key, month_label))
            monthly_data[month_key] = 0.0

        for inv in invoices:
            if inv.invoice_date:
                m_key = inv.invoice_date.strftime('%Y-%m')
                if m_key in monthly_data:
                    monthly_data[m_key] += inv.amount_total_signed

        max_val = max(monthly_data.values()) if monthly_data.values() else 0.0
        monthly_purchases = []
        for m_key, m_label in months:
            val = monthly_data[m_key]
            pct = int((val / max_val * 100)) if max_val > 0 else 0
            monthly_purchases.append({
                'label': m_label,
                'value': val,
                'pct': pct,
            })

        return {
            'revenue_total': revenue_total,
            'quotes_total': quotes_total,
            'exposure': exposure,
            'monthly_purchases': monthly_purchases,
        }

    @api.model
    def get_dossier_timeline(self, project_id):
        project = self.env['project.project'].browse(int(project_id)).exists()
        if not project:
            return []

        timeline = []
        import datetime

        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        emails = Mail.search([('cf_project_id', '=', project.id)], order='create_date desc', limit=50) if Mail else []
        for email in emails:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'casafolino.mail.message'),
                ('res_id', '=', email.id),
            ])
            timeline.append({
                'id': 'email-%s' % email.id,
                'type': 'email',
                'date': self._date_label(email.create_date or email.write_date),
                'timestamp': email.create_date or email.write_date,
                'title': email.sender_name or email.sender_email or 'Mittente sconosciuto',
                'sender_email': email.sender_email or '',
                'subject': email.subject or 'Nessun oggetto',
                'body': email.body_plain or email.snippet or '',
                'body_html': email.body_html or '',
                'direction': email.direction_computed or 'inbound',
                'attachments': [{'id': att.id, 'name': att.name} for att in attachments],
            })

        note_subtype = self.env.ref('mail.mt_note', raise_if_not_found=False)
        domain_notes = [
            ('model', '=', 'project.project'),
            ('res_id', '=', project.id),
        ]
        if note_subtype:
            domain_notes.append(('subtype_id', '=', note_subtype.id))

        notes = self.env['mail.message'].search(domain_notes, order='date desc', limit=50)
        for note in notes:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'project.project'),
                ('res_id', '=', project.id),
                ('res_name', '=', note.record_name),
            ])
            import re
            clean_body = re.sub('<[^<]+?>', '', note.body or '')
            timeline.append({
                'id': 'note-%s' % note.id,
                'type': 'note',
                'date': self._date_label(note.date),
                'timestamp': note.date,
                'title': note.author_id.name or 'Staff CasaFolino',
                'sender_email': note.author_id.email or '',
                'subject': 'Nota Interna',
                'body': clean_body,
                'body_html': note.body or '',
                'direction': 'note',
                'attachments': [{'id': att.id, 'name': att.name} for att in attachments],
            })

        timeline.sort(key=lambda x: x['timestamp'] or datetime.datetime.min, reverse=True)
        for item in timeline:
            if 'timestamp' in item:
                del item['timestamp']
        return timeline

    @api.model
    def post_dossier_note(self, project_id, body):
        project = self.env['project.project'].browse(int(project_id)).exists()
        if not project or not body:
            return False
        project.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return True


class CfPipelinePromoteDossierWizard(models.TransientModel):
    _name = 'cf.pipeline.promote.dossier.wizard'
    _description = 'Promuovi lead a dossier operativo'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    project_name = fields.Char(string='Nome dossier', required=True)
    next_action = fields.Char(string='Prossima azione')
    next_action_date = fields.Date(string='Data prossima azione')
    target_date = fields.Date(string='Data obiettivo')
    create_next_task = fields.Boolean(string='Crea task prossima azione', default=True)
    create_department_tasks = fields.Boolean(string='Crea task reparti', default=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        lead = self.env['crm.lead'].browse(self.env.context.get('default_lead_id')).exists()
        if lead:
            partner = lead.partner_id
            res.update({
                'lead_id': lead.id,
                'partner_id': partner.id if partner else False,
                'project_name': self._default_project_name(lead),
                'next_action': 'Follow-up commerciale',
                'next_action_date': fields.Date.context_today(self) + timedelta(days=7),
            })
        return res

    def action_promote(self):
        self.ensure_one()
        lead = self.lead_id
        project = getattr(lead, 'cf_project_id', False)
        if not project:
            vals = {
                'name': self.project_name,
                'partner_id': lead.partner_id.id if lead.partner_id else False,
                'user_id': lead.user_id.id or self.env.user.id,
            }
            Project = self.env['project.project']
            if 'cf_status_dossier' in Project._fields:
                vals['cf_status_dossier'] = 'exploration'
            if 'cf_dossier_priority' in Project._fields:
                vals['cf_dossier_priority'] = 'medium'
            if 'cf_next_action' in Project._fields:
                vals['cf_next_action'] = self.next_action or False
            if 'cf_next_action_date' in Project._fields:
                vals['cf_next_action_date'] = self.next_action_date or False
            if 'date' in Project._fields:
                vals['date'] = self.target_date or self.next_action_date or False
            project = Project.create(vals)
            if 'cf_project_id' in lead._fields:
                lead.cf_project_id = project.id
        else:
            project.write({'name': self.project_name})

        if self.create_next_task and self.next_action:
            self.env['project.task'].create({
                'name': self.next_action,
                'project_id': project.id,
                'partner_id': lead.partner_id.id if lead.partner_id else False,
                'user_ids': [(6, 0, [lead.user_id.id or self.env.user.id])],
                'date_deadline': self.next_action_date or False,
            })
        if self.create_department_tasks:
            self._ensure_department_tasks(project, lead)
        if self.next_action_date and 'cf_date_next_followup' in lead._fields:
            lead.cf_date_next_followup = self.next_action_date

        return {
            'type': 'ir.actions.act_window',
            'name': 'Dossier',
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _default_project_name(self, lead):
        partner = lead.partner_id
        if partner and lead.name:
            return '%s - %s' % (partner.name, lead.name)
        return lead.name or (partner.name if partner else 'Dossier commerciale')

    def _ensure_department_tasks(self, project, lead):
        Task = self.env['project.task']
        existing_names = set(Task.search([('project_id', '=', project.id)]).mapped('name'))
        partner_id = lead.partner_id.id if lead.partner_id else False
        owner_id = lead.user_id.id or self.env.user.id
        start_date = self.next_action_date or fields.Date.context_today(self)
        templates = [
            ('Commerciale - confermare richiesta cliente', 0, owner_id),
            ('Back office - verificare dati cliente e condizioni', 1, owner_id),
            ('Produzione - valutare fattibilita campione/prodotto', 2, False),
            ('Qualita - controllare requisiti, allergeni e certificazioni', 3, False),
            ('Logistica - stimare spedizione, imballo e tempi', 4, False),
        ]
        for name, offset, user_id in templates:
            if name in existing_names:
                continue
            vals = {
                'name': name,
                'project_id': project.id,
                'partner_id': partner_id,
                'date_deadline': start_date + timedelta(days=offset),
            }
            if user_id:
                vals['user_ids'] = [(6, 0, [user_id])]
            Task.create(vals)


class CfPipelineCreateDossierWizard(models.TransientModel):
    _name = 'cf.pipeline.create.dossier.wizard'
    _description = 'Crea dossier direttamente da email'

    message_id = fields.Integer(string='Email legacy', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente')
    partner_name = fields.Char(string='Nome cliente (Nuovo)')
    partner_email = fields.Char(string='Email cliente')
    project_name = fields.Char(string='Nome dossier', required=True)
    expected_revenue = fields.Monetary(string='Valore stimato (Ricavo atteso)', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.uid)
    next_action = fields.Char(string='Prossima azione')
    next_action_date = fields.Date(string='Data prossima azione')
    target_date = fields.Date(string='Data obiettivo')
    create_next_task = fields.Boolean(string='Crea task prossima azione', default=True)
    create_department_tasks = fields.Boolean(string='Crea task reparti', default=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        if not Mail:
            return res
        msg_id = self.env.context.get('default_message_id')
        if msg_id:
            msg = Mail.browse(msg_id).exists()
            if msg:
                res.update({
                    'message_id': msg.id,
                    'partner_id': msg.partner_id.id if msg.partner_id else False,
                    'partner_name': msg.sender_name or (msg.sender_email.split('@')[0] if msg.sender_email else ''),
                    'partner_email': msg.sender_email or '',
                    'project_name': msg.subject or 'Dossier da email',
                    'next_action': 'Risposta commerciale e listino',
                    'next_action_date': fields.Date.context_today(self) + timedelta(days=7),
                })
        return res

    def action_create_dossier(self):
        self.ensure_one()
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        msg = Mail.browse(self.message_id).exists() if Mail and self.message_id else False

        # 1. Partner
        partner = self.partner_id
        if not partner:
            if self.partner_email:
                partner = self.env['res.partner'].search([('email', '=ilike', self.partner_email.strip())], limit=1)
            if not partner and self.partner_name:
                partner = self.env['res.partner'].create({
                    'name': self.partner_name,
                    'email': self.partner_email,
                })
            elif not partner:
                raise UserError('Specificare un cliente esistente o inserire i dati per crearne uno nuovo.')

        # 2. Lead CRM
        lead_vals = {
            'name': self.project_name or (msg.subject if msg else False) or 'Richiesta commerciale',
            'partner_id': partner.id,
            'email_from': (msg.sender_email if msg else False) or self.partner_email,
            'user_id': self.user_id.id or self.env.user.id,
            'expected_revenue': self.expected_revenue,
            'source_email_id': msg.id if msg else False,
            'description': (msg.snippet if msg else False) or '',
        }
        # Find Export team & "New" stage
        team = self.env['crm.team'].search([('name', 'ilike', 'Export')], limit=1)
        if team:
            lead_vals['team_id'] = team.id
            stage = self.env['crm.stage'].search([('team_id', '=', team.id), ('name', 'ilike', 'New')], limit=1)
            if not stage:
                stage = self.env['crm.stage'].search([('team_id', '=', team.id)], order='sequence', limit=1)
            if stage:
                lead_vals['stage_id'] = stage.id
        
        lead = self.env['crm.lead'].create(lead_vals)

        # 3. Project / Dossier
        project_vals = {
            'name': self.project_name,
            'partner_id': partner.id,
            'user_id': self.user_id.id or self.env.user.id,
        }
        Project = self.env['project.project']
        if 'cf_status_dossier' in Project._fields:
            project_vals['cf_status_dossier'] = 'exploration'
        if 'cf_dossier_priority' in Project._fields:
            project_vals['cf_dossier_priority'] = 'medium'
        if 'cf_next_action' in Project._fields:
            project_vals['cf_next_action'] = self.next_action or False
        if 'cf_next_action_date' in Project._fields:
            project_vals['cf_next_action_date'] = self.next_action_date or False
        if 'date' in Project._fields:
            project_vals['date'] = self.target_date or self.next_action_date or False

        project = Project.create(project_vals)
        
        # Link project to lead
        if 'cf_project_id' in lead._fields:
            lead.cf_project_id = project.id

        # 4. Create tasks
        if self.create_next_task and self.next_action:
            self.env['project.task'].create({
                'name': self.next_action,
                'project_id': project.id,
                'partner_id': partner.id,
                'user_ids': [(6, 0, [self.user_id.id or self.env.user.id])],
                'date_deadline': self.next_action_date or False,
            })
        
        if self.create_department_tasks:
            # We can invoke the department task helper from CfPipelinePromoteDossierWizard
            promote_wizard = self.env['cf.pipeline.promote.dossier.wizard']
            promote_wizard._ensure_department_tasks(project, lead)

        # 5. Write back to message
        if msg:
            vals = {
                'lead_id': lead.id,
                'partner_id': partner.id if not msg.partner_id else msg.partner_id.id,
                'state': 'keep',
                'triage_user_id': self.env.user.id,
                'triage_date': fields.Datetime.now(),
            }
            if 'cf_project_id' in msg._fields:
                vals['cf_project_id'] = project.id
            msg.write(vals)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Dossier',
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _get_dossier_financials(self, partner):
        if not partner:
            return {
                'revenue_total': 0.0,
                'quotes_total': 0.0,
                'exposure': 0.0,
                'monthly_purchases': [],
            }

        # 1. Fatturato storico: query account.move (posted out invoices)
        domain_invoice = [
            ('partner_id', 'child_of', partner.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
        ]
        invoices = self.env['account.move'].search(domain_invoice)
        revenue_total = sum(inv.amount_total_signed for inv in invoices)

        # 2. Preventivi attivi: sale.order draft/sent
        domain_sale = [
            ('partner_id', 'child_of', partner.id),
            ('state', 'in', ['draft', 'sent']),
        ]
        sales = self.env['sale.order'].search(domain_sale)
        quotes_total = sum(so.amount_total for so in sales)

        # 3. Esposizione
        exposure = partner.credit or 0.0

        # 4. Grafico acquisti mensili (past 6 months)
        from collections import defaultdict
        import datetime
        monthly_data = defaultdict(float)

        today_dt = datetime.date.today()
        months = []
        for i in range(5, -1, -1):
            d = today_dt - datetime.timedelta(days=i * 30)
            month_key = d.strftime('%Y-%m')
            month_label = d.strftime('%b')
            months.append((month_key, month_label))
            monthly_data[month_key] = 0.0

        for inv in invoices:
            if inv.invoice_date:
                m_key = inv.invoice_date.strftime('%Y-%m')
                if m_key in monthly_data:
                    monthly_data[m_key] += inv.amount_total_signed

        monthly_purchases = []
        max_val = max(monthly_data.values()) if monthly_data.values() else 0.0
        for m_key, m_label in months:
            val = monthly_data[m_key]
            pct = int((val / max_val * 100)) if max_val > 0 else 0
            monthly_purchases.append({
                'label': m_label,
                'value': val,
                'pct': pct,
            })

        return {
            'revenue_total': revenue_total,
            'quotes_total': quotes_total,
            'exposure': exposure,
            'monthly_purchases': monthly_purchases,
        }

    @api.model
    def get_dossier_timeline(self, project_id):
        project = self.env['project.project'].browse(int(project_id)).exists()
        if not project:
            return []

        timeline = []
        import datetime

        # 1. Custom Emails: casafolino.mail.message
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        emails = Mail.search([('cf_project_id', '=', project.id)], order='create_date desc', limit=50) if Mail else []
        for email in emails:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'casafolino.mail.message'),
                ('res_id', '=', email.id)
            ])
            timeline.append({
                'id': 'email-%s' % email.id,
                'type': 'email',
                'date': self._date_label(email.create_date or email.write_date),
                'timestamp': email.create_date or email.write_date,
                'title': email.sender_name or email.sender_email or 'Mittente sconosciuto',
                'sender_email': email.sender_email or '',
                'subject': email.subject or 'Nessun oggetto',
                'body': email.body_plain or email.snippet or '',
                'body_html': email.body_html or '',
                'direction': email.direction_computed or 'inbound',
                'attachments': [{'id': att.id, 'name': att.name} for att in attachments],
            })

        # 2. Internal Notes: mail.message subtype Note
        note_subtype = self.env.ref('mail.mt_note', raise_if_not_found=False)
        domain_notes = [
            ('model', '=', 'project.project'),
            ('res_id', '=', project.id),
        ]
        if note_subtype:
            domain_notes.append(('subtype_id', '=', note_subtype.id))

        notes = self.env['mail.message'].search(domain_notes, order='date desc', limit=50)
        for note in notes:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'project.project'),
                ('res_id', '=', project.id),
                ('res_name', '=', note.record_name)
            ])
            import re
            clean_body = re.sub('<[^<]+?>', '', note.body or '')
            timeline.append({
                'id': 'note-%s' % note.id,
                'type': 'note',
                'date': self._date_label(note.date),
                'timestamp': note.date,
                'title': note.author_id.name or 'Staff CasaFolino',
                'sender_email': note.author_id.email or '',
                'subject': 'Nota Interna',
                'body': clean_body,
                'body_html': note.body or '',
                'direction': 'note',
                'attachments': [{'id': att.id, 'name': att.name} for att in attachments],
            })

        # Sort combined timeline chronologically descending (newest first)
        timeline.sort(key=lambda x: x['timestamp'] or datetime.datetime.min, reverse=True)

        for item in timeline:
            if 'timestamp' in item:
                del item['timestamp']

        return timeline

    @api.model
    def post_dossier_note(self, project_id, body):
        project = self.env['project.project'].browse(int(project_id)).exists()
        if not project or not body:
            return False
        project.message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )
        return True


class CfPipelineLinkLeadWizard(models.TransientModel):
    _name = 'cf.pipeline.link.lead.wizard'
    _description = 'Collega email commerciale a lead'

    message_id = fields.Integer(string='Email legacy', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    apply_to_thread = fields.Boolean(string='Collega tutto il thread', default=True)
    set_followup = fields.Boolean(string='Pianifica follow-up', default=True)
    next_followup_date = fields.Date(string='Data follow-up')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        if not Mail:
            return res
        message = Mail.browse(self.env.context.get('default_message_id')).exists()
        if message:
            res.update({
                'message_id': message.id,
                'partner_id': message.partner_id.id if message.partner_id else False,
                'lead_id': message.lead_id.id if message.lead_id else self._guess_lead(message).id,
                'next_followup_date': fields.Date.context_today(self) + timedelta(days=7),
            })
        return res

    def action_link(self):
        self.ensure_one()
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        if not Mail:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Mail V2 disinstallata',
                    'message': 'Il collegamento email legacy non è più disponibile.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        message = Mail.browse(self.message_id).exists()
        messages = message
        if self.apply_to_thread and message.thread_id:
            messages = Mail.search([
                ('thread_id', '=', message.thread_id.id),
                ('is_deleted', '=', False),
            ])
        messages.write({'lead_id': self.lead_id.id})
        if self.partner_id and not self.lead_id.partner_id:
            self.lead_id.partner_id = self.partner_id
        if self.set_followup and self.next_followup_date:
            date_field = 'cf_date_next_followup' if 'cf_date_next_followup' in self.lead_id._fields else 'date_deadline'
            self.lead_id.write({date_field: self.next_followup_date})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _guess_lead(self, message):
        if message.partner_id:
            return self.env['crm.lead'].search([
                ('partner_id', '=', message.partner_id.id),
                ('type', '=', 'opportunity'),
                ('active', '=', True),
            ], order='write_date desc, id desc', limit=1)
        return self.env['crm.lead']


class CfPipelineSnoozeWizard(models.TransientModel):
    _name = 'cf.pipeline.snooze.wizard'
    _description = 'Posticipa thread commerciale'

    message_id = fields.Integer(string='Email legacy', readonly=True)
    thread_id = fields.Integer(string='Thread legacy', readonly=True)
    wake_at = fields.Datetime(string='Rientra il', required=True)
    note = fields.Char(string='Nota')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        Mail = self.env['casafolino.mail.message'] if 'casafolino.mail.message' in self.env else False
        if not Mail:
            return res
        message = Mail.browse(self.env.context.get('default_message_id')).exists()
        if message:
            res.update({
                'message_id': message.id,
                'thread_id': message.thread_id.id if message.thread_id else 0,
                'wake_at': fields.Datetime.now() + timedelta(days=1),
                'note': 'Posticipato da Inbox Commerciale',
            })
        return res

    def action_snooze(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Mail V2 disinstallata',
                'message': 'Il posticipo thread legacy non è più disponibile.',
                'type': 'warning',
                'sticky': False,
            },
        }


class CfPipelinePlanFairFollowupWizard(models.TransientModel):
    _name = 'cf.pipeline.plan.fair.followup.wizard'
    _description = 'Pianifica follow-up massivi post-fiera'

    fair_id = fields.Many2one('cf.export.fair', string='Fiera', required=True, readonly=True)
    start_date = fields.Date(string='Prima data follow-up', required=True)
    batch_size = fields.Integer(string='Lead per giorno', default=20, required=True)
    batch_gap_days = fields.Integer(string='Giorni tra batch', default=1, required=True)
    only_without_plan = fields.Boolean(string='Solo lead senza prossima azione', default=True)
    create_tasks = fields.Boolean(string='Crea task commerciale per ogni lead', default=False)
    affected_count = fields.Integer(string='Lead coinvolti', compute='_compute_affected_count')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        fair = self.env['cf.export.fair'].browse(self.env.context.get('default_fair_id')).exists()
        if fair:
            res.update({
                'fair_id': fair.id,
                'start_date': fields.Date.context_today(self) + timedelta(days=1),
                'batch_size': 20,
                'batch_gap_days': 1,
                'only_without_plan': True,
                'create_tasks': False,
            })
        return res

    @api.depends('fair_id', 'only_without_plan')
    def _compute_affected_count(self):
        for wizard in self:
            wizard.affected_count = len(wizard._candidate_leads())

    def action_plan(self):
        self.ensure_one()
        leads = self._candidate_leads()
        if not leads:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Nessun lead da pianificare',
                    'message': 'Non ci sono lead compatibili con i filtri scelti.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        date_field = self._followup_date_field()
        batch_size = max(self.batch_size or 1, 1)
        batch_gap_days = max(self.batch_gap_days or 1, 1)
        Task = self.env['project.task']
        for index, lead in enumerate(leads):
            planned_date = self.start_date + timedelta(days=(index // batch_size) * batch_gap_days)
            lead.write({date_field: planned_date})
            if self.create_tasks:
                project = getattr(lead, 'cf_project_id', False)
                Task.create({
                    'name': 'Follow-up post-fiera: %s' % (lead.name or lead.display_name),
                    'project_id': project.id if project else False,
                    'partner_id': lead.partner_id.id if lead.partner_id else False,
                    'user_ids': [(6, 0, [lead.user_id.id or self.env.user.id])],
                    'date_deadline': planned_date,
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Follow-up pianificati',
                'message': '%s lead aggiornati da %s.' % (len(leads), self.fair_id.name),
                'type': 'success',
                'sticky': False,
            },
            'reload': True,
        }

    def _candidate_leads(self):
        self.ensure_one()
        leads = self.fair_id.lead_ids.exists()
        if self.only_without_plan:
            date_field = self._followup_date_field()
            leads = leads.filtered(lambda lead: not lead[date_field])
        return leads.sorted(key=lambda lead: (lead.user_id.name or '', lead.create_date or fields.Datetime.now(), lead.id))

    def _followup_date_field(self):
        Lead = self.env['crm.lead']
        return 'cf_date_next_followup' if 'cf_date_next_followup' in Lead._fields else 'date_deadline'
