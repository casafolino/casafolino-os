import json
import logging
import re

from odoo import http
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

    @http.route('/cf/mail/v3/threads/list', type='json', auth='user')
    def threads_list(self, **kw):
        account_ids = kw.get('account_ids')
        state = kw.get('state', 'keep')
        limit = min(int(kw.get('limit', 50)), 200)
        offset = int(kw.get('offset', 0))
        filters = kw.get('filters', {})

        domain = []
        if account_ids:
            domain.append(('account_id', 'in', account_ids))
        else:
            # All accounts for current user
            accounts = request.env['casafolino.mail.account'].search([
                ('responsible_user_id', '=', request.env.uid),
                ('active', '=', True),
            ])
            if accounts:
                domain.append(('account_id', 'in', accounts.ids))

        # Filter archived
        if not filters.get('show_archived'):
            domain.append(('is_archived', '=', False))

        threads = request.env['casafolino.mail.thread'].search(
            domain, limit=limit, offset=offset,
            order='last_message_date desc')
        total = request.env['casafolino.mail.thread'].search_count(domain)

        result = []
        for t in threads:
            # Get main participant (first non-company email)
            try:
                participants = json.loads(t.participant_emails or '[]')
            except (json.JSONDecodeError, TypeError):
                participants = []

            company_domain = t.account_id.company_domain or 'casafolino.com'
            external = [p for p in participants if company_domain not in p]
            main_participant = external[0] if external else (participants[0] if participants else '')

            # Preview from last message
            last_msg = request.env['casafolino.mail.message'].search([
                ('thread_id', '=', t.id),
                ('is_deleted', '=', False),
            ], order='email_date desc', limit=1)

            preview = ''
            if last_msg and last_msg.snippet:
                preview = last_msg.snippet[:100]
            elif last_msg and last_msg.body_plain:
                preview = last_msg.body_plain[:100]

            # Silent days
            silent_days = 0
            if t.last_message_date:
                from odoo import fields as odoo_fields
                delta = odoo_fields.Datetime.now() - t.last_message_date
                silent_days = delta.days

            # Hotness from snapshot or partner intelligence
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

            # Attachment count
            att_count = 0
            if t.has_attachments:
                att_count = request.env['ir.attachment'].search_count([
                    ('res_model', '=', 'casafolino.mail.message'),
                    ('res_id', 'in', t.message_ids.ids),
                ])

            # Lead open
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

    @http.route('/cf/mail/v3/draft/create', type='json', auth='user')
    def draft_create(self, **kw):
        account_id = kw.get('account_id')
        in_reply_to_id = kw.get('in_reply_to_message_id')
        mode = kw.get('mode', 'new')  # reply, reply_all, forward, new

        if not account_id:
            # Use first account of user
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
                    # Reply to sender
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

                # Quoted body
                quote_date = str(orig.email_date)[:16] if orig.email_date else ''
                quote_from = orig.sender_name or orig.sender_email or ''
                prefilled['body_html'] = (
                    '<br><br>'
                    '<div style="border-left:2px solid #ccc;padding-left:12px;margin-left:4px;color:#666;">'
                    '<p>Il %s, %s ha scritto:</p>'
                    '%s'
                    '</div>' % (quote_date, quote_from, orig.body_html or orig.body_plain or '')
                )

        # Set signature
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

    @http.route('/cf/mail/v3/partner/<int:partner_id>/sidebar_360', type='json', auth='user')
    def partner_sidebar_360(self, partner_id, **kw):
        partner = request.env['res.partner'].browse(partner_id)
        if not partner.exists():
            return {}

        # Company info
        company = partner if partner.is_company else partner.parent_id
        person = partner if not partner.is_company else False

        # Company block
        company_data = {}
        if company and company.exists():
            # Hotness
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

        # Person block
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

        # Relation block
        relation_data = {}
        msg_domain = [
            ('partner_id', 'in', [partner_id] + (company.child_ids.ids if company else [])),
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
            'avg_response_time': '',
        }

        # Business block
        business_data = {}
        p_ids = [partner_id]
        if company:
            p_ids += company.child_ids.ids
            p_ids.append(company.id)
        p_ids = list(set(p_ids))

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

        # Quick actions
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
            'relation': relation_data,
            'business': business_data,
            'quick_actions': quick_actions,
        }

    @http.route('/cf/mail/v3/accounts/summary', type='json', auth='user')
    def accounts_summary(self, **kw):
        accounts = request.env['casafolino.mail.account'].search([
            ('responsible_user_id', '=', request.env.uid),
            ('active', '=', True),
        ])

        # Also include accounts where user is admin
        if request.env.user.has_group('casafolino_mail.group_mail_v3_admin'):
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
            result.append({
                'id': a.id,
                'name': a.name or a.email_address,
                'email': a.email_address or '',
                'unread_count': unread,
                'last_sync': str(a.last_fetch_datetime) if a.last_fetch_datetime else '',
                'state': a.state or 'draft',
            })

        return {'accounts': result}
