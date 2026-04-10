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
    body_plain = fields.Text(string='Corpo plain',
        compute='_compute_body_plain', inverse='_inverse_body_plain')
    snippet = fields.Char('Anteprima')
    date = fields.Datetime('Data', default=fields.Datetime.now)
    is_read = fields.Boolean('Letta', default=False)
    is_starred = fields.Boolean('Preferita', default=False)
    is_archived = fields.Boolean('Archiviata', default=False)
    replied = fields.Boolean('Risposta inviata', default=False)
    direction = fields.Selection([('in', 'In entrata'), ('out', 'In uscita')], default='in')
    folder = fields.Char('Cartella', default='INBOX')
    message_uid = fields.Char('UID IMAP')
    thread_id = fields.Char('Thread ID')
    partner_id = fields.Many2one('res.partner', string='Contatto')
    lead_id = fields.Many2one('crm.lead', string='Trattativa CRM')
    export_lead_id = fields.Many2one('crm.lead', string='Trattativa',
        compute='_compute_export_lead_id', inverse='_inverse_export_lead_id', store=False)
    assigned_user_id = fields.Many2one('res.users', string='Assegnata a')
    tag_ids = fields.Many2many('cf.mail.tag', string='Tag')
    note = fields.Text('Note interne')
    snoozed_until = fields.Datetime('Posticipata fino a')
    has_attachments = fields.Boolean('Ha allegati', default=False)
    attachment_names = fields.Char('Allegati')

    @api.depends('body_text')
    def _compute_body_plain(self):
        for rec in self:
            rec.body_plain = rec.body_text

    def _inverse_body_plain(self):
        for rec in self:
            rec.body_text = rec.body_plain

    @api.depends('lead_id')
    def _compute_export_lead_id(self):
        for rec in self:
            rec.export_lead_id = rec.lead_id

    def _inverse_export_lead_id(self):
        for rec in self:
            rec.lead_id = rec.export_lead_id

    def action_mark_read(self):
        self.write({'is_read': True})

    def action_mark_unread(self):
        self.write({'is_read': False})

    def action_archive_msg(self):
        self.write({'is_archived': True})

    def action_archive_message(self):
        self.write({'is_archived': True})

    def action_star(self):
        for rec in self:
            rec.write({'is_starred': not rec.is_starred})

    def action_reply(self):
        return True

    def action_forward(self):
        return True

    def _msg_to_dict(self, m):
        tags = [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in m.tag_ids]
        sender_rule = self.env['cf.mail.sender.rule'].sudo().search(
            [('email', '=', (m.from_address or '').strip().lower())], limit=1)
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
            'replied': m.replied,
            'direction': m.direction,
            'folder': m.folder or 'INBOX',
            'has_attachments': m.has_attachments,
            'attachment_names': m.attachment_names or '',
            'thread_count': thread_count,
            'partner_id': m.partner_id.id if m.partner_id else False,
            'partner_name': m.partner_id.name if m.partner_id else '',
            'lead_id': m.lead_id.id if m.lead_id else False,
            'lead_name': m.lead_id.name if m.lead_id else '',
            'assigned_user_id': m.assigned_user_id.id if m.assigned_user_id else False,
            'assigned_user_name': m.assigned_user_id.name if m.assigned_user_id else '',
            'tags': tags,
            'lead_stage': m.lead_id.stage_id.name if m.lead_id and m.lead_id.stage_id else '',
            'sender_action': sender_rule.action if sender_rule else False,
        }

    @api.model
    def advanced_search(self, *args, **kw):
        query = kw.get('query') or ''
        folder = kw.get('folder') or 'INBOX'
        date_from = kw.get('date_from') or False
        date_to = kw.get('date_to') or False
        tag_id = kw.get('tag_id') or False
        has_attachments = kw.get('has_attachments') or False
        account_id = kw.get('account_id') or False
        is_admin = self.env.user.has_group('base.group_system') or self.env.user.login == 'antonio@casafolino.com'
        domain = []
        if not is_admin:
            user_accounts = self.env['cf.mail.account'].search([
                '|',
                ('user_id', '=', self.env.uid),
                ('is_team', '=', True),
            ])
            domain.append(('account_id', 'in', user_accounts.ids))
        elif account_id:
            domain.append(('account_id', '=', int(account_id)))
        if folder and folder != 'ALL':
            if folder == 'Starred':
                domain.append(('is_starred', '=', True))
            elif folder == 'Sent':
                domain.append(('direction', '=', 'out'))
            elif folder == 'Archived':
                domain.append(('is_archived', '=', True))
            else:
                domain += [('folder', '=', folder), ('is_archived', '=', False)]
        if query:
            domain += ['|', '|', '|', '|',
                ('subject', 'ilike', query),
                ('from_address', 'ilike', query),
                ('from_name', 'ilike', query),
                ('snippet', 'ilike', query),
                ('body_text', 'ilike', query),
            ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to + ' 23:59:59'))
        if tag_id:
            domain.append(('tag_ids', 'in', [int(tag_id)]))
        if has_attachments:
            domain.append(('has_attachments', '=', True))
        msgs = self.search(domain, limit=100, order='date desc')
        return [self._msg_to_dict(m) for m in msgs]

    @api.model
    def get_messages(self, *args, **kw):
        account_id = kw.get('account_id')
        folder = kw.get('folder') or 'INBOX'
        limit = int(kw.get('limit') or 50)
        offset = int(kw.get('offset') or 0)
        search = kw.get('search') or ''
        tag_id = kw.get('tag_id') or False
        is_admin = self.env.user.has_group('base.group_system') or self.env.user.login == 'antonio@casafolino.com'
        if not is_admin:
            user_accounts = self.env['cf.mail.account'].search([
                '|',
                ('user_id', '=', self.env.uid),
                ('is_team', '=', True),
            ])
            if account_id not in user_accounts.ids:
                return []
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
        if not msg.partner_id and msg.from_address:
            partner = self.env['res.partner'].search([('email', 'ilike', msg.from_address)], limit=1)
            if not partner:
                user = self.env['res.users'].search([('login', 'ilike', msg.from_address)], limit=1)
                if user:
                    partner = user.partner_id
            if partner:
                msg.with_context(mail_notrack=True).write({'partner_id': partner.id})
        if msg.partner_id:
            try:
                leads = self.env['crm.lead'].search([('partner_id', '=', msg.partner_id.id)], limit=5)
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
        sender_rule = self.env['cf.mail.sender.rule'].sudo().search(
            [('email', '=', (msg.from_address or '').strip().lower())], limit=1)
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
            'replied': msg.replied,
            'direction': msg.direction,
            'has_attachments': msg.has_attachments,
            'attachment_names': msg.attachment_names or '',
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
            'sender_action': sender_rule.action if sender_rule else False,
            'note': msg.note or '',
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
            leads = self.env['crm.lead'].search([('active', '=', True)], limit=100, order='id desc')
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
    def save_draft(self, *args, **kw):
        account_id = kw.get('account_id') or None
        if not account_id:
            return {'success': False, 'error': 'Account mancante'}
        draft = self.create({
            'account_id': int(account_id),
            'subject': kw.get('subject') or '(bozza)',
            'to_address': kw.get('to_address') or '',
            'cc_address': kw.get('cc_address') or '',
            'body_html': kw.get('body') or '',
            'direction': 'out',
            'folder': 'Drafts',
            'is_read': True,
        })
        return {'success': True, 'id': draft.id}

    @api.model
    def send_reply(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        to_addr = kw.get('to_address') or ''
        cc_addr = kw.get('cc_address') or ''
        bcc_addr = kw.get('bcc_address') or ''
        subject = kw.get('subject') or ''
        body = kw.get('body') or ''
        account_id = kw.get('account_id') or None
        if not to_addr or not body:
            return {'success': False, 'error': 'Destinatario o corpo mancante'}
        try:
            acc = self.env['cf.mail.account'].browse(int(account_id)) if account_id else None
            from_email = acc.email if acc else self.env.user.email
            if acc and acc.imap_password and acc.smtp_host:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                import ssl as ssl_lib
                msg_obj = MIMEMultipart('alternative')
                msg_obj['Subject'] = subject
                msg_obj['From'] = f'{acc.name or acc.email} <{acc.email}>'
                msg_obj['To'] = to_addr
                if cc_addr:
                    msg_obj['Cc'] = cc_addr
                if message_id:
                    orig = self.browse(int(message_id))
                    if orig.exists() and orig.message_uid:
                        msg_obj['In-Reply-To'] = orig.message_uid
                        msg_obj['References'] = orig.message_uid
                msg_obj.attach(MIMEText(body, 'html', 'utf-8'))
                recipients = [r.strip() for r in to_addr.split(',') if r.strip()]
                if cc_addr:
                    recipients += [r.strip() for r in cc_addr.split(',') if r.strip()]
                if bcc_addr:
                    recipients += [r.strip() for r in bcc_addr.split(',') if r.strip()]
                if acc.smtp_tls:
                    server = smtplib.SMTP(acc.smtp_host, acc.smtp_port, timeout=30)
                    server.ehlo()
                    server.starttls(context=ssl_lib.create_default_context())
                else:
                    server = smtplib.SMTP_SSL(acc.smtp_host, acc.smtp_port,
                        context=ssl_lib.create_default_context(), timeout=30)
                server.ehlo()
                server.login(acc.email, acc.imap_password)
                server.sendmail(acc.email, recipients, msg_obj.as_string())
                try:
                    import imaplib
                    if acc.imap_ssl:
                        imap = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port,
                            ssl_context=ssl_lib.create_default_context())
                    else:
                        imap = imaplib.IMAP4(acc.imap_host, acc.imap_port)
                    imap.login(acc.email, acc.imap_password)
                    for sf in ['[Gmail]/Sent Mail', 'Sent', 'Sent Items']:
                        try:
                            imap.append(sf, '\\Seen', None, msg_obj.as_bytes())
                            break
                        except Exception:
                            continue
                    imap.logout()
                except Exception as e2:
                    _logger.warning('Could not append to Sent folder: %s', e2)
                server.quit()
            else:
                mail = self.env['mail.mail'].create({
                    'subject': subject,
                    'email_to': to_addr,
                    'email_cc': cc_addr,
                    'body_html': body,
                    'email_from': from_email,
                })
                mail.send()
            thread_id = None
            if message_id:
                orig = self.browse(int(message_id))
                if orig.exists():
                    thread_id = orig.thread_id or str(orig.id)
                    orig.write({'replied': True})
            sent_msg = self.create({
                'account_id': int(account_id) if account_id else False,
                'subject': subject,
                'from_address': from_email,
                'from_name': acc.name if acc else '',
                'to_address': to_addr,
                'cc_address': cc_addr,
                'body_html': body,
                'direction': 'out',
                'folder': 'Sent',
                'is_read': True,
                'replied': False,
                'thread_id': thread_id,
            })
            return {'success': True, 'id': sent_msg.id}
        except Exception as e:
            _logger.error('send_reply error: %s', e)
            return {'success': False, 'error': str(e)}

    @api.model
    def get_crm_data(self, *args, **kw):
        try:
            stages = self.env['crm.stage'].search([], order='sequence')
            pipelines = [{'id': s.id, 'name': s.name} for s in stages]
        except Exception:
            pipelines = []
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
            lead = self.env['crm.lead'].create(vals)
            if message_id:
                msg = self.browse(int(message_id))
                if msg.exists():
                    msg.write({'lead_id': lead.id})
                    if not msg.partner_id and partner_id:
                        msg.write({'partner_id': int(partner_id)})
            return {'success': True, 'lead_id': lead.id, 'lead_name': lead.name}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # Enrichment RPC

    @api.model
    def rpc_save_enrichment(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return False
        msg = self.browse(int(message_id))
        if not msg.exists():
            return False
        vals = {}
        if 'note' in kw:
            vals['note'] = kw['note'] or ''
        if 'partner_id' in kw:
            vals['partner_id'] = int(kw['partner_id']) if kw['partner_id'] else False
        if 'tag_ids' in kw:
            vals['tag_ids'] = [(6, 0, [int(t) for t in (kw['tag_ids'] or [])])]
        if 'assigned_user_id' in kw:
            vals['assigned_user_id'] = int(kw['assigned_user_id']) if kw['assigned_user_id'] else False
        if 'lead_id' in kw:
            vals['lead_id'] = int(kw['lead_id']) if kw['lead_id'] else False
        if vals:
            msg.write(vals)
        return True

    @api.model
    def rpc_search_partners(self, *args, **kw):
        query = kw.get('query') or (args[1] if len(args) > 1 else '')
        if not query:
            return []
        partners = self.env['res.partner'].search([
            '|',
            ('name', 'ilike', query),
            ('email', 'ilike', query),
        ], limit=10)
        return [{'id': p.id, 'name': p.name, 'email': p.email or ''} for p in partners]

    @api.model
    def rpc_search_leads(self, *args, **kw):
        query = kw.get('query') or (args[1] if len(args) > 1 else '')
        if not query:
            return []
        try:
            leads = self.env['crm.lead'].search([
                ('name', 'ilike', query),
            ], limit=10)
            return [{'id': l.id, 'name': l.name} for l in leads]
        except Exception:
            return []

    # Sender rule actions

    def action_keep_sender(self):
        """Tieni mittente: crea regola keep e triggera sync storica."""
        self.ensure_one()
        addr = (self.from_address or '').strip().lower()
        if not addr:
            return
        self.env['cf.mail.sender.rule'].set_rule(addr, 'keep', trigger_sync=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Mittente mantenuto',
                'message': f'Sync storica avviata per {addr}.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_exclude_sender(self):
        """Escludi mittente: crea regola exclude ed elimina tutte le sue email."""
        self.ensure_one()
        addr = (self.from_address or '').strip().lower()
        if not addr:
            return
        self.env['cf.mail.sender.rule'].set_rule(addr, 'exclude', trigger_sync=False)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Mittente escluso',
                'message': f'Tutte le email da {addr} sono state eliminate.',
                'type': 'warning',
                'sticky': False,
            }
        }

    @api.model
    def bulk_keep_senders(self, message_ids):
        """Azione massiva: tieni mittenti delle email selezionate."""
        msgs = self.browse([int(i) for i in message_ids])
        addresses = list({(m.from_address or '').strip().lower() for m in msgs if m.from_address})
        for addr in addresses:
            self.env['cf.mail.sender.rule'].set_rule(addr, 'keep', trigger_sync=True)
        return {
            'success': True,
            'message': f'Regola KEEP applicata a {len(addresses)} mittenti. Sync storica in avvio.'
        }

    @api.model
    def bulk_exclude_senders(self, message_ids):
        """Azione massiva: escludi mittenti delle email selezionate."""
        msgs = self.browse([int(i) for i in message_ids])
        addresses = list({(m.from_address or '').strip().lower() for m in msgs if m.from_address})
        total_deleted = 0
        for addr in addresses:
            result = self.env['cf.mail.sender.rule'].set_rule(addr, 'exclude', trigger_sync=False)
            if result.get('success'):
                total_deleted += 1
        return {
            'success': True,
            'message': f'{len(addresses)} mittenti esclusi. Email eliminate.'
        }

    @api.model
    def rpc_keep_sender(self, *args, **kw):
        """OWL RPC: tieni mittente per message_id."""
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return {'success': False}
        msg = self.browse(int(message_id))
        if not msg.exists():
            return {'success': False}
        addr = (msg.from_address or '').strip().lower()
        if not addr:
            return {'success': False}
        self.env['cf.mail.sender.rule'].set_rule(addr, 'keep', trigger_sync=True)
        return {'success': True, 'action': 'keep', 'email': addr}

    @api.model
    def rpc_exclude_sender(self, *args, **kw):
        """OWL RPC: escludi mittente per message_id. Elimina tutte le sue email."""
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return {'success': False}
        msg = self.browse(int(message_id))
        if not msg.exists():
            return {'success': False}
        addr = (msg.from_address or '').strip().lower()
        if not addr:
            return {'success': False}
        self.env['cf.mail.sender.rule'].set_rule(addr, 'exclude', trigger_sync=False)
        return {'success': True, 'action': 'exclude', 'email': addr}


    @api.model
    def ai_action(self, *args, **kw):
        """Esegue azioni AI (traduci, riassumi, suggerisci risposta, analizza, scrivi bozza) via Groq."""
        import urllib.request, json as _json
        action = kw.get('action', 'translate')
        text = kw.get('text', '')
        context_data = kw.get('context', {})

        api_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.groq_api_key', '')
        if not api_key:
            return {'error': 'API key Groq non configurata'}

        prompts = {
            'translate': f"Traduci in italiano questa email. Rispondi SOLO con il testo tradotto, senza commenti:\n\n{text}",
            'summarize': f"Riassumi questa email in 3-5 punti chiave in italiano. Sii conciso e diretto:\n\n{text}",
            'suggest_reply': f"""Sei l'assistente email di CasaFolino, azienda alimentare calabrese.
Contesto mittente: {context_data.get('partner', '')} - {context_data.get('company', '')}
Trattative attive: {context_data.get('leads', '')}

Suggerisci 2 possibili risposte brevi a questa email, in italiano e inglese.
Email originale:\n{text}""",
            'draft': f"""Scrivi una email professionale per CasaFolino su questo argomento: {text}
Tono: caldo, professionale, orientato al business internazionale food.""",
            'analyze': f"""Analizza questa email dal punto di vista commerciale per CasaFolino.
Mittente: {context_data.get('partner', '')} - {context_data.get('company', '')}
Fornisci: 1) Intento del mittente 2) Opportunità commerciale 3) Azione consigliata
Email:\n{text}""",
        }

        prompt = prompts.get(action, prompts['translate'])
        payload = _json.dumps({
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7,
        }).encode()

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read())
                result = data['choices'][0]['message']['content']
                return {'result': result}
        except Exception as e:
            return {'error': str(e)}
