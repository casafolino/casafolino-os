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
    partner_id = fields.Many2one('res.partner', string='Contatto')
    lead_id = fields.Many2one('cf.export.lead', string='Trattativa CRM')
    assigned_user_id = fields.Many2one('res.users', string='Assegnata a')
    tag_ids = fields.Many2many('cf.mail.tag', string='Tag')

    def action_mark_read(self):
        self.write({'is_read': True})

    def action_mark_unread(self):
        self.write({'is_read': False})

    def action_star(self):
        self.write({'is_starred': not self.is_starred})

    def action_archive_msg(self):
        self.write({'is_archived': True})

    @api.model
    def get_messages(self, *args, **kw):
        account_id = kw.get('account_id') or (args[1] if len(args) > 1 else None)
        folder = kw.get('folder') or (args[2] if len(args) > 2 else 'INBOX')
        limit = int(kw.get('limit') or (args[3] if len(args) > 3 else 50))
        offset = int(kw.get('offset') or (args[4] if len(args) > 4 else 0))
        search = kw.get('search') or (args[5] if len(args) > 5 else '')

        domain = [('account_id', '=', account_id), ('is_archived', '=', False)]
        if folder == 'Starred':
            domain.append(('is_starred', '=', True))
        elif folder == 'Sent':
            domain.append(('direction', '=', 'out'))
        elif folder == 'Archived':
            domain = [('account_id', '=', account_id), ('is_archived', '=', True)]
        else:
            domain.append(('folder', '=', folder))

        if search:
            domain += ['|', '|',
                ('subject', 'ilike', search),
                ('from_address', 'ilike', search),
                ('snippet', 'ilike', search),
            ]

        msgs = self.search(domain, limit=limit, offset=offset)
        result = []
        for m in msgs:
            tags = []
            for t in m.tag_ids:
                tags.append({'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'})
            result.append({
                'id': m.id,
                'subject': m.subject or '(nessun oggetto)',
                'from_address': m.from_address or '',
                'from_name': m.from_name or m.from_address or '',
                'snippet': m.snippet or '',
                'date': m.date.strftime('%d/%m/%Y %H:%M') if m.date else '',
                'date_short': m.date.strftime('%d %b') if m.date else '',
                'is_read': m.is_read,
                'is_starred': m.is_starred,
                'direction': m.direction,
                'partner_id': m.partner_id.id if m.partner_id else False,
                'partner_name': m.partner_id.name if m.partner_id else '',
                'lead_id': m.lead_id.id if m.lead_id else False,
                'lead_name': m.lead_id.name if m.lead_id else '',
                'assigned_user_id': m.assigned_user_id.id if m.assigned_user_id else False,
                'assigned_user_name': m.assigned_user_id.name if m.assigned_user_id else '',
                'tags': tags,
            })
        return result

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

        tags = []
        for t in msg.tag_ids:
            tags.append({'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'})

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
            'partner_id': msg.partner_id.id if msg.partner_id else False,
            'partner_name': msg.partner_id.name if msg.partner_id else '',
            'partner_email': msg.partner_id.email if msg.partner_id else '',
            'lead_id': msg.lead_id.id if msg.lead_id else False,
            'lead_name': msg.lead_id.name if msg.lead_id else '',
            'assigned_user_id': msg.assigned_user_id.id if msg.assigned_user_id else False,
            'assigned_user_name': msg.assigned_user_id.name if msg.assigned_user_id else '',
            'partner_leads': partner_leads,
            'partner_orders': partner_orders,
            'tags': tags,
            'signature': msg.account_id.signature or '',
        }

    @api.model
    def do_bulk_action(self, *args, **kw):
        ids = kw.get('ids') or (args[1] if len(args) > 1 else [])
        action = kw.get('action') or (args[2] if len(args) > 2 else '')
        if not ids or not action:
            return False
        msgs = self.browse([int(i) for i in ids])
        if action == 'read':
            msgs.write({'is_read': True})
        elif action == 'unread':
            msgs.write({'is_read': False})
        elif action == 'star':
            msgs.write({'is_starred': True})
        elif action == 'archive':
            msgs.write({'is_archived': True})
        elif action == 'delete':
            msgs.unlink()
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
    def get_users_list(self, *args, **kw):
        users = self.env['res.users'].search([('share', '=', False), ('active', '=', True)])
        return [{'id': u.id, 'name': u.name} for u in users]

    @api.model
    def get_leads_list(self, *args, **kw):
        try:
            leads = self.env['cf.export.lead'].search([('active', '=', True)], limit=50, order='id desc')
            return [{'id': l.id, 'name': l.name} for l in leads]
        except Exception:
            return []

    @api.model
    def send_reply(self, *args, **kw):
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        to_addr = kw.get('to_address') or (args[2] if len(args) > 2 else '')
        subject = kw.get('subject') or (args[3] if len(args) > 3 else '')
        body = kw.get('body') or (args[4] if len(args) > 4 else '')
        account_id = kw.get('account_id') or (args[5] if len(args) > 5 else None)
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
            sent_msg = self.create({
                'account_id': int(account_id) if account_id else False,
                'subject': subject,
                'from_address': from_email,
                'to_address': to_addr,
                'body_html': body,
                'direction': 'out',
                'folder': 'Sent',
                'is_read': True,
            })
            return {'success': True, 'id': sent_msg.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}
