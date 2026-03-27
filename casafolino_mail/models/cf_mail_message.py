from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CfMailMessage(models.Model):
    _name = 'cf.mail.message'
    _description = 'Messaggio Email CasaFolino'
    _order = 'date desc, id desc'

    account_id = fields.Many2one('cf.mail.account', string='Account', required=True, ondelete='cascade')
    subject = fields.Char('Oggetto', default='(nessun oggetto)')
    from_address = fields.Char('Da')
    from_name = fields.Char('Nome mittente')
    to_address = fields.Char('A')
    cc_address = fields.Char('CC')
    body_html = fields.Html('Corpo HTML', sanitize=False)
    body_text = fields.Text('Corpo testo')
    snippet = fields.Char('Anteprima')
    date = fields.Datetime('Data', default=fields.Datetime.now)
    is_read = fields.Boolean('Letta', default=False)
    is_starred = fields.Boolean('Preferita', default=False)
    is_archived = fields.Boolean('Archiviata', default=False)
    direction = fields.Selection([('in', 'In entrata'), ('out', 'In uscita')], default='in')
    folder = fields.Char('Cartella', default='INBOX')
    message_uid = fields.Char('UID IMAP')
    thread_id = fields.Char('Thread ID')
    partner_id = fields.Many2one('res.partner', string='Contatto')
    lead_id = fields.Many2one('cf.export.lead', string='Trattativa CRM')
    assigned_user_id = fields.Many2one('res.users', string='Assegnata a')
    tag_ids = fields.Many2many('cf.mail.tag', string='Tag')
    snoozed_until = fields.Datetime('Posticipata fino a')
    has_attachments = fields.Boolean('Ha allegati', default=False)

    def action_mark_read(self):
        self.write({'is_read': True})

    def action_mark_unread(self):
        self.write({'is_read': False})

    def action_archive_msg(self):
        self.write({'is_archived': True})

    def _msg_to_dict(self, m):
        tags = [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in m.tag_ids]
        thread_count = 0
        if m.thread_id:
            thread_count = self.search_count([('thread_id', '=', m.thread_id), ('id', '!=', m.id)])
        return {
            'id': m.id,
            'subject': m.subject or '(nessun oggetto)',
            'from_address': m.from_address or '',
            'from_name': m.from_name or m.from_address or '',
            'snippet': m.snippet or '',
            'date': m.date.strftime('%d/%m/%Y %H:%M') if m.date else '',
            'date_short': m.date.strftime('%d %b') if m.date else '',
            'is_read': m.is_read,
            'is_starred': m.is_starred,
            'is_archived': m.is_archived,
            'direction': m.direction,
            'folder': m.folder or 'INBOX',
            'has_attachments': m.has_attachments,
            'thread_count': thread_count,
            'partner_id': m.partner_id.id if m.partner_id else False,
            'partner_name': m.partner_id.name if m.partner_id else '',
            'lead_id': m.lead_id.id if m.lead_id else False,
            'lead_name': m.lead_id.name if m.lead_id else '',
            'assigned_user_id': m.assigned_user_id.id if m.assigned_user_id else False,
            'assigned_user_name': m.assigned_user_id.name if m.assigned_user_id else '',
            'tags': tags,
        }

    @api.model
    def get_messages(self, *args, **kw):
        account_id = kw.get('account_id')
        folder = kw.get('folder') or 'INBOX'
        limit = int(kw.get('limit') or 50)
        offset = int(kw.get('offset') or 0)
        search = kw.get('search') or ''
        tag_id = kw.get('tag_id') or False

        domain = [('account_id', '=', account_id), ('is_archived', '=', False)]
        if folder == 'Starred':
            domain.append(('is_starred', '=', True))
        elif folder == 'Sent':
            domain.append(('direction', '=', 'out'))
        elif folder == 'Archived':
            domain = [('account_id', '=', account_id), ('is_archived', '=', True)]
        elif folder == 'Assigned':
            domain.append(('assigned_user_id', '=', self.env.uid))
        elif folder.startswith('TAG_'):
            try:
                tid = int(folder.replace('TAG_', ''))
                domain.append(('tag_ids', 'in', [tid]))
            except Exception:
                pass
        else:
            domain.append(('folder', '=', folder))

        if search:
            domain += ['|', '|', '|',
                ('subject', 'ilike', search),
                ('from_address', 'ilike', search),
                ('from_name', 'ilike', search),
                ('snippet', 'ilike', search),
            ]

        msgs = self.search(domain, limit=limit, offset=offset)
        return [self._msg_to_dict(m) for m in msgs]

    @api.model
    def get_message_detail(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return {}
        msg = self.browse(int(message_id))
        if not msg.exists():
            return {}
        if not msg.is_read:
            msg.action_mark_read()

        partner_orders = []
        partner_leads = []
        partner_other_emails = []
        if msg.partner_id:
            try:
                leads = self.env['cf.export.lead'].search([('partner_id', '=', msg.partner_id.id)], limit=5)
                for l in leads:
                    partner_leads.append({'id': l.id, 'name': l.name, 'stage': l.stage_id.name if l.stage_id else ''})
            except Exception:
                pass
            try:
                orders = self.env['sale.order'].search([('partner_id', '=', msg.partner_id.id)], limit=5, order='date_order desc')
                for o in orders:
                    partner_orders.append({'id': o.id, 'name': o.name, 'amount': o.amount_total, 'currency': o.currency_id.symbol or '€'})
            except Exception:
                pass
            other_msgs = self.search([('partner_id', '=', msg.partner_id.id), ('id', '!=', msg.id)], limit=5, order='date desc')
            for om in other_msgs:
                partner_other_emails.append({
                    'id': om.id,
                    'subject': om.subject or '(nessun oggetto)',
                    'date_short': om.date.strftime('%d %b') if om.date else '',
                    'direction': om.direction,
                })

        tags = [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in msg.tag_ids]

        thread_messages = []
        if msg.thread_id:
            thread_msgs = self.search([('thread_id', '=', msg.thread_id), ('id', '!=', msg.id)], order='date asc')
            for tm in thread_msgs:
                thread_messages.append({
                    'id': tm.id,
                    'from_name': tm.from_name or tm.from_address or '',
                    'from_address': tm.from_address or '',
                    'date': tm.date.strftime('%d/%m/%Y %H:%M') if tm.date else '',
                    'body_html': tm.body_html or tm.body_text or '',
                    'direction': tm.direction,
                })

        return {
            'id': msg.id,
            'subject': msg.subject or '(nessun oggetto)',
            'from_address': msg.from_address or '',
            'from_name': msg.from_name or msg.from_address or '',
            'to_address': msg.to_address or '',
            'cc_address': msg.cc_address or '',
            'body_html': msg.body_html or msg.body_text or '',
            'date': msg.date.strftime('%d/%m/%Y %H:%M') if msg.date else '',
            'is_read': msg.is_read,
            'is_starred': msg.is_starred,
            'direction': msg.direction,
            'has_attachments': msg.has_attachments,
            'partner_id': msg.partner_id.id if msg.partner_id else False,
            'partner_name': msg.partner_id.name if msg.partner_id else '',
            'partner_email': msg.partner_id.email if msg.partner_id else '',
            'partner_phone': msg.partner_id.phone if msg.partner_id else '',
            'partner_company': msg.partner_id.parent_id.name if msg.partner_id and msg.partner_id.parent_id else '',
            'lead_id': msg.lead_id.id if msg.lead_id else False,
            'lead_name': msg.lead_id.name if msg.lead_id else '',
            'assigned_user_id': msg.assigned_user_id.id if msg.assigned_user_id else False,
            'assigned_user_name': msg.assigned_user_id.name if msg.assigned_user_id else '',
            'partner_leads': partner_leads,
            'partner_orders': partner_orders,
            'partner_other_emails': partner_other_emails,
            'tags': tags,
            'thread_messages': thread_messages,
            'signature': msg.account_id.signature or '',
        }

    @api.model
    def do_bulk_action(self, *args, **kw):
        ids = kw.get('ids') or []
        action = kw.get('action') or ''
        tag_id = kw.get('tag_id') or False
        if not ids or not action:
            return False
        msgs = self.browse([int(i) for i in ids])
        if action == 'read':
            msgs.write({'is_read': True})
        elif action == 'unread':
            msgs.write({'is_read': False})
        elif action == 'star':
            msgs.write({'is_starred': True})
        elif action == 'unstar':
            msgs.write({'is_starred': False})
        elif action == 'archive':
            msgs.write({'is_archived': True})
        elif action == 'delete':
            msgs.unlink()
        elif action == 'add_tag' and tag_id:
            for m in msgs:
                m.tag_ids = [(4, int(tag_id))]
        elif action == 'remove_tag' and tag_id:
            for m in msgs:
                m.tag_ids = [(3, int(tag_id))]
        return True

    @api.model
    def do_assign(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        user_id = kw.get('user_id') or (args[2] if len(args) > 2 else None)
        if not message_id:
            return False
        msg = self.browse(int(message_id))
        msg.write({'assigned_user_id': int(user_id) if user_id else False})
        return msg.assigned_user_id.name if msg.assigned_user_id else ''

    @api.model
    def do_link_lead(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        lead_id = kw.get('lead_id') or (args[2] if len(args) > 2 else None)
        if not message_id:
            return False
        msg = self.browse(int(message_id))
        msg.write({'lead_id': int(lead_id) if lead_id else False})
        return True

    @api.model
    def do_toggle_star(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return False
        msg = self.browse(int(message_id))
        msg.write({'is_starred': not msg.is_starred})
        return msg.is_starred

    @api.model
    def do_add_tag(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        tag_id = kw.get('tag_id') or (args[2] if len(args) > 2 else None)
        if not message_id or not tag_id:
            return False
        msg = self.browse(int(message_id))
        msg.tag_ids = [(4, int(tag_id))]
        return [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in msg.tag_ids]

    @api.model
    def do_remove_tag(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        tag_id = kw.get('tag_id') or (args[2] if len(args) > 2 else None)
        if not message_id or not tag_id:
            return False
        msg = self.browse(int(message_id))
        msg.tag_ids = [(3, int(tag_id))]
        return [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in msg.tag_ids]

    @api.model
    def do_snooze(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        until = kw.get('until') or (args[2] if len(args) > 2 else None)
        if not message_id:
            return False
        msg = self.browse(int(message_id))
        msg.write({'snoozed_until': until})
        return True

    @api.model
    def get_users_list(self, *args, **kw):
        users = self.env['res.users'].search([('share', '=', False), ('active', '=', True)])
        return [{'id': u.id, 'name': u.name} for u in users]

    @api.model
    def get_leads_list(self, *args, **kw):
        try:
            leads = self.env['cf.export.lead'].search([('active', '=', True)], limit=100, order='id desc')
            return [{'id': l.id, 'name': l.name} for l in leads]
        except Exception:
            return []

    @api.model
    def get_tags_list(self, *args, **kw):
        tags = self.env['cf.mail.tag'].search([])
        return [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in tags]

    @api.model
    def create_tag(self, *args, **kw):
        name = kw.get('name') or (args[1] if len(args) > 1 else None)
        color = kw.get('color') or '#5A6E3A'
        if not name:
            return False
        tag = self.env['cf.mail.tag'].create({'name': name, 'color': color})
        return {'id': tag.id, 'name': tag.name, 'color': tag.color}

    @api.model
    def send_reply(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        to_addr = kw.get('to_address') or ''
        subject = kw.get('subject') or ''
        body = kw.get('body') or ''
        account_id = kw.get('account_id') or None
        if not to_addr or not body:
            return {'success': False, 'error': 'Destinatario o corpo mancante'}
        try:
            acc = self.env['cf.mail.account'].browse(int(account_id)) if account_id else None
            from_email = acc.email if acc else self.env.user.email
            mail = self.env['mail.mail'].create({
                'subject': subject,
                'email_to': to_addr,
                'body_html': body,
                'email_from': from_email,
            })
            mail.send()
            thread_id = None
            if message_id:
                orig = self.browse(int(message_id))
                thread_id = orig.thread_id or str(orig.id)
            sent_msg = self.create({
                'account_id': int(account_id) if account_id else False,
                'subject': subject,
                'from_address': from_email,
                'to_address': to_addr,
                'body_html': body,
                'direction': 'out',
                'folder': 'Sent',
                'is_read': True,
                'thread_id': thread_id,
            })
            return {'success': True, 'id': sent_msg.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @api.model
    def get_crm_data(self, *args, **kw):
        # Pipeline (stages di cf.export.lead)
        try:
            stages = self.env['cf.export.stage'].search([], order='sequence')
            pipelines = [{'id': s.id, 'name': s.name} for s in stages]
        except Exception:
            pipelines = []
        # Partner list
        partners = self.env['res.partner'].search([('active', '=', True)], limit=100, order='name')
        partner_list = [{'id': p.id, 'name': p.name, 'email': p.email or ''} for p in partners]
        return {'pipelines': pipelines, 'partners': partner_list}

    @api.model
    def create_lead_from_form(self, *args, **kw):
        name = kw.get('name') or 'Lead da email'
        partner_id = kw.get('partner_id') or False
        stage_id = kw.get('stage_id') or False
        expected_revenue = kw.get('expected_revenue') or 0
        description = kw.get('description') or ''
        message_id = kw.get('message_id') or False
        try:
            vals = {
                'name': name,
                'partner_id': int(partner_id) if partner_id else False,
                'stage_id': int(stage_id) if stage_id else False,
                'expected_revenue': float(expected_revenue) if expected_revenue else 0,
                'description': description,
            }
            lead = self.env['cf.export.lead'].create(vals)
            if message_id:
                msg = self.browse(int(message_id))
                if msg.exists():
                    msg.write({'lead_id': lead.id})
                    if not msg.partner_id and partner_id:
                        msg.write({'partner_id': int(partner_id)})
            return {'success': True, 'lead_id': lead.id, 'lead_name': lead.name}
        except Exception as e:
            return {'success': False, 'error': str(e)}
