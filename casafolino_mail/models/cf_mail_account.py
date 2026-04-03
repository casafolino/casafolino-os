from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CfMailAccount(models.Model):
    _name = 'cf.mail.account'
    _description = 'Account Email CasaFolino'
    _order = 'sequence, id'

    name = fields.Char('Nome account')
    email = fields.Char('Indirizzo email')
    user_id = fields.Many2one('res.users', string='Utente', default=lambda self: self.env.uid)
    is_team = fields.Boolean('Team Inbox', default=False)
    color = fields.Char('Colore', default='#5A6E3A')
    signature = fields.Text('Firma')
    sequence = fields.Integer('Sequenza', default=10)
    active = fields.Boolean(default=True)
    message_ids = fields.One2many('cf.mail.message', 'account_id', string='Messaggi')

    account_type = fields.Selection([
        ('personal', 'Personale'),
        ('shared', 'Condiviso'),
    ], string='Tipo account', default='personal')

    owner_id = fields.Many2one('res.users', string='Proprietario',
        default=lambda self: self.env.uid)

    allowed_user_ids = fields.Many2many(
        'res.users', 'cf_mail_account_user_rel', 'account_id', 'user_id',
        string='Utenti autorizzati')

    display_name_custom = fields.Char(string='Nome visualizzato',
        compute='_compute_display_name_custom', store=True)

    email_address = fields.Char(string='Email',
        compute='_compute_email_address', store=True)

    unread_count = fields.Integer(string='Non lette',
        compute='_compute_counts')

    email_count = fields.Integer(string='Totale email',
        compute='_compute_counts')

    last_sync = fields.Datetime('Ultima sincronizzazione', readonly=True)

    fetchmail_server_id = fields.Many2one('fetchmail.server',
        string='Server posta in entrata',
        domain=[('server_type', '=', 'imap')])

    imap_host = fields.Char('IMAP Host', default='imap.gmail.com')
    imap_port = fields.Integer('IMAP Port', default=993)
    imap_ssl = fields.Boolean('SSL', default=True)
    imap_password = fields.Char('Password / App Password')
    imap_last_uid = fields.Integer('Ultimo UID INBOX', default=0)
    imap_sent_last_uid = fields.Integer('Ultimo UID Sent', default=0)
    imap_enabled = fields.Boolean('IMAP attivo', default=False)
    imap_status = fields.Char('Stato IMAP', default='Non configurato')
    imap_since_date = fields.Date('Importa dal', default='2026-01-01',
        help='Data di partenza per import storico IMAP')

    smtp_host = fields.Char('SMTP Host', default='smtp.gmail.com')
    smtp_port = fields.Integer('SMTP Port', default=587)
    smtp_tls = fields.Boolean('SMTP TLS', default=True)

    ooo_enabled = fields.Boolean('OOO attivo', default=False)
    ooo_subject = fields.Char('Oggetto OOO', default='Sono fuori ufficio')
    ooo_message = fields.Text('Messaggio OOO')
    ooo_start = fields.Date('OOO inizio')
    ooo_end = fields.Date('OOO fine')

    @api.depends('name', 'email')
    def _compute_display_name_custom(self):
        for rec in self:
            rec.display_name_custom = rec.name or rec.email or 'Account'

    @api.depends('email')
    def _compute_email_address(self):
        for rec in self:
            rec.email_address = rec.email or ''

    def _compute_counts(self):
        for rec in self:
            msgs = self.env['cf.mail.message'].search([('account_id', '=', rec.id)])
            rec.email_count = len(msgs)
            rec.unread_count = len(msgs.filtered(lambda m: not m.is_read and not m.is_archived))

    def action_sync_inbox(self):
        self.sync_imap()
        return True

    def action_import_history(self):
        """Reset UID e importa dal imap_since_date (default 01/01/2026)."""
        from datetime import date as date_cls
        for acc in self:
            acc.imap_last_uid = 0
            acc.imap_sent_last_uid = 0
            if not acc.imap_since_date:
                acc.imap_since_date = date_cls(2026, 1, 1)
            acc.sync_imap()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Storico',
                'message': 'Import completato per %s' % ', '.join(self.mapped('email')),
                'type': 'success',
            }
        }

    @api.model
    def _sync_all_accounts(self):
        """Cron: sync tutti gli account attivi con IMAP abilitato."""
        accounts = self.search([('imap_enabled', '=', True), ('active', '=', True)])
        for account in accounts:
            try:
                account.sync_imap()
            except Exception as e:
                _logger.error('Cron sync error for %s: %s', account.email, e)

    def action_mark_all_read(self):
        msgs = self.env['cf.mail.message'].search([
            ('account_id', 'in', self.ids),
            ('is_read', '=', False),
        ])
        msgs.write({'is_read': True})
        return True

    @api.model
    def is_admin(self, *args, **kw):
        return (
            self.env.user.has_group('base.group_system') or
            self.env.user.login in ('antonio@casafolino.com',)
        )

    @api.model
    def get_accounts(self, *args, **kw):
        is_admin = (
            self.env.user.has_group('base.group_system')
            or self.env.user.login == 'antonio@casafolino.com'
        )
        if is_admin:
            accounts = self.search([('active', '=', True)], order='sequence, is_team, id')
        else:
            accounts = self.search([
                ('active', '=', True),
                '|',
                ('user_id', '=', self.env.uid),
                ('is_team', '=', True),
            ], order='sequence, is_team, id')
        if not accounts:
            user = self.env.user
            acc = self.create({
                'name': user.name,
                'email': user.email or user.login,
                'user_id': user.id,
                'color': '#5A6E3A',
            })
            accounts = acc
        result = []
        for a in accounts:
            unread = self.env['cf.mail.message'].search_count([
                ('account_id', '=', a.id),
                ('is_read', '=', False),
                ('is_archived', '=', False),
                ('folder', '=', 'INBOX'),
            ])
            label = a.email or a.name or a.user_id.email or a.user_id.login or 'Account'
            result.append({
                'id': a.id,
                'name': a.name or label,
                'email': label,
                'color': a.color or '#5A6E3A',
                'is_team': a.is_team,
                'unread': unread,
                'signature': a.signature or '',
                'imap_enabled': a.imap_enabled,
                'imap_status': a.imap_status or 'Non configurato',
            })
        return result

    @api.model
    def get_account_detail(self, *args, **kw):
        account_id = kw.get('account_id')
        if not account_id:
            return {}
        acc = self.browse(int(account_id))
        return {
            'id': acc.id,
            'name': acc.name or '',
            'email': acc.email or '',
            'color': acc.color or '#5A6E3A',
            'signature': acc.signature or '',
            'imap_host': acc.imap_host or 'imap.gmail.com',
            'imap_port': acc.imap_port or 993,
            'imap_ssl': acc.imap_ssl,
            'imap_enabled': acc.imap_enabled,
            'imap_status': acc.imap_status or '',
            'smtp_host': acc.smtp_host or 'smtp.gmail.com',
            'smtp_port': acc.smtp_port or 587,
            'smtp_tls': acc.smtp_tls,
            'ooo_enabled': acc.ooo_enabled,
            'ooo_subject': acc.ooo_subject or 'Sono fuori ufficio',
            'ooo_message': acc.ooo_message or '',
            'ooo_start': acc.ooo_start.strftime('%Y-%m-%d') if acc.ooo_start else '',
            'ooo_end': acc.ooo_end.strftime('%Y-%m-%d') if acc.ooo_end else '',
        }

    @api.model
    def save_account(self, *args, **kw):
        account_id = kw.get('id') or False
        vals = {
            'name': kw.get('name') or '',
            'email': kw.get('email') or '',
            'color': kw.get('color') or '#5A6E3A',
            'signature': kw.get('signature') or '',
            'imap_host': kw.get('imap_host') or 'imap.gmail.com',
            'imap_port': int(kw.get('imap_port') or 993),
            'imap_ssl': bool(kw.get('imap_ssl')),
            'imap_enabled': bool(kw.get('imap_enabled')),
            'smtp_host': kw.get('smtp_host') or 'smtp.gmail.com',
            'smtp_port': int(kw.get('smtp_port') or 587),
            'smtp_tls': bool(kw.get('smtp_tls')),
            'ooo_enabled': bool(kw.get('ooo_enabled')),
            'ooo_subject': kw.get('ooo_subject') or 'Sono fuori ufficio',
            'ooo_message': kw.get('ooo_message') or '',
            'ooo_start': kw.get('ooo_start') or False,
            'ooo_end': kw.get('ooo_end') or False,
        }
        if kw.get('imap_password'):
            vals['imap_password'] = kw.get('imap_password')
        if account_id:
            acc = self.browse(int(account_id))
            acc.write(vals)
        else:
            acc = self.create(vals)
        return {'success': True, 'id': acc.id}

    @api.model
    def delete_account(self, *args, **kw):
        account_id = kw.get('account_id')
        if not account_id:
            return False
        self.browse(int(account_id)).write({'active': False})
        return True

    @api.model
    def test_connection(self, *args, **kw):
        account_id = kw.get('account_id')
        if not account_id:
            return {'success': False, 'error': 'Account non trovato'}
        acc = self.browse(int(account_id))
        if not acc.exists():
            return {'success': False, 'error': 'Account non trovato'}
        imap_ok = False
        smtp_ok = False
        errors = []
        try:
            import imaplib, ssl as ssl_lib
            if acc.imap_ssl:
                mail = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port,
                    ssl_context=ssl_lib.create_default_context())
            else:
                mail = imaplib.IMAP4(acc.imap_host, acc.imap_port)
                mail.starttls()
            mail.login(acc.email, acc.imap_password)
            mail.logout()
            imap_ok = True
        except Exception as e:
            errors.append(f'IMAP: {str(e)[:80]}')
        try:
            import smtplib, ssl as ssl_lib
            if acc.smtp_tls:
                server = smtplib.SMTP(acc.smtp_host, acc.smtp_port, timeout=10)
                server.ehlo()
                server.starttls(context=ssl_lib.create_default_context())
            else:
                server = smtplib.SMTP_SSL(acc.smtp_host, acc.smtp_port,
                    context=ssl_lib.create_default_context(), timeout=10)
            server.ehlo()
            server.login(acc.email, acc.imap_password)
            server.quit()
            smtp_ok = True
        except Exception as e:
            errors.append(f'SMTP: {str(e)[:80]}')
        if imap_ok and smtp_ok:
            status = 'IMAP + SMTP OK ✓'
            acc.write({'imap_status': status})
            return {'success': True, 'message': status}
        elif imap_ok:
            status = f'IMAP OK ✓ | {errors[0]}'
            acc.write({'imap_status': status})
            return {'success': True, 'message': status}
        else:
            status = ' | '.join(errors)
            acc.write({'imap_status': f'Errore: {status[:100]}'})
            return {'success': False, 'error': status}

    @api.model
    def get_imap_folders(self, *args, **kw):
        account_id = kw.get('account_id')
        if not account_id:
            return []
        acc = self.browse(int(account_id))
        if not acc.exists() or not acc.imap_enabled or not acc.imap_password:
            return []
        try:
            import imaplib, ssl as ssl_lib, re
            if acc.imap_ssl:
                mail = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port,
                    ssl_context=ssl_lib.create_default_context())
            else:
                mail = imaplib.IMAP4(acc.imap_host, acc.imap_port)
                mail.starttls()
            mail.login(acc.email, acc.imap_password)
            status, folder_list = mail.list()
            mail.logout()
            folders = []
            if status == 'OK':
                for item in folder_list:
                    decoded = item.decode() if isinstance(item, bytes) else item
                    m = re.search(r'"/" (.+)', decoded) or re.search(r'"\." (.+)', decoded)
                    if m:
                        name = m.group(1).strip().strip('"')
                        folders.append(name)
            return folders
        except Exception as e:
            _logger.warning('get_imap_folders error: %s', e)
            return []

    @api.model
    def sync_now(self, *args, **kw):
        account_id = kw.get('account_id')
        if account_id:
            acc = self.browse(int(account_id))
        else:
            acc = self.search([('imap_enabled', '=', True)])
        acc.sync_imap()
        return {'success': True}

    # ── Sender-rule helpers ────────────────────────────────────────────────

    def _get_sender_rules(self):
        """Ritorna dict {email_lower: action} per tutti i mittenti con regola."""
        rules = self.env['cf.mail.sender.rule'].search([])
        return {r.email.lower(): r.action for r in rules}

    def _should_import(self, from_address, sender_rules, cutoff_date, msg_date):
        """
        Fase 1 (nessuna regola): importa solo ultimi 4 mesi.
        Fase 2 (regole presenti):
          - keep  → importa sempre (tutta la storia)
          - exclude → mai
          - nessuna regola → solo ultimi 4 mesi
        Ritorna True se il messaggio va importato.
        """
        addr = (from_address or '').lower().strip()
        if not sender_rules:
            # Fase 1: nessuna regola → solo 4 mesi
            return msg_date >= cutoff_date
        rule = sender_rules.get(addr)
        if rule == 'exclude':
            return False
        if rule == 'keep':
            return True
        # Nessuna regola → 4 mesi
        return msg_date >= cutoff_date

    def _sync_sender_history(self, sender_email):
        """Sync storica completa per un mittente specifico (regola keep)."""
        import imaplib, ssl as ssl_lib
        for acc in self:
            if not acc.imap_enabled or not acc.email or not acc.imap_password:
                continue
            try:
                if acc.imap_ssl:
                    mail = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port,
                                             ssl_context=ssl_lib.create_default_context())
                else:
                    mail = imaplib.IMAP4(acc.imap_host, acc.imap_port)
                    mail.starttls()
                mail.login(acc.email, acc.imap_password)

                # Cerca tutte le email da quel mittente in INBOX
                self._sync_folder(mail, acc, 'INBOX', 'in', 'imap_last_uid',
                                   sender_filter=sender_email, ignore_cutoff=True)
                # E nella cartella Sent
                for sent_folder in ['[Gmail]/Sent Mail', 'Sent', 'Sent Items', 'SENT']:
                    try:
                        status, _ = mail.select(sent_folder)
                        if status == 'OK':
                            self._sync_folder(mail, acc, sent_folder, 'out', 'imap_sent_last_uid',
                                              sender_filter=sender_email, ignore_cutoff=True)
                            break
                    except Exception:
                        continue
                mail.logout()
            except Exception as e:
                _logger.error('History sync error for %s / %s: %s', acc.email, sender_email, e)

    # ── Core sync ─────────────────────────────────────────────────────────

    def _sync_folder(self, mail, acc, folder_name, direction, last_uid_field,
                     sender_filter=None, ignore_cutoff=False):
        import email as email_lib
        from email.header import decode_header
        from email.utils import parsedate_to_datetime
        from datetime import datetime, timedelta
        import pytz
        try:
            status, _ = mail.select(folder_name)
            if status != 'OK':
                return 0
        except Exception:
            return 0

        # Determina il criterio di ricerca IMAP
        if sender_filter:
            # Sync storica per un mittente specifico: cerca per FROM
            safe_sender = sender_filter.replace('"', '')
            status, messages = mail.uid('search', None, f'FROM "{safe_sender}"')
        else:
            last_uid = getattr(acc, last_uid_field) or 0
            if last_uid > 0:
                status, messages = mail.uid('search', None, f'UID {last_uid + 1}:*')
            else:
                # Prima sync: usa imap_since_date se presente, altrimenti 4 mesi
                from datetime import date
                if acc.imap_since_date:
                    since_str = acc.imap_since_date.strftime('%d-%b-%Y')
                else:
                    cutoff = date.today() - timedelta(days=120)
                    since_str = cutoff.strftime('%d-%b-%Y')
                status, messages = mail.uid('search', None, f'SINCE {since_str}')

        if status != 'OK':
            return 0
        uids = messages[0].split()
        if not uids or uids == [b'']:
            return 0

        # Limite di 100 uid per ciclo normale; nessun limite per sync storica
        if not sender_filter:
            uids = uids[-100:]

        # Regole mittenti per il filtro intelligente
        sender_rules = {} if sender_filter else self._get_sender_rules()
        cutoff_dt = datetime.now() - timedelta(days=120)

        last_uid = getattr(acc, last_uid_field) or 0
        max_uid = last_uid
        count = 0
        for uid in uids:
            uid_int = int(uid)
            if not sender_filter and uid_int <= last_uid:
                continue
            existing = self.env['cf.mail.message'].search([
                ('account_id', '=', acc.id),
                ('message_uid', '=', f'{folder_name}_{uid_int}'),
            ], limit=1)
            if existing:
                if not sender_filter:
                    max_uid = max(max_uid, uid_int)
                continue
            try:
                status2, msg_data = mail.uid('fetch', uid, '(RFC822)')
                if status2 != 'OK' or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                def decode_str(s):
                    if not s: return ''
                    parts = decode_header(s)
                    result = []
                    for part, enc in parts:
                        if isinstance(part, bytes):
                            result.append(part.decode(enc or 'utf-8', errors='replace'))
                        else:
                            result.append(str(part))
                    return ''.join(result)
                subject = decode_str(msg.get('Subject', '')) or '(nessun oggetto)'
                from_raw = decode_str(msg.get('From', ''))
                to_raw = decode_str(msg.get('To', ''))
                cc_raw = decode_str(msg.get('CC', ''))
                date_str = msg.get('Date', '')
                message_id_header = msg.get('Message-ID', '')
                from_name = ''
                from_address = from_raw
                if '<' in from_raw and '>' in from_raw:
                    from_name = from_raw.split('<')[0].strip().strip('"\'')
                    from_address = from_raw.split('<')[1].replace('>', '').strip()
                try:
                    dt = parsedate_to_datetime(date_str)
                    if dt.tzinfo:
                        dt = dt.astimezone(pytz.utc).replace(tzinfo=None)
                except Exception:
                    dt = datetime.now()

                # ── Filtro mittente intelligente (sender rules) ───────────
                if not ignore_cutoff and not self._should_import(
                        from_address, sender_rules, cutoff_dt, dt):
                    if not sender_filter:
                        max_uid = max(max_uid, uid_int)
                    continue

                body_html = ''
                body_text = ''
                has_attachments = False
                attachment_names = []
                if msg.is_multipart():
                    for part in msg.walk():
                        ct = part.get_content_type()
                        cd = str(part.get('Content-Disposition', ''))
                        if 'attachment' in cd:
                            has_attachments = True
                            fn = part.get_filename()
                            if fn:
                                attachment_names.append(decode_str(fn))
                            continue
                        if ct == 'text/html' and not body_html:
                            charset = part.get_content_charset() or 'utf-8'
                            try:
                                body_html = part.get_payload(decode=True).decode(charset, errors='replace')
                            except Exception:
                                pass
                        elif ct == 'text/plain' and not body_text:
                            charset = part.get_content_charset() or 'utf-8'
                            try:
                                body_text = part.get_payload(decode=True).decode(charset, errors='replace')
                            except Exception:
                                pass
                else:
                    ct = msg.get_content_type()
                    charset = msg.get_content_charset() or 'utf-8'
                    payload = msg.get_payload(decode=True)
                    if payload:
                        try:
                            if ct == 'text/html':
                                body_html = payload.decode(charset, errors='replace')
                            else:
                                body_text = payload.decode(charset, errors='replace')
                        except Exception:
                            pass
                snippet = (body_text or body_html or '')[:150].replace('\n', ' ').replace('\r', '')
                partner = self.env['res.partner'].search([('email', 'ilike', from_address)], limit=1)
                if not partner:
                    user = self.env['res.users'].search([('login', 'ilike', from_address)], limit=1)
                    if user:
                        partner = user.partner_id

                thread_id = None
                clean_subject = subject.replace('Re: ', '').replace('Fwd: ', '').strip()
                existing_thread = self.env['cf.mail.message'].search([
                    ('account_id', '=', acc.id),
                    ('subject', 'ilike', clean_subject),
                    ('thread_id', '!=', False),
                ], limit=1)
                if existing_thread:
                    thread_id = existing_thread.thread_id
                elif message_id_header:
                    thread_id = message_id_header
                self.env['cf.mail.message'].create({
                    'account_id': acc.id,
                    'subject': subject,
                    'from_address': from_address,
                    'from_name': from_name,
                    'to_address': to_raw[:500] if to_raw else '',
                    'cc_address': cc_raw[:500] if cc_raw else '',
                    'body_html': body_html,
                    'body_text': body_text,
                    'snippet': snippet,
                    'date': dt,
                    'is_read': direction == 'out',
                    'direction': direction,
                    'folder': 'INBOX' if direction == 'in' else 'Sent',
                    'message_uid': f'{folder_name}_{uid_int}',
                    'partner_id': partner.id if partner else False,
                    'has_attachments': has_attachments,
                    'attachment_names': ', '.join(attachment_names) if attachment_names else False,
                    'thread_id': thread_id,
                })
                if not sender_filter:
                    max_uid = max(max_uid, uid_int)
                count += 1
            except Exception as e:
                _logger.warning('Error fetching UID %s: %s', uid_int, e)
                continue

        if not sender_filter:
            acc.write({last_uid_field: max_uid})
        return count

    def sync_imap(self):
        for acc in self:
            if not acc.imap_enabled or not acc.email or not acc.imap_password:
                continue
            try:
                import imaplib, ssl as ssl_lib
                if acc.imap_ssl:
                    mail = imaplib.IMAP4_SSL(acc.imap_host, acc.imap_port,
                        ssl_context=ssl_lib.create_default_context())
                else:
                    mail = imaplib.IMAP4(acc.imap_host, acc.imap_port)
                    mail.starttls()
                mail.login(acc.email, acc.imap_password)
                inbox_count = self._sync_folder(mail, acc, 'INBOX', 'in', 'imap_last_uid')
                sent_folders = ['[Gmail]/Sent Mail', 'Sent', 'Sent Items', 'SENT']
                for sent_folder in sent_folders:
                    try:
                        status, _ = mail.select(sent_folder)
                        if status == 'OK':
                            self._sync_folder(mail, acc, sent_folder, 'out', 'imap_sent_last_uid')
                            break
                    except Exception:
                        continue
                mail.logout()
                total = self.env['cf.mail.message'].search_count([('account_id', '=', acc.id)])
                acc.write({
                    'imap_status': f'✓ Sincronizzato — {total} email ({inbox_count} nuove)',
                    'last_sync': fields.Datetime.now(),
                })
            except Exception as e:
                _logger.error('IMAP sync error for %s: %s', acc.email, e)
                acc.write({'imap_status': f'Errore: {str(e)[:100]}'})
