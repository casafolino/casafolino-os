import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CfPipelineControl(models.AbstractModel):
    _name = 'cf.pipeline.control'
    _description = 'CasaFolino Pipeline Control data provider'

    @api.model
    def get_dashboard_data(self, fair_id=False):
        today = fields.Date.context_today(self)
        user = self.env.user
        return {
            'kpis': self._safe_section('kpis', lambda: self._get_kpis(today, user), []),
            'lanes': self._safe_section('lanes', lambda: self._get_control_lanes(today, user), []),
            'followup': self._safe_section('followup', lambda: self._get_followup_data(today, user), {'kpis': [], 'columns': [], 'timeline': []}),
            'post_fair': self._safe_section('post_fair', lambda: self._get_post_fair_data(today, fair_id), {'kpis': [], 'columns': [], 'timeline': [], 'fair_options': []}),
            'pipeline': self._safe_section('pipeline', lambda: self._get_pipeline_data(today), []),
            'inbox': self._safe_section('inbox', lambda: self._get_inbox_data(user), {'to_reply': [], 'waiting_customer': []}),
            'dossiers': self._safe_section('dossiers', lambda: self._get_dossier_data(today), []),
        }

    def _safe_section(self, name, func, fallback):
        try:
            return func()
        except Exception:
            _logger.exception("Pipeline Control section %s failed", name)
            return fallback

    def _get_kpis(self, today, user):
        Mail = self.env['casafolino.mail.message']
        Lead = self.env['crm.lead']
        Sample = self.env['cf.export.sample']
        Project = self.env['project.project']

        to_reply_domain = self._mail_to_reply_domain(user)
        followup_domain = self._lead_followup_domain(today)
        hot_domain = self._hot_lead_domain()
        samples_domain = self._sample_feedback_overdue_domain(today)
        blocked_domain = self._blocked_project_domain()

        return [
            {
                'key': 'to_reply',
                'label': 'Da rispondere',
                'value': Mail.search_count(to_reply_domain),
                'hint': 'Email cliente con azione richiesta',
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
                'hint': 'Priorita alta o valore stimato',
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
            'timeline': self._followup_timeline(overdue | week | no_plan | waiting_leads, today),
        }

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
        Mail = self.env['casafolino.mail.message']
        Lead = self.env['crm.lead']
        Project = self.env['project.project']

        to_reply = Mail.search(self._mail_to_reply_domain(user), limit=6)
        followups = Lead.search(self._lead_followup_domain(today), order='cf_date_next_followup asc, date_deadline asc, id desc', limit=6)
        hot = Lead.search(self._hot_lead_domain(), order='expected_revenue desc, create_date desc', limit=6)
        blocked = Project.search(self._blocked_project_domain(), limit=6)

        return [
            {
                'key': 'to_reply',
                'title': 'Tocca a noi',
                'tone': 'red',
                'count': len(to_reply),
                'items': [self._format_mail_item(msg) for msg in to_reply],
            },
            {
                'key': 'followups',
                'title': 'Follow-up oggi',
                'tone': 'amber',
                'count': len(followups),
                'items': [self._format_lead_item(lead, today) for lead in followups],
            },
            {
                'key': 'hot',
                'title': 'Clienti caldi',
                'tone': 'green',
                'count': len(hot),
                'items': [self._format_lead_item(lead, today) for lead in hot],
            },
            {
                'key': 'blocked',
                'title': 'Bloccati',
                'tone': 'red',
                'count': len(blocked),
                'items': [self._format_project_item(project) for project in blocked],
            },
        ]

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
                {'label': 'Follow-up 1', 'value': len(first_followup), 'hint': '%s%% del totale' % pct(len(first_followup), len(leads))},
                {'label': 'Follow-up 2', 'value': len(second_followup), 'hint': '%s%% del totale' % pct(len(second_followup), len(leads))},
                {'label': 'Follow-up 3', 'value': len(third_followup), 'hint': '%s%% del totale' % pct(len(third_followup), len(leads))},
                {'label': 'Response rate', 'value': '%s%%' % pct(len(replied), len(leads)), 'hint': '%s risposte su %s lead' % (len(replied), len(leads))},
                {'label': 'Quotazioni', 'value': len(quoted), 'hint': 'Con valore atteso'},
                {'label': 'Campionature', 'value': len(samples), 'hint': 'Standard/custom'},
                {'label': 'Dossier', 'value': len(dossiers), 'hint': 'Lead promossi'},
            ],
            'columns': [
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
            leads = Lead.search([('stage_id', '=', stage.id)], order='expected_revenue desc, create_date desc', limit=5)
            columns.append({
                'id': stage.id,
                'title': stage.name,
                'count': Lead.search_count([('stage_id', '=', stage.id)]),
                'items': [self._format_lead_item(lead, today) for lead in leads],
            })
        return columns

    def _get_inbox_data(self, user):
        inbox, waiting = self._get_latest_commercial_threads(user)
        return {
            'to_reply': [self._format_mail_row(msg) for msg in inbox[:24]],
            'waiting_customer': [self._format_mail_row(msg) for msg in waiting[:24]],
        }

    @api.model
    def mail_quick_action(self, message_id, quick_action):
        msg = self.env['casafolino.mail.message'].browse(int(message_id)).exists()
        if not msg:
            return self._notify('Email non trovata', 'Il thread non e piu disponibile.', 'warning')

        if quick_action == 'open':
            return self._open_record(msg, 'Email')
        if quick_action == 'reply':
            return self._reply_from_message(msg)
        if quick_action == 'open_lead':
            if msg.lead_id:
                return self._open_record(msg.lead_id, 'Lead')
            return msg.action_create_lead()
        if quick_action == 'create_lead':
            return msg.action_create_lead()
        if quick_action == 'link_lead':
            return self._open_record(msg, 'Collega lead')
        if quick_action == 'task':
            return self._new_task_from_message(msg)
        if quick_action == 'quote':
            return self._new_quote_from_message(msg)
        if quick_action == 'sample':
            return self._new_sample_from_message(msg)
        if quick_action == 'snooze':
            return self._snooze_message_thread(msg)
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
        if quick_action == 'quote':
            return self._new_quote_from_lead(lead)
        if quick_action == 'task':
            return self._new_task_from_lead(lead)
        if quick_action == 'dossier':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Promuovi a dossier',
                'res_model': 'cf.pipeline.promote.dossier.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_lead_id': lead.id},
            }
        return self._notify('Azione non disponibile', quick_action, 'warning')

    def _get_latest_commercial_threads(self, user):
        Mail = self.env['casafolino.mail.message']
        domain = [
            ('is_archived', '=', False),
            ('is_deleted', '=', False),
            ('state', 'in', ['new', 'review', 'keep', 'auto_keep', 'auto_attached']),
            '|',
            ('partner_id', '!=', False),
            ('lead_id', '!=', False),
        ]
        if user and not user.has_group('base.group_system'):
            domain = ['|', ('assigned_user_ids', '=', False), ('assigned_user_ids', 'in', user.ids)] + domain
        messages = Mail.search(domain, order='email_date desc, id desc', limit=250)
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
        projects = Project.search(self._blocked_project_domain(), limit=10)
        return [self._format_project_detail(project, today) for project in projects]

    def _mail_to_reply_domain(self, user):
        domain = [
            ('direction_computed', '=', 'inbound'),
            ('is_archived', '=', False),
            ('is_deleted', '=', False),
            ('state', 'in', ['new', 'review', 'keep', 'auto_keep', 'auto_attached']),
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
            ('state', 'not in', ['done', 'cancelled']),
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
        item.update({
            'lead': msg.lead_id.display_name if msg.lead_id else '',
            'lead_id': msg.lead_id.id if msg.lead_id else False,
            'partner_id': msg.partner_id.id if msg.partner_id else False,
            'thread_id': msg.thread_id.id if msg.thread_id else False,
            'owner': ', '.join(msg.assigned_user_ids.mapped('name')) or '',
            'snippet': msg.snippet or '',
            'can_sample': bool(msg.lead_id),
        })
        return item

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

    def _snooze_message_thread(self, msg):
        if not msg.thread_id:
            return self._notify('Thread richiesto', 'Questa email non ha ancora un thread V3.', 'warning')
        wake_at = fields.Datetime.now() + timedelta(days=1)
        self.env['casafolino.mail.snooze'].create({
            'thread_id': msg.thread_id.id,
            'user_id': self.env.user.id,
            'snooze_type': 'until_date',
            'wake_at': wake_at,
            'snoozed_at': fields.Datetime.now(),
            'note': 'Posticipato da Inbox Commerciale',
        })
        msg.thread_id.write({'is_snoozed': True})
        return self._notify('Thread posticipato', 'Rientra domani nella gestione commerciale.', reload=True)

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

    def _format_project_detail(self, project, today):
        return {
            'id': project.id,
            'name': project.name,
            'partner': self._project_partner_name(project),
            'status': self._project_status(project),
            'blocker': self._project_blocker_label(project),
            'target_date': self._date_label(getattr(project, 'cf_target_date', False) or getattr(project, 'date', False)),
            'departments': self._project_departments(project),
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
