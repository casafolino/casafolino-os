import json
import logging
import re
from datetime import timedelta

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

_SUBJECT_PREFIX_RE = re.compile(
    r'^\s*(Re|R|Fwd|FW|Fw|AW|SV|VS|RE|Rif|RIF)\s*:\s*',
    re.IGNORECASE,
)


def _normalize_subject(subject):
    if not subject:
        return ''
    cleaned = _SUBJECT_PREFIX_RE.sub('', subject)
    while _SUBJECT_PREFIX_RE.search(cleaned):
        cleaned = _SUBJECT_PREFIX_RE.sub('', cleaned)
    return cleaned.strip()


def _hotness_emoji(tier):
    return {
        'hot': '\U0001f525',
        'warm': '\U0001f536',
        'active': '\U0001f4bc',
        'cold': '\U0001f9ca',
        'dormant': '\u26ab',
    }.get(tier, '')


class MailV3Controller(http.Controller):

    def _get_user_account_ids(self):
        """Return IDs of accounts owned by current user."""
        return request.env['casafolino.mail.account'].search([
            ('responsible_user_id', '=', request.env.uid),
            ('active', '=', True),
        ]).ids

    def _check_thread_ownership(self, thread):
        """Return True if thread belongs to current user's accounts."""
        return thread.exists() and thread.account_id.id in self._get_user_account_ids()

    # ── Thread List ──────────────────────────────────────────────────

    @http.route('/cf/mail/v3/threads/list', type='json', auth='user')
    def threads_list(self, **kw):
        user_accounts = self._get_user_account_ids()
        if not user_accounts:
            return {'threads': [], 'total': 0}

        account_ids = kw.get('account_ids')
        state = kw.get('state', 'keep')
        limit = min(int(kw.get('limit', 50)), 200)
        offset = int(kw.get('offset', 0))
        filters = kw.get('filters', {})
        folder = kw.get('folder')

        # Intersect requested accounts with user's own accounts
        if account_ids:
            account_ids = [a for a in account_ids if a in user_accounts]
        else:
            account_ids = user_accounts

        domain = [('account_id', 'in', account_ids)]

        if not filters.get('show_archived'):
            domain.append(('is_archived', '=', False))

        # Hide snoozed threads by default (unless viewing snoozed folder)
        if folder != 'snoozed':
            domain.append(('is_snoozed', '=', False))

        # ── V12.6: Build dismissed sender set for filtering ──
        dismissed_emails = set()
        Preference = request.env['casafolino.mail.sender_preference']
        dismissed_prefs = Preference.search([
            ('account_id', 'in', account_ids),
            ('status', '=', 'dismissed'),
        ])
        for dp in dismissed_prefs:
            dismissed_emails.add((dp.email or '').lower().strip())

        # Build pending sender set for badge
        pending_emails = set()
        pending_prefs = Preference.search([
            ('account_id', 'in', account_ids),
            ('status', '=', 'pending'),
        ])
        for pp in pending_prefs:
            pending_emails.add((pp.email or '').lower().strip())

        # ── V15 FIX Bug B: Pre-filter dismissed threads in SQL domain ──
        # Instead of post-filtering (which breaks pagination), exclude
        # thread IDs where ALL inbound senders are dismissed upfront.
        if dismissed_emails:
            dismissed_list = list(dismissed_emails)
            # Find threads where ALL inbound messages have dismissed senders
            # (and none have pending senders)
            request.env.cr.execute("""
                SELECT DISTINCT m.thread_id
                FROM casafolino_mail_message m
                WHERE m.account_id IN %s
                  AND m.is_deleted = false
                  AND m.thread_id IS NOT NULL
                  AND (m.direction = 'inbound' OR m.direction_computed = 'inbound')
                  AND LOWER(TRIM(m.sender_email)) = ANY(%s)
                  AND m.thread_id NOT IN (
                      -- Exclude threads that have at least one non-dismissed inbound sender
                      SELECT DISTINCT m2.thread_id
                      FROM casafolino_mail_message m2
                      WHERE m2.account_id IN %s
                        AND m2.is_deleted = false
                        AND m2.thread_id IS NOT NULL
                        AND (m2.direction = 'inbound' OR m2.direction_computed = 'inbound')
                        AND LOWER(TRIM(m2.sender_email)) NOT IN %s
                  )
                  AND m.thread_id NOT IN (
                      -- Exclude threads that have pending senders
                      SELECT DISTINCT m3.thread_id
                      FROM casafolino_mail_message m3
                      WHERE m3.account_id IN %s
                        AND m3.is_deleted = false
                        AND m3.thread_id IS NOT NULL
                        AND LOWER(TRIM(m3.sender_email)) IN %s
                  )
            """, (
                tuple(account_ids), dismissed_list,
                tuple(account_ids), tuple(dismissed_list),
                tuple(account_ids), tuple(pending_emails) if pending_emails else ('__none__',),
            ))
            dismissed_thread_ids = [r[0] for r in request.env.cr.fetchall()]
            if dismissed_thread_ids:
                domain.append(('id', 'not in', dismissed_thread_ids))

        # Folder filters
        if folder == 'starred':
            starred_msgs = request.env['casafolino.mail.message'].search([
                ('is_starred', '=', True), ('is_deleted', '=', False),
            ])
            starred_thread_ids = starred_msgs.mapped('thread_id').ids
            domain.append(('id', 'in', starred_thread_ids))
        elif folder == 'sent':
            domain.append(('has_outbound', '=', True))
        elif folder == 'snoozed':
            domain = [d for d in domain if d[0] != 'is_snoozed']
            domain.append(('is_snoozed', '=', True))
        elif folder == 'trash':
            domain = [d for d in domain if d[0] != 'is_archived']
            domain.append(('is_archived', '=', True))

        # V14: Folder-based filtering (numeric folder_id)
        folder_id = kw.get('folder_id')
        if folder_id:
            folder_id = int(folder_id)
            folder_msgs = request.env['casafolino.mail.message'].search([
                ('folder_id', '=', folder_id),
                ('is_deleted', '=', False),
            ])
            folder_thread_ids = folder_msgs.mapped('thread_id').ids
            domain.append(('id', 'in', folder_thread_ids))

        threads = request.env['casafolino.mail.thread'].search(
            domain, limit=limit, offset=offset,
            order='last_message_date desc, id desc')
        total = request.env['casafolino.mail.thread'].search_count(domain)

        result = []
        for t in threads:
            try:
                participants = json.loads(t.participant_emails or '[]')
            except (json.JSONDecodeError, TypeError):
                participants = []

            company_domain = t.account_id.company_domain or 'casafolino.com'
            external = [p for p in participants if company_domain not in p]
            main_participant = external[0] if external else (participants[0] if participants else '')

            last_msg = request.env['casafolino.mail.message'].search([
                ('thread_id', '=', t.id),
                ('is_deleted', '=', False),
            ], order='email_date desc', limit=1)

            preview = ''
            if last_msg and last_msg.snippet:
                preview = last_msg.snippet[:100]
            elif last_msg and last_msg.body_plain:
                preview = last_msg.body_plain[:100]

            silent_days = 0
            if t.last_message_date:
                from odoo import fields as odoo_fields
                delta = odoo_fields.Datetime.now() - t.last_message_date
                silent_days = delta.days

            hotness_score = t.hotness_snapshot or 0
            hotness_tier = ''
            hotness_emoji_str = ''
            if hotness_score >= 80:
                hotness_tier = 'hot'
            elif hotness_score >= 60:
                hotness_tier = 'warm'
            elif hotness_score >= 40:
                hotness_tier = 'active'
            elif hotness_score >= 20:
                hotness_tier = 'cold'
            elif hotness_score > 0:
                hotness_tier = 'dormant'
            if hotness_tier:
                hotness_emoji_str = _hotness_emoji(hotness_tier)

            att_count = 0
            if t.has_attachments:
                att_count = request.env['ir.attachment'].search_count([
                    ('res_model', '=', 'casafolino.mail.message'),
                    ('res_id', 'in', t.message_ids.ids),
                ])

            lead_open = False
            if t.partner_ids:
                lead = request.env['crm.lead'].sudo().search([
                    ('partner_id', 'in', t.partner_ids.ids),
                    ('active', '=', True),
                    ('stage_id.is_won', '=', False),
                ], limit=1)
                lead_open = bool(lead)

            # Badge data: keep state and lead name from messages
            active_msgs = t.message_ids.filtered(lambda m: not m.is_deleted)
            has_keep_message = any(
                m.state in ('keep', 'auto_keep') for m in active_msgs
            )
            lead_name = ''
            for m in active_msgs:
                if m.lead_id:
                    lead_name = m.lead_id.name or ''
                    break

            # V12.8: Check pending sender badge (dismissed filter moved to SQL pre-query in V15)
            has_pending_sender = False
            for m in active_msgs:
                se = (m.sender_email or '').lower().strip()
                if se in pending_emails:
                    has_pending_sender = True
                    break

            result.append({
                'id': t.id,
                'subject': t.subject or '',
                'subject_normalized': t.subject_normalized or '',
                'account_id': t.account_id.id,
                'account_name': t.account_id.name or '',
                'main_participant': main_participant,
                'message_count': t.message_count,
                'unread_count': t.unread_count,
                'is_read': t.unread_count == 0,
                'has_attachments': t.has_attachments,
                'is_archived': t.is_archived,
                'first_message_date': str(t.first_message_date) if t.first_message_date else '',
                'last_message_date': str(t.last_message_date) if t.last_message_date else '',
                'preview': preview,
                'silent_days': silent_days,
                'hotness_score': hotness_score,
                'hotness_tier': hotness_tier,
                'hotness_emoji': hotness_emoji_str,
                'attachment_count': att_count,
                'lead_open': lead_open,
                'has_keep_message': has_keep_message,
                'lead_name': lead_name,
                'partner_ids': t.partner_ids.ids,
                'has_pending_sender': has_pending_sender,
            })

        has_more = (offset + len(result)) < total
        return {'threads': result, 'total': total, 'has_more': has_more}

    # ── Thread Messages ──────────────────────────────────────────────

    @http.route('/cf/mail/v3/thread/<int:thread_id>/messages', type='json', auth='user')
    def thread_messages(self, thread_id, **kw):
        thread = request.env['casafolino.mail.thread'].browse(thread_id)
        if not self._check_thread_ownership(thread):
            return {'messages': []}

        messages = request.env['casafolino.mail.message'].search([
            ('thread_id', '=', thread_id),
            ('is_deleted', '=', False),
        ], order='email_date asc')

        result = []
        for m in messages:
            result.append({
                'id': m.id,
                'subject': m.subject or '',
                'sender_email': m.sender_email or '',
                'sender_name': m.sender_name or '',
                'recipient_emails': m.recipient_emails or '',
                'cc_emails': m.cc_emails or '',
                'direction': m.direction or 'inbound',
                'direction_computed': m.direction_computed or m.direction or 'inbound',
                'email_date': str(m.email_date) if m.email_date else '',
                'body_html': m.body_html or '',
                'body_plain': m.body_plain or '',
                'is_read': m.is_read,
                'is_starred': m.is_starred,
                'is_archived': m.is_archived,
                'intent_detected': getattr(m, 'intent_detected', '') or '',
                'partner_id': m.partner_id.id if m.partner_id else False,
                'partner_name': m.partner_id.name if m.partner_id else '',
                'attachment_ids': [{'id': a.id, 'name': a.name, 'mimetype': a.mimetype or ''}
                                    for a in m.attachment_ids],
                'message_id_rfc': m.message_id_rfc or '',
            })

        return {'messages': result}

    @http.route('/cf/mail/v3/thread/<int:thread_id>/mark_all_read', type='json', auth='user')
    def thread_mark_all_read(self, thread_id, **kw):
        thread = request.env['casafolino.mail.thread'].browse(thread_id)
        if not self._check_thread_ownership(thread):
            return {'success': False, 'error': 'Not your thread'}
        messages = request.env['casafolino.mail.message'].search([
            ('thread_id', '=', thread_id),
            ('is_read', '=', False),
        ])
        messages.action_mark_read()
        return {'success': True}

    # ── Message Actions ──────────────────────────────────────────────

    @http.route('/cf/mail/v3/message/<int:msg_id>/<string:action>', type='json', auth='user')
    def message_action(self, msg_id, action, **kw):
        msg = request.env['casafolino.mail.message'].browse(msg_id)
        if not msg.exists():
            return {'success': False, 'error': 'Message not found'}
        if msg.account_id.id not in self._get_user_account_ids():
            return {'success': False, 'error': 'Not your message'}

        action_map = {
            'mark_read': 'action_mark_read',
            'mark_unread': 'action_mark_unread',
            'archive': 'action_archive',
            'unarchive': 'action_unarchive',
            'delete_soft': 'action_delete_soft',
            'restore': 'action_restore',
            'toggle_star': 'action_toggle_star',
        }

        method = action_map.get(action)
        if not method:
            return {'success': False, 'error': 'Invalid action'}

        getattr(msg, method)()
        return {'success': True}

    # ── Delete Single Message ───────────────────────────────────────

    @http.route('/cf/mail/v3/message/delete_single', type='json', auth='user')
    def message_delete_single(self, **kw):
        message_id = int(kw.get('message_id', 0))
        if not message_id:
            return {'success': False, 'error': 'message_id required'}
        user_accounts = self._get_user_account_ids()
        msg = request.env['casafolino.mail.message'].sudo().search([
            ('id', '=', message_id),
            ('account_id', 'in', user_accounts),
        ], limit=1)
        if not msg:
            return {'success': False, 'error': 'Message not found or no access'}
        thread = msg.thread_id
        msg.unlink()
        thread_deleted = False
        if thread and thread.exists() and not thread.message_ids:
            thread.unlink()
            thread_deleted = True
        return {'success': True, 'thread_deleted': thread_deleted}

    # ── Draft CRUD ───────────────────────────────────────────────────

    @http.route('/cf/mail/v3/draft/create', type='json', auth='user')
    def draft_create(self, **kw):
        account_id = kw.get('account_id')
        in_reply_to_id = kw.get('in_reply_to_message_id')
        mode = kw.get('mode', 'new')

        if not account_id:
            account = request.env['casafolino.mail.account'].search([
                ('responsible_user_id', '=', request.env.uid),
                ('active', '=', True),
            ], limit=1)
            if account:
                account_id = account.id
            else:
                return {'success': False, 'error': 'No account found'}

        vals = {
            'account_id': account_id,
            'user_id': request.env.uid,
        }

        prefilled = {'to': '', 'cc': '', 'subject': '', 'body_html': ''}

        if in_reply_to_id and mode in ('reply', 'reply_all', 'forward'):
            orig = request.env['casafolino.mail.message'].browse(in_reply_to_id)
            if orig.exists():
                vals['in_reply_to_message_id'] = orig.id

                if mode == 'reply':
                    if orig.direction == 'inbound':
                        prefilled['to'] = orig.sender_email or ''
                    else:
                        prefilled['to'] = orig.recipient_emails or ''
                    prefilled['subject'] = 'Re: ' + _normalize_subject(orig.subject or '')

                elif mode == 'reply_all':
                    if orig.direction == 'inbound':
                        prefilled['to'] = orig.sender_email or ''
                        prefilled['cc'] = orig.cc_emails or ''
                    else:
                        prefilled['to'] = orig.recipient_emails or ''
                        prefilled['cc'] = orig.cc_emails or ''
                    prefilled['subject'] = 'Re: ' + _normalize_subject(orig.subject or '')

                elif mode == 'forward':
                    prefilled['to'] = ''
                    prefilled['subject'] = 'Fwd: ' + _normalize_subject(orig.subject or '')

                quote_date = str(orig.email_date)[:16] if orig.email_date else ''
                quote_from = orig.sender_name or orig.sender_email or ''
                prefilled['body_html'] = (
                    '<br><br>'
                    '<div style="border-left:2px solid #ccc;padding-left:12px;margin-left:4px;color:#666;">'
                    '<p>Il %s, %s ha scritto:</p>'
                    '%s'
                    '</div>' % (quote_date, quote_from, orig.body_html or orig.body_plain or '')
                )

        sig = request.env['casafolino.mail.signature'].search([
            ('account_id', '=', account_id),
            ('is_default', '=', True),
        ], limit=1)
        if sig:
            vals['signature_id'] = sig.id

        vals['to_emails'] = prefilled['to']
        vals['cc_emails'] = prefilled['cc']
        vals['subject'] = prefilled['subject']
        vals['body_html'] = prefilled['body_html']

        draft = request.env['casafolino.mail.draft'].create(vals)

        return {
            'draft_id': draft.id,
            'prefilled': prefilled,
        }

    @http.route('/cf/mail/v3/draft/<int:draft_id>/autosave', type='json', auth='user')
    def draft_autosave(self, draft_id, **kw):
        draft = request.env['casafolino.mail.draft'].browse(draft_id)
        if not draft.exists():
            return {'success': False}

        vals = {}
        for field in ('to_emails', 'cc_emails', 'bcc_emails', 'subject', 'body_html'):
            if field in kw:
                vals[field] = kw[field]
        if 'attachment_ids' in kw:
            vals['attachment_ids'] = [(6, 0, kw['attachment_ids'])]

        vals['auto_saved_at'] = request.env['casafolino.mail.draft']._fields['auto_saved_at'].now()
        draft.write(vals)
        return {'success': True}

    @http.route('/cf/mail/v3/draft/<int:draft_id>/send', type='json', auth='user')
    def draft_send(self, draft_id, **kw):
        draft = request.env['casafolino.mail.draft'].browse(draft_id)
        if not draft.exists():
            return {'success': False, 'error': 'Draft not found'}
        return draft.action_send()

    # ── Sidebar 360 ──────────────────────────────────────────────────

    @http.route('/cf/mail/v3/partner/<int:partner_id>/sidebar_360', type='json', auth='user')
    def partner_sidebar_360(self, partner_id, **kw):
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {}

        company = partner if partner.is_company else partner.parent_id
        person = partner if not partner.is_company else False

        # ── Company block ──
        company_data = {}
        intel = None
        if company and company.exists():
            intel = request.env['casafolino.partner.intelligence'].search([
                ('partner_id', '=', company.id)
            ], limit=1)
            hotness_score = intel.hotness_score if intel else 0
            hotness_tier = intel.hotness_tier if intel else ''
            hotness_emoji_str = _hotness_emoji(hotness_tier) if hotness_tier else ''

            company_data = {
                'id': company.id,
                'name': company.name or '',
                'country': company.country_id.name if company.country_id else '',
                'country_flag': company.country_id.code.lower() if company.country_id and company.country_id.code else '',
                'vat': company.vat or '',
                'website': company.website or '',
                'hotness_score': hotness_score,
                'hotness_tier': hotness_tier,
                'hotness_emoji': hotness_emoji_str,
                'tags': [{'id': t.id, 'name': t.name} for t in (company.category_id or [])],
            }

        # ── Person block ──
        person_data = {}
        if person and person.exists():
            person_data = {
                'id': person.id,
                'name': person.name or '',
                'email': person.email or '',
                'phone': person.phone or person.mobile or '',
                'role': person.function or (person.cf_job_title if hasattr(person, 'cf_job_title') else ''),
                'image_url': '/web/image/res.partner/%s/avatar_128' % person.id,
            }

        # ── NBA block ──
        nba_data = {}
        if intel and not intel.pinned_ignore and intel.nba_text:
            nba_data = {
                'nba_text': intel.nba_text,
                'nba_urgency': intel.nba_urgency or 'info',
                'nba_rule_id': intel.nba_rule_id or 0,
                'nba_from_llm': intel.nba_from_llm or False,
                'partner_id': company.id if company else partner_id,
            }

        # ── Relation block ──
        p_ids = [partner_id]
        if company:
            p_ids += company.child_ids.ids
            p_ids.append(company.id)
        p_ids = list(set(p_ids))

        msg_domain = [
            ('partner_id', 'in', p_ids),
            ('state', 'in', ['keep', 'auto_keep']),
        ]
        total_emails = request.env['casafolino.mail.message'].search_count(msg_domain)
        first_msg = request.env['casafolino.mail.message'].search(
            msg_domain, order='email_date asc', limit=1)
        last_reply = request.env['casafolino.mail.message'].search(
            msg_domain + [('direction', '=', 'outbound')],
            order='email_date desc', limit=1)

        relation_data = {
            'first_contact': str(first_msg.email_date)[:10] if first_msg and first_msg.email_date else '',
            'total_emails': total_emails,
            'last_reply': str(last_reply.email_date)[:10] if last_reply and last_reply.email_date else '',
        }

        # ── Business block ──
        business_data = {}
        try:
            from datetime import date
            year_start = date(date.today().year, 1, 1)
            invoices = request.env['account.move'].sudo().search([
                ('partner_id', 'in', p_ids),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', year_start),
            ])
            ytd_revenue = sum(inv.amount_untaxed_signed for inv in invoices)

            open_orders = request.env['sale.order'].sudo().search_count([
                ('partner_id', 'in', p_ids),
                ('state', 'in', ['sale', 'draft']),
            ])

            overdue = request.env['account.move'].sudo().search_count([
                ('partner_id', 'in', p_ids),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('invoice_date_due', '<', date.today()),
            ])

            business_data = {
                'ytd_revenue': round(ytd_revenue, 2),
                'open_orders': open_orders,
                'overdue': overdue,
            }
        except Exception as e:
            _logger.warning('[mail v3] Business block error: %s', e)
            business_data = {'ytd_revenue': 0, 'open_orders': 0, 'overdue': 0}

        # ── Pipeline block ──
        pipeline_data = []
        try:
            leads = request.env['crm.lead'].sudo().search([
                ('partner_id', 'in', p_ids),
                ('active', '=', True),
            ], order='expected_revenue desc', limit=5)
            for lead in leads:
                pipeline_data.append({
                    'id': lead.id,
                    'name': lead.name or '',
                    'stage': lead.stage_id.name if lead.stage_id else '',
                    'revenue': lead.expected_revenue or 0,
                    'probability': lead.probability or 0,
                    'is_won': lead.stage_id.is_won if lead.stage_id else False,
                })
        except Exception as e:
            _logger.warning('[mail v3] Pipeline block error: %s', e)

        # ── Timeline block ──
        timeline_data = []
        try:
            timeline_msgs = request.env['casafolino.mail.message'].search([
                ('partner_id', 'in', p_ids),
                ('state', 'in', ['keep', 'auto_keep']),
                ('is_deleted', '=', False),
            ], order='email_date desc', limit=5)
            for m in timeline_msgs:
                timeline_data.append({
                    'id': m.id,
                    'subject': (m.subject or '')[:60],
                    'date': str(m.email_date)[:10] if m.email_date else '',
                    'direction': m.direction or 'inbound',
                    'intent': getattr(m, 'intent_detected', '') or '',
                })
        except Exception as e:
            _logger.warning('[mail v3] Timeline block error: %s', e)

        # ── Notes block ──
        notes_data = ''
        if partner.exists():
            target = company if company and company.exists() else partner
            notes_data = target.mv3_private_notes or '' if hasattr(target, 'mv3_private_notes') else ''

        # ── Quick actions ──
        quick_actions = [
            {'key': 'reply', 'label': 'Rispondi', 'icon': 'fa-reply'},
            {'key': 'new_lead', 'label': 'Nuovo lead', 'icon': 'fa-bullseye'},
            {'key': 'new_activity', 'label': 'Crea attivit\u00e0', 'icon': 'fa-calendar-plus-o'},
            {'key': 'new_order', 'label': 'Nuovo ordine', 'icon': 'fa-shopping-cart'},
            {'key': 'open_partner', 'label': 'Apri partner', 'icon': 'fa-user'},
        ]

        return {
            'company': company_data,
            'person': person_data,
            'nba': nba_data,
            'relation': relation_data,
            'business': business_data,
            'pipeline': pipeline_data,
            'timeline': timeline_data,
            'notes': notes_data,
            'quick_actions': quick_actions,
            'partner_id': partner_id,
        }

    # ── F10 WP3: Domain Enrichment ─────────────────────────────────

    @http.route('/cf/mail/v3/partner/<int:partner_id>/enrich_domain', type='json', auth='user')
    def partner_enrich_domain(self, partner_id, **kw):
        """Trigger domain-based company enrichment for a person contact."""
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {'success': False, 'error': 'Partner not found'}
        if partner.is_company or partner.parent_id:
            return {'success': True, 'message': 'Already linked to company',
                    'company_id': (partner.parent_id.id if partner.parent_id else partner.id)}
        result = partner.action_enrich_from_domain()
        if result and result.get('company_id'):
            return {'success': True, 'company_id': result['company_id'],
                    'company_name': result.get('company_name', ''), 'source': result.get('source', '')}
        return {'success': False, 'error': 'Could not resolve company from domain'}

    # ── NBA Endpoints ────────────────────────────────────────────────

    @http.route('/cf/mail/v3/partner/<int:partner_id>/nba/dismiss', type='json', auth='user')
    def partner_nba_dismiss(self, partner_id, **kw):
        intel = request.env['casafolino.partner.intelligence'].search([
            ('partner_id', '=', partner_id)
        ], limit=1)
        if intel:
            intel.write({'pinned_ignore': True})
            # Log calibration feedback
            from odoo.addons.casafolino_mail.models.casafolino_partner_intelligence_feedback import IntelligenceFeedback
            IntelligenceFeedback._log_feedback(request.env, partner_id, 'nba_dismissed')
        return {'success': True}

    # ── Partner Notes ────────────────────────────────────────────────

    @http.route('/cf/mail/v3/partner/<int:partner_id>/notes', type='json', auth='user', methods=['POST'])
    def partner_notes_save(self, partner_id, **kw):
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {'success': False}
        notes = kw.get('notes', '')
        partner.write({'mv3_private_notes': notes})
        return {'success': True}

    # ── Accounts Summary ─────────────────────────────────────────────

    @http.route('/cf/mail/v3/accounts/summary', type='json', auth='user')
    def accounts_summary(self, **kw):
        accounts = request.env['casafolino.mail.account'].search([
            ('responsible_user_id', '=', request.env.uid),
            ('active', '=', True),
        ])

        result = []
        for a in accounts:
            unread = request.env['casafolino.mail.message'].search_count([
                ('account_id', '=', a.id),
                ('is_read', '=', False),
                ('state', 'in', ['keep', 'auto_keep']),
                ('is_deleted', '=', False),
            ])
            # Generate initials from name
            name_parts = (a.name or 'U').split()
            initials = ''.join([p[0].upper() for p in name_parts[:2]]) if name_parts else 'U'

            result.append({
                'id': a.id,
                'name': a.name or a.email_address,
                'email': a.email_address or '',
                'unread_count': unread,
                'last_sync': str(a.last_fetch_datetime) if a.last_fetch_datetime else '',
                'state': a.state or 'draft',
                'initials': initials,
            })

        return {'accounts': result}

    # ── Full-text Search ─────────────────────────────────────────────

    @http.route('/cf/mail/v3/search', type='json', auth='user')
    def search(self, **kw):
        query = kw.get('query', '')
        limit = min(int(kw.get('limit', 50)), 200)

        if not query or len(query) < 2:
            return {'results': []}

        # Use ORM search to respect record rules, then full-text on accessible IDs
        user_accounts = self._get_user_account_ids()
        if not user_accounts:
            return {'results': []}
        Message = request.env['casafolino.mail.message']
        accessible_ids = Message.search([
            ('account_id', 'in', user_accounts),
            ('state', 'in', ['keep', 'auto_keep']),
            ('is_deleted', '=', False),
        ]).ids

        if not accessible_ids:
            return {'results': []}

        cr = request.env.cr
        cr.execute("""
            SELECT id, subject, sender_email, email_date, thread_id,
                   ts_rank(
                       to_tsvector('simple', coalesce(subject,'')||' '||coalesce(body_plain,'')),
                       plainto_tsquery('simple', %s)
                   ) as rank
            FROM casafolino_mail_message
            WHERE id = ANY(%s)
              AND to_tsvector('simple', coalesce(subject,'')||' '||coalesce(body_plain,''))
                  @@ plainto_tsquery('simple', %s)
            ORDER BY rank DESC, email_date DESC
            LIMIT %s
        """, (query, accessible_ids, query, limit))

        rows = cr.dictfetchall()
        results = []
        for r in rows:
            results.append({
                'id': r['id'],
                'subject': r['subject'] or '',
                'sender_email': r['sender_email'] or '',
                'email_date': str(r['email_date'])[:16] if r['email_date'] else '',
                'thread_id': r['thread_id'],
                'snippet': '',
            })

        return {'results': results}

    # ── Reply Assistant AI ───────────────────────────────────────────

    @http.route('/cf/mail/v3/message/<int:message_id>/reply_assistant', type='json', auth='user')
    def reply_assistant(self, message_id, **kw):
        import requests as http_requests

        msg = request.env['casafolino.mail.message'].browse(message_id)
        if not msg.exists():
            return {'error': 'Message not found'}

        partner = msg.partner_id
        intel = None
        if partner:
            intel = request.env['casafolino.partner.intelligence'].search([
                ('partner_id', '=', partner.id)
            ], limit=1)

        # Thread history (last 3)
        thread_msgs = []
        if msg.thread_id:
            thread_msgs = msg.thread_id.message_ids.sorted('email_date', reverse=True)[:3]

        context_text = (
            "Azienda: %s\n"
            "Paese: %s\n"
            "Intent email: %s\n"
            "Hotness: %s\n"
            "Oggetto: %s\n"
            "Body ultima email: %s\n"
            "Ultimi scambi: %s"
        ) % (
            partner.name if partner else 'Sconosciuto',
            partner.country_id.name if partner and partner.country_id else 'N/A',
            getattr(msg, 'intent_detected', '') or 'general',
            '%s %s' % (intel.hotness_tier, intel.hotness_score) if intel else 'N/A',
            msg.subject or '',
            (msg.body_plain or msg.body_html or '')[:500],
            ', '.join([(m.subject or '')[:50] for m in thread_msgs]),
        )

        prompt = (
            "Sei l'assistente email di Antonio Folino, CEO di CasaFolino (food export italiano).\n"
            "CONTESTO:\n%s\n\n"
            "Genera 3 bozze di risposta email in italiano, professionali ma calde.\n"
            "Formato JSON (solo JSON, nient'altro):\n"
            '{"bozze": [\n'
            '  {"tipo": "Diretta", "testo": "..."},\n'
            '  {"tipo": "Relazionale", "testo": "..."},\n'
            '  {"tipo": "Proattiva", "testo": "..."}\n'
            ']}\n\n'
            "Regole:\n"
            "- Diretta: 3-4 righe, risposta secca al punto\n"
            "- Relazionale: 4-5 righe, richiamo a storia/contesto, poi risposta\n"
            "- Proattiva: 5-6 righe, risposta + proposta prossimo step (call, invio materiale, meeting)\n"
            "- Non firmare (la firma viene aggiunta automaticamente)\n"
            "- Non inventare date, numeri, prezzi"
        ) % context_text

        ICP = request.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('casafolino.groq_api_key')
        if not api_key:
            return {'error': 'Risposta AI non disponibile al momento. Chiave API non configurata.'}

        # Retry with exponential backoff (AC9)
        base_delay = 2
        max_retries = 3
        last_error = ''
        for attempt in range(max_retries):
            try:
                r = http_requests.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={'Authorization': 'Bearer %s' % api_key, 'Content-Type': 'application/json'},
                    json={
                        'model': 'llama-3.3-70b-versatile',
                        'messages': [{'role': 'user', 'content': prompt}],
                        'max_tokens': 800,
                        'temperature': 0.5,
                        'response_format': {'type': 'json_object'},
                    },
                    timeout=20,
                )
                if r.status_code == 429:
                    retry_after = int(r.headers.get('retry-after', base_delay * (2 ** attempt)))
                    wait = min(retry_after, 8)
                    _logger.warning('[mail v3] Groq 429, retry %d/%d in %ds', attempt + 1, max_retries, wait)
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(wait)
                        continue
                    return {'error': 'Risposta AI non disponibile al momento. Riprova tra qualche secondo.'}
                r.raise_for_status()
                content = r.json()['choices'][0]['message']['content']
                data = json.loads(content)
                return {'bozze': data.get('bozze', [])}
            except Exception as e:
                last_error = str(e)[:200]
                _logger.warning('[mail v3] Reply assistant attempt %d fail: %s', attempt + 1, last_error)
                if attempt < max_retries - 1:
                    import time
                    time.sleep(base_delay * (2 ** attempt))
                    continue
        return {'error': 'Risposta AI non disponibile dopo %d tentativi. Riprova tra qualche secondo.' % max_retries}

    # ── Compose Wizard Action ────────────────────────────────────────

    @http.route('/cf/mail/v3/compose/open', type='json', auth='user')
    def compose_open(self, **kw):
        """Return action dict to open compose wizard with pre-filled values."""
        account_id = kw.get('account_id')
        mode = kw.get('mode', 'new')
        reply_to_id = kw.get('reply_to_id')
        prefilled_body = kw.get('prefilled_body', '')

        if not account_id:
            account = request.env['casafolino.mail.account'].search([
                ('responsible_user_id', '=', request.env.uid),
                ('active', '=', True),
            ], limit=1)
            account_id = account.id if account else False

        ctx = {
            'default_account_id': account_id,
        }

        if reply_to_id and mode in ('reply', 'reply_all', 'forward'):
            orig = request.env['casafolino.mail.message'].browse(reply_to_id)
            if orig.exists():
                ctx['default_in_reply_to_message_id'] = orig.id

                if mode == 'reply':
                    ctx['default_to_emails'] = orig.sender_email if orig.direction == 'inbound' else orig.recipient_emails
                    ctx['default_subject'] = 'Re: ' + _normalize_subject(orig.subject or '')
                elif mode == 'reply_all':
                    ctx['default_to_emails'] = orig.sender_email if orig.direction == 'inbound' else orig.recipient_emails
                    ctx['default_cc_emails'] = orig.cc_emails or ''
                    ctx['default_subject'] = 'Re: ' + _normalize_subject(orig.subject or '')
                elif mode == 'forward':
                    ctx['default_to_emails'] = ''
                    ctx['default_subject'] = 'Fwd: ' + _normalize_subject(orig.subject or '')

                quote_date = str(orig.email_date)[:16] if orig.email_date else ''
                quote_from = orig.sender_name or orig.sender_email or ''
                quoted = (
                    '<br><br>'
                    '<div style="border-left:2px solid #ccc;padding-left:12px;margin-left:4px;color:#666;">'
                    '<p>Il %s, %s ha scritto:</p>'
                    '%s'
                    '</div>' % (quote_date, quote_from, orig.body_html or orig.body_plain or '')
                )
                ctx['default_body_html'] = (prefilled_body or '') + quoted

        if prefilled_body and 'default_body_html' not in ctx:
            ctx['default_body_html'] = prefilled_body

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'casafolino.mail.compose.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': ctx,
        }

    # ── Compose Prepare (F10: OWL ComposeWizard) ──────────────────

    @http.route('/cf/mail/v3/compose/prepare', type='json', auth='user')
    def compose_prepare(self, **kw):
        """Create draft and return prefilled data for OWL ComposeWizard."""
        account_id = kw.get('account_id')
        mode = kw.get('mode', 'new')
        reply_to_id = kw.get('reply_to_id')
        prefilled_body = kw.get('prefilled_body', '')

        if not account_id:
            account = request.env['casafolino.mail.account'].search([
                ('responsible_user_id', '=', request.env.uid),
                ('active', '=', True),
            ], limit=1)
            account_id = account.id if account else False

        prefilled = {
            'to': '',
            'cc': '',
            'bcc': '',
            'subject': '',
            'body_html': prefilled_body or '',
            'signature_html': '',
        }

        # Load signature
        if account_id:
            sig = request.env['casafolino.mail.signature'].search([
                ('account_id', '=', account_id),
                ('is_default', '=', True),
            ], limit=1)
            if not sig:
                sig = request.env['casafolino.mail.signature'].search([
                    ('account_id', '=', account_id),
                ], limit=1)
            if sig:
                prefilled['signature_html'] = sig.body_html or ''

        if reply_to_id and mode in ('reply', 'reply_all', 'forward'):
            orig = request.env['casafolino.mail.message'].browse(reply_to_id)
            if orig.exists():
                if mode == 'reply':
                    prefilled['to'] = orig.sender_email if orig.direction == 'inbound' else (orig.recipient_emails or '')
                    prefilled['subject'] = 'Re: ' + _normalize_subject(orig.subject or '')
                elif mode == 'reply_all':
                    prefilled['to'] = orig.sender_email if orig.direction == 'inbound' else (orig.recipient_emails or '')
                    prefilled['cc'] = orig.cc_emails or ''
                    prefilled['subject'] = 'Re: ' + _normalize_subject(orig.subject or '')
                elif mode == 'forward':
                    prefilled['subject'] = 'Fwd: ' + _normalize_subject(orig.subject or '')

                quote_date = str(orig.email_date)[:16] if orig.email_date else ''
                quote_from = orig.sender_name or orig.sender_email or ''
                quoted = (
                    '<br><br>'
                    '<div style="border-left:2px solid #ccc;padding-left:12px;margin-left:4px;color:#666;">'
                    '<p>Il %s, %s ha scritto:</p>'
                    '%s'
                    '</div>' % (quote_date, quote_from, orig.body_html or orig.body_plain or '')
                )
                prefilled['body_html'] = (prefilled_body or '') + quoted

        # Create draft
        draft_vals = {
            'account_id': account_id,
            'user_id': request.env.uid,
            'to_emails': prefilled['to'],
            'cc_emails': prefilled['cc'],
            'bcc_emails': prefilled['bcc'],
            'subject': prefilled['subject'],
            'body_html': prefilled['body_html'],
        }
        if reply_to_id:
            draft_vals['in_reply_to_message_id'] = reply_to_id

        draft = request.env['casafolino.mail.draft'].create(draft_vals)

        return {
            'draft_id': draft.id,
            'prefilled': prefilled,
        }

    # ── Smart Snooze ───────────────────────────���────────────────────

    @http.route('/cf/mail/v3/thread/<int:thread_id>/snooze', type='json', auth='user')
    def snooze_thread(self, thread_id, **kw):
        thread = request.env['casafolino.mail.thread'].browse(thread_id)
        if not self._check_thread_ownership(thread):
            return {'success': False, 'error': 'Thread not found'}

        snooze_type = kw.get('snooze_type', 'until_date')
        wake_at = kw.get('wake_at')
        deadline_days = int(kw.get('deadline_days', 3))
        note = kw.get('note', '')

        vals = {
            'thread_id': thread_id,
            'user_id': request.env.uid,
            'snooze_type': snooze_type,
            'deadline_days': deadline_days,
            'note': note,
            'snoozed_at': fields.Datetime.now(),
        }
        if wake_at:
            vals['wake_at'] = wake_at

        request.env['casafolino.mail.snooze'].create(vals)
        thread.write({'is_snoozed': True})

        return {'success': True}

    @http.route('/cf/mail/v3/snooze/<int:snooze_id>/unsnooze', type='json', auth='user')
    def unsnooze(self, snooze_id, **kw):
        snooze = request.env['casafolino.mail.snooze'].browse(snooze_id)
        if not snooze.exists():
            return {'success': False, 'error': 'Snooze not found'}
        snooze.thread_id.write({'is_snoozed': False})
        snooze.write({'active': False})
        return {'success': True}

    @http.route('/cf/mail/v3/thread/<int:thread_id>/unsnooze', type='json', auth='user')
    def unsnooze_thread(self, thread_id, **kw):
        thread = request.env['casafolino.mail.thread'].browse(thread_id)
        if not thread.exists():
            return {'success': False}
        thread.write({'is_snoozed': False})
        snoozes = request.env['casafolino.mail.snooze'].search([
            ('thread_id', '=', thread_id), ('active', '=', True),
        ])
        snoozes.write({'active': False})
        return {'success': True}

    @http.route('/cf/mail/v3/snoozes', type='json', auth='user')
    def list_snoozes(self, **kw):
        snoozes = request.env['casafolino.mail.snooze'].search([
            ('user_id', '=', request.env.uid),
            ('active', '=', True),
        ])
        result = []
        for s in snoozes:
            result.append({
                'id': s.id,
                'thread_id': s.thread_id.id,
                'thread_subject': s.thread_id.subject or '',
                'snooze_type': s.snooze_type,
                'wake_at': str(s.wake_at) if s.wake_at else '',
                'deadline_days': s.deadline_days,
                'note': s.note or '',
            })
        return {'snoozes': result}

    # ── Undo Send ───────────────────────��───────────────────────────

    @http.route('/cf/mail/v3/draft/<int:draft_id>/send_undoable', type='json', auth='user')
    def draft_send_undoable(self, draft_id, **kw):
        """Send draft via outbox with 10s undo window."""
        draft = request.env['casafolino.mail.draft'].browse(draft_id)
        if not draft.exists():
            return {'success': False, 'error': 'Draft not found'}

        now = fields.Datetime.now()
        undo_until = now + timedelta(seconds=10)

        outbox = request.env['casafolino.mail.outbox'].queue_send(
            account_id=draft.account_id.id,
            to_emails=draft.to_emails or '',
            subject=draft.subject or '',
            body_html=draft.body_html or '',
            cc_emails=draft.cc_emails or '',
            bcc_emails=draft.bcc_emails or '',
            signature_html=draft.signature_id.body_html if draft.signature_id else '',
            in_reply_to=draft.in_reply_to_message_id.message_id_rfc if draft.in_reply_to_message_id else '',
            attachment_ids=draft.attachment_ids.ids or None,
            source_message_id=draft.in_reply_to_message_id.id if draft.in_reply_to_message_id else False,
        )
        outbox.write({'state': 'undoable', 'undo_until': undo_until})

        # Delete draft after queuing
        draft.unlink()

        return {
            'success': True,
            'outbox_id': outbox.id,
            'undo_until': str(undo_until),
        }

    @http.route('/cf/mail/v3/outbox/<int:outbox_id>/undo', type='json', auth='user')
    def undo_send(self, outbox_id, **kw):
        outbox = request.env['casafolino.mail.outbox'].browse(outbox_id)
        if not outbox.exists():
            return {'success': False, 'error': 'Non trovato'}
        if outbox.state != 'undoable':
            return {'success': False, 'error': 'Non più annullabile'}

        # Restore as draft
        draft = request.env['casafolino.mail.draft'].create({
            'account_id': outbox.account_id.id,
            'user_id': request.env.uid,
            'to_emails': outbox.to_emails,
            'cc_emails': outbox.cc_emails,
            'bcc_emails': outbox.bcc_emails,
            'subject': outbox.subject,
            'body_html': outbox.body_html,
            'in_reply_to_message_id': outbox.source_message_id.id if outbox.source_message_id else False,
        })
        outbox.unlink()
        return {'success': True, 'draft_id': draft.id}

    # ── Scheduled Send ────────────────────────��─────────────────────

    @http.route('/cf/mail/v3/draft/<int:draft_id>/schedule', type='json', auth='user')
    def draft_schedule(self, draft_id, **kw):
        draft = request.env['casafolino.mail.draft'].browse(draft_id)
        if not draft.exists():
            return {'success': False, 'error': 'Draft not found'}
        scheduled_at = kw.get('scheduled_send_at')
        if not scheduled_at:
            return {'success': False, 'error': 'Data richiesta'}
        draft.write({
            'scheduled_send_at': scheduled_at,
            'is_scheduled': True,
        })
        return {'success': True}

    @http.route('/cf/mail/v3/draft/<int:draft_id>/unschedule', type='json', auth='user')
    def draft_unschedule(self, draft_id, **kw):
        draft = request.env['casafolino.mail.draft'].browse(draft_id)
        if not draft.exists():
            return {'success': False}
        draft.write({'is_scheduled': False, 'scheduled_send_at': False})
        return {'success': True}

    @http.route('/cf/mail/v3/scheduled', type='json', auth='user')
    def list_scheduled(self, **kw):
        drafts = request.env['casafolino.mail.draft'].search([
            ('user_id', '=', request.env.uid),
            ('is_scheduled', '=', True),
        ], order='scheduled_send_at asc')
        result = []
        for d in drafts:
            result.append({
                'id': d.id,
                'to_emails': d.to_emails or '',
                'subject': d.subject or '',
                'scheduled_send_at': str(d.scheduled_send_at) if d.scheduled_send_at else '',
            })
        return {'drafts': result}

    # ── Dark Mode ────────────────────────���──────────────────────────

    @http.route('/cf/mail/v3/user/dark_mode', type='json', auth='user')
    def toggle_dark_mode(self, **kw):
        user = request.env.user
        enabled = kw.get('enabled')
        if enabled is None:
            enabled = not user.mail_v3_dark_mode
        user.sudo().write({'mail_v3_dark_mode': bool(enabled)})
        return {'success': True, 'dark_mode': bool(enabled)}

    @http.route('/cf/mail/v3/user/preferences', type='json', auth='user')
    def get_user_preferences(self, **kw):
        user = request.env.user
        return {
            'dark_mode': user.mail_v3_dark_mode,
            'reading_pane_position': user.mail_v3_reading_pane_position or 'right',
            'thread_list_density': user.mail_v3_thread_list_density or 'comfortable',
            'keyboard_shortcuts': user.mail_v3_keyboard_shortcuts_enabled,
            'font_size': user.mv3_font_size or 'medium',
            'ai_reply_enabled': user.mv3_ai_reply_enabled,
            'ai_temperature': user.mv3_ai_temperature or 0.5,
            'ai_model': user.mv3_ai_model or 'llama-3.3-70b-versatile',
            'notifications_enabled': user.mv3_notifications_enabled,
        }

    @http.route('/cf/mail/v3/user/preferences/save', type='json', auth='user')
    def save_user_preferences(self, **kw):
        user = request.env.user
        vals = {}
        field_map = {
            'dark_mode': 'mail_v3_dark_mode',
            'reading_pane_position': 'mail_v3_reading_pane_position',
            'thread_list_density': 'mail_v3_thread_list_density',
            'keyboard_shortcuts': 'mail_v3_keyboard_shortcuts_enabled',
            'font_size': 'mv3_font_size',
            'ai_reply_enabled': 'mv3_ai_reply_enabled',
            'ai_temperature': 'mv3_ai_temperature',
            'ai_model': 'mv3_ai_model',
            'notifications_enabled': 'mv3_notifications_enabled',
        }
        for key, field in field_map.items():
            if key in kw:
                vals[field] = kw[key]
        if vals:
            user.sudo().write(vals)
        return {'success': True}

    # ── Settings: Signatures ────────────────────���───────────────────

    @http.route('/cf/mail/v3/signatures', type='json', auth='user')
    def list_signatures(self, **kw):
        sigs = request.env['casafolino.mail.signature'].search([])
        return {'signatures': [{
            'id': s.id,
            'name': s.name or '',
            'body_html': s.body_html or '',
            'is_default': s.is_default,
            'account_id': s.account_id.id if s.account_id else False,
            'account_name': s.account_id.name if s.account_id else '',
        } for s in sigs]}

    # ── Settings: AI Test Connection ───────────────��────────────────

    @http.route('/cf/mail/v3/settings/test_groq', type='json', auth='user')
    def test_groq_connection(self, **kw):
        import requests as http_requests
        ICP = request.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('casafolino.groq_api_key')
        if not api_key:
            return {'success': False, 'error': 'API key non configurata'}
        try:
            r = http_requests.get(
                'https://api.groq.com/openai/v1/models',
                headers={'Authorization': 'Bearer %s' % api_key},
                timeout=10,
            )
            r.raise_for_status()
            models = [m['id'] for m in r.json().get('data', [])]
            return {'success': True, 'models': models}
        except Exception as e:
            return {'success': False, 'error': str(e)[:200]}

    # ── Settings: Autoresponder ──────────────────────────────────

    @http.route('/cf/mail/v3/autoresponder/get', type='json', auth='user')
    def autoresponder_get(self, **kw):
        """Get current user's autoresponder config."""
        AR = request.env['casafolino.mail.autoresponder'].sudo()
        ar = AR.search([('user_id', '=', request.env.uid)], limit=1)
        if not ar:
            return {'exists': False}

        # Get alternate contact users for dropdown
        users = request.env['res.users'].sudo().search([
            ('share', '=', False),
            ('id', '!=', request.env.uid),
        ])
        alternate_users = [{'id': u.id, 'name': u.name} for u in users]

        return {
            'exists': True,
            'id': ar.id,
            'active': ar.active,
            'date_start': str(ar.date_start) if ar.date_start else '',
            'date_end': str(ar.date_end) if ar.date_end else '',
            'subject_prefix': ar.subject_prefix or '',
            'body_html_it': ar.body_html_it or '',
            'body_html_en': ar.body_html_en or '',
            'body_html_es': ar.body_html_es or '',
            'contact_alternate_id': ar.contact_alternate_id.id if ar.contact_alternate_id else False,
            'contact_alternate_name': ar.contact_alternate_id.name if ar.contact_alternate_id else '',
            'sent_count': ar.sent_count,
            'alternate_users': alternate_users,
        }

    @http.route('/cf/mail/v3/autoresponder/save', type='json', auth='user')
    def autoresponder_save(self, **kw):
        """Create or update current user's autoresponder."""
        AR = request.env['casafolino.mail.autoresponder'].sudo()
        ar = AR.search([('user_id', '=', request.env.uid)], limit=1)

        vals = {}
        field_map = {
            'date_start': 'date_start',
            'date_end': 'date_end',
            'subject_prefix': 'subject_prefix',
            'body_html_it': 'body_html_it',
            'body_html_en': 'body_html_en',
            'body_html_es': 'body_html_es',
            'contact_alternate_id': 'contact_alternate_id',
        }
        for key, field in field_map.items():
            if key in kw:
                val = kw[key]
                if key in ('date_start', 'date_end'):
                    vals[field] = val if val else False
                elif key == 'contact_alternate_id':
                    vals[field] = int(val) if val else False
                else:
                    vals[field] = val

        if ar:
            ar.write(vals)
        else:
            vals['user_id'] = request.env.uid
            ar = AR.create(vals)

        return {'success': True, 'id': ar.id}

    @http.route('/cf/mail/v3/autoresponder/toggle', type='json', auth='user')
    def autoresponder_toggle(self, **kw):
        """Toggle autoresponder active state."""
        AR = request.env['casafolino.mail.autoresponder'].sudo()
        ar = AR.search([('user_id', '=', request.env.uid)], limit=1)
        if not ar:
            return {'success': False, 'error': 'Autoresponder non configurato'}

        new_active = kw.get('active')
        if new_active is None:
            new_active = not ar.active
        ar.active = bool(new_active)

        return {'success': True, 'active': ar.active}

    @http.route('/cf/mail/v3/autoresponder/preview', type='json', auth='user')
    def autoresponder_preview(self, **kw):
        """Preview autoresponder email with sample data."""
        AR = request.env['casafolino.mail.autoresponder'].sudo()
        ar = AR.search([('user_id', '=', request.env.uid)], limit=1)
        if not ar:
            return {'success': False, 'error': 'Autoresponder non configurato'}

        lang = kw.get('lang', 'it')
        sample_sender = kw.get('sender_name', 'Mario Rossi')

        body = ar._render_body(sample_sender, lang=lang)
        prefix = ar.subject_prefix or '[Fuori sede] '
        subject = '%sRe: Richiesta informazioni prodotti' % prefix

        return {
            'success': True,
            'subject': subject,
            'body_html': body,
        }

    # ── Bulk Actions ──────────────────────────────────────────────

    @http.route('/cf/mail/v3/threads/bulk', type='json', auth='user')
    def threads_bulk_action(self, **kw):
        action = kw.get('action')
        thread_ids = kw.get('thread_ids', [])
        if not action or not thread_ids:
            return {'success': False, 'error': 'Missing action or ids'}

        user_accounts = self._get_user_account_ids()
        threads = request.env['casafolino.mail.thread'].browse(thread_ids).filtered(
            lambda t: t.account_id.id in user_accounts
        )
        processed = 0

        for thread in threads:
            msgs = thread.message_ids.filtered(lambda m: not m.is_deleted)
            if action == 'mark_read':
                msgs.filtered(lambda m: not m.is_read).action_mark_read()
            elif action == 'mark_unread':
                msgs.filtered(lambda m: m.is_read).action_mark_unread()
            elif action == 'archive':
                msgs.action_archive()
            elif action == 'delete':
                msgs.action_delete_soft()
            elif action == 'star':
                for m in msgs:
                    if not m.is_starred:
                        m.action_toggle_star()
            elif action == 'unstar':
                for m in msgs:
                    if m.is_starred:
                        m.action_toggle_star()
            elif action == 'snooze':
                wake_at = kw.get('wake_at')
                if wake_at:
                    request.env['casafolino.mail.snooze'].create({
                        'thread_id': thread.id,
                        'user_id': request.env.uid,
                        'snooze_type': 'until_date',
                        'wake_at': wake_at,
                    })
                    thread.write({'is_snoozed': True})
            processed += 1

        return {'success': True, 'processed': processed}

    # ── Calibration Feedback ───────────────────��────────────────────

    @http.route('/cf/mail/v3/partner/<int:partner_id>/feedback', type='json', auth='user')
    def partner_feedback(self, partner_id, **kw):
        action_type = kw.get('action_type')
        if not action_type:
            return {'success': False, 'error': 'action_type required'}

        from odoo.addons.casafolino_mail.models.casafolino_partner_intelligence_feedback import IntelligenceFeedback
        IntelligenceFeedback._log_feedback(
            request.env, partner_id, action_type,
            extra=kw.get('context')
        )
        return {'success': True}

    # ── Response Time Analytics ──────────────���──────────────────────

    @http.route('/cf/mail/v3/analytics', type='json', auth='user')
    def analytics(self, **kw):
        days = int(kw.get('days', 30))
        user_accounts = self._get_user_account_ids()
        account_ids = kw.get('account_ids')
        if account_ids:
            account_ids = [a for a in account_ids if a in user_accounts]
        else:
            account_ids = user_accounts
        Metric = request.env['casafolino.mail.response.metric']
        return Metric.get_analytics(days=days, account_ids=account_ids)

    # ── F6: Auto-link Leads ─────────────────────────────────────────

    @http.route('/cf/mail/v3/leads/auto_create', type='json', auth='user')
    def leads_auto_create(self, **kw):
        if not request.env.user.has_group('casafolino_mail.group_mail_v3_admin'):
            return {'success': False, 'error': 'Admin only'}
        Rule = request.env['casafolino.mail.lead.rule']
        rule_id = kw.get('rule_id')
        if rule_id:
            rules = Rule.browse(int(rule_id))
        else:
            rules = Rule.search([('active', '=', True)])
        total = 0
        lead_ids = []
        for rule in rules:
            count = rule._run_rule()
            total += count
        if total:
            leads = request.env['crm.lead'].search([
                ('cf_auto_created', '=', True),
            ], order='create_date desc', limit=total)
            lead_ids = leads.ids
        return {'success': True, 'count': total, 'lead_ids': lead_ids}

    # ── F6: Quote Wizard Open ───────────────────────────────────────

    @http.route('/cf/mail/v3/thread/<int:thread_id>/quote/open_wizard', type='json', auth='user')
    def quote_open_wizard(self, thread_id, **kw):
        Thread = request.env['casafolino.mail.thread']
        thread = Thread.browse(thread_id)
        if not thread.exists():
            return {'success': False, 'error': 'Thread not found'}
        partner = thread.partner_ids[:1]
        return {
            'success': True,
            'action': {
                'type': 'ir.actions.act_window',
                'res_model': 'casafolino.mail.quote.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_thread_id': thread.id,
                    'default_partner_id': partner.id if partner else False,
                },
            },
        }

    # ── F6: Commercial Context ──────────────────────────────────────

    @http.route('/cf/mail/v3/partner/<int:partner_id>/commercial_context', type='json', auth='user')
    def commercial_context(self, partner_id, **kw):
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {'success': False, 'error': 'Partner not found'}

        # Sale orders last 12 months
        cutoff = fields.Datetime.now() - timedelta(days=365)
        SaleOrder = request.env['sale.order']
        orders = SaleOrder.search([
            ('partner_id', '=', partner_id),
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', cutoff),
        ], order='date_order desc')

        # Top 5 SKU by qty
        top_skus = []
        try:
            groups = request.env['sale.report'].read_group(
                domain=[('partner_id', '=', partner_id), ('state', 'in', ['sale', 'done'])],
                fields=['product_id', 'product_uom_qty:sum'],
                groupby=['product_id'],
                orderby='product_uom_qty desc',
                limit=5,
            )
            for g in groups:
                if g.get('product_id'):
                    top_skus.append({
                        'product_id': g['product_id'][0],
                        'name': g['product_id'][1],
                        'qty': g.get('product_uom_qty', 0),
                    })
        except Exception:
            pass

        # Open leads
        open_leads = request.env['crm.lead'].search_count([
            ('partner_id', '=', partner_id),
            ('stage_id.is_won', '=', False),
            ('active', '=', True),
        ])

        # Open quotes
        open_quotes = SaleOrder.search_count([
            ('partner_id', '=', partner_id),
            ('state', 'in', ['draft', 'sent']),
        ])

        return {
            'success': True,
            'data': {
                'total_revenue_12m': sum(orders.mapped('amount_total')),
                'order_count_12m': len(orders),
                'last_order_date': orders[0].date_order.strftime('%d/%m/%Y') if orders and orders[0].date_order else None,
                'last_order_number': orders[0].name if orders else None,
                'top_skus': top_skus,
                'open_leads_count': open_leads,
                'open_quotes_count': open_quotes,
                'pricelist': partner.property_product_pricelist.name if partner.property_product_pricelist else '-',
                'payment_term': partner.property_payment_term_id.name if partner.property_payment_term_id else '-',
                'preferred_language': partner.lang or '-',
            },
        }

    # ── F6: Template Render Preview ─────────────────────────────────

    @http.route('/cf/mail/v3/template/render', type='json', auth='user')
    def template_render(self, **kw):
        template_id = int(kw.get('template_id', 0))
        partner_id = int(kw.get('partner_id', 0))
        thread_id = kw.get('thread_id')
        if not template_id or not partner_id:
            return {'success': False, 'error': 'template_id and partner_id required'}
        Template = request.env['casafolino.mail.template']
        rendered = Template.render_template(template_id, partner_id, thread_id)
        return {'success': True, 'rendered': rendered}

    # ── F6: User Undo Seconds ───────────────────────────────────────

    @http.route('/cf/mail/v3/user/undo_seconds', type='json', auth='user')
    def user_undo_seconds(self, **kw):
        return {'undo_seconds': request.env.user.mv3_undo_send_seconds or 0}

    # ═══════════════════════════════════════════════════════════════════
    # V12.6: Sender Decision Endpoints
    # ═══════════════════════════════════════════════════════════════════

    @http.route('/cf/mail/v3/sender_decision/get', type='json', auth='user')
    def sender_decision_get(self, **kw):
        email = (kw.get('email') or '').strip().lower()
        if not email:
            return {'status': 'unknown'}
        user_accounts = self._get_user_account_ids()
        pref = request.env['casafolino.mail.sender_preference'].search([
            ('email', '=ilike', email),
            ('account_id', 'in', user_accounts),
        ], limit=1)
        if not pref:
            return {'status': 'unknown'}
        return {
            'status': pref.status,
            'decided_at': str(pref.decided_at) if pref.decided_at else '',
            'dismissed_email_count': pref.dismissed_email_count,
        }

    @http.route('/cf/mail/v3/sender_decision/keep', type='json', auth='user')
    def sender_decision_keep(self, **kw):
        email = (kw.get('email') or '').strip().lower()
        if not email:
            return {'success': False, 'error': 'Email required'}
        user_accounts = self._get_user_account_ids()
        pref = request.env['casafolino.mail.sender_preference'].search([
            ('email', '=ilike', email),
            ('account_id', 'in', user_accounts),
        ], limit=1)
        if not pref:
            # Auto-create as kept
            if user_accounts:
                pref = request.env['casafolino.mail.sender_preference'].create({
                    'email': email,
                    'account_id': user_accounts[0],
                    'status': 'kept',
                    'decided_at': fields.Datetime.now(),
                    'decided_by_id': request.env.uid,
                })
            return {'success': True, 'status': 'kept'}
        pref.action_keep()
        return {'success': True, 'status': 'kept'}

    @http.route('/cf/mail/v3/sender_decision/dismiss', type='json', auth='user')
    def sender_decision_dismiss(self, **kw):
        email = (kw.get('email') or '').strip().lower()
        if not email:
            return {'success': False, 'error': 'Email required'}
        user_accounts = self._get_user_account_ids()
        Preference = request.env['casafolino.mail.sender_preference']
        # V12.8: Dismiss cross-account — find ALL preferences for this email
        prefs = Preference.search([
            ('email', '=ilike', email),
            ('account_id', 'in', user_accounts),
        ])
        if not prefs:
            return {'success': False, 'error': 'Sender not found'}
        # Count emails that will be deleted across all accounts
        pending_count = request.env['casafolino.mail.message'].search_count([
            ('sender_email', '=ilike', email),
            ('account_id', 'in', user_accounts),
        ])
        # Dismiss all preferences, use token from the first one
        undo_token = None
        for pref in prefs:
            token = pref.action_dismiss()
            if not undo_token:
                undo_token = token
        # Create missing preferences for accounts that don't have one yet
        existing_account_ids = set(prefs.mapped('account_id').ids)
        for acc_id in user_accounts:
            if acc_id not in existing_account_ids:
                try:
                    new_pref = Preference.sudo().create({
                        'email': email,
                        'account_id': acc_id,
                        'status': 'pending',
                    })
                    new_pref.action_dismiss()
                except Exception:
                    pass  # UNIQUE constraint — already exists
        return {
            'success': True,
            'pending_deletion_count': pending_count,
            'undo_token': undo_token,
        }

    @http.route('/cf/mail/v3/sender_decision/cancel_dismiss', type='json', auth='user')
    def sender_decision_cancel_dismiss(self, **kw):
        token = kw.get('undo_token', '')
        if not token:
            return {'success': False, 'error': 'Token required'}
        user_accounts = self._get_user_account_ids()
        pref = request.env['casafolino.mail.sender_preference'].search([
            ('undo_token', '=', token),
            ('account_id', 'in', user_accounts),
        ], limit=1)
        if not pref:
            return {'success': False, 'error': 'Invalid or expired token'}
        ok = pref.action_cancel_dismiss(token)
        # V12.8: Also revert all sibling preferences for this email
        if ok:
            siblings = request.env['casafolino.mail.sender_preference'].search([
                ('email', '=ilike', pref.email),
                ('account_id', 'in', user_accounts),
                ('status', '=', 'dismissed'),
                ('id', '!=', pref.id),
            ])
            for sib in siblings:
                sib.write({
                    'status': 'pending',
                    'undo_token': False,
                    'decided_at': False,
                    'decided_by_id': False,
                })
        return {'success': ok}

    @http.route('/cf/mail/v3/sender_decision/defer', type='json', auth='user')
    def sender_decision_defer(self, **kw):
        return {'success': True}

    @http.route('/cf/mail/v3/sender_decision/list_dismissed', type='json', auth='user')
    def sender_decision_list_dismissed(self, **kw):
        search_term = (kw.get('search') or '').strip()
        user_accounts = self._get_user_account_ids()
        domain = [
            ('account_id', 'in', user_accounts),
            ('status', '=', 'dismissed'),
        ]
        if search_term:
            domain.append(('email', 'ilike', search_term))
        prefs = request.env['casafolino.mail.sender_preference'].search(
            domain, order='decided_at desc', limit=200)
        result = []
        for p in prefs:
            result.append({
                'email': p.email,
                'decided_at': str(p.decided_at) if p.decided_at else '',
                'dismissed_email_count': p.dismissed_email_count,
            })
        return {'dismissed': result}

    @http.route('/cf/mail/v3/sender_decision/restore', type='json', auth='user')
    def sender_decision_restore(self, **kw):
        email = (kw.get('email') or '').strip().lower()
        recover_days = int(kw.get('recover_days') or 0)
        if not email:
            return {'success': False, 'error': 'Email required'}
        user_accounts = self._get_user_account_ids()
        pref = request.env['casafolino.mail.sender_preference'].search([
            ('email', '=ilike', email),
            ('account_id', 'in', user_accounts),
            ('status', '=', 'dismissed'),
        ], limit=1)
        if not pref:
            return {'success': False, 'error': 'Dismissed sender not found'}
        pref.action_restore(recover_days)
        msg = 'Mittente riabilitato'
        if recover_days > 0:
            msg += '. Recovery IMAP avviato per ultimi %d giorni.' % recover_days
        return {'success': True, 'message': msg}

    # ── F7: Triage Auto-Cleanup Noreply (§3.7) ─────────────────────

    @http.route('/cf/mail/v3/triage/autoclean_noreply', type='json', auth='user', methods=['POST'])
    def triage_autoclean_noreply(self, **kw):
        """Admin endpoint: auto-ignora tutti gli orfani con email noreply-like."""
        if not request.env.user.has_group('base.group_system'):
            return {'success': False, 'error': 'Admin only'}

        Orphan = request.env['casafolino.mail.orphan.partner']
        result = Orphan.action_bulk_autoclean_noreply()

        # Count cleaned from notification message
        cleaned = 0
        if result.get('params', {}).get('message'):
            msg = result['params']['message']
            import re as _re
            m = _re.search(r'(\d+)', msg)
            if m:
                cleaned = int(m.group(1))

        return {'success': True, 'cleaned': cleaned}

    # ── F8: Template List Endpoint ─────────────────────────────────

    @http.route('/cf/mail/v3/templates/list', type='json', auth='user')
    def templates_list(self, **kw):
        """Return all templates accessible to the user, optionally filtered by account."""
        account_id = kw.get('account_id')
        domain = []
        if account_id:
            domain = ['|', ('account_ids', '=', False), ('account_ids', 'in', [account_id])]

        templates = request.env['casafolino.mail.template'].search(domain, order='sequence, name')
        result = []
        for t in templates:
            result.append({
                'id': t.id,
                'name': t.name or '',
                'description': t.description or '',
                'subject': t.subject or '',
                'language': t.language or '',
                'category': t.category or '',
                'usage_count': t.usage_count,
                'sequence': t.sequence,
            })
        return {'templates': result}

    # ── F8: Template Preview Endpoint ──────────────────────────────

    @http.route('/cf/mail/v3/template/<int:template_id>/preview', type='json', auth='user')
    def template_preview(self, template_id, **kw):
        """Render template with partner data for preview."""
        partner_id = int(kw.get('partner_id') or 0)
        thread_id = kw.get('thread_id')

        Template = request.env['casafolino.mail.template']
        template = Template.browse(template_id)
        if not template.exists():
            return {'subject': '', 'body_html': ''}

        if partner_id:
            rendered = Template.render_template(template_id, partner_id, thread_id)
            return {
                'subject': rendered.get('subject', ''),
                'body_html': rendered.get('body_html', ''),
            }
        return {
            'subject': template.subject or '',
            'body_html': template.body_html or '',
        }

    # ── V12.8: Snippet Endpoints ────────────────────────────────────

    @http.route('/cf/mail/v3/snippets/list', type='json', auth='user')
    def snippets_list(self, **kw):
        code_prefix = (kw.get('code_prefix') or '').strip()
        domain = [('active', '=', True)]
        if code_prefix:
            domain.append(('code', 'ilike', code_prefix))
        snippets = request.env['casafolino.mail.snippet'].sudo().search(
            domain, order='usage_count desc, name', limit=10)
        return {
            'snippets': [{
                'id': s.id,
                'name': s.name,
                'code': s.code,
                'language': s.language,
                'category': s.category,
                'subject': s.subject or '',
                'body': s.body,
            } for s in snippets],
        }

    @http.route('/cf/mail/v3/snippets/apply', type='json', auth='user')
    def snippet_apply(self, **kw):
        snippet_id = int(kw.get('snippet_id', 0))
        partner_id = int(kw.get('partner_id') or 0)
        s = request.env['casafolino.mail.snippet'].sudo().browse(snippet_id)
        if not s.exists():
            return {'success': False}
        # Render with partner data if available
        partner = request.env['res.partner'].browse(partner_id) if partner_id else None
        user = request.env.user
        rendered_body = s._render_snippet(partner=partner, user=user)
        s.sudo().write({
            'usage_count': (s.usage_count or 0) + 1,
            'last_used': fields.Datetime.now(),
        })
        return {
            'success': True,
            'body': rendered_body,
            'subject': s.subject or '',
        }

    # ── F8: Partner Language Detection ─────────────────────────────

    COUNTRY_TO_LANG = {
        'IT': 'it_IT', 'SM': 'it_IT', 'VA': 'it_IT',
        'DE': 'de_DE', 'AT': 'de_DE', 'CH': 'de_DE', 'LI': 'de_DE',
        'ES': 'es_ES', 'MX': 'es_ES', 'AR': 'es_ES', 'CL': 'es_ES',
        'CO': 'es_ES', 'PE': 'es_ES',
        'FR': 'fr_FR', 'BE': 'fr_FR', 'LU': 'fr_FR', 'MC': 'fr_FR',
        'CA': 'fr_FR',
    }

    @http.route('/cf/mail/v3/partner/detect_language', type='json', auth='user')
    def partner_detect_language(self, **kw):
        """Detect partner language from country code."""
        partner_id = int(kw.get('partner_id') or 0)
        email = kw.get('email', '')

        partner = None
        if partner_id:
            partner = request.env['res.partner'].browse(partner_id)
        elif email:
            partner = request.env['res.partner'].search([
                ('email', '=ilike', email.strip()),
            ], limit=1)

        if not partner or not partner.exists():
            return {'lang': 'en_US'}

        country_code = partner.country_id.code if partner.country_id else ''
        lang = self.COUNTRY_TO_LANG.get(country_code, 'en_US')
        return {'lang': lang, 'country_code': country_code}

    # ═══════════════════════════════════════════════════════════════════
    # V12.4: Insight 360 Tab Bar Endpoints
    # ═══════════════════════════════════════════════════════════════════

    @http.route('/cf/mail/v3/insight360/contact', type='json', auth='user')
    def insight360_contact(self, **kw):
        partner_id = int(kw.get('partner_id') or 0)
        if not partner_id:
            return {}
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {}
        return {
            'id': partner.id,
            'name': partner.name or '',
            'email': partner.email or '',
            'phone': partner.phone or '',
            'mobile': partner.mobile or '',
            'function': partner.function or '',
            'lang': partner.lang or '',
            'avatar_url': '/web/image/res.partner/%d/avatar_128' % partner.id,
        }

    @http.route('/cf/mail/v3/insight360/company', type='json', auth='user')
    def insight360_company(self, **kw):
        partner_id = int(kw.get('partner_id') or 0)
        if not partner_id:
            return {}
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {}
        company = partner if partner.is_company else partner.parent_id
        if not company or not company.exists():
            return {'name': ''}
        return {
            'id': company.id,
            'name': company.name or '',
            'vat': company.vat or '',
            'country_code': company.country_id.code if company.country_id else '',
            'country_name': company.country_id.name if company.country_id else '',
            'industry_name': company.industry_id.name if company.industry_id else '',
            'employee_count': company.employee if hasattr(company, 'employee') else 0,
            'website': company.website or '',
        }

    @http.route('/cf/mail/v3/insight360/leads', type='json', auth='user')
    def insight360_leads(self, **kw):
        partner_id = int(kw.get('partner_id') or 0)
        if not partner_id:
            return {'leads': []}
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {'leads': []}
        p_ids = [partner_id]
        if partner.parent_id:
            p_ids.append(partner.parent_id.id)
        leads = request.env['crm.lead'].sudo().search([
            ('partner_id', 'in', p_ids),
        ], order='date_deadline desc', limit=20)
        result = []
        for lead in leads:
            result.append({
                'id': lead.id,
                'name': lead.name or '',
                'stage': lead.stage_id.name if lead.stage_id else '',
                'stage_id': lead.stage_id.id if lead.stage_id else False,
                'expected_revenue': lead.expected_revenue or 0,
                'probability': lead.probability or 0,
                'date_deadline': str(lead.date_deadline) if lead.date_deadline else '',
                'user_name': lead.user_id.name if lead.user_id else '',
            })
        return {'leads': result}

    @http.route('/cf/mail/v3/insight360/timeline', type='json', auth='user')
    def insight360_timeline(self, **kw):
        partner_id = int(kw.get('partner_id') or 0)
        if not partner_id:
            return {'events': []}
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {'events': []}
        p_ids = [partner_id]
        if partner.parent_id:
            p_ids.append(partner.parent_id.id)
        if partner.is_company:
            p_ids += partner.child_ids.ids

        events = []

        # Emails
        try:
            emails = request.env['casafolino.mail.message'].search([
                ('partner_id', 'in', p_ids),
                ('state', 'in', ['keep', 'auto_keep']),
                ('is_deleted', '=', False),
            ], order='email_date desc', limit=10)
            for m in emails:
                events.append({
                    'type': 'email_out' if m.direction == 'outbound' else 'email_in',
                    'date': str(m.email_date) if m.email_date else '',
                    'title': (m.subject or '')[:80],
                    'icon': 'fa-reply' if m.direction == 'outbound' else 'fa-envelope',
                })
        except Exception as e:
            _logger.warning('[insight360] timeline emails error: %s', e)

        # Sales
        try:
            orders = request.env['sale.order'].sudo().search([
                ('partner_id', 'in', p_ids),
                ('state', 'in', ['sale', 'done']),
            ], order='date_order desc', limit=5)
            for o in orders:
                events.append({
                    'type': 'order',
                    'date': str(o.date_order) if o.date_order else '',
                    'title': '%s (%s)' % (o.name, o.state),
                    'icon': 'fa-shopping-cart',
                })
        except Exception as e:
            _logger.warning('[insight360] timeline orders error: %s', e)

        # Leads
        try:
            leads = request.env['crm.lead'].sudo().search([
                ('partner_id', 'in', p_ids),
            ], order='create_date desc', limit=5)
            for l in leads:
                events.append({
                    'type': 'lead',
                    'date': str(l.create_date) if l.create_date else '',
                    'title': l.name or '',
                    'icon': 'fa-bullseye',
                })
        except Exception as e:
            _logger.warning('[insight360] timeline leads error: %s', e)

        # Sort all by date desc, take top 20
        events.sort(key=lambda x: x.get('date', ''), reverse=True)
        return {'events': events[:20]}

    @http.route('/cf/mail/v3/insight360/revenue', type='json', auth='user')
    def insight360_revenue(self, **kw):
        from datetime import date
        partner_id = int(kw.get('partner_id') or 0)
        if not partner_id:
            return {}
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {}
        p_ids = [partner_id]
        if partner.parent_id:
            p_ids.append(partner.parent_id.id)
        if partner.is_company:
            p_ids += partner.child_ids.ids

        Move = request.env['account.move'].sudo()
        base_domain = [
            ('partner_id', 'in', p_ids),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
        ]

        today = date.today()
        ytd_start = date(today.year, 1, 1)
        prev_start = date(today.year - 1, 1, 1)
        prev_end = date(today.year - 1, 12, 31)

        ytd_invoices = Move.search(base_domain + [('invoice_date', '>=', ytd_start)])
        ytd_total = sum(inv.amount_untaxed_signed for inv in ytd_invoices)

        prev_invoices = Move.search(base_domain + [
            ('invoice_date', '>=', prev_start),
            ('invoice_date', '<=', prev_end),
        ])
        prev_year_total = sum(inv.amount_untaxed_signed for inv in prev_invoices)

        all_invoices = Move.search(base_domain)
        all_time_total = sum(inv.amount_untaxed_signed for inv in all_invoices)

        last_order = request.env['sale.order'].sudo().search([
            ('partner_id', 'in', p_ids),
            ('state', 'in', ['sale', 'done']),
        ], order='date_order desc', limit=1)

        return {
            'ytd_total': round(ytd_total, 2),
            'prev_year_total': round(prev_year_total, 2),
            'all_time_total': round(all_time_total, 2),
            'last_order_date': str(last_order.date_order) if last_order and last_order.date_order else '',
            'last_order_ref': last_order.name if last_order else '',
            'currency': 'EUR',
        }

    @http.route('/cf/mail/v3/insight360/orders', type='json', auth='user')
    def insight360_orders(self, **kw):
        partner_id = int(kw.get('partner_id') or 0)
        if not partner_id:
            return {'orders': []}
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {'orders': []}
        orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner_id),
        ], order='date_order desc', limit=20)
        result = []
        for o in orders:
            result.append({
                'id': o.id,
                'name': o.name or '',
                'date_order': str(o.date_order) if o.date_order else '',
                'amount_total': o.amount_total or 0,
                'state': o.state or '',
                'currency': o.currency_id.name if o.currency_id else 'EUR',
            })
        return {'orders': result}

    @http.route('/cf/mail/v3/insight360/notes', type='json', auth='user', methods=['POST'])
    def insight360_notes(self, **kw):
        partner_id = int(kw.get('partner_id') or 0)
        new_comment = kw.get('new_comment')
        if not partner_id:
            return {'comment_plain': '', 'last_updated_date': ''}
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {'comment_plain': '', 'last_updated_date': ''}
        if new_comment is not None:
            partner.sudo().write({'comment': new_comment})
            return {'success': True}
        return {
            'comment_plain': partner.comment or '',
            'last_updated_date': str(partner.write_date)[:10] if partner.write_date else '',
        }

    @http.route('/cf/mail/v3/insight360/activities', type='json', auth='user')
    def insight360_activities(self, **kw):
        partner_id = int(kw.get('partner_id') or 0)
        if not partner_id:
            return {'activities': []}
        activities = request.env['mail.activity'].sudo().search([
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', partner_id),
        ], order='date_deadline asc')
        result = []
        for a in activities:
            result.append({
                'id': a.id,
                'summary': a.summary or a.note or '',
                'activity_type_name': a.activity_type_id.name if a.activity_type_id else '',
                'date_deadline': str(a.date_deadline) if a.date_deadline else '',
                'user_name': a.user_id.name if a.user_id else '',
                'state': a.state or '',
            })
        return {'activities': result}

    @http.route('/cf/mail/v3/insight360/products', type='json', auth='user')
    def insight360_products(self, **kw):
        partner_id = int(kw.get('partner_id') or 0)
        if not partner_id:
            return {'products': []}
        try:
            cr = request.env.cr
            cr.execute("""
                SELECT pt.name->>'en_US' as product_name,
                       SUM(sol.product_uom_qty) as qty_total,
                       MAX(so.date_order) as last_order_date,
                       SUM(sol.price_subtotal) as total_amount
                FROM sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id
                JOIN product_product pp ON pp.id = sol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE so.partner_id = %s
                  AND so.state IN ('sale', 'done')
                GROUP BY pt.id, pt.name
                ORDER BY qty_total DESC
                LIMIT 10
            """, (partner_id,))
            rows = cr.dictfetchall()
            products = []
            for r in rows:
                products.append({
                    'product_name': r['product_name'] or '',
                    'qty_total': round(r['qty_total'] or 0, 1),
                    'last_order_date': str(r['last_order_date'])[:10] if r['last_order_date'] else '',
                    'total_amount': round(r['total_amount'] or 0, 2),
                })
            return {'products': products}
        except Exception as e:
            _logger.warning('[insight360] products error: %s', e)
            return {'products': []}

    @http.route('/cf/mail/v3/insight360/ai_insight', type='json', auth='user')
    def insight360_ai_insight(self, **kw):
        thread_id = int(kw.get('thread_id') or 0)
        if not thread_id:
            return {'intent': 'N/D', 'sentiment': 'N/D', 'hotness_score': 'N/D'}
        thread = request.env['casafolino.mail.thread'].browse(thread_id)
        if not thread.exists():
            return {'intent': 'N/D', 'sentiment': 'N/D', 'hotness_score': 'N/D'}
        # Get last message
        last_msg = request.env['casafolino.mail.message'].search([
            ('thread_id', '=', thread_id),
            ('is_deleted', '=', False),
        ], order='email_date desc', limit=1)
        if not last_msg:
            return {'intent': 'N/D', 'sentiment': 'N/D', 'hotness_score': 'N/D'}

        # Defensive getattr for all AI fields
        intent = getattr(last_msg, 'intent_detected', None) or 'N/D'
        sentiment = getattr(last_msg, 'sentiment', None) or 'N/D'

        # Hotness from thread or intel
        hotness_score = getattr(thread, 'hotness_snapshot', None) or 0
        hotness_tier = ''
        if hotness_score >= 80:
            hotness_tier = 'hot'
        elif hotness_score >= 60:
            hotness_tier = 'warm'
        elif hotness_score >= 40:
            hotness_tier = 'active'
        elif hotness_score >= 20:
            hotness_tier = 'cold'
        elif hotness_score > 0:
            hotness_tier = 'dormant'

        classification_date = getattr(last_msg, 'classification_date', None)
        if not classification_date:
            classification_date = getattr(last_msg, 'write_date', None)

        suggested = getattr(last_msg, 'suggested_reply_hint', None) or ''

        return {
            'intent': intent,
            'sentiment': sentiment,
            'hotness_score': hotness_score,
            'hotness_tier': hotness_tier,
            'last_ai_classification_date': str(classification_date)[:10] if classification_date else '',
            'suggested_reply_hint': suggested,
        }

    @http.route('/cf/mail/v3/insight360/create_contact', type='json', auth='user', methods=['POST'])
    def insight360_create_contact(self, **kw):
        email = kw.get('email', '').strip()
        name = kw.get('name', '').strip()
        company_name = kw.get('company_name', '').strip()
        thread_id = int(kw.get('thread_id') or 0)

        if not email:
            return {'success': False, 'message': 'Email richiesta'}

        # Check existing
        existing = request.env['res.partner'].search([
            ('email', '=ilike', email),
        ], limit=1)
        if existing:
            # Link to thread if needed
            if thread_id:
                thread = request.env['casafolino.mail.thread'].browse(thread_id)
                if thread.exists() and existing.id not in thread.partner_ids.ids:
                    thread.write({'partner_ids': [(4, existing.id)]})
            return {'success': True, 'partner_id': existing.id, 'message': 'Contatto esistente collegato'}

        vals = {
            'name': name or email.split('@')[0],
            'email': email,
            'is_company': False,
        }

        # Company handling
        if company_name:
            company = request.env['res.partner'].search([
                ('name', '=ilike', company_name),
                ('is_company', '=', True),
            ], limit=1)
            if not company:
                company = request.env['res.partner'].create({
                    'name': company_name,
                    'is_company': True,
                })
            vals['parent_id'] = company.id

        partner = request.env['res.partner'].create(vals)

        # Link to thread
        if thread_id:
            thread = request.env['casafolino.mail.thread'].browse(thread_id)
            if thread.exists():
                thread.write({'partner_ids': [(4, partner.id)]})

        return {'success': True, 'partner_id': partner.id, 'message': 'Contatto creato'}

    # ── V14: Folder endpoints ─────────────────────────────────────────

    @http.route('/cf/mail/v3/folders/list', type='json', auth='user')
    def folders_list(self, **kw):
        """Return folder tree for user's accounts."""
        user_accounts = self._get_user_account_ids()
        if not user_accounts:
            return {'folders': []}

        Folder = request.env['casafolino.mail.folder']
        folders = Folder.search([
            ('account_id', 'in', user_accounts),
        ], order='account_id, sequence, id')

        result = []
        for f in folders:
            result.append({
                'id': f.id,
                'name': f.name,
                'account_id': f.account_id.id,
                'account_name': f.account_id.name,
                'icon': f.icon or '',
                'color': f.color,
                'sequence': f.sequence,
                'is_system': f.is_system,
                'system_code': f.system_code or '',
                'parent_folder_id': f.parent_folder_id.id if f.parent_folder_id else False,
                'folder_path': f.folder_path or f.name,
                'message_count': f.message_count,
                'unread_count': f.unread_count,
            })

        return {'folders': result}

    @http.route('/cf/mail/v3/folder/create', type='json', auth='user', methods=['POST'])
    def folder_create(self, **kw):
        """Create a custom folder."""
        name = (kw.get('name') or '').strip()
        account_id = int(kw.get('account_id') or 0)
        parent_folder_id = int(kw.get('parent_folder_id') or 0) or False
        icon = kw.get('icon', '\U0001f4c1')
        color = int(kw.get('color') or 0)

        if not name or not account_id:
            return {'success': False, 'message': 'Nome e account richiesti'}

        user_accounts = self._get_user_account_ids()
        if account_id not in user_accounts:
            return {'success': False, 'message': 'Account non autorizzato'}

        try:
            folder = request.env['casafolino.mail.folder'].create({
                'name': name,
                'account_id': account_id,
                'parent_folder_id': parent_folder_id,
                'icon': icon,
                'color': color,
                'is_system': False,
            })
            return {'success': True, 'folder_id': folder.id}
        except Exception as e:
            return {'success': False, 'message': str(e)[:200]}

    @http.route('/cf/mail/v3/folder/rename', type='json', auth='user', methods=['POST'])
    def folder_rename(self, **kw):
        """Rename a custom folder."""
        folder_id = int(kw.get('folder_id') or 0)
        name = (kw.get('name') or '').strip()

        if not folder_id or not name:
            return {'success': False, 'message': 'ID e nome richiesti'}

        folder = request.env['casafolino.mail.folder'].browse(folder_id)
        if not folder.exists():
            return {'success': False, 'message': 'Cartella non trovata'}
        if folder.account_id.id not in self._get_user_account_ids():
            return {'success': False, 'message': 'Non autorizzato'}
        if folder.is_system:
            return {'success': False, 'message': 'Cartella di sistema non rinominabile'}

        folder.write({'name': name})
        return {'success': True}

    @http.route('/cf/mail/v3/folder/delete', type='json', auth='user', methods=['POST'])
    def folder_delete(self, **kw):
        """Delete a custom folder, moving messages to inbox."""
        folder_id = int(kw.get('folder_id') or 0)

        folder = request.env['casafolino.mail.folder'].browse(folder_id)
        if not folder.exists():
            return {'success': False, 'message': 'Cartella non trovata'}
        if folder.account_id.id not in self._get_user_account_ids():
            return {'success': False, 'message': 'Non autorizzato'}
        if folder.is_system:
            return {'success': False, 'message': 'Cartella di sistema non eliminabile'}

        folder.action_delete_folder()
        return {'success': True}

    @http.route('/cf/mail/v3/message/move_to_folder', type='json', auth='user', methods=['POST'])
    def message_move_to_folder(self, **kw):
        """Move a message to a different folder."""
        message_id = int(kw.get('message_id') or 0)
        folder_id = int(kw.get('folder_id') or 0)

        msg = request.env['casafolino.mail.message'].browse(message_id)
        if not msg.exists():
            return {'success': False, 'message': 'Messaggio non trovato'}

        folder = request.env['casafolino.mail.folder'].browse(folder_id)
        if not folder.exists():
            return {'success': False, 'message': 'Cartella non trovata'}
        if folder.account_id.id not in self._get_user_account_ids():
            return {'success': False, 'message': 'Non autorizzato'}

        msg.write({'folder_id': folder_id})
        return {'success': True}

    @http.route('/cf/mail/v3/thread/move_to_folder', type='json', auth='user', methods=['POST'])
    def thread_move_to_folder(self, **kw):
        """Move all messages of a thread to a folder."""
        thread_id = int(kw.get('thread_id') or 0)
        folder_id = int(kw.get('folder_id') or 0)

        thread = request.env['casafolino.mail.thread'].browse(thread_id)
        if not thread.exists() or not self._check_thread_ownership(thread):
            return {'success': False, 'message': 'Thread non trovato'}

        folder = request.env['casafolino.mail.folder'].browse(folder_id)
        if not folder.exists():
            return {'success': False, 'message': 'Cartella non trovata'}

        thread.message_ids.filtered(lambda m: not m.is_deleted).write({
            'folder_id': folder_id,
        })
        return {'success': True}

    # ═══════════════════════════════════════════════════════════════
    # V15: Mass Actions with Undo
    # ═══════════════════════════════════════════════════════════════

    def _validate_mass_threads(self, thread_ids):
        """Validate thread_ids belong to current user. Returns filtered recordset."""
        if not thread_ids:
            return None
        user_accounts = self._get_user_account_ids()
        threads = request.env['casafolino.mail.thread'].browse(thread_ids).filtered(
            lambda t: t.exists() and t.account_id.id in user_accounts
        )
        return threads if threads else None

    @http.route('/cf/mail/v3/mass_action/move', type='json', auth='user', methods=['POST'])
    def mass_action_move(self, **kw):
        """Move threads to a folder with undo support."""
        thread_ids = kw.get('thread_ids', [])
        folder_id = int(kw.get('folder_id') or 0)

        threads = self._validate_mass_threads(thread_ids)
        if not threads:
            return {'success': False, 'error': 'No valid threads'}

        folder = request.env['casafolino.mail.folder'].browse(folder_id)
        if not folder.exists():
            return {'success': False, 'error': 'Folder not found'}

        # Snapshot previous state for undo
        previous_state = {}
        for t in threads:
            msgs = t.message_ids.filtered(lambda m: not m.is_deleted)
            if msgs:
                previous_state[str(t.id)] = {
                    'folder_ids': {str(m.id): m.folder_id.id for m in msgs},
                }

        # Move all messages to target folder
        for t in threads:
            t.message_ids.filtered(lambda m: not m.is_deleted).write({
                'folder_id': folder_id,
            })

        # Create undo log
        MassLog = request.env['casafolino.mail.mass.action.log']
        token = MassLog.create_log('move', thread_ids, previous_state)

        return {
            'success': True,
            'processed': len(threads),
            'undo_token': token,
            'folder_name': folder.name,
        }

    @http.route('/cf/mail/v3/mass_action/archive', type='json', auth='user', methods=['POST'])
    def mass_action_archive(self, **kw):
        """Archive threads with undo support."""
        thread_ids = kw.get('thread_ids', [])

        threads = self._validate_mass_threads(thread_ids)
        if not threads:
            return {'success': False, 'error': 'No valid threads'}

        # Snapshot previous state
        previous_state = {}
        archive_folder_cache = {}
        for t in threads:
            msgs = t.message_ids.filtered(lambda m: not m.is_deleted)
            if msgs:
                previous_state[str(t.id)] = {
                    'folder_ids': {str(m.id): m.folder_id.id for m in msgs},
                    'archived': {str(m.id): m.is_archived for m in msgs},
                }

        # Archive: set is_archived + move to archive folder
        for t in threads:
            account_id = t.account_id.id
            if account_id not in archive_folder_cache:
                af = request.env['casafolino.mail.folder'].search([
                    ('account_id', '=', account_id),
                    ('system_code', '=', 'archive'),
                ], limit=1)
                archive_folder_cache[account_id] = af.id if af else False

            msgs = t.message_ids.filtered(lambda m: not m.is_deleted)
            vals = {'is_archived': True}
            if archive_folder_cache[account_id]:
                vals['folder_id'] = archive_folder_cache[account_id]
            msgs.write(vals)
            t._recompute_aggregates()

        MassLog = request.env['casafolino.mail.mass.action.log']
        token = MassLog.create_log('archive', thread_ids, previous_state)

        return {
            'success': True,
            'processed': len(threads),
            'undo_token': token,
        }

    @http.route('/cf/mail/v3/mass_action/trash', type='json', auth='user', methods=['POST'])
    def mass_action_trash(self, **kw):
        """Move threads to trash with undo support."""
        thread_ids = kw.get('thread_ids', [])

        threads = self._validate_mass_threads(thread_ids)
        if not threads:
            return {'success': False, 'error': 'No valid threads'}

        # Snapshot previous state
        previous_state = {}
        trash_folder_cache = {}
        for t in threads:
            msgs = t.message_ids.filtered(lambda m: not m.is_deleted)
            if msgs:
                previous_state[str(t.id)] = {
                    'folder_ids': {str(m.id): m.folder_id.id for m in msgs},
                    'deleted': {str(m.id): m.is_deleted for m in msgs},
                    'deleted_at': {str(m.id): str(m.is_deleted_at) if m.is_deleted_at else False for m in msgs},
                }

        # Trash: set is_deleted + is_deleted_at + move to trash folder
        now = fields.Datetime.now()
        for t in threads:
            account_id = t.account_id.id
            if account_id not in trash_folder_cache:
                tf = request.env['casafolino.mail.folder'].search([
                    ('account_id', '=', account_id),
                    ('system_code', '=', 'trash'),
                ], limit=1)
                trash_folder_cache[account_id] = tf.id if tf else False

            msgs = t.message_ids.filtered(lambda m: not m.is_deleted)
            vals = {
                'is_deleted': True,
                'is_deleted_at': now,
            }
            if trash_folder_cache[account_id]:
                vals['folder_id'] = trash_folder_cache[account_id]
            msgs.write(vals)
            t._recompute_aggregates()

        MassLog = request.env['casafolino.mail.mass.action.log']
        token = MassLog.create_log('trash', thread_ids, previous_state)

        return {
            'success': True,
            'processed': len(threads),
            'undo_token': token,
        }

    @http.route('/cf/mail/v3/mass_action/mark_read', type='json', auth='user', methods=['POST'])
    def mass_action_mark_read(self, **kw):
        """Mark all messages in threads as read with undo support."""
        thread_ids = kw.get('thread_ids', [])

        threads = self._validate_mass_threads(thread_ids)
        if not threads:
            return {'success': False, 'error': 'No valid threads'}

        # Snapshot previous read state
        previous_state = {}
        for t in threads:
            msgs = t.message_ids.filtered(lambda m: not m.is_deleted)
            if msgs:
                previous_state[str(t.id)] = {
                    'read': {str(m.id): m.is_read for m in msgs},
                }

        # Mark read
        for t in threads:
            msgs = t.message_ids.filtered(lambda m: not m.is_deleted and not m.is_read)
            if msgs:
                msgs.write({'is_read': True})

        MassLog = request.env['casafolino.mail.mass.action.log']
        token = MassLog.create_log('mark_read', thread_ids, previous_state)

        return {
            'success': True,
            'processed': len(threads),
            'undo_token': token,
        }

    @http.route('/cf/mail/v3/mass_action/dismiss_senders', type='json', auth='user', methods=['POST'])
    def mass_action_dismiss_senders(self, **kw):
        """Dismiss all inbound senders from selected threads."""
        thread_ids = kw.get('thread_ids', [])

        threads = self._validate_mass_threads(thread_ids)
        if not threads:
            return {'success': False, 'error': 'No valid threads'}

        # Collect unique sender emails from inbound messages
        sender_emails = set()
        for t in threads:
            for m in t.message_ids.filtered(lambda m: not m.is_deleted):
                direction = m.direction or m.direction_computed or 'inbound'
                if direction == 'inbound' and m.sender_email:
                    sender_emails.add(m.sender_email.lower().strip())

        if not sender_emails:
            return {'success': False, 'error': 'No inbound senders found'}

        # Snapshot previous preferences for undo
        previous_state = {'dismissed_emails': []}
        Preference = request.env['casafolino.mail.sender_preference']
        user_accounts = self._get_user_account_ids()

        for email_addr in sender_emails:
            for account_id in user_accounts:
                pref = Preference.search([
                    ('account_id', '=', account_id),
                    ('email', '=', email_addr),
                ], limit=1)
                if pref:
                    if pref.status != 'dismissed':
                        previous_state['dismissed_emails'].append({
                            'email': email_addr,
                            'account_id': account_id,
                            'prev_status': pref.status,
                            'pref_id': pref.id,
                        })
                        pref.write({
                            'status': 'dismissed',
                            'decided_at': fields.Datetime.now(),
                        })
                else:
                    new_pref = Preference.create({
                        'account_id': account_id,
                        'email': email_addr,
                        'status': 'dismissed',
                        'decided_at': fields.Datetime.now(),
                    })
                    previous_state['dismissed_emails'].append({
                        'email': email_addr,
                        'account_id': account_id,
                        'prev_status': None,
                        'pref_id': new_pref.id,
                    })

        MassLog = request.env['casafolino.mail.mass.action.log']
        token = MassLog.create_log('dismiss', thread_ids, previous_state)

        return {
            'success': True,
            'processed': len(sender_emails),
            'undo_token': token,
            'dismissed_count': len(sender_emails),
        }

    @http.route('/cf/mail/v3/mass_action/permanent_delete', type='json', auth='user', methods=['POST'])
    def mass_action_permanent_delete(self, **kw):
        """Permanently delete threads (from trash only). No undo."""
        thread_ids = kw.get('thread_ids', [])

        threads = self._validate_mass_threads(thread_ids)
        if not threads:
            return {'success': False, 'error': 'No valid threads'}

        deleted = 0
        for t in threads:
            # Only allow permanent delete for messages in trash
            trash_msgs = t.message_ids.filtered(lambda m: m.is_deleted)
            if trash_msgs:
                trash_msgs.unlink()
                deleted += len(trash_msgs)
            # If thread has no messages left, delete thread too
            if t.exists() and not t.message_ids:
                t.unlink()

        return {
            'success': True,
            'deleted': deleted,
        }

    @http.route('/cf/mail/v3/mass_action/undo', type='json', auth='user', methods=['POST'])
    def mass_action_undo(self, **kw):
        """Undo a mass action using the undo token."""
        token = kw.get('token', '')
        if not token:
            return {'success': False, 'error': 'Token required'}

        MassLog = request.env['casafolino.mail.mass.action.log']
        log = MassLog.search([
            ('token', '=', token),
            ('user_id', '=', request.env.uid),
            ('expires_at', '>', fields.Datetime.now()),
        ], limit=1)

        if not log:
            return {'success': False, 'error': 'Token expired or not found'}

        prev = log.get_previous_state()
        action_type = log.action_type

        if action_type == 'move':
            # Restore folder_ids
            for thread_id_str, state in prev.items():
                folder_ids = state.get('folder_ids', {})
                for msg_id_str, fid in folder_ids.items():
                    msg = request.env['casafolino.mail.message'].browse(int(msg_id_str))
                    if msg.exists():
                        msg.write({'folder_id': fid or False})

        elif action_type == 'archive':
            for thread_id_str, state in prev.items():
                folder_ids = state.get('folder_ids', {})
                archived = state.get('archived', {})
                for msg_id_str in folder_ids:
                    msg = request.env['casafolino.mail.message'].browse(int(msg_id_str))
                    if msg.exists():
                        msg.write({
                            'folder_id': folder_ids[msg_id_str] or False,
                            'is_archived': archived.get(msg_id_str, False),
                        })
                thread = request.env['casafolino.mail.thread'].browse(int(thread_id_str))
                if thread.exists():
                    thread._recompute_aggregates()

        elif action_type == 'trash':
            for thread_id_str, state in prev.items():
                folder_ids = state.get('folder_ids', {})
                deleted = state.get('deleted', {})
                deleted_at = state.get('deleted_at', {})
                for msg_id_str in folder_ids:
                    msg = request.env['casafolino.mail.message'].browse(int(msg_id_str))
                    if msg.exists():
                        dat = deleted_at.get(msg_id_str)
                        msg.write({
                            'folder_id': folder_ids[msg_id_str] or False,
                            'is_deleted': deleted.get(msg_id_str, False),
                            'is_deleted_at': dat if dat and dat != 'False' else False,
                        })
                thread = request.env['casafolino.mail.thread'].browse(int(thread_id_str))
                if thread.exists():
                    thread._recompute_aggregates()

        elif action_type == 'mark_read':
            for thread_id_str, state in prev.items():
                read_state = state.get('read', {})
                for msg_id_str, was_read in read_state.items():
                    msg = request.env['casafolino.mail.message'].browse(int(msg_id_str))
                    if msg.exists():
                        msg.write({'is_read': was_read})

        elif action_type == 'dismiss':
            dismissed_emails = prev.get('dismissed_emails', [])
            Preference = request.env['casafolino.mail.sender_preference']
            for entry in dismissed_emails:
                pref = Preference.browse(entry.get('pref_id'))
                if pref.exists():
                    if entry.get('prev_status') is None:
                        pref.unlink()
                    else:
                        pref.write({
                            'status': entry['prev_status'],
                            'decided_at': fields.Datetime.now(),
                        })

        # Delete the log entry (one-time use)
        log.unlink()

        return {'success': True}

    @http.route('/cf/mail/v3/mass_action/folders_for_move', type='json', auth='user')
    def mass_action_folders_for_move(self, **kw):
        """Get folders available for move, excluding current folder."""
        account_ids = kw.get('account_ids', [])
        exclude_folder_id = kw.get('exclude_folder_id')

        if not account_ids:
            account_ids = self._get_user_account_ids()

        domain = [('account_id', 'in', account_ids)]
        if exclude_folder_id:
            domain.append(('id', '!=', int(exclude_folder_id)))

        folders = request.env['casafolino.mail.folder'].search(
            domain, order='is_system desc, sequence asc, name asc')

        result = []
        for f in folders:
            result.append({
                'id': f.id,
                'name': f.name,
                'icon': f.icon or '',
                'is_system': f.is_system,
                'system_code': f.system_code or '',
                'account_id': f.account_id.id,
                'account_name': f.account_id.name or '',
            })

        return {'folders': result}

    # ── V17: Browser Notifications — Poll Unread ───────────────────

    @http.route('/cf/mail/v3/poll/unread', type='json', auth='user')
    def poll_unread(self, **kw):
        """Lightweight endpoint for browser notification polling."""
        account_ids = self._get_user_account_ids()
        if not account_ids:
            return {'unread_count': 0, 'new_since_last_poll': 0}

        last_check = kw.get('last_check')  # ISO datetime string from client

        Message = request.env['casafolino.mail.message']
        # Total unread count (non-deleted, non-archived, inbound, unread)
        unread_domain = [
            ('account_id', 'in', account_ids),
            ('direction', '=', 'inbound'),
            ('is_read', '=', False),
            ('is_deleted', '=', False),
            ('is_archived', '=', False),
        ]
        unread_count = Message.search_count(unread_domain)

        # New messages since last poll
        new_since = 0
        if last_check:
            try:
                new_domain = unread_domain + [('create_date', '>', last_check)]
                new_since = Message.search_count(new_domain)
            except Exception:
                pass

        return {
            'unread_count': unread_count,
            'new_since_last_poll': new_since,
            'server_time': str(fields.Datetime.now()),
        }

    # ── V17.1: Sync Status Badge ──────────────────────────────────

    @http.route('/cf/mail/v3/sync_status', type='json', auth='user')
    def sync_status(self, **kw):
        """Return sync status for current user's accounts."""
        Account = request.env['casafolino.mail.account']
        accounts = Account.search([
            ('responsible_user_id', '=', request.env.uid),
            ('active', '=', True),
        ])
        now = fields.Datetime.now()
        result = []
        worst_status = 'ok'

        for acct in accounts:
            last_ok = acct.last_successful_fetch_datetime
            if last_ok:
                delta = (now - last_ok).total_seconds()
                minutes_ago = int(delta / 60)
            else:
                minutes_ago = 9999

            if acct.state == 'error' or minutes_ago > 30:
                status = 'error'
            elif minutes_ago > 10:
                status = 'delayed'
            else:
                status = 'ok'

            # Track worst status
            if status == 'error':
                worst_status = 'error'
            elif status == 'delayed' and worst_status != 'error':
                worst_status = 'delayed'

            result.append({
                'id': acct.id,
                'email': acct.email_address or '',
                'last_sync_at': str(last_ok) if last_ok else None,
                'minutes_ago': minutes_ago,
                'status': status,
                'error_message': acct.error_message if acct.state == 'error' else None,
            })

        return {
            'accounts': result,
            'global_status': worst_status,
        }

    @http.route('/cf/mail/v3/sync_status/force', type='json', auth='user')
    def sync_force(self, **kw):
        """Force immediate IMAP fetch for current user's accounts."""
        Account = request.env['casafolino.mail.account'].sudo()
        accounts = Account.search([
            ('responsible_user_id', '=', request.env.uid),
            ('active', '=', True),
        ])
        if not accounts:
            return {'success': False, 'error': 'Nessun account trovato'}

        for acct in accounts:
            try:
                acct._fetch_emails()
            except Exception as e:
                _logger.warning("[sync force] Fetch error for %s: %s", acct.email_address, e)

        return {'success': True, 'message': 'Sync completato'}
