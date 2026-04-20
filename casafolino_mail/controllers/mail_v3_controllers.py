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

    # ── Thread List ──────────────────────────────────────────────────

    @http.route('/cf/mail/v3/threads/list', type='json', auth='user')
    def threads_list(self, **kw):
        account_ids = kw.get('account_ids')
        state = kw.get('state', 'keep')
        limit = min(int(kw.get('limit', 50)), 200)
        offset = int(kw.get('offset', 0))
        filters = kw.get('filters', {})
        folder = kw.get('folder')

        domain = []
        if account_ids:
            domain.append(('account_id', 'in', account_ids))

        if not filters.get('show_archived'):
            domain.append(('is_archived', '=', False))

        # Hide snoozed threads by default (unless viewing snoozed folder)
        if folder != 'snoozed':
            domain.append(('is_snoozed', '=', False))

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

        threads = request.env['casafolino.mail.thread'].search(
            domain, limit=limit, offset=offset,
            order='last_message_date desc')
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
                'partner_ids': t.partner_ids.ids,
            })

        return {'threads': result, 'total': total}

    # ── Thread Messages ──────────────────────────────────────────────

    @http.route('/cf/mail/v3/thread/<int:thread_id>/messages', type='json', auth='user')
    def thread_messages(self, thread_id, **kw):
        thread = request.env['casafolino.mail.thread'].browse(thread_id)
        if not thread.exists():
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
                'intent_detected': m.intent_detected or '',
                'partner_id': m.partner_id.id if m.partner_id else False,
                'partner_name': m.partner_id.name if m.partner_id else '',
                'attachment_ids': [{'id': a.id, 'name': a.name, 'mimetype': a.mimetype or ''}
                                    for a in m.attachment_ids],
                'message_id_rfc': m.message_id_rfc or '',
            })

        return {'messages': result}

    @http.route('/cf/mail/v3/thread/<int:thread_id>/mark_all_read', type='json', auth='user')
    def thread_mark_all_read(self, thread_id, **kw):
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
                    'intent': m.intent_detected or '',
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
        Message = request.env['casafolino.mail.message']
        accessible_ids = Message.search([
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
            msg.intent_detected or 'general',
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
            'target': 'new',
            'context': ctx,
        }

    # ── Smart Snooze ───────────────────────────���────────────────────

    @http.route('/cf/mail/v3/thread/<int:thread_id>/snooze', type='json', auth='user')
    def snooze_thread(self, thread_id, **kw):
        thread = request.env['casafolino.mail.thread'].browse(thread_id)
        if not thread.exists():
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

    # ── Bulk Actions ─────────────────────────��──────────────────────

    @http.route('/cf/mail/v3/threads/bulk', type='json', auth='user')
    def threads_bulk_action(self, **kw):
        action = kw.get('action')
        thread_ids = kw.get('thread_ids', [])
        if not action or not thread_ids:
            return {'success': False, 'error': 'Missing action or ids'}

        threads = request.env['casafolino.mail.thread'].browse(thread_ids)
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
        account_ids = kw.get('account_ids')
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
