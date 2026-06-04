import logging
import json
from datetime import datetime, time, timedelta
from email.utils import getaddresses

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_INTERNAL_EMAIL_DOMAINS = {'casafolino.com', 'folinofood.com'}


class CrmLeadPipelineControl(models.Model):
    _inherit = 'crm.lead'

    cf_pc_mail_count = fields.Integer(string='Email operative', compute='_compute_cf_pc_counts')
    cf_pc_quote_count = fields.Integer(string='Quotazioni aperte', compute='_compute_cf_pc_counts')
    cf_pc_task_count = fields.Integer(string='Task dossier', compute='_compute_cf_pc_counts')

    def _compute_cf_pc_counts(self):
        Mail = self.env['casafolino.mail.message']
        Sale = self.env['sale.order']
        Task = self.env['project.task']
        has_opportunity = 'opportunity_id' in Sale._fields
        for lead in self:
            lead.cf_pc_mail_count = Mail.search_count([
                ('lead_id', '=', lead.id),
                ('is_deleted', '=', False),
            ])
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
            'name': 'Sala Controllo',
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
    cf360_mail_ids = fields.Many2many(
        'casafolino.mail.message',
        compute='_compute_cf360_mail_ids',
        string='Comunicazioni 360',
    )
    cf360_mail_count = fields.Integer(
        compute='_compute_cf360_mail_ids',
        string='Numero comunicazioni 360',
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

    @api.depends('partner_id')
    def _compute_cf360_mail_ids(self):
        Mail = self.env['casafolino.mail.message']
        for project in self:
            domain = [('cf_project_id', '=', project.id)]
            if project.partner_id:
                domain = ['|', ('cf_project_id', '=', project.id), ('partner_id', '=', project.partner_id.id)]
            mails = Mail.search(domain, order='email_date desc, id desc', limit=200)
            project.cf360_mail_ids = mails
            project.cf360_mail_count = len(mails)

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
        last_mail = self.cf360_mail_ids[:1]
        partner = last_mail.partner_id if last_mail else self.partner_id
        partner_email = ''
        subject = '[%s] ' % (self.name or '')
        if last_mail:
            partner_email = last_mail.sender_email or (partner.email if partner else '')
            raw_subject = last_mail.subject or self.name or ''
            subject = raw_subject if raw_subject.lower().startswith('re:') else 'Re: %s' % raw_subject
        elif partner:
            partner_email = partner.email or ''
        return {
            'type': 'ir.actions.client',
            'tag': 'casafolino_mail.compose_f8',
            'context': {
                'default_partner_email': partner_email,
                'default_subject': subject,
                'default_body': '<p>Buongiorno,</p><p>le rispondo in merito al dossier <strong>%s</strong>.</p><p></p>' % (self.name or ''),
                'default_partner_id': partner.id if partner else False,
                'default_thread_id': self.id,
                'default_thread_model': 'project.project',
                'default_project_id': self.id,
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
            'lanes': self._safe_section('lanes', lambda: self._get_control_lanes(today, user), []),
            'b2b_registrations': self._safe_section('b2b_registrations', lambda: self._get_b2b_registration_data(today), {'kpis': [], 'rows': []}),
            'followup': self._safe_section('followup', lambda: self._get_followup_data(today, user), {'kpis': [], 'columns': [], 'routes': [], 'timeline': []}),
            'post_fair': self._safe_section('post_fair', lambda: self._get_post_fair_data(today, fair_id), {'kpis': [], 'columns': [], 'timeline': [], 'fair_options': []}),
            'pipeline': self._safe_section('pipeline', lambda: self._get_pipeline_data(today), []),
            'inbox': self._safe_section('inbox', lambda: self._get_inbox_data(user), {'to_reply': [], 'waiting_customer': []}),
            'dossiers': self._safe_section('dossiers', lambda: self._get_dossier_data(today), []),
            'operations': self._safe_section('operations', lambda: self._get_operations_data(today, user), {'tasks': [], 'shipments': [], 'samples': [], 'entities': [], 'ai_queue': []}),
        }

    @api.model
    def mass_archive(self, message_ids):
        msgs = self.env['casafolino.mail.message'].browse([int(mid) for mid in message_ids]).exists()
        if msgs:
            msgs.action_archive()
        return True

    @api.model
    def mass_keep_senders(self, message_ids):
        msgs = self.env['casafolino.mail.message'].browse([int(mid) for mid in message_ids]).exists()
        for msg in msgs:
            self._keep_sender_from_message(msg)
        return {'count': len(msgs)}

    @api.model
    def mass_dismiss_senders(self, message_ids):
        msgs = self.env['casafolino.mail.message'].browse([int(mid) for mid in message_ids]).exists()
        for msg in msgs:
            self._dismiss_sender_from_message(msg)
        return {'count': len(msgs)}

    @api.model
    def mass_snooze_tomorrow(self, message_ids):
        msgs = self.env['casafolino.mail.message'].browse([int(mid) for mid in message_ids]).exists()
        wake_date = fields.Date.context_today(self) + timedelta(days=1)
        wake_at = fields.Datetime.to_string(datetime.combine(wake_date, time(hour=9)))
        snoozed = 0
        Snooze = self.env['casafolino.mail.snooze']
        for msg in msgs:
            if not msg.thread_id:
                continue
            Snooze.search([
                ('thread_id', '=', msg.thread_id.id),
                ('active', '=', True),
            ]).write({'active': False})
            Snooze.create({
                'thread_id': msg.thread_id.id,
                'user_id': self.env.uid,
                'snooze_type': 'until_date',
                'wake_at': wake_at,
                'snoozed_at': fields.Datetime.now(),
                'note': 'Posticipato dalla Console Commerciale',
            })
            msg.thread_id.write({'is_snoozed': True})
            snoozed += 1
        return {'count': snoozed, 'wake_at': wake_at}

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
    def search_entity_360(self, query, limit=8):
        if not query or len(query.strip()) < 2:
            return []
        query = query.strip()
        limit = max(1, min(int(limit or 8), 20))
        rows = []
        seen = set()

        Partner = self.env['res.partner']
        partner_domain = ['|', '|', ('name', 'ilike', query), ('email', 'ilike', query), ('phone', 'ilike', query)]
        for partner in Partner.search(partner_domain, order='write_date desc, id desc', limit=limit):
            key = ('res.partner', partner.id)
            if key in seen:
                continue
            seen.add(key)
            rows.append(self._format_entity360_partner(partner))

        remaining = max(limit - len(rows), 0)
        if remaining:
            Lead = self.env['crm.lead']
            lead_domain = ['|', '|', ('name', 'ilike', query), ('partner_id.name', 'ilike', query), ('email_from', 'ilike', query)]
            for lead in Lead.search(lead_domain, order='write_date desc, expected_revenue desc, id desc', limit=remaining):
                key = ('crm.lead', lead.id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(self._format_entity360_lead(lead))

        remaining = max(limit - len(rows), 0)
        if remaining:
            Project = self.env['project.project']
            project_domain = ['|', ('name', 'ilike', query), ('partner_id.name', 'ilike', query)]
            for project in Project.search(project_domain, order='write_date desc, id desc', limit=remaining):
                key = ('project.project', project.id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(self._format_entity360_project(project))

        remaining = max(limit - len(rows), 0)
        if remaining:
            Mail = self.env['casafolino.mail.message']
            mail_domain = [
                ('is_deleted', '=', False),
                '|', '|', '|',
                ('subject', 'ilike', query),
                ('sender_name', 'ilike', query),
                ('sender_email', 'ilike', query),
                ('recipient_emails', 'ilike', query),
            ]
            for mail in Mail.search(mail_domain, order='email_date desc, id desc', limit=remaining):
                key = ('casafolino.mail.message', mail.id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(self._format_entity360_mail(mail))

        remaining = max(limit - len(rows), 0)
        if remaining:
            Task = self.env['project.task']
            for task in Task.search([('name', 'ilike', query)], order='write_date desc, id desc', limit=remaining):
                key = ('project.task', task.id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(self._format_entity360_task(task))

        remaining = max(limit - len(rows), 0)
        if remaining and 'cf.export.sample' in self.env.registry:
            Sample = self.env['cf.export.sample']
            sample_domain = ['|', '|', ('reference', 'ilike', query), ('partner_id.name', 'ilike', query), ('lead_id.name', 'ilike', query)]
            for sample in Sample.search(sample_domain, order='write_date desc, id desc', limit=remaining):
                key = ('cf.export.sample', sample.id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(self._format_entity360_sample(sample))

        remaining = max(limit - len(rows), 0)
        if remaining:
            Sale = self.env['sale.order']
            quote_domain = ['|', '|', ('name', 'ilike', query), ('client_order_ref', 'ilike', query), ('partner_id.name', 'ilike', query)]
            for order in Sale.search(quote_domain, order='write_date desc, amount_total desc, id desc', limit=remaining):
                key = ('sale.order', order.id)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(self._format_entity360_quote(order))
        return rows

    @api.model
    def get_entity_360_detail(self, model, res_id):
        allowed_models = {
            'res.partner',
            'crm.lead',
            'project.project',
            'casafolino.mail.message',
            'project.task',
            'cf.export.sample',
            'cf.project.shipment',
            'sale.order',
        }
        if model not in allowed_models or model not in self.env.registry:
            return {'found': False, 'error': 'Entita non disponibile'}
        record = self.env[model].browse(int(res_id)).exists()
        if not record:
            return {'found': False, 'error': 'Record non trovato'}

        context = self._entity360_context_from_record(record)
        partner = context.get('partner')
        company = context.get('company')
        lead = context.get('lead')
        project = context.get('project')

        partner_ids = set()
        if company:
            partner_ids.add(company.id)
            partner_ids.update(self.env['res.partner'].search([('parent_id', '=', company.id)], limit=80).ids)
        if partner:
            partner_ids.add(partner.id)
            if partner.parent_id:
                partner_ids.add(partner.parent_id.id)
        partner_ids = list(partner_ids)

        lead_domain = [('active', 'in', [True, False])]
        lead_or_parts = []
        if partner_ids:
            lead_or_parts.append([('partner_id', 'in', partner_ids)])
        if lead:
            lead_or_parts.append([('id', '=', lead.id)])
        leads = self.env['crm.lead'].search(
            self._or_domain(lead_or_parts) + lead_domain,
            order='write_date desc, expected_revenue desc, id desc',
            limit=10,
        ) if lead_or_parts else self.env['crm.lead']

        project_or_parts = []
        if partner_ids:
            project_or_parts.append([('partner_id', 'in', partner_ids)])
        if leads and 'cf_lead_ids' in self.env['project.project']._fields:
            project_or_parts.append([('cf_lead_ids', 'in', leads.ids)])
        if project:
            project_or_parts.append([('id', '=', project.id)])
        projects = self.env['project.project'].search(
            self._or_domain(project_or_parts),
            order='write_date desc, id desc',
            limit=10,
        ) if project_or_parts else self.env['project.project']

        project_ids = projects.ids
        lead_ids = leads.ids

        mail_parts = []
        if partner_ids:
            mail_parts.append([('partner_id', 'in', partner_ids)])
        if lead_ids:
            mail_parts.append([('lead_id', 'in', lead_ids)])
        if project_ids and 'cf_project_id' in self.env['casafolino.mail.message']._fields:
            mail_parts.append([('cf_project_id', 'in', project_ids)])
        if record._name == 'casafolino.mail.message':
            mail_parts.append([('id', '=', record.id)])
        mails = self.env['casafolino.mail.message'].search(
            self._or_domain(mail_parts) + [('is_deleted', '=', False)],
            order='email_date desc, id desc',
            limit=12,
        ) if mail_parts else self.env['casafolino.mail.message']

        tasks = self.env['project.task'].search(
            [('project_id', 'in', project_ids), ('stage_id.fold', '=', False)],
            order='date_deadline asc, priority desc, write_date desc',
            limit=10,
        ) if project_ids else self.env['project.task']

        sample_rows = []
        if 'cf.export.sample' in self.env.registry:
            sample_parts = []
            if partner_ids:
                sample_parts.append([('partner_id', 'in', partner_ids)])
            if lead_ids:
                sample_parts.append([('lead_id', 'in', lead_ids)])
            if project_ids:
                sample_parts.append([('project_id', 'in', project_ids)])
            if record._name == 'cf.export.sample':
                sample_parts.append([('id', '=', record.id)])
            samples = self.env['cf.export.sample'].search(
                self._or_domain(sample_parts),
                order='date_feedback_expected asc, write_date desc, id desc',
                limit=10,
            ) if sample_parts else self.env['cf.export.sample']
            sample_rows = [self._format_entity360_sample(sample) for sample in samples]

        shipment_rows = []
        if project_ids and 'cf.project.shipment' in self.env.registry:
            shipments = self.env['cf.project.shipment'].search(
                [('project_id', 'in', project_ids)],
                order='estimated_delivery asc, ship_date desc, id desc',
                limit=8,
            )
            today = fields.Date.context_today(self)
            shipment_rows = [self._format_shipment_item(shipment, today) for shipment in shipments]

        quote_parts = []
        Sale = self.env['sale.order']
        if partner_ids:
            quote_parts.append([('partner_id', 'in', partner_ids)])
        if lead_ids and 'opportunity_id' in Sale._fields:
            quote_parts.append([('opportunity_id', 'in', lead_ids)])
        if project_ids and 'cf_project_id' in Sale._fields:
            quote_parts.append([('cf_project_id', 'in', project_ids)])
        quotes = Sale.search(
            self._or_domain(quote_parts) + [('state', 'in', ['draft', 'sent', 'sale'])],
            order='write_date desc, id desc',
            limit=10,
        ) if quote_parts else Sale

        contact_rows = []
        if company:
            contact_rows = [self._format_entity360_partner(p) for p in self.env['res.partner'].search(
                [('parent_id', '=', company.id)], order='write_date desc, id desc', limit=8
            )]
        elif partner:
            contact_rows = [self._format_entity360_partner(partner)]

        header = self._entity360_header(record, partner, company, lead, project)
        counts = {
            'mail_count': len(mails),
            'lead_count': len(leads),
            'project_count': len(projects),
            'task_count': len(tasks),
            'sample_count': len(sample_rows),
            'shipment_count': len(shipment_rows),
            'quote_count': len(quotes),
        }
        next_moves = self._entity360_next_moves(record, partner, company, lead, project, tasks, mails, sample_rows, quotes)
        return {
            'found': True,
            'header': header,
            'next_moves': next_moves,
            'kpis': [
                {'label': 'Mail', 'value': counts['mail_count']},
                {'label': 'Lead', 'value': counts['lead_count']},
                {'label': 'Dossier', 'value': counts['project_count']},
                {'label': 'Task', 'value': counts['task_count']},
                {'label': 'Campioni', 'value': counts['sample_count']},
                {'label': 'Preventivi', 'value': counts['quote_count']},
            ],
            'sections': {
                'contacts': contact_rows,
                'mails': [self._format_entity360_mail(mail) for mail in mails],
                'leads': [self._format_entity360_lead(item) for item in leads],
                'dossiers': [self._format_entity360_project(item) for item in projects],
                'tasks': [self._format_entity360_task(item) for item in tasks],
                'samples': sample_rows,
                'shipments': shipment_rows,
                'quotes': [self._format_entity360_quote(item) for item in quotes],
            },
        }

    def _entity360_next_moves(self, record, partner, company, lead, project, tasks, mails, sample_rows, quotes):
        moves = []
        overdue_tasks = tasks.filtered(lambda task: self._is_overdue(task.date_deadline)) if tasks else self.env['project.task']
        action_required = mails.filtered(lambda mail: mail.ai_action_required) if mails else self.env['casafolino.mail.message']
        open_quotes = quotes.filtered(lambda order: order.state in ['draft', 'sent']) if quotes else self.env['sale.order']
        overdue_samples = [row for row in sample_rows if row.get('tone') == 'red']

        if overdue_tasks:
            moves.append({
                'label': 'Task scadute',
                'value': len(overdue_tasks),
                'hint': overdue_tasks[0].name,
                'tone': 'red',
            })
        if action_required:
            moves.append({
                'label': 'Mail da lavorare',
                'value': len(action_required),
                'hint': action_required[0].subject or action_required[0].sender_email or 'Thread cliente',
                'tone': 'red',
            })
        if overdue_samples:
            moves.append({
                'label': 'Feedback campioni',
                'value': len(overdue_samples),
                'hint': overdue_samples[0].get('title') or 'Campionatura da chiudere',
                'tone': 'amber',
            })
        if open_quotes:
            moves.append({
                'label': 'Preventivi aperti',
                'value': len(open_quotes),
                'hint': open_quotes[0].name,
                'tone': 'blue',
            })
        if project and getattr(project, 'cf_next_action', False):
            moves.append({
                'label': 'Prossima azione dossier',
                'value': '!',
                'hint': project.cf_next_action,
                'tone': 'green',
            })
        if lead:
            followup_field = 'cf_date_next_followup' if 'cf_date_next_followup' in lead._fields else 'date_deadline'
            followup = getattr(lead, followup_field, False)
            if followup:
                moves.append({
                    'label': 'Follow-up pipeline',
                    'value': self._date_label(followup),
                    'hint': lead.name,
                    'tone': 'green',
                })
        if not moves:
            moves.append({
                'label': 'Contesto stabile',
                'value': 'OK',
                'hint': (company or partner).display_name if (company or partner) else record.display_name,
                'tone': 'green',
            })
        return moves[:4]

    @api.model
    def get_message_context_info(self, message_id):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return {
                'has_partner': False,
                'partner': None,
                'participants': [],
                'duplicate_partners': [],
                'mail_timeline': [],
                'open_tasks': [],
                'next_move': {},
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
            'participants': self._message_participant_context(msg),
            'duplicate_partners': self._message_duplicate_partner_context(msg),
            'mail_timeline': self._message_context_mail_timeline(msg, partner),
            'open_tasks': self._message_context_open_tasks(msg, partner, leads_list, projects_list),
            'next_move': self._message_next_move_context(msg, partner, leads_list, projects_list, sales_list),
            'sender_rule_impact': self._message_sender_rule_impact(msg),
            'ai_brief': self._message_ai_brief(msg),
            'contact_plan': self._message_contact_plan(msg),
            'summary': {
                'sender_email': msg.sender_email or '',
                'sender_domain': msg.sender_domain or '',
                'subject': msg.subject or '',
                'decision': self._sender_decision_status(msg),
                'ai_category': msg.ai_category or '',
                'ai_urgency': msg.ai_urgency or '',
                'ai_language': msg.ai_language or '',
                'ai_action_required': bool(msg.ai_action_required),
                'account': msg.account_id.display_name if msg.account_id else '',
                'thread_count': msg.thread_id.message_count if msg.thread_id else 1,
                'lead_count': len(leads_list),
                'dossier_count': len(projects_list),
                'quote_count': len(sales_list),
                'suggested_partner_count': len(suggested_partners),
                'is_linked': bool(partner or msg.lead_id),
                'next_step': self._mail_suggested_action(msg),
            },
            'ai_actions': self._mail_context_ai_actions(msg, partner, leads_list, projects_list, sales_list),
            'suggested_partners': suggested_partners,
            'leads': leads_list,
            'dossiers': projects_list,
            'quotes': sales_list,
        }

    def _message_ai_brief(self, msg):
        ai_payload = self._message_ai_payload(msg)
        text = ' '.join([
            msg.subject or '',
            msg.snippet or '',
            (msg.body_plain or '')[:1200],
        ]).lower()
        products = []
        product_patterns = [
            ('Pesto', ['pesto', 'genovese']),
            ('Olive Oil', ['olive oil', 'olio evo', 'extra virgin', 'olio extravergine']),
            ('Pickles / Relish', ['pickle', 'pickles', 'relish']),
            ('Pasta', ['pasta']),
            ('Sauces', ['sauce', 'salsa', 'sughi', 'sugo']),
            ('Catalogo', ['catalog', 'catalogo', 'brochure']),
            ('Campioni', ['sample', 'samples', 'campione', 'campioni', 'campionatura']),
        ]
        for label, needles in product_patterns:
            if any(needle in text for needle in needles):
                products.append(label)
        for product in ai_payload.get('products', []):
            product_label = str(product or '').strip()
            if product_label and product_label not in products:
                products.append(product_label)

        intent = ai_payload.get('intent') or ai_payload.get('category_label') or 'Da qualificare'
        if any(word in text for word in ['quote', 'quotation', 'preventivo', 'pricing', 'price list', 'listino']):
            intent = 'Richiesta quotazione'
        elif any(word in text for word in ['sample', 'campione', 'campionatura']):
            intent = 'Campionatura'
        elif any(word in text for word in ['order', 'ordine', 'po ', 'purchase order']):
            intent = 'Ordine / richiesta acquisto'
        elif any(word in text for word in ['catalog', 'catalogo', 'brochure', 'scheda tecnica', 'technical sheet']):
            intent = 'Richiesta materiali'
        elif msg.ai_category:
            intent = dict(msg._fields['ai_category'].selection).get(msg.ai_category, msg.ai_category)

        action_items = [str(item).strip() for item in ai_payload.get('action_items', []) if str(item or '').strip()]
        business_risk = 'medium' if msg.ai_action_required or msg.ai_urgency == 'high' else 'low'
        value_signal = 'standard'
        recommended_action = 'task'
        decision_reason = 'Serve tracciare la prossima azione e mantenere il thread agganciato al CRM.'
        if msg.ai_action_required:
            action_items.append('Rispondere al cliente')
        if not msg.partner_id:
            action_items.append('Creare o collegare anagrafica')
        if not msg.lead_id:
            action_items.append('Creare lead pipeline')
        if msg.ai_urgency == 'high':
            action_items.append('Gestire oggi')
        if any(product in products for product in ['Campioni', 'Pickles / Relish', 'Pesto', 'Olive Oil']):
            action_items.append('Verificare prodotto e disponibilita')
        if not action_items:
            action_items.append('Programmare follow-up')

        if intent == 'Richiesta quotazione':
            value_signal = 'commerciale'
            recommended_action = 'quote' if msg.lead_id else 'create_lead'
            decision_reason = 'La mail contiene richiesta prezzo/preventivo: prima pipeline, poi quotazione.'
        elif intent == 'Campionatura':
            value_signal = 'campionatura'
            recommended_action = 'sample'
            decision_reason = 'La richiesta riguarda campioni: crea campionatura o task campione con tracking.'
        elif intent == 'Richiesta materiali':
            value_signal = 'materiali'
            recommended_action = 'catalog'
            decision_reason = 'La mail richiede materiale commerciale/tecnico: assegna a Grafica o prepara catalogo.'
        elif intent == 'Ordine / richiesta acquisto':
            value_signal = 'ordine'
            business_risk = 'high'
            recommended_action = 'reply'
            decision_reason = 'Possibile ordine o PO: dare risposta rapida e collegare a pipeline/cliente.'
        elif not msg.partner_id:
            recommended_action = 'create_company'
            decision_reason = 'Manca ancora il collegamento anagrafico: prima crea azienda/contatti.'

        if msg.ai_urgency == 'high':
            business_risk = 'high'
        if ai_payload.get('risk') in ('low', 'medium', 'high'):
            business_risk = ai_payload['risk']
        if ai_payload.get('value_signal'):
            value_signal = ai_payload['value_signal']
        if ai_payload.get('recommended_action'):
            recommended_action = ai_payload['recommended_action']
        if ai_payload.get('decision_reason'):
            decision_reason = ai_payload['decision_reason']

        confidence = 45
        if msg.ai_category:
            confidence += 20
        if msg.ai_urgency:
            confidence += 10
        if msg.ai_action_required:
            confidence += 10
        if products:
            confidence += 10
        if ai_payload:
            confidence += 10

        return {
            'intent': intent,
            'products': products[:5],
            'action_items': action_items[:5],
            'confidence': min(confidence, 95),
            'sentiment': msg.ai_sentiment or 'neutral',
            'risk': business_risk,
            'value_signal': value_signal,
            'recommended_action': recommended_action,
            'decision_reason': decision_reason,
            'summary': ai_payload.get('summary') or msg.snippet or '',
            'provider': ai_payload.get('provider') or ('classificatore AI' if msg.ai_classified_at else 'euristica console'),
        }

    def _message_ai_payload(self, msg):
        raw = msg.ai_raw_response or ''
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        if isinstance(data.get('choices'), list):
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            try:
                data = json.loads(content)
            except Exception:
                return {}
        category = (data.get('category') or msg.ai_category or '').lower()
        urgency = (data.get('urgency') or msg.ai_urgency or '').lower()
        summary = data.get('summary') or data.get('reasoning') or data.get('decision_reason') or ''
        action_items = data.get('action_items') or data.get('actions') or []
        if isinstance(action_items, str):
            action_items = [action_items]
        products = data.get('products') or data.get('product_interests') or []
        if isinstance(products, str):
            products = [products]
        intent = data.get('intent') or data.get('customer_intent') or ''
        recommended = data.get('recommended_action') or data.get('next_action') or ''
        if recommended in ('sample_request', 'sample_task'):
            recommended = 'sample'
        elif recommended in ('catalog_request', 'materials'):
            recommended = 'catalog'
        elif recommended in ('quotation', 'quote_request'):
            recommended = 'quote'
        risk = data.get('risk') or ''
        if not risk and urgency == 'high':
            risk = 'high'
        category_labels = dict(msg._fields['ai_category'].selection)
        value_signal = data.get('value_signal') or ''
        if not value_signal and category == 'commerciale':
            value_signal = 'commerciale'
        return {
            'intent': intent,
            'category_label': category_labels.get(category, category),
            'products': products,
            'action_items': action_items,
            'summary': summary,
            'recommended_action': recommended,
            'decision_reason': data.get('decision_reason') or data.get('reasoning') or '',
            'risk': risk if risk in ('low', 'medium', 'high') else '',
            'value_signal': value_signal,
            'provider': data.get('provider') or data.get('model') or '',
        }

    def _message_sender_rule_impact(self, msg):
        Mail = self.env['casafolino.mail.message']
        base_domain = [
            ('is_deleted', '=', False),
            ('is_archived', '=', False),
        ]
        if msg.account_id:
            base_domain.append(('account_id', '=', msg.account_id.id))
        sender_count = 0
        domain_count = 0
        sender_domain = msg.sender_domain or self._email_domain(msg.sender_email)
        if msg.sender_email:
            sender_count = Mail.search_count(base_domain + [('sender_email', '=ilike', msg.sender_email)])
        if sender_domain:
            domain_count = Mail.search_count(base_domain + ['|', ('sender_domain', '=', sender_domain), ('sender_email', 'ilike', '@' + sender_domain)])
        return {
            'sender_email': msg.sender_email or '',
            'sender_domain': sender_domain or '',
            'sender_visible_count': sender_count,
            'domain_visible_count': domain_count,
            'suggested_scope': 'domain' if domain_count > sender_count and domain_count <= 30 else 'sender',
        }

    def _message_contact_plan(self, msg):
        participants = self._message_external_participants(msg)
        company = self._find_company_for_message(msg, participants)
        existing = 0
        to_create = 0
        to_link = 0
        domains = []
        for person in participants:
            if person.get('domain') and person['domain'] not in domains:
                domains.append(person['domain'])
            contact = self.env['res.partner'].search([
                ('is_company', '=', False),
                ('email', '=ilike', person['email']),
            ], limit=1)
            if contact:
                existing += 1
                if company and not contact.parent_id:
                    to_link += 1
            else:
                to_create += 1
        return {
            'company_id': company.id if company else False,
            'company_name': company.display_name if company else '',
            'company_target': company.display_name if company else self._company_name_from_email_context(msg, participants),
            'domains': domains[:4],
            'total_participants': len(participants),
            'existing_contacts': existing,
            'contacts_to_create': to_create,
            'contacts_to_link': to_link,
            'company_will_create': not bool(company) and bool(participants or msg.sender_domain or msg.sender_email),
            'next_step': self._contact_plan_next_step(company, existing, to_create, to_link),
        }

    def _company_name_from_email_context(self, msg, participants):
        domain = msg.sender_domain or (participants[0]['domain'] if participants else '')
        if not domain:
            return msg.sender_name or msg.sender_email or ''
        root = domain.split('.')[0].replace('-', ' ').replace('_', ' ').strip()
        return root.title() if root else domain

    def _contact_plan_next_step(self, company, existing, to_create, to_link):
        if not company:
            return 'Crea azienda e aggancia tutti i partecipanti esterni.'
        if to_create and to_link:
            return 'Crea i contatti mancanti e collega quelli senza azienda.'
        if to_create:
            return 'Crea i contatti mancanti sotto azienda.'
        if to_link:
            return 'Collega i contatti esistenti alla azienda.'
        if existing:
            return 'Contatti gia allineati: porta la mail in pipeline.'
        return 'Verifica anagrafica prima di creare lead o dossier.'

    def _message_next_move_context(self, msg, partner, leads, projects, sales):
        ai_brief = self._message_ai_brief(msg)
        recommended = ai_brief.get('recommended_action')
        if self._sender_decision_status(msg) == 'pending':
            return {
                'title': 'Decidi il mittente',
                'detail': 'Tieni se e commerciale, scarta se non deve piu entrare in console.',
                'quick_action': 'keep_sender',
                'button': 'Tieni mittente',
                'tone': 'amber',
                'icon': 'fa-check',
            }
        if not partner:
            return {
                'title': 'Crea o collega contatto',
                'detail': 'Prima aggancia anagrafica e azienda, poi porta la mail in pipeline.',
                'quick_action': 'create_company',
                'button': 'Azienda + contatti',
                'tone': 'amber',
                'icon': 'fa-building-o',
            }
        if recommended == 'sample':
            return {
                'title': 'Crea campionatura',
                'detail': ai_brief.get('decision_reason') or 'La mail sembra richiedere campioni: apri task/campionatura con tracking.',
                'quick_action': 'sample',
                'button': 'Campione',
                'tone': 'amber',
                'icon': 'fa-truck',
            }
        if recommended == 'catalog':
            return {
                'title': 'Prepara catalogo',
                'detail': ai_brief.get('decision_reason') or 'La mail richiede materiale commerciale o tecnico: crea task per grafica/commerciale.',
                'quick_action': 'catalog',
                'button': 'Catalogo',
                'tone': 'amber',
                'icon': 'fa-book',
            }
        if recommended == 'quote' and (msg.lead_id or leads):
            return {
                'title': 'Prepara preventivo',
                'detail': ai_brief.get('decision_reason') or 'Richiesta prezzo rilevata: apri o crea quotazione collegata alla pipeline.',
                'quick_action': 'quote',
                'button': 'Preventivo',
                'tone': 'amber',
                'icon': 'fa-file-text-o',
            }
        if not msg.lead_id and not leads:
            return {
                'title': 'Porta in pipeline',
                'detail': 'Nessun lead collegato: crea la trattativa dalla mail.',
                'quick_action': 'create_lead',
                'button': 'Crea lead',
                'tone': 'blue',
                'icon': 'fa-star-o',
            }
        if leads and not projects:
            return {
                'title': 'Serve dossier operativo',
                'detail': 'Lead presente ma dossier assente: prepara mini-progetto e task reparto.',
                'quick_action': 'create_dossier',
                'button': 'Crea dossier',
                'tone': 'green',
                'icon': 'fa-folder-open-o',
            }
        if msg.ai_action_required or msg.ai_urgency == 'high':
            return {
                'title': 'Risposta o task urgente',
                'detail': 'AI ha rilevato azione richiesta: rispondi o crea una task memoria.',
                'quick_action': 'reply',
                'button': 'Rispondi AI',
                'tone': 'red',
                'icon': 'fa-magic',
            }
        if not sales and (msg.lead_id or leads):
            return {
                'title': 'Valuta preventivo',
                'detail': 'Pipeline attiva senza quotazione aperta.',
                'quick_action': 'quote',
                'button': 'Preventivo',
                'tone': 'amber',
                'icon': 'fa-file-text-o',
            }
        return {
            'title': 'Programma follow-up',
            'detail': 'Lascia una task o reminder per non perdere il prossimo passo.',
            'quick_action': 'task',
            'button': 'Task rapida',
            'tone': 'neutral',
            'icon': 'fa-check-square-o',
        }

    def _mail_context_ai_actions(self, msg, partner, leads, projects, sales):
        actions = []
        participants = self._message_external_participants(msg)
        if self._sender_decision_status(msg) == 'pending':
            actions.append({
                'key': 'keep',
                'label': 'Tieni mittente',
                'hint': 'Fai entrare questo mittente nel lavoro commerciale',
                'icon': 'fa-check',
                'quick_action': 'keep_sender',
                'tone': 'green',
            })
        if len(participants) > 1:
            actions.append({
                'key': 'company_contacts',
                'label': 'Azienda + contatti',
                'hint': 'Crea/aggancia tutti i partecipanti esterni',
                'icon': 'fa-building-o',
                'quick_action': 'create_company',
                'tone': 'green',
            })
        if not partner:
            actions.append({
                'key': 'contact',
                'label': 'Crea contatto',
                'hint': 'Anagrafica mancante',
                'icon': 'fa-user-o',
                'quick_action': 'create_contact',
                'tone': 'amber',
            })
        if not msg.lead_id:
            actions.append({
                'key': 'lead',
                'label': 'Crea lead',
                'hint': 'Porta la mail in pipeline',
                'icon': 'fa-star-o',
                'quick_action': 'create_lead',
                'tone': 'blue',
            })
        if msg.ai_urgency == 'high' or msg.ai_action_required:
            actions.append({
                'key': 'reply',
                'label': 'Rispondi con AI',
                'hint': 'Thread urgente o con azione richiesta',
                'icon': 'fa-magic',
                'quick_action': 'reply',
                'tone': 'green',
            })
        ai_brief = self._message_ai_brief(msg)
        if ai_brief.get('recommended_action') == 'sample':
            actions.append({
                'key': 'sample',
                'label': 'Campione',
                'hint': 'Crea campionatura o task campione da questa mail',
                'icon': 'fa-truck',
                'quick_action': 'sample',
                'tone': 'amber',
            })
        if ai_brief.get('recommended_action') == 'catalog':
            actions.append({
                'key': 'catalog',
                'label': 'Catalogo',
                'hint': 'Crea task catalogo/materiali per grafica',
                'icon': 'fa-book',
                'quick_action': 'catalog',
                'tone': 'amber',
            })
        if leads and not projects:
            actions.append({
                'key': 'dossier',
                'label': 'Crea dossier',
                'hint': 'Lead presente, dossier assente',
                'icon': 'fa-folder-open-o',
                'quick_action': 'create_dossier',
                'tone': 'blue',
            })
        if not sales and msg.lead_id:
            actions.append({
                'key': 'quote',
                'label': 'Preventivo',
                'hint': 'Lead senza quotazione aperta',
                'icon': 'fa-file-text-o',
                'quick_action': 'quote',
                'tone': 'amber',
            })
        actions.append({
            'key': 'task',
            'label': 'Task rapida',
            'hint': 'Promessa o prossima azione da non perdere',
            'icon': 'fa-check-square-o',
            'quick_action': 'task',
            'tone': 'neutral',
        })
        deduped = []
        seen = set()
        for action in actions:
            key = action.get('quick_action') or action.get('key')
            if key in seen:
                continue
            seen.add(key)
            deduped.append(action)
        return deduped[:7]

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
    def generate_ai_draft(self, message_id, instruction='', mode='reply', tone='professional'):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return {'success': False, 'error': 'Email non trovata'}

        original_body = msg.body_plain or msg.snippet or ''
        partner = msg.partner_id
        lead = msg.lead_id
        project = getattr(msg, 'cf_project_id', False)
        ai_brief = self._message_ai_brief(msg)
        open_tasks = []
        if project:
            open_tasks = self.env['project.task'].search([
                ('project_id', '=', project.id),
                ('stage_id.fold', '=', False),
            ], order='date_deadline asc, id desc', limit=5)
        elif lead and partner:
            open_tasks = self.env['project.task'].search([
                ('partner_id', '=', partner.id),
                ('stage_id.fold', '=', False),
            ], order='date_deadline asc, id desc', limit=5)
        task_lines = []
        for task in open_tasks:
            deadline = fields.Date.to_string(task.date_deadline) if task.date_deadline else 'senza scadenza'
            task_lines.append("- %s (%s)" % (task.display_name, deadline))
        mode = mode or 'reply'
        tone = tone or 'professional'
        mode_instructions = {
            'reply': 'Write a complete customer reply: acknowledge, answer, clarify next step, and ask for missing facts only when needed.',
            'quote': 'Focus on a quotation/pricing request. Ask for missing products, quantities, destination, billing/company data, and timing. Do not invent prices.',
            'catalog': 'Focus on sending catalog, price list, product sheets, or technical material. Confirm what material will be prepared and ask for the exact line/product if unclear.',
            'sample': 'Focus on sample shipment. Confirm sample handling, ask for products/address if missing, mention tracking only when available or as next step.',
            'data': 'Ask elegantly for missing company/billing data: company name, address, VAT/tax ID, contact person, phone, email.',
            'reminder': 'Write a polite follow-up/reminder. Mention the open topic, keep it short, and propose a clear next deadline or action.',
        }
        tone_instructions = {
            'professional': 'Tone: professional, warm, concise.',
            'commercial': 'Tone: commercial and proactive, but never pushy.',
            'formal': 'Tone: formal and precise.',
            'polite': 'Tone: very polite and diplomatic.',
            'operational': 'Tone: practical, clear, action-oriented.',
            'short': 'Tone: short, direct, maximum 2-3 short paragraphs.',
        }
        
        system_instruction = (
            "You are an expert sales assistant for CasaFolino, an Italian artisan gourmet food company.\n"
            "Your task is to write a highly professional, polite, and helpful email reply to the customer's email.\n"
            "Write the reply in the same language as the customer's email (typically Italian or English).\n"
            "Do NOT include any email subject or headers. Output ONLY the email body text in HTML format. Keep paragraphs clean using <p> tags. Do not put markdown placeholders. Keep it elegant.\n"
            "Use only facts provided in the context. If something is missing, ask for it politely instead of inventing details.\n"
            "Never promise shipment, prices, discounts, delivery dates, or attachments unless explicitly present in the context."
        )

        user_prompt = (
            f"Composer mode: {mode}\n"
            f"Composer objective: {mode_instructions.get(mode, mode_instructions['reply'])}\n"
            f"Composer tone: {tone_instructions.get(tone, tone_instructions['professional'])}\n"
            f"Customer email sender: {msg.sender_name or 'Customer'} <{msg.sender_email or ''}>\n"
            f"Customer email subject: {msg.subject or '(no subject)'}\n"
            f"Matched company/contact: {(partner.display_name if partner else 'not linked yet')}\n"
            f"Pipeline lead: {(lead.display_name if lead else 'none')}\n"
            f"Dossier/project: {(project.display_name if project else 'none')}\n"
            f"AI intent: {ai_brief.get('intent')}\n"
            f"AI recommended action: {ai_brief.get('recommended_action')}\n"
            f"AI action items: {', '.join(ai_brief.get('action_items') or []) or 'none'}\n"
            f"Open operational tasks:\n{chr(10).join(task_lines) if task_lines else '- none'}\n"
            f"Customer email body:\n\"\"\"\n{original_body[:3000]}\n\"\"\"\n\n"
        )
        
        if instruction:
            user_prompt += f"USER EXTRA INSTRUCTIONS for the reply: {instruction}\n\n"
        else:
            user_prompt += "No extra user instructions. Follow the composer objective and context.\n\n"

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
            'casafolino_pipeline_control.menu_cf_pipeline_control_root',
            'casafolino_crm_export.menu_cf_projects_360',
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
                'label': 'Tocca a noi',
                'value': len(inbox_threads),
                'hint': 'Thread cliente con azione richiesta',
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
        messages = self.env['casafolino.mail.message'].search([
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
        groups = self.env['casafolino.mail.message'].read_group(
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
            stage_domain = [('stage_id', '=', stage.id)]
            leads = Lead.search(stage_domain, order='expected_revenue desc, create_date desc', limit=5)
            all_count = Lead.search_count(stage_domain)
            followup_field = 'cf_date_next_followup' if 'cf_date_next_followup' in Lead._fields else 'date_deadline'
            overdue_domain = stage_domain + [(followup_field, '<=', today)]
            no_next_domain = stage_domain + [(followup_field, '=', False)]
            stale_limit = fields.Datetime.now() - timedelta(days=21)
            stale_count = Lead.search_count(stage_domain + [('write_date', '<=', stale_limit)])
            value_rows = Lead.read_group(stage_domain, ['expected_revenue:sum'], [])
            expected_total = 0.0
            if value_rows:
                expected_total = value_rows[0].get('expected_revenue_sum') or value_rows[0].get('expected_revenue') or 0.0
            columns.append({
                'id': stage.id,
                'title': stage.name,
                'count': all_count,
                'overdue_count': Lead.search_count(overdue_domain),
                'no_next_count': Lead.search_count(no_next_domain),
                'stale_count': stale_count,
                'expected_total': expected_total,
                'items': [self._format_lead_item(lead, today) for lead in leads],
            })
        return columns

    def _get_operations_data(self, today, user):
        return {
            'tasks': self._get_operational_tasks(user),
            'shipments': self._get_sample_shipments(today),
            'samples': self._get_sample_tracking(today),
            'entities': self._get_entity_360_suggestions(today),
            'ai_queue': self._get_ai_action_queue(user),
        }

    def _get_operational_tasks(self, user):
        Task = self.env['project.task']
        domain = [('stage_id.fold', '=', False)]
        if 'cf_task_origin' in Task._fields:
            domain = ['|', ('cf_task_origin', '!=', False), ('cf_is_mini_project', '=', True)] + domain
        if user and 'user_ids' in Task._fields and not user.has_group('base.group_system'):
            domain = ['|', ('user_ids', '=', False), ('user_ids', 'in', user.ids)] + domain
        tasks = Task.search(domain, order='date_deadline asc, priority desc, write_date desc', limit=8)
        return [self._format_task_item(task) for task in tasks]

    def _get_sample_shipments(self, today):
        if 'cf.project.shipment' not in self.env.registry:
            return []
        Shipment = self.env['cf.project.shipment']
        shipments = Shipment.search([('state', 'not in', ['delivered', 'feedback'])], order='estimated_delivery asc, ship_date desc, id desc', limit=10)
        return [self._format_shipment_item(shipment, today) for shipment in shipments]

    def _get_sample_tracking(self, today):
        if 'cf.export.sample' not in self.env.registry:
            return []
        Sample = self.env['cf.export.sample']
        samples = Sample.search([('state', 'not in', ['feedback_ok', 'feedback_ko', 'no_feedback'])], order='date_feedback_expected asc, promised_date asc, id desc', limit=10)
        return [self._format_sample_item(sample, today) for sample in samples]

    def _get_entity_360_suggestions(self, today):
        rows = []
        for msg in self.env['casafolino.mail.message'].search(self._mail_to_reply_domain(self.env.user), order='email_date desc, id desc', limit=5):
            partner = msg.partner_id
            lead = msg.lead_id
            if not partner and not lead:
                continue
            rows.append({
                'id': msg.id,
                'model': partner._name if partner else lead._name,
                'res_id': partner.id if partner else lead.id,
                'title': partner.display_name if partner else lead.display_name,
                'subtitle': msg.subject or '',
                'meta': 'Mail %s' % (self._date_label(msg.email_date) or ''),
                'badges': self._compact([
                    'partner' if partner else False,
                    'lead' if lead else False,
                    lead.stage_id.name if lead and lead.stage_id else False,
                ]),
            })
        if len(rows) < 5:
            Lead = self.env['crm.lead']
            for lead in Lead.search(self._hot_lead_domain(), order='expected_revenue desc, write_date desc', limit=5 - len(rows)):
                rows.append({
                    'id': lead.id,
                    'model': lead._name,
                    'res_id': lead.id,
                    'title': lead.partner_id.display_name if lead.partner_id else lead.name,
                    'subtitle': lead.name,
                    'meta': lead.stage_id.name if lead.stage_id else '',
                    'badges': self._compact(['lead', self._lead_origin_label(lead)]),
                })
        return rows

    @staticmethod
    def _or_domain(parts):
        parts = [part for part in (parts or []) if part]
        if not parts:
            return []
        domain = ['|'] * (len(parts) - 1)
        for part in parts:
            domain += part
        return domain

    def _entity360_context_from_record(self, record):
        partner = self.env['res.partner']
        company = self.env['res.partner']
        lead = self.env['crm.lead']
        project = self.env['project.project']

        if record._name == 'res.partner':
            partner = record
            company = record if record.is_company else record.parent_id
        elif record._name == 'crm.lead':
            lead = record
            partner = record.partner_id
            company = partner if partner and partner.is_company else partner.parent_id
            project = getattr(record, 'cf_project_id', False)
        elif record._name == 'project.project':
            project = record
            partner = getattr(record, 'partner_id', False) or getattr(record, 'cf_partner_id', False)
            company = partner if partner and partner.is_company else partner.parent_id
        elif record._name == 'casafolino.mail.message':
            partner = record.partner_id
            lead = record.lead_id
            project = getattr(record, 'cf_project_id', False) or getattr(lead, 'cf_project_id', False)
            company = partner if partner and partner.is_company else partner.parent_id
        elif record._name == 'project.task':
            project = record.project_id
            partner = project.partner_id if project else self.env['res.partner']
            company = partner if partner and partner.is_company else partner.parent_id
        elif record._name == 'cf.export.sample':
            partner = record.partner_id
            lead = record.lead_id
            project = record.project_id
            company = partner if partner and partner.is_company else partner.parent_id
        elif record._name == 'cf.project.shipment':
            project = record.project_id
            partner = record.partner_id
            company = partner if partner and partner.is_company else partner.parent_id
        elif record._name == 'sale.order':
            partner = record.partner_id
            lead = record.opportunity_id if 'opportunity_id' in record._fields else self.env['crm.lead']
            project = record.cf_project_id if 'cf_project_id' in record._fields else self.env['project.project']
            company = partner if partner and partner.is_company else partner.parent_id

        return {
            'partner': partner if partner and partner.exists() else self.env['res.partner'],
            'company': company if company and company.exists() else self.env['res.partner'],
            'lead': lead if lead and lead.exists() else self.env['crm.lead'],
            'project': project if project and project.exists() else self.env['project.project'],
        }

    def _entity360_header(self, record, partner=False, company=False, lead=False, project=False):
        title = ''
        subtitle = ''
        badges = []
        if partner:
            title = partner.display_name
            subtitle = partner.email or partner.phone or partner.mobile or ''
            badges = self._compact(['contatto' if not partner.is_company else 'azienda', partner.country_id.code if partner.country_id else False])
        elif lead:
            title = lead.partner_id.display_name if lead.partner_id else lead.name
            subtitle = lead.name
            badges = self._compact(['lead', lead.stage_id.name if lead.stage_id else False])
        elif project:
            title = project.name
            subtitle = self._project_partner_name(project)
            badges = self._compact(['dossier', self._project_status(project)])
        else:
            title = record.display_name
            subtitle = record._description or record._name
            badges = [record._name]
        if company and company != partner:
            badges.append(company.display_name)
        return {
            'model': record._name,
            'res_id': record.id,
            'title': title or record.display_name,
            'subtitle': subtitle or '',
            'badges': badges,
            'company_id': company.id if company else False,
            'company_name': company.display_name if company else '',
        }

    def _format_entity360_mail(self, mail):
        return {
            'id': mail.id,
            'model': mail._name,
            'res_id': mail.id,
            'title': mail.partner_id.display_name if mail.partner_id else (mail.sender_name or mail.sender_email or 'Email'),
            'subtitle': mail.subject or 'Senza oggetto',
            'meta': self._date_label(mail.email_date),
            'next_action': self._mail_suggested_action(mail),
            'badges': self._compact([
                'mail',
                mail.ai_category,
                mail.ai_language,
                'urgente' if mail.ai_urgency == 'high' else False,
                mail.lead_id.stage_id.name if mail.lead_id and mail.lead_id.stage_id else False,
            ]),
        }

    def _format_entity360_task(self, task):
        return self._format_task_item(task)

    def _format_entity360_sample(self, sample):
        today = fields.Date.context_today(self)
        return self._format_sample_item(sample, today)

    def _format_entity360_quote(self, order):
        state_label = dict(order._fields['state'].selection).get(order.state, order.state) if order.state else ''
        return {
            'id': order.id,
            'model': order._name,
            'res_id': order.id,
            'title': order.partner_id.display_name if order.partner_id else order.name,
            'subtitle': order.name,
            'meta': '€ %s' % int(order.amount_total or 0),
            'next_action': self._date_label(order.validity_date) if 'validity_date' in order._fields and order.validity_date else '',
            'badges': self._compact(['preventivo', state_label, order.user_id.name if order.user_id else False]),
        }

    def _format_entity360_partner(self, partner):
        counts = self._entity360_counts(partner=partner)
        return {
            'id': partner.id,
            'model': partner._name,
            'res_id': partner.id,
            'title': partner.display_name,
            'subtitle': partner.email or partner.phone or partner.mobile or 'Cliente / contatto',
            'meta': self._entity360_meta(counts),
            'next_action': counts.get('next_action') or '',
            'badges': self._compact([
                'cliente',
                partner.country_id.code if partner.country_id else False,
                '%s mail' % counts['mail_count'] if counts['mail_count'] else False,
                '%s lead' % counts['lead_count'] if counts['lead_count'] else False,
                '%s dossier' % counts['project_count'] if counts['project_count'] else False,
            ]),
        }

    def _format_entity360_lead(self, lead):
        counts = self._entity360_counts(partner=lead.partner_id, lead=lead)
        return {
            'id': lead.id,
            'model': lead._name,
            'res_id': lead.id,
            'title': lead.partner_id.display_name if lead.partner_id else lead.name,
            'subtitle': lead.name or 'Lead pipeline',
            'meta': self._entity360_meta(counts),
            'next_action': counts.get('next_action') or '',
            'badges': self._compact([
                'lead',
                lead.stage_id.name if lead.stage_id else False,
                self._lead_origin_label(lead),
                '€ %s' % int(lead.expected_revenue) if lead.expected_revenue else False,
            ]),
        }

    def _format_entity360_project(self, project):
        counts = self._entity360_counts(partner=project.partner_id, project=project)
        return {
            'id': project.id,
            'model': project._name,
            'res_id': project.id,
            'title': project.name,
            'subtitle': project.partner_id.display_name if project.partner_id else 'Dossier',
            'meta': self._entity360_meta(counts),
            'next_action': counts.get('next_action') or '',
            'badges': self._compact([
                'dossier',
                self._project_status(project),
                self._project_blocker_label(project),
                '%s task' % counts['task_count'] if counts['task_count'] else False,
            ]),
        }

    def _entity360_counts(self, partner=False, lead=False, project=False):
        Mail = self.env['casafolino.mail.message']
        Lead = self.env['crm.lead']
        Project = self.env['project.project']
        Task = self.env['project.task']
        Sale = self.env['sale.order']

        mail_domain = [('is_deleted', '=', False)]
        lead_domain = [('active', 'in', [True, False])]
        project_domain = []
        task_domain = []
        sale_domain = [('state', 'in', ['draft', 'sent'])]

        if partner:
            mail_domain.append(('partner_id', '=', partner.id))
            lead_domain.append(('partner_id', '=', partner.id))
            project_domain.append(('partner_id', '=', partner.id))
            sale_domain.append(('partner_id', '=', partner.id))
        if lead:
            mail_domain = ['|', ('lead_id', '=', lead.id)] + mail_domain
            project = project or getattr(lead, 'cf_project_id', False)
            if 'opportunity_id' in Sale._fields:
                sale_domain = ['|', ('opportunity_id', '=', lead.id)] + sale_domain
        if project:
            task_domain.append(('project_id', '=', project.id))
            if 'cf_project_id' in Mail._fields:
                mail_domain = ['|', ('cf_project_id', '=', project.id)] + mail_domain
        elif partner:
            projects = Project.search(project_domain, limit=50)
            if projects:
                task_domain.append(('project_id', 'in', projects.ids))

        next_action = ''
        if project and 'cf_next_action' in Project._fields:
            next_action = project.cf_next_action or ''
        elif lead:
            date_field = 'cf_date_next_followup' if 'cf_date_next_followup' in Lead._fields else 'date_deadline'
            next_date = getattr(lead, date_field, False)
            next_action = self._date_label(next_date) if next_date else ''

        return {
            'mail_count': Mail.search_count(mail_domain),
            'lead_count': Lead.search_count(lead_domain) if partner else (1 if lead else 0),
            'project_count': Project.search_count(project_domain) if partner else (1 if project else 0),
            'task_count': Task.search_count(task_domain) if task_domain else 0,
            'quote_count': Sale.search_count(sale_domain),
            'next_action': next_action,
        }

    def _entity360_meta(self, counts):
        parts = []
        if counts.get('lead_count'):
            parts.append('%s lead' % counts['lead_count'])
        if counts.get('project_count'):
            parts.append('%s dossier' % counts['project_count'])
        if counts.get('mail_count'):
            parts.append('%s mail' % counts['mail_count'])
        if counts.get('task_count'):
            parts.append('%s task' % counts['task_count'])
        if counts.get('quote_count'):
            parts.append('%s preventivi' % counts['quote_count'])
        return ' · '.join(parts) or 'Nessun collegamento operativo'

    def _get_ai_action_queue(self, user):
        Mail = self.env['casafolino.mail.message']
        domain = [
            ('is_archived', '=', False),
            ('is_deleted', '=', False),
            '|',
            ('ai_action_required', '=', True),
            ('ai_urgency', '=', 'high'),
        ]
        if user and not user.has_group('base.group_system'):
            domain = ['|', ('assigned_user_ids', '=', False), ('assigned_user_ids', 'in', user.ids)] + domain
        messages = Mail.search(domain, order='email_date desc, id desc', limit=6)
        rows = [self._format_ai_queue_item(msg) for msg in messages]
        seen = set(messages.ids)

        recent_domain = [
            ('is_archived', '=', False),
            ('is_deleted', '=', False),
            ('ai_category', 'in', ['commerciale', 'admin']),
        ]
        if user and not user.has_group('base.group_system'):
            recent_domain = ['|', ('assigned_user_ids', '=', False), ('assigned_user_ids', 'in', user.ids)] + recent_domain
        for msg in Mail.search(recent_domain, order='email_date desc, id desc', limit=40):
            if msg.id in seen:
                continue
            ai_brief = self._message_ai_brief(msg)
            if ai_brief.get('recommended_action') not in ('sample', 'catalog', 'quote', 'create_lead'):
                continue
            rows.append(self._format_ai_queue_item(msg, ai_brief=ai_brief))
            seen.add(msg.id)
            if len(rows) >= 8:
                break
        return rows[:8]

    def _get_inbox_data(self, user):
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
            'ai_status': self._get_ai_readiness_status(all_rows),
            'distribution_stats': stats_list,
            'to_reply': rows_to_reply,
            'waiting_customer': rows_waiting,
        }

    def _get_ai_readiness_status(self, inbox_rows):
        ICP = self.env['ir.config_parameter'].sudo()
        gemini_configured = bool(ICP.get_param('casafolino.gemini_api_key', '').strip())
        groq_configured = bool(ICP.get_param('casafolino.groq_api_key', '').strip())
        provider = 'Gemini' if gemini_configured else ('Groq fallback' if groq_configured else 'Non configurata')

        Mail = self.env['casafolino.mail.message']
        seven_days_ago = fields.Datetime.now() - timedelta(days=7)
        weekly_domain = [
            ('email_date', '>=', seven_days_ago),
            ('is_deleted', '=', False),
            ('is_archived', '=', False),
        ]
        weekly_total = Mail.search_count(weekly_domain)
        weekly_classified = Mail.search_count(weekly_domain + [
            '|',
            ('ai_category', '!=', False),
            ('ai_action_required', '=', True),
        ])
        pending_senders = len([row for row in inbox_rows if row.get('sender_decision') == 'pending'])
        kept_senders = len([row for row in inbox_rows if row.get('sender_decision') == 'kept'])
        urgent_actions = len([row for row in inbox_rows if row.get('urgency') == 'high' or row.get('needs_action')])
        coverage = int((weekly_classified / weekly_total) * 100) if weekly_total else 0

        return {
            'provider': provider,
            'configured': gemini_configured or groq_configured,
            'coverage': coverage,
            'weekly_total': weekly_total,
            'weekly_classified': weekly_classified,
            'pending_senders': pending_senders,
            'kept_senders': kept_senders,
            'urgent_actions': urgent_actions,
            'health_label': 'Pronta' if (gemini_configured or groq_configured) else 'Da configurare',
            'health_tone': 'green' if (gemini_configured or groq_configured) else 'red',
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
        if quick_action == 'keep_sender':
            return self._keep_sender_from_message(msg)
        if quick_action == 'dismiss_sender':
            return self._dismiss_sender_from_message(msg)
        if quick_action == 'create_contact':
            return self._create_or_open_contact_from_message(msg)
        if quick_action == 'create_company':
            return self._create_or_open_company_from_message(msg)
        if quick_action == 'open_lead':
            if msg.lead_id:
                return self._open_record(msg.lead_id, 'Lead')
            self._ensure_company_contacts_from_message(msg)
            return msg.action_create_lead()
        if quick_action == 'create_lead':
            self._ensure_company_contacts_from_message(msg)
            return msg.action_create_lead()
        if quick_action == 'create_dossier':
            self._ensure_company_contacts_from_message(msg)
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
            self._ensure_company_contacts_from_message(msg)
            return self._new_task_from_message(msg)
        if quick_action == 'catalog':
            self._ensure_company_contacts_from_message(msg)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Task catalogo da email',
                'res_model': 'cf.pipeline.quick.task.wizard',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'new',
                'context': {
                    'default_message_id': msg.id,
                    'default_quick_kind': 'catalog',
                    'default_name': 'Pagina catalogo: %s' % (msg.subject or msg.sender_name or msg.sender_email or 'cliente'),
                    'default_task_type': 'catalog_page',
                    'default_department': 'graphics',
                    'default_source_channel': 'mail',
                    'default_urgency': 'high',
                    'default_is_mini_project': True,
                    'default_checklist_required': True,
                    'default_note': '%s\n%s' % (msg.subject or '', msg.snippet or ''),
                    'default_customer_promise': 'Confermare fattibilita e tempi appena assegnata a grafica.',
                    'default_next_checkpoint': 'Recuperare brief minimo, contenuti, immagini e scadenza cliente.',
                    'default_ai_suggested_next_step': 'Crea task catalogo, collega cliente/azienda e assegna a Grafica con checklist.',
                },
            }
        if quick_action == 'quote':
            self._ensure_company_contacts_from_message(msg)
            return self._new_quote_from_message(msg)
        if quick_action == 'sample':
            self._ensure_company_contacts_from_message(msg)
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
            return self._notify('Thread archiviato', 'La conversazione e stata rimossa dalla sala controllo.', reload=True)
        return self._notify('Azione non disponibile', quick_action, 'warning')

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
        if quick_action == 'catalog':
            return self._new_operational_task(
                lead,
                quick_kind='catalog',
                forced_task_type='catalog_page',
                forced_department='graphics',
            )
        if quick_action == 'sample_task':
            return self._new_operational_task(
                lead,
                quick_kind='sample',
                forced_task_type='sample_shipment',
                forced_department='logistics',
            )
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
            'res.partner': 'Cliente',
            'sale.order': 'Quotazione',
            'cf.export.sample': 'Campionatura',
            'cf.project.shipment': 'Spedizione campioni',
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
        if model == 'res.partner' and quick_action == 'email':
            return {
                'type': 'ir.actions.client',
                'tag': 'casafolino_mail.compose_f8',
                'context': {
                    'default_partner_email': record.email or '',
                    'default_partner_id': record.id,
                    'default_subject': '',
                    'default_body': '<p>Buongiorno,</p><p></p>',
                },
            }
        if model == 'project.project' and quick_action == 'email' and hasattr(record, 'action_compose_email_f8'):
            return record.action_compose_email_f8()
        if model == 'project.project' and quick_action == 'reply' and hasattr(record, 'action_reply_last_email_f8'):
            return record.action_reply_last_email_f8()
        if quick_action == 'task':
            return self._new_operational_task(record)
        if quick_action == 'catalog':
            return self._new_operational_task(
                record,
                quick_kind='catalog',
                forced_task_type='catalog_page',
                forced_department='graphics',
            )
        if quick_action == 'sample_task':
            return self._new_operational_task(
                record,
                quick_kind='sample',
                forced_task_type='sample_shipment',
                forced_department='logistics',
            )
        if quick_action == 'followup7':
            return self._new_followup_task(record, fields.Date.context_today(self) + timedelta(days=7))
        if quick_action == 'today':
            return self._new_followup_task(record, fields.Date.context_today(self))
        return self._notify('Azione non disponibile', quick_action, 'warning')

    def _get_latest_commercial_threads(self, user):
        Mail = self.env['casafolino.mail.message']
        domain = [
            ('is_archived', '=', False),
            ('is_deleted', '=', False),
            ('state', 'in', ['new', 'review', 'keep', 'auto_keep', 'auto_attached']),
            '|',
            ('thread_id', '=', False),
            ('thread_id.is_snoozed', '=', False),
        ]
        if user and not user.has_group('base.group_system'):
            domain = ['|', ('assigned_user_ids', '=', False), ('assigned_user_ids', 'in', user.ids)] + domain
        messages = Mail.search(domain, order='email_date desc, id desc', limit=400)
        messages = messages.filtered(lambda msg: self._sender_decision_status(msg) != 'dismissed')
        latest_by_thread = {}
        for msg in messages:
            key = msg.thread_key or (msg.partner_id.id and 'partner:%s' % msg.partner_id.id) or msg.sender_email or msg.subject or msg.id
            if key not in latest_by_thread:
                latest_by_thread[key] = msg
        to_reply = []
        waiting = []
        for msg in latest_by_thread.values():
            if msg.direction_computed == 'inbound' or msg.ai_action_required:
                to_reply.append(msg)
            elif msg.direction_computed == 'outbound':
                waiting.append(msg)
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
            'sender_email': msg.sender_email or '',
            'sender_domain': msg.sender_domain or '',
            'sender_decision': self._sender_decision_status(msg),
            'suggested_partner': suggested_partner,
            'thread_id': msg.thread_id.id if msg.thread_id else False,
            'owner': ', '.join(msg.assigned_user_ids.mapped('name')) or '',
            'snippet': msg.snippet or '',
            'can_sample': bool(msg.sender_email or msg.lead_id),
            'account': msg.account_id.display_name if msg.account_id else '',
            'direction': msg.direction_computed or msg.direction or '',
            'urgency': msg.ai_urgency or '',
            'category': msg.ai_category or '',
            'language': msg.ai_language or '',
            'needs_action': bool(msg.ai_action_required),
            'has_attachments': bool(msg.attachment_ids),
            'attachment_count': len(msg.attachment_ids),
            'thread_count': msg.thread_id.message_count if msg.thread_id else 1,
            'suggested_action': self._mail_suggested_action(msg),
        })
        return item

    def _sender_preference(self, msg):
        if not msg.sender_email or not msg.account_id:
            return self.env['casafolino.mail.sender_preference']
        return self.env['casafolino.mail.sender_preference'].search([
            ('email', '=ilike', msg.sender_email),
            ('account_id', '=', msg.account_id.id),
        ], limit=1)

    def _sender_decision_status(self, msg):
        pref = self._sender_preference(msg)
        if pref:
            return pref.status or 'pending'
        if msg.state in ('keep', 'auto_keep', 'auto_attached'):
            return 'kept'
        return 'pending'

    def _ensure_sender_preference(self, msg):
        Preference = self.env['casafolino.mail.sender_preference']
        pref = self._sender_preference(msg)
        if pref or not msg.sender_email or not msg.account_id:
            return pref
        return Preference.create({
            'email': msg.sender_email.lower().strip(),
            'account_id': msg.account_id.id,
            'status': 'pending',
        })

    def _mail_suggested_action(self, msg):
        if not msg.lead_id:
            return 'Collega lead'
        if msg.direction_computed == 'inbound' or msg.ai_action_required:
            return 'Rispondi'
        return 'Attendi risposta'

    def _keep_sender_from_message(self, msg):
        pref = self._ensure_sender_preference(msg)
        if pref:
            pref.action_keep()
        if hasattr(msg, 'action_keep'):
            msg.action_keep()
        visible_count = self._sender_visible_message_count(msg)
        return self._notify(
            'Mittente tenuto',
            'Le prossime email resteranno nella Inbox CasaFolino. Thread visibili oggi: %s.' % visible_count,
            reload=True,
        )

    def _dismiss_sender_from_message(self, msg):
        pref = self._ensure_sender_preference(msg)
        if pref:
            pref.write({
                'status': 'dismissed',
                'decided_at': fields.Datetime.now(),
                'decided_by_id': self.env.uid,
                'last_dismissed_at': fields.Datetime.now(),
                'undo_token': False,
            })
        # Hide existing messages from this sender in the operating inbox; Gmail is not touched.
        if msg.sender_email:
            domain = [
                ('sender_email', '=ilike', msg.sender_email),
                ('is_deleted', '=', False),
            ]
            if msg.account_id:
                domain.append(('account_id', '=', msg.account_id.id))
            hidden = self.env['casafolino.mail.message'].search(domain, limit=200)
            hidden_count = len(hidden)
            hidden.write({'is_deleted': True})
        else:
            hidden_count = 0
        return self._notify(
            'Mittente scartato',
            'Nascoste %s mail dalla Inbox CasaFolino. Gmail resta invariato.' % hidden_count,
            reload=True,
        )

    def _sender_visible_message_count(self, msg):
        if not msg.sender_email:
            return 0
        domain = [
            ('sender_email', '=ilike', msg.sender_email),
            ('is_deleted', '=', False),
            ('is_archived', '=', False),
        ]
        if msg.account_id:
            domain.append(('account_id', '=', msg.account_id.id))
        return self.env['casafolino.mail.message'].search_count(domain)

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
        return {
            'type': 'ir.actions.client',
            'tag': 'casafolino_mail.compose_f8',
            'context': {
                'default_partner_email': partner_email,
                'default_subject': 'Re: %s' % (msg.subject or ''),
                'default_partner_id': partner.id if partner else False,
                'default_thread_id': msg.id,
                'default_thread_model': 'casafolino.mail.message',
            },
        }

    def _create_or_open_contact_from_message(self, msg):
        partner = msg.partner_id
        if not partner and msg.sender_email:
            partner = self.env['res.partner'].search([('email', '=ilike', msg.sender_email)], limit=1)
            if partner:
                msg.partner_id = partner.id
        if partner:
            return self._open_record(partner, 'Contatto')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuovo contatto da email',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_name': msg.sender_name or msg.sender_email or '',
                'default_email': msg.sender_email or '',
                'default_comment': 'Creato da mail CasaFolino: %s' % (msg.subject or ''),
                'default_is_company': False,
            },
        }

    @staticmethod
    def _email_domain(email):
        email = (email or '').strip().lower()
        if '@' not in email:
            return ''
        return email.rsplit('@', 1)[-1]

    @classmethod
    def _is_internal_email(cls, email):
        return cls._email_domain(email) in _INTERNAL_EMAIL_DOMAINS

    @staticmethod
    def _company_name_from_domain(domain):
        if not domain:
            return ''
        label = domain.split('.')[0].replace('-', ' ').replace('_', ' ').strip()
        return label.title() if label else domain

    def _message_external_participants(self, msg):
        participants = []
        seen = set()

        def add(name, email, role):
            email = (email or '').strip().lower()
            if not email or '@' not in email:
                return
            if self._is_internal_email(email):
                return
            if email in seen:
                return
            seen.add(email)
            participants.append({
                'name': (name or '').strip() or email.split('@')[0].replace('.', ' ').title(),
                'email': email,
                'role': role,
                'domain': self._email_domain(email),
            })

        add(msg.sender_name, msg.sender_email, 'from')
        for name, email in getaddresses([(msg.recipient_emails or '')]):
            add(name, email, 'to')
        for name, email in getaddresses([(msg.cc_emails or '')]):
            add(name, email, 'cc')
        return participants

    def _message_participant_context(self, msg):
        Partner = self.env['res.partner']
        rows = []
        target_company = self._find_company_for_message(msg)
        for person in self._message_external_participants(msg):
            partners = Partner.search([
                ('is_company', '=', False),
                ('email', '=ilike', person['email']),
            ], order='parent_id desc, id asc', limit=6)
            primary = partners[:1]
            company = primary.parent_id if primary and not primary.is_company else primary
            will_link = bool(primary and target_company and not primary.parent_id)
            rows.append({
                'name': person['name'],
                'email': person['email'],
                'role': person['role'],
                'domain': person['domain'],
                'partner_id': primary.id if primary else False,
                'company_id': company.id if company else False,
                'company_name': company.name if company else '',
                'exists': bool(primary),
                'duplicate_count': len(partners),
                'will_create': not bool(primary),
                'will_link': will_link,
            })
        return rows

    def _message_duplicate_partner_context(self, msg):
        Partner = self.env['res.partner']
        rows = []
        seen = set()
        for person in self._message_external_participants(msg):
            matches = Partner.search([('email', '=ilike', person['email'])], order='parent_id desc, id asc', limit=12)
            if len(matches) <= 1:
                continue
            for partner in matches:
                if partner.id in seen:
                    continue
                seen.add(partner.id)
                reasons = ['email uguale']
                score = 70
                if partner.parent_id:
                    reasons.append('azienda collegata')
                    score += 10
                if partner.phone or partner.mobile:
                    reasons.append('telefono presente')
                    score += 10
                if partner.company_name or partner.parent_id:
                    reasons.append('storico anagrafica')
                    score += 5
                rows.append({
                    'id': partner.id,
                    'name': partner.name or '',
                    'email': partner.email or '',
                    'phone': partner.phone or partner.mobile or '',
                    'company': partner.parent_id.name if partner.parent_id else '',
                    'is_company': bool(partner.is_company),
                    'score': min(score, 95),
                    'reasons': reasons[:4],
                })
        return rows

    def _message_context_mail_timeline(self, msg, partner=None):
        Mail = self.env['casafolino.mail.message']
        domain = [
            ('is_deleted', '=', False),
            ('is_archived', '=', False),
        ]
        if partner:
            domain.append(('partner_id', '=', partner.id))
        elif msg.sender_domain:
            domain.append(('sender_domain', '=', msg.sender_domain))
        elif msg.sender_email:
            domain.append(('sender_email', '=ilike', msg.sender_email))
        else:
            return []

        rows = []
        for mail in Mail.search(domain, order='email_date desc, id desc', limit=6):
            rows.append({
                'id': mail.id,
                'subject': mail.subject or 'Senza oggetto',
                'date': self._date_label(mail.email_date),
                'direction': mail.direction_computed or mail.direction or '',
                'sender': mail.sender_name or mail.sender_email or '',
                'snippet': mail.snippet or '',
                'is_current': mail.id == msg.id,
                'needs_action': bool(mail.ai_action_required),
                'urgency': mail.ai_urgency or '',
            })
        return rows

    def _message_context_open_tasks(self, msg, partner=None, leads=None, projects=None):
        Task = self.env['project.task']
        domains = []
        project_ids = [row['id'] for row in (projects or []) if row.get('id')]
        if project_ids:
            domains.append([('project_id', 'in', project_ids)])
        if msg.lead_id:
            lead_project = getattr(msg.lead_id, 'cf_project_id', False)
            if lead_project:
                domains.append([('project_id', '=', lead_project.id)])
        if partner:
            partner_projects = self.env['project.project'].search([('partner_id', '=', partner.id)], limit=20)
            if partner_projects:
                domains.append([('project_id', 'in', partner_projects.ids)])
        if not domains:
            return []

        domain = ['|'] * (len(domains) - 1)
        for part in domains:
            domain += part
        domain += [('stage_id.fold', '=', False)]

        rows = []
        for task in Task.search(domain, order='date_deadline asc, write_date desc', limit=5):
            rows.append(self._format_task_item(task))
        return rows


    def _find_company_for_message(self, msg, participants=None):
        Partner = self.env['res.partner']
        partner = msg.partner_id
        if partner and partner.exists():
            company = partner if partner.is_company else partner.parent_id
            if company:
                return company

        participants = participants or self._message_external_participants(msg)
        domains = []
        if msg.sender_domain and msg.sender_domain not in _INTERNAL_EMAIL_DOMAINS:
            domains.append(msg.sender_domain)
        domains.extend(p['domain'] for p in participants if p.get('domain'))

        for domain in dict.fromkeys(domains):
            company = Partner.search([
                ('is_company', '=', True),
                '|',
                ('website', 'ilike', domain),
                ('email', 'ilike', '@' + domain),
            ], limit=1)
            if company:
                return company
            company = Partner.search([
                ('is_company', '=', False),
                ('email', 'ilike', '@' + domain),
                ('parent_id', '!=', False),
            ], limit=1).parent_id
            if company:
                return company
        return Partner.browse()

    def _ensure_company_contacts_from_message(self, msg, company=None):
        Partner = self.env['res.partner']
        participants = self._message_external_participants(msg)
        company = company or self._find_company_for_message(msg, participants)
        if not company:
            domain = (participants[0]['domain'] if participants else msg.sender_domain) or ''
            company = Partner.create({
                'name': self._company_name_from_domain(domain) or msg.sender_name or msg.sender_email or 'Nuova azienda',
                'email': False,
                'website': 'https://%s' % domain if domain else False,
                'is_company': True,
                'comment': 'Creato da mail CasaFolino: %s' % (msg.subject or ''),
            })

        created = 0
        linked = 0
        primary_contact = False
        for person in participants:
            contact = Partner.search([
                ('is_company', '=', False),
                ('email', '=ilike', person['email']),
            ], limit=1)
            if contact:
                vals = {}
                if not contact.parent_id and not contact.is_company:
                    vals['parent_id'] = company.id
                if vals:
                    contact.write(vals)
                    linked += 1
            else:
                contact = Partner.create({
                    'name': person['name'],
                    'email': person['email'],
                    'parent_id': company.id,
                    'is_company': False,
                    'comment': 'Creato da mail CasaFolino: %s' % (msg.subject or ''),
                })
                created += 1
            if person['email'] == (msg.sender_email or '').lower().strip():
                primary_contact = contact

        if primary_contact:
            msg.partner_id = primary_contact.id
            msg.match_type = 'manual'
        elif company and not msg.partner_id:
            msg.partner_id = company.id
            msg.match_type = 'domain'

        return company, created, linked, len(participants)

    def _create_or_open_company_from_message(self, msg):
        company, created, linked, total = self._ensure_company_contacts_from_message(msg)
        action = self._open_record(company, 'Azienda')
        action.update({
            'display_notification': {
                'title': 'Azienda aggiornata',
                'message': 'Contatti esterni trovati: %s. Creati: %s. Agganciati: %s.' % (
                    total, created, linked
                ),
                'type': 'success',
            },
        })
        return action

    def _new_task_from_message(self, msg):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Task veloce da email',
            'res_model': 'cf.pipeline.quick.task.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_message_id': msg.id,
                'default_quick_kind': 'todo',
                'default_name': msg.subject or 'Follow-up commerciale',
                'default_task_type': 'followup',
                'default_department': 'sales',
                'default_note': '%s\n%s' % (msg.subject or '', msg.snippet or ''),
            },
        }

    def _new_task_from_lead(self, lead):
        project = getattr(lead, 'cf_project_id', False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Task veloce da lead',
            'res_model': 'cf.pipeline.quick.task.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_quick_kind': 'todo',
                'default_lead_id': lead.id,
                'default_name': 'Follow-up: %s' % (lead.name or lead.display_name),
                'default_project_id': project.id if project else False,
                'default_partner_id': lead.partner_id.id if lead.partner_id else False,
                'default_task_type': 'followup',
                'default_department': 'sales',
                'default_note': 'Verificare stato trattativa, prossima decisione cliente e prossima azione.',
            },
        }

    def _new_operational_task(self, record, quick_kind=None, forced_task_type=None, forced_department=None):
        partner = self._record_partner(record)
        project = record if record._name == 'project.project' else getattr(record, 'project_id', False)
        if record._name == 'crm.lead':
            project = getattr(record, 'cf_project_id', False)
        lead = record if record._name == 'crm.lead' else getattr(record, 'lead_id', False)
        if not lead and record._name == 'project.project' and 'cf_lead_ids' in record._fields:
            lead = record.cf_lead_ids[:1]
        task_type = forced_task_type or self._task_type_for_record(record)
        kind = quick_kind or ('sample' if task_type == 'sample_shipment' else 'todo')
        department = forced_department or self._task_department_for_record(record)
        title = self._task_title_for_record(record)
        note = self._task_description_for_record(record)
        if kind == 'catalog':
            title = 'Pagina catalogo personalizzata: %s' % (partner.display_name if partner else record.display_name)
            note = 'Creare pagina catalogo personalizzata: brief minimo, contenuti, immagini, owner grafica e scadenza cliente.'
        elif kind == 'sample':
            title = 'Campionatura cliente: %s' % (partner.display_name if partner else record.display_name)
            note = 'Gestire campionatura come mini-progetto: prodotti, indirizzo, spedizione, tracking TrackBot e reminder feedback.'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Task veloce',
            'res_model': 'cf.pipeline.quick.task.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_quick_kind': kind,
                'default_name': title,
                'default_lead_id': lead.id if lead else False,
                'default_project_id': project.id if project else False,
                'default_partner_id': partner.id if partner else False,
                'default_task_type': task_type,
                'default_department': department,
                'default_note': note,
                'default_is_mini_project': kind in ('catalog', 'sample'),
                'default_checklist_required': kind in ('catalog', 'sample'),
                'default_create_sample_shipment': kind == 'sample',
                'default_source_channel': 'manual',
                'default_urgency': 'high' if kind in ('catalog', 'sample') else 'normal',
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
            return {
                'type': 'ir.actions.act_window',
                'name': 'Task campionatura da email',
                'res_model': 'cf.pipeline.quick.task.wizard',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'new',
                'context': {
                    'default_message_id': msg.id,
                    'default_quick_kind': 'sample',
                    'default_name': 'Campionatura: %s' % (msg.subject or msg.sender_name or msg.sender_email or 'cliente'),
                    'default_task_type': 'sample_shipment',
                    'default_department': 'logistics',
                    'default_source_channel': 'mail',
                    'default_urgency': 'high',
                    'default_create_sample_shipment': True,
                    'default_is_mini_project': True,
                    'default_checklist_required': True,
                    'default_note': '%s\n%s' % (msg.subject or '', msg.snippet or ''),
                    'default_customer_promise': 'Inviare tracking appena disponibile.',
                    'default_next_checkpoint': 'Creare/collegare lead o dossier e verificare prodotti, indirizzo e feedback atteso.',
                    'default_ai_suggested_next_step': 'Crea task campionatura, collega cliente/azienda e trasforma in lead se la richiesta e commerciale.',
                },
            }
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
        if record._name == 'res.partner':
            return record
        return getattr(record, 'partner_id', False) or getattr(record, 'cf_partner_id', False)

    def _task_title_for_record(self, record):
        if record._name == 'res.partner':
            return 'Prossima azione cliente: %s' % (record.display_name or record.id)
        if record._name == 'sale.order':
            return 'Follow-up quotazione: %s' % (record.name or record.display_name)
        if record._name == 'cf.export.sample':
            return 'Sollecito feedback campione: %s' % (record.display_name or getattr(record, 'reference', ''))
        if record._name == 'project.project':
            return 'Prossima azione dossier: %s' % (record.name or record.display_name)
        return 'Task operativa: %s' % (record.display_name or record.id)

    def _task_description_for_record(self, record):
        if record._name == 'res.partner':
            return 'Aggiornare contesto cliente, prossima azione commerciale e collegamenti a lead/dossier.'
        if record._name == 'sale.order':
            return 'Verificare stato quotazione, prossima decisione cliente e possibilita ordine.'
        if record._name == 'cf.export.sample':
            return 'Verificare feedback campionatura, eventuali note qualita/logistica e prossima azione commerciale.'
        if record._name == 'project.project':
            return 'Aggiornare stato reparto, blocchi, prossima decisione e owner.'
        return ''

    def _task_type_for_record(self, record):
        if record._name in ('cf.export.sample', 'cf.project.shipment'):
            return 'sample_shipment'
        if record._name == 'sale.order':
            return 'quote'
        return 'todo'

    def _task_department_for_record(self, record):
        if record._name in ('cf.export.sample', 'cf.project.shipment'):
            return 'logistics'
        return 'sales'

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

    def _format_task_item(self, task):
        deadline = fields.Date.to_date(task.date_deadline) if task.date_deadline else False
        overdue = bool(deadline and deadline <= fields.Date.context_today(self))
        department = ''
        if 'cf_department' in task._fields and task.cf_department:
            department = dict(task._fields['cf_department'].selection).get(task.cf_department, task.cf_department)
        task_type = ''
        if 'cf_task_type' in task._fields and task.cf_task_type:
            task_type = dict(task._fields['cf_task_type'].selection).get(task.cf_task_type, task.cf_task_type)
        origin = ''
        if 'cf_task_origin' in task._fields and task.cf_task_origin:
            origin = dict(task._fields['cf_task_origin'].selection).get(task.cf_task_origin, task.cf_task_origin)
        return {
            'id': task.id,
            'model': task._name,
            'res_id': task.id,
            'title': task.name,
            'subtitle': task.project_id.name if task.project_id else '',
            'meta': self._date_label(deadline) if deadline else 'Senza scadenza',
            'tone': 'red' if overdue else 'amber' if getattr(task, 'cf_is_mini_project', False) else 'blue',
            'badges': self._compact([
                department,
                task_type,
                origin,
                'mini-progetto' if getattr(task, 'cf_is_mini_project', False) else False,
                'scaduta' if overdue else False,
            ]),
        }

    def _format_shipment_item(self, shipment, today):
        estimated = fields.Date.to_date(shipment.estimated_delivery) if shipment.estimated_delivery else False
        overdue = bool(estimated and estimated <= today and shipment.state not in ['delivered', 'feedback'])
        return {
            'id': shipment.id,
            'model': shipment._name,
            'res_id': shipment.id,
            'title': shipment.partner_id.display_name if shipment.partner_id else shipment.project_id.name,
            'subtitle': shipment.tracking_number or shipment.project_id.name,
            'meta': self._date_label(estimated) if estimated else 'Consegna non stimata',
            'tone': 'red' if overdue else 'green' if shipment.state == 'shipped' else 'amber',
            'next_action': self._shipment_next_action(shipment, estimated, overdue),
            'badges': self._compact([
                dict(shipment._fields['state'].selection).get(shipment.state, shipment.state) if shipment.state else False,
                shipment.carrier,
                'TrackBot' if shipment.trackbot_enabled else False,
                'feedback' if shipment.feedback_reminder_date else False,
            ]),
            'tracking_url': shipment.tracking_url or '',
        }

    def _shipment_next_action(self, shipment, estimated=False, overdue=False):
        if overdue:
            return 'Verificare consegna e sollecitare feedback cliente.'
        if shipment.state == 'draft':
            return 'Preparare collo e inserire tracking.'
        if shipment.state in ('ready', 'prepared'):
            return 'Spedire e comunicare tracking.'
        if shipment.state == 'shipped':
            return 'Monitorare tracking TrackBot.'
        if shipment.feedback_reminder_date:
            return 'Attendere feedback campione.'
        if estimated:
            return 'Consegna stimata %s.' % self._date_label(estimated)
        return 'Aggiornare stato spedizione.'

    def _format_ai_queue_item(self, msg, ai_brief=None):
        ai_brief = ai_brief or self._message_ai_brief(msg)
        return {
            'id': msg.id,
            'model': msg._name,
            'res_id': msg.id,
            'title': msg.partner_id.display_name if msg.partner_id else (msg.sender_name or msg.sender_email or 'Email'),
            'subtitle': msg.subject or '',
            'meta': ai_brief.get('decision_reason') or self._mail_suggested_action(msg),
            'tone': 'red' if ai_brief.get('risk') == 'high' else 'amber',
            'badges': self._compact([
                msg.ai_category,
                msg.ai_language,
                ai_brief.get('recommended_action'),
                'azione richiesta' if msg.ai_action_required else False,
            ]),
            'snippet': msg.snippet or '',
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

        emails = self.env['casafolino.mail.message'].search([('cf_project_id', '=', project.id)], order='create_date desc', limit=50)
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

class CfPipelineQuickTaskWizard(models.TransientModel):
    _name = 'cf.pipeline.quick.task.wizard'
    _description = 'Task veloce commerciale'

    quick_kind = fields.Selection([
        ('todo', 'To-do'),
        ('call', 'Chiamata'),
        ('catalog', 'Catalogo'),
        ('sample', 'Campione'),
    ], string='Tipo rapido', default='todo', required=True)
    name = fields.Char(string='Cosa devo ricordare?', required=True)
    note = fields.Text(string='Nota veloce')
    source_channel = fields.Selection([
        ('mail', 'Email'),
        ('call', 'Chiamata'),
        ('whatsapp', 'WhatsApp'),
        ('meeting', 'Riunione'),
        ('voice_ai', 'Voice AI'),
        ('manual', 'Manuale'),
    ], string='Origine', default='manual', required=True)
    urgency = fields.Selection([
        ('low', 'Bassa'),
        ('normal', 'Normale'),
        ('high', 'Alta'),
        ('critical', 'Critica'),
    ], string='Urgenza', default='normal', required=True)
    customer_promise = fields.Char(string='Promessa fatta al cliente')
    next_checkpoint = fields.Char(string='Checkpoint prossimo')
    partner_id = fields.Many2one('res.partner', string='Cliente')
    project_id = fields.Many2one('project.project', string='Dossier')
    lead_id = fields.Many2one('crm.lead', string='Lead pipeline')
    user_ids = fields.Many2many('res.users', string='Assegnato a')
    due_preset = fields.Selection([
        ('now', 'Subito'),
        ('today', 'Oggi'),
        ('tomorrow', 'Domani'),
        ('this_week', 'Questa settimana'),
        ('monday', 'Prossimo lunedi'),
        ('week', 'Entro 7 giorni'),
        ('custom', 'Data manuale'),
    ], string='Quando', default='today', required=True)
    deadline = fields.Date(string='Scadenza')
    task_type = fields.Selection([
        ('todo', 'To-do operativo'),
        ('catalog_page', 'Pagina catalogo'),
        ('sample_shipment', 'Campionatura / spedizione'),
        ('quote', 'Preventivo'),
        ('followup', 'Follow-up cliente'),
        ('data_update', 'Aggiornamento anagrafica'),
        ('issue', 'Problema / blocco'),
    ], string='Tipo richiesta', default='todo', required=True)
    department = fields.Selection([
        ('sales', 'Commerciale'),
        ('graphics', 'Grafica'),
        ('production', 'Produzione'),
        ('logistics', 'Logistica'),
        ('admin', 'Amministrazione'),
        ('management', 'Direzione'),
    ], string='Reparto owner', default='sales', required=True)
    is_mini_project = fields.Boolean(string='Mini-progetto')
    checklist_required = fields.Boolean(string='Checklist obbligatoria')
    create_sample_shipment = fields.Boolean(string='Crea spedizione/TrackBot')
    create_reminder = fields.Boolean(string='Crea reminder', default=True)
    ai_suggested_next_step = fields.Text(string='Prossimo passo')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        kind = self.env.context.get('default_quick_kind') or 'todo'
        today = fields.Date.context_today(self)
        res.update({
            'quick_kind': kind,
            'due_preset': self.env.context.get('default_due_preset') or 'today',
            'deadline': self.env.context.get('default_deadline') or today,
            'user_ids': [(6, 0, [self.env.uid])],
        })
        if kind == 'call':
            res.update({
                'name': 'Richiesta da chiamata cliente',
                'task_type': 'todo',
                'department': 'sales',
                'is_mini_project': True,
                'source_channel': 'call',
                'urgency': 'high',
                'due_preset': 'tomorrow',
                'deadline': today + timedelta(days=1),
                'note': 'Telefonata cliente: annotare richiesta, persona che ha chiamato, urgenza e reparti coinvolti.',
                'customer_promise': 'Richiamare / dare riscontro appena assegnata la richiesta.',
                'next_checkpoint': 'Assegnare owner e prima scadenza.',
                'ai_suggested_next_step': 'Collega cliente/dossier, assegna owner e imposta la prossima scadenza.',
            })
        elif kind == 'catalog':
            res.update({
                'name': 'Pagina catalogo personalizzata',
                'task_type': 'catalog_page',
                'department': 'graphics',
                'is_mini_project': True,
                'checklist_required': True,
                'source_channel': 'call',
                'urgency': 'high',
                'due_preset': 'tomorrow',
                'deadline': today + timedelta(days=1),
                'note': 'Cliente richiede una pagina catalogo personalizzata: raccogliere brief, contenuti, immagini e scadenza.',
                'customer_promise': 'Confermare fattibilita e tempi appena assegnata a grafica.',
                'next_checkpoint': 'Recuperare brief minimo e assegnare a Grafica.',
                'ai_suggested_next_step': 'Trasforma la richiesta in mini-progetto con checklist grafica e reminder al reparto.',
            })
        elif kind == 'sample':
            res.update({
                'name': 'Gestire campionatura cliente',
                'task_type': 'sample_shipment',
                'department': 'logistics',
                'is_mini_project': True,
                'checklist_required': True,
                'create_sample_shipment': True,
                'source_channel': 'manual',
                'urgency': 'high',
                'due_preset': 'tomorrow',
                'deadline': today + timedelta(days=1),
                'note': 'Campionatura da preparare/spedire: prodotti, indirizzo, tracking e feedback atteso.',
                'customer_promise': 'Inviare tracking appena disponibile.',
                'next_checkpoint': 'Verificare indirizzo, prodotti e data feedback attesa.',
                'ai_suggested_next_step': 'Crea o collega la spedizione, abilita TrackBot e programma reminder feedback.',
            })
        else:
            res.update({
                'name': self.env.context.get('default_name') or 'Nuova richiesta operativa',
                'task_type': self.env.context.get('default_task_type') or 'todo',
                'department': self.env.context.get('default_department') or 'sales',
                'note': self.env.context.get('default_note') or 'Richiesta creata dalla Console Commerciale.',
                'source_channel': self.env.context.get('default_source_channel') or 'manual',
                'urgency': self.env.context.get('default_urgency') or 'normal',
            })

        for field_name in (
            'name',
            'task_type',
            'department',
            'note',
            'source_channel',
            'urgency',
            'customer_promise',
            'next_checkpoint',
            'ai_suggested_next_step',
            'is_mini_project',
            'checklist_required',
            'create_sample_shipment',
            'create_reminder',
        ):
            context_key = 'default_%s' % field_name
            if context_key in self.env.context:
                res[field_name] = self.env.context.get(context_key)

        lead = self.env['crm.lead'].browse(self.env.context.get('default_lead_id')).exists()
        project = self.env['project.project'].browse(self.env.context.get('default_project_id')).exists()
        partner = self.env['res.partner'].browse(self.env.context.get('default_partner_id')).exists()
        message = self.env['casafolino.mail.message'].browse(self.env.context.get('default_message_id')).exists()
        if message:
            lead = lead or message.lead_id
            partner = partner or message.partner_id
            res.update({
                'name': message.subject or res.get('name'),
                'note': '%s\n%s' % (message.subject or '', message.snippet or ''),
                'quick_kind': kind if kind != 'todo' else 'todo',
                'task_type': 'followup' if kind != 'sample' else 'sample_shipment',
                'source_channel': 'mail',
                'urgency': 'high' if message.ai_urgency == 'high' or message.ai_action_required else 'normal',
                'next_checkpoint': self.env['cf.pipeline.control']._mail_suggested_action(message),
            })
        if lead:
            project = project or getattr(lead, 'cf_project_id', False)
            partner = partner or lead.partner_id
            res['lead_id'] = lead.id
        if project:
            res['project_id'] = project.id
            partner = partner or project.partner_id
        if partner:
            res['partner_id'] = partner.id
        return res

    @api.onchange('quick_kind')
    def _onchange_quick_kind(self):
        today = fields.Date.context_today(self)
        if self.quick_kind == 'call':
            self.name = self.name if self.name and self.name != 'Nuova richiesta operativa' else 'Richiesta da chiamata cliente'
            self.task_type = 'todo'
            self.department = 'sales'
            self.is_mini_project = True
            self.source_channel = 'call'
            self.urgency = 'high'
            self.due_preset = 'tomorrow'
            self.deadline = today + timedelta(days=1)
            self.checklist_required = self.checklist_required or False
            if not self.note:
                self.note = 'Telefonata cliente: annotare richiesta, persona che ha chiamato, urgenza e reparti coinvolti.'
            if not self.customer_promise:
                self.customer_promise = 'Richiamare / dare riscontro appena assegnata la richiesta.'
            if not self.next_checkpoint:
                self.next_checkpoint = 'Assegnare owner e prima scadenza.'
            if not self.ai_suggested_next_step:
                self.ai_suggested_next_step = 'Collega cliente/dossier, assegna owner e imposta la prossima scadenza.'
        elif self.quick_kind == 'catalog':
            self.name = self.name if self.name and self.name != 'Nuova richiesta operativa' else 'Pagina catalogo personalizzata'
            self.task_type = 'catalog_page'
            self.department = 'graphics'
            self.is_mini_project = True
            self.checklist_required = True
            self.source_channel = self.source_channel if self.source_channel != 'manual' else 'call'
            self.urgency = 'high'
            self.due_preset = 'tomorrow'
            self.deadline = today + timedelta(days=1)
            if not self.note:
                self.note = 'Cliente richiede una pagina catalogo personalizzata: raccogliere brief, contenuti, immagini e scadenza.'
            if not self.customer_promise:
                self.customer_promise = 'Confermare fattibilita e tempi appena assegnata a grafica.'
            if not self.next_checkpoint:
                self.next_checkpoint = 'Recuperare brief minimo e assegnare a Grafica.'
            if not self.ai_suggested_next_step:
                self.ai_suggested_next_step = 'Trasforma la richiesta in mini-progetto con checklist grafica e reminder al reparto.'
        elif self.quick_kind == 'sample':
            self.name = self.name if self.name and self.name != 'Nuova richiesta operativa' else 'Gestire campionatura cliente'
            self.task_type = 'sample_shipment'
            self.department = 'logistics'
            self.is_mini_project = True
            self.checklist_required = True
            self.create_sample_shipment = True
            self.source_channel = self.source_channel or 'manual'
            self.urgency = 'high'
            self.due_preset = 'tomorrow'
            self.deadline = today + timedelta(days=1)
            if not self.note:
                self.note = 'Campionatura da preparare/spedire: prodotti, indirizzo, tracking e feedback atteso.'
            if not self.customer_promise:
                self.customer_promise = 'Inviare tracking appena disponibile.'
            if not self.next_checkpoint:
                self.next_checkpoint = 'Verificare indirizzo, prodotti e data feedback attesa.'
            if not self.ai_suggested_next_step:
                self.ai_suggested_next_step = 'Crea o collega la spedizione, abilita TrackBot e programma reminder feedback.'
        else:
            self.task_type = self.task_type or 'todo'
            self.department = self.department or 'sales'

    @api.onchange('due_preset')
    def _onchange_due_preset(self):
        today = fields.Date.context_today(self)
        if self.due_preset in ('now', 'today'):
            self.deadline = today
        elif self.due_preset == 'tomorrow':
            self.deadline = today + timedelta(days=1)
        elif self.due_preset == 'this_week':
            self.deadline = today + timedelta(days=max(0, 4 - today.weekday()))
        elif self.due_preset == 'monday':
            days_until_monday = (7 - today.weekday()) % 7
            self.deadline = today + timedelta(days=days_until_monday or 7)
        elif self.due_preset == 'week':
            self.deadline = today + timedelta(days=7)

    def action_create_task(self):
        self.ensure_one()
        self._create_task()
        return {'type': 'ir.actions.act_window_close'}

    def action_create_and_open(self):
        self.ensure_one()
        task = self._create_task()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Task',
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _create_task(self):
        project = self._ensure_project_for_operational_task()
        vals = {
            'name': self.name,
            'project_id': project.id if project else False,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'date_deadline': self.deadline or False,
            'description': self._task_description_payload(),
            'user_ids': [(6, 0, self.user_ids.ids or [self.env.uid])],
            'cf_task_origin': self._task_origin_value(),
            'cf_task_type': self.task_type,
            'cf_department': self.department,
            'cf_customer_id': self.partner_id.id if self.partner_id else False,
            'cf_waiting_for': self._waiting_for_value(),
            'cf_is_mini_project': self.is_mini_project,
            'cf_checklist_required': self.checklist_required,
            'cf_source_note': self.note or '',
            'cf_ai_suggested_next_step': self.ai_suggested_next_step or '',
        }
        if self.urgency in ('high', 'critical') and 'priority' in self.env['project.task']._fields:
            vals['priority'] = '1'
        task = self.env['project.task'].create(vals)
        if self.create_sample_shipment and project:
            shipment = self.env['cf.project.shipment'].create({
                'project_id': project.id,
                'state': 'draft',
                'trackbot_enabled': True,
                'notes': self.note or '',
            })
            task.cf_shipment_id = shipment.id
        self._create_default_checklist(task)
        if self.create_reminder:
            self._schedule_task_reminders(task)
        task.message_post(body=self._task_chatter_note())
        return task

    def _ensure_project_for_operational_task(self):
        self.ensure_one()
        if self.project_id:
            return self.project_id
        if not self.create_sample_shipment:
            return self.env['project.project']

        project = self.env['project.project']
        if self.lead_id and hasattr(self.lead_id, '_ensure_project_360'):
            project = self.lead_id._ensure_project_360()
        elif self.partner_id:
            domain_parts = [[('partner_id', '=', self.partner_id.id)]]
            if 'cf_partner_id' in project._fields:
                domain_parts.append([('cf_partner_id', '=', self.partner_id.id)])
            domain = ['|'] * (len(domain_parts) - 1)
            for part in domain_parts:
                domain += part
            project = project.search(domain, order='write_date desc, id desc', limit=1)
            if not project:
                vals = {
                    'name': 'Campionatura - %s' % self.partner_id.display_name,
                    'partner_id': self.partner_id.id,
                    'user_id': self.env.user.id,
                }
                if 'cf_partner_id' in project._fields:
                    vals['cf_partner_id'] = self.partner_id.id
                if 'cf_project_type' in project._fields:
                    vals['cf_project_type'] = 'sample_client'
                if 'cf_status_dossier' in project._fields:
                    vals['cf_status_dossier'] = 'exploration'
                if 'cf_dossier_priority' in project._fields:
                    vals['cf_dossier_priority'] = 'medium'
                project = project.create(vals)
        if project:
            self.project_id = project.id
        return project

    def _task_origin_value(self):
        if self.source_channel in ('call', 'mail', 'voice_ai', 'manual'):
            return self.source_channel
        return 'manual'

    def _waiting_for_value(self):
        if self.department == 'graphics':
            return 'graphic'
        if self.department == 'production':
            return 'production'
        if self.department == 'logistics':
            return 'internal'
        if self.department in ('admin', 'management'):
            return 'internal'
        return 'client' if self.task_type in ('followup', 'data_update') else 'internal'

    def _schedule_task_reminders(self, task):
        deadline = self.deadline or fields.Date.context_today(self)
        summary = 'Seguire: %s' % self.name
        users = self.user_ids or self.env.user
        for user in users:
            task.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=deadline,
                user_id=user.id,
                summary=summary,
                note=self.next_checkpoint or self.customer_promise or self.note or '',
            )

    def _task_chatter_note(self):
        return ''.join([
            '<p><strong>Task salva-memoria creata dalla Console Commerciale.</strong></p>',
            '<p>%s</p>' % (self.note or ''),
            '<p><strong>Promessa:</strong> %s<br/><strong>Checkpoint:</strong> %s</p>' % (
                self.customer_promise or 'n.d.',
                self.next_checkpoint or 'n.d.',
            ),
        ])

    def _task_description_payload(self):
        parts = [
            '<p><strong>Richiesta</strong><br/>%s</p>' % (self.note or ''),
            '<ul>',
            '<li><strong>Origine:</strong> %s</li>' % dict(self._fields['source_channel'].selection).get(self.source_channel, self.source_channel),
            '<li><strong>Urgenza:</strong> %s</li>' % dict(self._fields['urgency'].selection).get(self.urgency, self.urgency),
            '<li><strong>Tipo:</strong> %s</li>' % dict(self._fields['task_type'].selection).get(self.task_type, self.task_type),
            '<li><strong>Reparto:</strong> %s</li>' % dict(self._fields['department'].selection).get(self.department, self.department),
        ]
        if self.deadline:
            parts.append('<li><strong>Scadenza:</strong> %s</li>' % fields.Date.to_string(self.deadline))
        if self.customer_promise:
            parts.append('<li><strong>Promessa al cliente:</strong> %s</li>' % self.customer_promise)
        if self.next_checkpoint:
            parts.append('<li><strong>Checkpoint:</strong> %s</li>' % self.next_checkpoint)
        if self.ai_suggested_next_step:
            parts.append('<li><strong>Prossimo passo AI:</strong> %s</li>' % self.ai_suggested_next_step)
        parts.append('</ul>')
        return ''.join(parts)

    def _create_default_checklist(self, task):
        if not self.checklist_required and self.task_type != 'sample_shipment':
            return
        if self.task_type == 'sample_shipment':
            items = [
                'Confermare indirizzo spedizione cliente',
                'Definire prodotti e quantita campioni',
                'Preparare collo e documenti',
                'Inserire tracking e abilitare TrackBot',
                'Programmare reminder feedback cliente',
            ]
        elif self.task_type == 'catalog_page':
            items = [
                'Raccogliere brief minimo dal cliente',
                'Recuperare logo, immagini e testi necessari',
                'Assegnare lavorazione a Grafica',
                'Preparare bozza pagina catalogo',
                'Inviare bozza al cliente e programmare feedback',
            ]
        elif self.task_type == 'quote':
            items = [
                'Verificare anagrafica e condizioni commerciali',
                'Raccogliere prodotti, quantita e destinazione',
                'Preparare preventivo',
                'Inviare preventivo al cliente',
                'Programmare follow-up preventivo',
            ]
        elif self.task_type == 'followup':
            items = [
                'Rileggere ultime mail e dossier cliente',
                'Preparare risposta o chiamata',
                'Registrare esito del contatto',
                'Aggiornare fase pipeline e prossima azione',
            ]
        elif self.task_type == 'data_update':
            items = [
                'Verificare azienda, contatto e indirizzi',
                'Aggiornare dati fiscali e commerciali',
                'Collegare eventuali contatti duplicati',
                'Confermare dati al commerciale owner',
            ]
        elif self.task_type == 'issue':
            items = [
                'Descrivere blocco e impatto cliente',
                'Assegnare reparto risolutore',
                'Definire workaround o risposta provvisoria',
                'Aggiornare cliente e prossima scadenza',
            ]
        else:
            items = [
                'Chiarire richiesta e risultato atteso',
                'Assegnare owner/reparto',
                'Confermare scadenza',
            ]
        self.env['cf.project.checklist.item'].create([
            {'task_id': task.id, 'name': name, 'sequence': (idx + 1) * 10}
            for idx, name in enumerate(items)
        ])


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

    message_id = fields.Many2one('casafolino.mail.message', string='Email', required=True, readonly=True)
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
        msg_id = self.env.context.get('default_message_id')
        if msg_id:
            msg = self.env['casafolino.mail.message'].browse(msg_id).exists()
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
        msg = self.message_id

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
            'name': self.project_name or msg.subject or 'Richiesta commerciale',
            'partner_id': partner.id,
            'email_from': msg.sender_email or self.partner_email,
            'user_id': self.user_id.id or self.env.user.id,
            'expected_revenue': self.expected_revenue,
            'source_email_id': msg.id,
            'description': msg.snippet or '',
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
        msg.write({
            'lead_id': lead.id,
            'cf_project_id': project.id if 'cf_project_id' in msg._fields else False,
            'partner_id': partner.id if not msg.partner_id else msg.partner_id.id,
            'state': 'keep',
            'triage_user_id': self.env.user.id,
            'triage_date': fields.Datetime.now(),
        })

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
        emails = self.env['casafolino.mail.message'].search([('cf_project_id', '=', project.id)], order='create_date desc', limit=50)
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

    message_id = fields.Many2one('casafolino.mail.message', string='Email', required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    apply_to_thread = fields.Boolean(string='Collega tutto il thread', default=True)
    set_followup = fields.Boolean(string='Pianifica follow-up', default=True)
    next_followup_date = fields.Date(string='Data follow-up')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        message = self.env['casafolino.mail.message'].browse(self.env.context.get('default_message_id')).exists()
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
        messages = self.message_id
        if self.apply_to_thread and self.message_id.thread_id:
            messages = self.env['casafolino.mail.message'].search([
                ('thread_id', '=', self.message_id.thread_id.id),
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

    preset = fields.Selection([
        ('tomorrow', 'Domani mattina'),
        ('weekend', 'Weekend'),
        ('next_week', 'Prossima settimana'),
        ('custom', 'Data personalizzata'),
    ], string='Quando', default='tomorrow', required=True)
    message_id = fields.Many2one('casafolino.mail.message', string='Email', required=True, readonly=True)
    thread_id = fields.Many2one('casafolino.mail.thread', string='Thread', readonly=True)
    wake_at = fields.Datetime(string='Rientra il', required=True)
    note = fields.Char(string='Nota')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        message = self.env['casafolino.mail.message'].browse(self.env.context.get('default_message_id')).exists()
        if message:
            res.update({
                'message_id': message.id,
                'thread_id': message.thread_id.id if message.thread_id else False,
                'preset': 'tomorrow',
                'wake_at': self._snooze_preset_datetime('tomorrow'),
                'note': 'Posticipato da Inbox Commerciale',
            })
        return res

    @api.onchange('preset')
    def _onchange_preset(self):
        for wizard in self:
            if wizard.preset and wizard.preset != 'custom':
                wizard.wake_at = wizard._snooze_preset_datetime(wizard.preset)

    def _snooze_preset_datetime(self, preset):
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        if preset == 'weekend':
            days = (5 - now.weekday()) % 7
            days = days or 7
            target = now + timedelta(days=days)
            return fields.Datetime.to_string(target.replace(hour=9, minute=0, second=0, microsecond=0))
        if preset == 'next_week':
            days = 7 - now.weekday()
            target = now + timedelta(days=days)
            return fields.Datetime.to_string(target.replace(hour=9, minute=0, second=0, microsecond=0))
        target = now + timedelta(days=1)
        return fields.Datetime.to_string(target.replace(hour=9, minute=0, second=0, microsecond=0))

    def action_snooze(self):
        self.ensure_one()
        if not self.thread_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thread richiesto',
                    'message': 'Questa email non ha ancora un thread V3.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        self.env['casafolino.mail.snooze'].create({
            'thread_id': self.thread_id.id,
            'user_id': self.env.user.id,
            'snooze_type': 'until_date',
            'wake_at': self.wake_at,
            'snoozed_at': fields.Datetime.now(),
            'note': self.note or 'Posticipato da Inbox Commerciale',
        })
        self.thread_id.write({'is_snoozed': True})
        self._schedule_partner_activity()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thread posticipato',
                'message': 'La conversazione rientra nella data scelta.',
                'type': 'success',
                'sticky': False,
            },
            'reload': True,
        }

    def _schedule_partner_activity(self):
        partner = self.message_id.partner_id
        if not partner:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return
        partner.activity_schedule(
            activity_type_id=activity_type.id,
            date_deadline=fields.Date.to_date(self.wake_at),
            user_id=self.env.user.id,
            summary='Riprendere email: %s' % (self.message_id.subject or self.message_id.sender_email or 'thread cliente'),
            note=self.note or 'Posticipato da Inbox Commerciale',
        )


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
