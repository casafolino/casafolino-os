import email
import imaplib
import logging
from datetime import timedelta, timezone
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CasafolinoMailAccount(models.Model):
    _name = 'casafolino.mail.account'
    _inherit = ['casafolino.mail.sender.filter']
    _description = 'Account Email IMAP — Mail Hub'
    _order = 'name'

    name = fields.Char('Nome account', required=True)
    email_address = fields.Char('Indirizzo email', required=True)
    responsible_user_id = fields.Many2one('res.users', string='Responsabile triage',
                                          default=lambda self: self.env.uid)
    imap_host = fields.Char('IMAP Host', default='imap.gmail.com')
    imap_port = fields.Integer('IMAP Port', default=993)
    imap_password = fields.Char('App Password')
    imap_use_ssl = fields.Boolean('SSL', default=True)
    sent_folder = fields.Char('Cartella Sent', help='Auto-detected o manuale. Es. [Gmail]/Posta inviata')
    sync_start_date = fields.Date('Importa dal', default='2025-01-01')
    last_fetch_datetime = fields.Datetime('Ultimo fetch', readonly=True)
    last_fetch_uid = fields.Char('Ultimo UID processato', readonly=True)
    state = fields.Selection([
        ('draft', 'Bozza'),
        ('connected', 'Connesso'),
        ('error', 'Errore'),
    ], string='Stato', default='draft')
    error_message = fields.Text('Errore')
    active = fields.Boolean(default=True)
    gmail_label = fields.Char('Label Gmail', default='Odoo',
        help='Label Gmail da cui pescare email. Default: Odoo')
    use_allowlist = fields.Boolean('Usa allowlist domini', default=True,
        help='Se attivo, importa solo da domini con sender_policy auto_keep')
    last_successful_fetch_datetime = fields.Datetime('Ultimo fetch OK', readonly=True)
    fetch_inbox = fields.Boolean('Scarica INBOX', default=True)
    fetch_sent = fields.Boolean('Scarica Sent', default=True)
    company_domain = fields.Char('Dominio aziendale', default='casafolino.com',
        help='Email da questo dominio sono considerate interne')
    signature_html = fields.Html('Firma Email',
        help='Firma HTML inserita automaticamente nelle email')

    # ── Connection helpers ────────────────────────────────────────────

    def _get_imap_connection(self):
        """Apre connessione IMAP SSL a Gmail."""
        self.ensure_one()
        try:
            if self.imap_use_ssl:
                imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, timeout=60)
            else:
                imap = imaplib.IMAP4(self.imap_host, self.imap_port, timeout=60)
            imap.login(self.email_address, self.imap_password)
            return imap
        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})
            raise UserError("Connessione IMAP fallita: %s" % e)

    def action_test_connection(self):
        """Testa la connessione e rileva la cartella Sent."""
        self.ensure_one()
        imap = self._get_imap_connection()

        # Rileva cartella sent
        status, folders = imap.list()
        sent_folder = None
        if status == 'OK':
            for folder in folders:
                decoded = folder.decode() if isinstance(folder, bytes) else folder
                if '\\Sent' in decoded:
                    parts = decoded.split('"')
                    if len(parts) >= 3:
                        sent_folder = parts[-2]
                    break

        imap.logout()

        vals = {'state': 'connected', 'error_message': False}
        if sent_folder:
            vals['sent_folder'] = sent_folder
        self.write(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'OK',
                'message': 'Connessione riuscita. Sent: %s' % (sent_folder or '(non rilevata)'),
                'type': 'success',
            },
        }

    def action_fetch_now(self):
        """Fetch manuale per questo account."""
        self.ensure_one()
        self._fetch_emails()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fetch completato',
                'message': 'Email scaricate per %s' % self.email_address,
                'type': 'success',
            },
        }

    # ── Fetch engine (Step 2) ───────────────────��────────────────────

    def _fetch_emails(self):
        """Fetch principale: scarica header da INBOX e/o Sent."""
        self.ensure_one()
        imap = self._get_imap_connection()
        total_new = 0
        total_skip = 0
        total_blacklist = 0

        try:
            folders_to_fetch = []
            if self.fetch_inbox:
                folders_to_fetch.append(('INBOX', 'inbound'))
            if self.fetch_sent and self.sent_folder:
                folders_to_fetch.append((self.sent_folder, 'outbound'))

            for folder_name, direction in folders_to_fetch:
                new, skip, bl = self._fetch_folder(imap, folder_name, direction)
                total_new += new
                total_skip += skip
                total_blacklist += bl

            self.write({
                'state': 'connected',
                'error_message': False,
                'last_successful_fetch_datetime': fields.Datetime.now(),
            })

            _logger.info(
                "[%s] fetched %d, skipped %d, excluded %d",
                self.email_address, total_new, total_skip, total_blacklist
            )

        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})
            _logger.error("Mail fetch error %s: %s", self.email_address, e)
            raise
        finally:
            self.write({'last_fetch_datetime': fields.Datetime.now()})
            try:
                imap.logout()
            except Exception:
                pass

    def _build_account_email_map(self):
        """Costruisce mappa email→account_id per tutti gli account attivi. Chiamare UNA volta per sync."""
        accounts = self.env['casafolino.mail.account'].search([('active', '=', True)])
        return {a.email_address.lower().strip(): a.id for a in accounts if a.email_address}

    def _resolve_account_id(self, sender_email, recipient_emails, cc_emails, account_map):
        """Determina l'account_id corretto basandosi su from/to/cc.
        1. Se il mittente è un account CasaFolino → quell'account
        2. Se un destinatario/cc è un account CasaFolino → quell'account
        3. Fallback → self.id (account che esegue la sync)
        """
        # Check mittente
        if sender_email:
            aid = account_map.get(sender_email.lower().strip())
            if aid:
                return aid
        # Check destinatari
        all_recipients = (recipient_emails or '') + ',' + (cc_emails or '')
        for addr in all_recipients.split(','):
            addr = addr.strip().lower()
            if addr:
                aid = account_map.get(addr)
                if aid:
                    return aid
        return self.id

    def _load_exclude_rules(self):
        """Carica set di email/domini da escludere da sender_policy auto_discard."""
        excluded = set()
        try:
            policies = self.env['casafolino.mail.sender_policy'].sudo().search([
                ('action', '=', 'auto_discard'), ('active', '=', True)
            ])
            for p in policies:
                if p.pattern_type == 'email_exact' and p.pattern_value:
                    excluded.add(p.pattern_value.lower().strip())
        except Exception:
            pass
        return excluded

    def _fetch_folder(self, imap, folder_name, direction):
        """Dispatcher: legacy (MESSAGE) o RAW in base a feature flag."""
        use_raw = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.use_raw_pipeline', 'false'
        ).lower() == 'true'
        if use_raw:
            return self._fetch_folder_raw(imap, folder_name, direction)
        return self._fetch_folder_legacy(imap, folder_name, direction)

    def _fetch_folder_legacy(self, imap, folder_name, direction):
        """Fetch legacy: whitelist CRM-based, scrive in casafolino.mail.message."""
        Message = self.env['casafolino.mail.message']

        new_count = 0
        skip_count = 0
        filtered_out = 0

        account_map = self._build_account_email_map()

        status, data = imap.select('"%s"' % folder_name, readonly=True)
        if status != 'OK':
            _logger.warning("Cannot select folder %s: %s", folder_name, data)
            return 0, 0, 0

        if self.last_fetch_datetime:
            since_date = self.last_fetch_datetime.strftime('%d-%b-%Y')
        else:
            since_date = self.sync_start_date.strftime('%d-%b-%Y')

        search_criteria = '(SINCE %s)' % since_date
        status, msg_ids = imap.search(None, search_criteria)

        if status != 'OK' or not msg_ids[0]:
            return 0, 0, 0

        uid_list = msg_ids[0].split()
        _logger.info("Folder %s: %d email trovate dal %s", folder_name, len(uid_list), since_date)

        batch_size = 50
        for i in range(0, len(uid_list), batch_size):
            batch = uid_list[i:i + batch_size]

            for uid in batch:
                uid_str = uid.decode()

                status2, header_data = imap.fetch(uid, '(BODY.PEEK[HEADER])')
                if status2 != 'OK':
                    continue

                raw_header = None
                for part in header_data:
                    if isinstance(part, tuple):
                        raw_header = part[1]
                        break
                if not raw_header:
                    continue

                msg = email.message_from_bytes(raw_header)

                message_id = msg.get('Message-ID', '').strip()
                if not message_id:
                    message_id = "<%s-%s-%s@generated>" % (self.email_address, uid_str, folder_name)

                sender_name, sender_email_addr = parseaddr(msg.get('From', ''))
                sender_name = self._decode_header_value(sender_name)
                sender_email_addr = sender_email_addr.lower().strip() if sender_email_addr else ''

                to_raw = msg.get('To', '')
                cc_raw = msg.get('Cc', '')
                recipient_emails = self._extract_emails(to_raw)
                cc_emails = self._extract_emails(cc_raw)

                resolved_account_id = self._resolve_account_id(
                    sender_email_addr, recipient_emails, cc_emails, account_map)

                existing = Message.search([('message_id_rfc', '=', message_id)], limit=1)
                if existing:
                    skip_count += 1
                    continue

                Preference = self.env['casafolino.mail.sender_preference']
                pref = Preference.search([
                    ('email', '=ilike', sender_email_addr),
                    ('account_id', '=', resolved_account_id),
                ], limit=1)
                if pref and pref.status == 'dismissed':
                    filtered_out += 1
                    continue

                actual_direction = direction
                if direction == 'inbound' and sender_email_addr == self.email_address.lower():
                    actual_direction = 'outbound'

                partner_id = False
                match_type = 'none'

                if actual_direction == 'outbound':
                    ext_email = self._get_external_email(sender_email_addr, recipient_emails)
                    if ext_email and ext_email != sender_email_addr:
                        allowed, pid, mt = self.is_sender_allowed(ext_email)
                        if allowed:
                            partner_id = pid
                            match_type = mt
                else:
                    allowed, pid, mt = self.is_sender_allowed(sender_email_addr)
                    if not allowed:
                        filtered_out += 1
                        continue
                    partner_id = pid
                    match_type = mt

                subject = self._decode_header_value(msg.get('Subject', '(nessun oggetto)'))

                date_str = msg.get('Date', '')
                try:
                    email_date = parsedate_to_datetime(date_str)
                    if email_date.tzinfo is not None:
                        email_date = email_date.astimezone(timezone.utc).replace(tzinfo=None)
                except Exception:
                    email_date = fields.Datetime.now()

                vals = {
                    'account_id': resolved_account_id,
                    'message_id_rfc': message_id,
                    'imap_uid': uid_str,
                    'imap_folder': folder_name,
                    'direction': actual_direction,
                    'sender_email': sender_email_addr,
                    'sender_name': sender_name,
                    'recipient_emails': recipient_emails,
                    'cc_emails': cc_emails,
                    'subject': subject,
                    'email_date': email_date,
                    'state': 'new',
                    'partner_id': partner_id,
                    'match_type': match_type,
                    'fetch_state': 'pending',
                }

                try:
                    Message.create(vals)
                    new_count += 1

                    if actual_direction == 'inbound' and sender_email_addr and not pref:
                        try:
                            Preference.sudo().create({
                                'email': sender_email_addr.lower().strip(),
                                'account_id': resolved_account_id,
                                'status': 'pending',
                            })
                        except Exception:
                            pass

                except Exception as e:
                    _logger.warning("Error creating mail message: %s", e)
                    continue

            self.env.cr.commit()
            _logger.info("Batch %d: %d nuove fin qui", i // batch_size + 1, new_count)

        _logger.info(
            "[%s] %s: fetched %d, skipped-dedup %d, filtered-out %d",
            self.email_address, folder_name, new_count, skip_count, filtered_out
        )
        return new_count, skip_count, filtered_out

    def _fetch_folder_raw(self, imap, folder_name, direction):
        """Fetch V13: scarica header + preview in casafolino.mail.raw.

        Nessun filtro, nessuna whitelist, nessuna classificazione.
        Il cron triage processa i RAW separatamente.
        """
        Raw = self.env['casafolino.mail.raw']

        new_count = 0
        skip_count = 0

        account_map = self._build_account_email_map()

        status, data = imap.select('"%s"' % folder_name, readonly=True)
        if status != 'OK':
            _logger.warning("Cannot select folder %s: %s", folder_name, data)
            return 0, 0, 0

        if self.last_fetch_datetime:
            since_date = self.last_fetch_datetime.strftime('%d-%b-%Y')
        else:
            since_date = self.sync_start_date.strftime('%d-%b-%Y')

        search_criteria = '(SINCE %s)' % since_date
        status, msg_ids = imap.search(None, search_criteria)

        if status != 'OK' or not msg_ids[0]:
            return 0, 0, 0

        uid_list = msg_ids[0].split()
        _logger.info("Folder %s: %d email trovate dal %s", folder_name, len(uid_list), since_date)

        batch_size = 50
        for i in range(0, len(uid_list), batch_size):
            batch = uid_list[i:i + batch_size]

            for uid in batch:
                uid_str = uid.decode()

                status2, fetch_data = imap.fetch(
                    uid, '(BODY.PEEK[HEADER] BODY.PEEK[TEXT]<0.500>)')
                if status2 != 'OK':
                    continue

                raw_header = None
                raw_preview = None
                for part in fetch_data:
                    if isinstance(part, tuple):
                        desc = part[0].decode() if isinstance(part[0], bytes) else str(part[0])
                        if 'HEADER' in desc.upper():
                            raw_header = part[1]
                        elif 'TEXT' in desc.upper():
                            raw_preview = part[1]

                if not raw_header:
                    continue

                msg = email.message_from_bytes(raw_header)

                message_id = msg.get('Message-ID', '').strip()
                if not message_id:
                    message_id = "<%s-%s-%s@generated>" % (self.email_address, uid_str, folder_name)

                sender_name, sender_email_addr = parseaddr(msg.get('From', ''))
                sender_name = self._decode_header_value(sender_name)
                sender_email_addr = sender_email_addr.lower().strip() if sender_email_addr else ''

                to_raw = msg.get('To', '')
                cc_raw = msg.get('Cc', '')
                recipient_emails = self._extract_emails(to_raw)
                cc_emails = self._extract_emails(cc_raw)

                resolved_account_id = self._resolve_account_id(
                    sender_email_addr, recipient_emails, cc_emails, account_map)

                existing_raw = Raw.search([
                    ('account_id', '=', resolved_account_id),
                    ('message_id', '=', message_id),
                ], limit=1)
                if existing_raw:
                    skip_count += 1
                    continue
                existing_msg = self.env['casafolino.mail.message'].search([
                    ('message_id_rfc', '=', message_id),
                ], limit=1)
                if existing_msg:
                    skip_count += 1
                    continue

                actual_direction = direction
                if direction == 'inbound' and sender_email_addr == self.email_address.lower():
                    actual_direction = 'outbound'

                subject = self._decode_header_value(msg.get('Subject', '(nessun oggetto)'))

                date_str = msg.get('Date', '')
                try:
                    email_date = parsedate_to_datetime(date_str)
                    if email_date.tzinfo is not None:
                        email_date = email_date.astimezone(timezone.utc).replace(tzinfo=None)
                except Exception:
                    email_date = fields.Datetime.now()

                body_preview = ''
                if raw_preview:
                    try:
                        body_preview = raw_preview.decode('utf-8', errors='ignore')[:500]
                    except Exception:
                        body_preview = ''

                content_type = msg.get('Content-Type', '')
                has_attachments = 'multipart/mixed' in content_type.lower()

                headers_text = raw_header.decode('utf-8', errors='ignore')

                vals = {
                    'account_id': resolved_account_id,
                    'uid': uid_str,
                    'message_id': message_id,
                    'subject': subject,
                    'sender_email': sender_email_addr,
                    'sender_name': sender_name,
                    'recipient_emails': recipient_emails,
                    'cc_emails': cc_emails,
                    'email_date': email_date,
                    'body_preview': body_preview,
                    'has_attachments': has_attachments,
                    'headers_raw': headers_text,
                    'imap_folder': folder_name,
                    'direction': actual_direction,
                    'triage_state': 'pending',
                }

                try:
                    Raw.create(vals)
                    new_count += 1
                except Exception as e:
                    _logger.warning("Error creating RAW record: %s", e)
                    continue

            self.env.cr.commit()
            _logger.info("Batch %d: %d nuove fin qui", i // batch_size + 1, new_count)

        _logger.info(
            "[%s] %s: raw fetched %d, skipped-dedup %d",
            self.email_address, folder_name, new_count, skip_count
        )
        return new_count, skip_count, 0

    # ── Helper methods ────────────────────────────────────────��───────

    def _decode_header_value(self, value):
        """Decodifica header MIME (=?UTF-8?Q?...?= etc)."""
        if not value:
            return ''
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or 'utf-8', errors='ignore'))
            else:
                result.append(part)
        return ' '.join(result).strip()

    def _extract_emails(self, header_value):
        """Estrae lista email da header To/Cc."""
        if not header_value:
            return ''
        addresses = []
        for part in header_value.split(','):
            name, addr = parseaddr(part.strip())
            if addr:
                addresses.append(addr.lower().strip())
        return ', '.join(addresses)

    def _get_external_email(self, sender_email, recipient_emails):
        """Se il mittente è interno (company_domain), ritorna il primo destinatario esterno."""
        self.ensure_one()
        cd = (self.company_domain or '').lower().strip()
        if not cd:
            return sender_email

        sender_domain = sender_email.split('@')[1].lower() if '@' in sender_email else ''
        if sender_domain != cd:
            # Mittente è esterno — usa il mittente
            return sender_email

        # Mittente è interno — cerca primo destinatario esterno
        if recipient_emails:
            for addr in recipient_emails.split(','):
                addr = addr.strip().lower()
                if addr and '@' in addr and addr.split('@')[1] != cd:
                    return addr

        # Tutti interni — fallback sul mittente
        return sender_email

    def _match_partner(self, sender_email, recipient_emails, direction):
        """Cerca partner corrispondente. Ritorna (partner_id, match_type) o (False, 'none')."""
        Partner = self.env['res.partner']

        if direction == 'inbound':
            # Se mittente è interno, cerca sul primo destinatario esterno
            email_to_match = self._get_external_email(sender_email, recipient_emails)
        else:
            # Per outbound, prendi il primo destinatario esterno
            email_to_match = self._get_external_email(sender_email, recipient_emails)
            # Se il risultato è il sender (tutti interni), prova il primo recipient
            if email_to_match == sender_email and recipient_emails:
                first_rcpt = recipient_emails.split(',')[0].strip()
                if first_rcpt:
                    email_to_match = first_rcpt

        if not email_to_match:
            return False, 'none'

        # 1. Match esatto per email
        partner = Partner.search([('email', '=ilike', email_to_match)], limit=1)
        if partner:
            return partner.id, 'exact'

        # 2. Match per dominio (company website)
        domain = email_to_match.split('@')[1] if '@' in email_to_match else ''
        if domain:
            partner = Partner.search([
                ('is_company', '=', True),
                ('website', 'ilike', domain),
            ], limit=1)
            if partner:
                return partner.id, 'domain'

        return False, 'none'

    # ── Cron (Step 8) ────────────────────────────────────────────────

    @api.model
    def _cron_fetch_all_accounts(self):
        """Fetch incrementale per tutti gli account connessi."""
        accounts = self.search([('state', '=', 'connected'), ('active', '=', True)])
        for account in accounts:
            try:
                account._fetch_emails()
            except Exception as e:
                account.write({'state': 'error', 'error_message': str(e)})
                _logger.error("Cron fetch error %s: %s", account.email_address, e)

    # ── Cron: Silent Partners Alert ────────────────────────────────

    @api.model
    def _cron_silent_partners_alert(self):
        """Crea mail.activity per partner con lead aperti e silenti da X giorni."""
        threshold = int(self.env['ir.config_parameter'].sudo().get_param(
            'casafolino_mail.silent_days_threshold', '21'))
        cutoff_date = fields.Datetime.now() - timedelta(days=threshold)

        # Partner con lead CRM aperti (non vinti, non persi)
        open_leads = self.env['crm.lead'].search([
            ('active', '=', True),
            ('stage_id.is_won', '=', False),
            ('probability', '<', 100),
            ('partner_id', '!=', False),
        ])
        partners_with_leads = open_leads.mapped('partner_id')

        Message = self.env['casafolino.mail.message']
        Activity = self.env['mail.activity']
        partner_model_id = self.env['ir.model']._get('res.partner').id
        todo_type = self.env.ref('mail.mail_activity_data_todo')

        silent_count = 0
        for partner in partners_with_leads:
            # Ultima email keep/auto_keep per questo partner
            last_email = Message.search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['keep', 'auto_keep']),
            ], order='email_date desc', limit=1)

            if last_email and last_email.email_date and last_email.email_date > cutoff_date:
                continue  # non silente

            # Evita duplicati: se esiste già activity "Riattivare" pending
            existing = Activity.search([
                ('res_model_id', '=', partner_model_id),
                ('res_id', '=', partner.id),
                ('summary', 'ilike', 'Riattivare conversazione'),
                ('date_deadline', '>=', fields.Date.today()),
            ], limit=1)
            if existing:
                continue

            # Salesperson dal lead, o admin
            related_lead = open_leads.filtered(lambda l: l.partner_id == partner)[:1]
            user = related_lead.user_id if related_lead and related_lead.user_id else False
            if not user:
                user = self.env.ref('base.user_admin')

            last_date_str = str(last_email.email_date.date()) if last_email and last_email.email_date else 'mai'
            Activity.create({
                'activity_type_id': todo_type.id,
                'summary': 'Riattivare conversazione',
                'note': 'Partner silente da oltre %d giorni. Ultima email: %s' % (threshold, last_date_str),
                'date_deadline': fields.Date.today(),
                'user_id': user.id,
                'res_model_id': partner_model_id,
                'res_id': partner.id,
            })
            silent_count += 1

        _logger.info('Silent partners alert: %d activity create', silent_count)
        return silent_count

    # ── OWL Client API ───────────────────────────────────────────────

    @api.model
    def is_admin(self, *args, **kw):
        return (
            self.env.user.has_group('base.group_system')
            or self.env.user.login in ('antonio@casafolino.com',)
        )

    @api.model
    def get_accounts(self, *args, **kw):
        domain = [('active', '=', True), ('responsible_user_id', '=', self.env.uid)]
        accounts = self.search(domain, order='name')
        result = []
        for a in accounts:
            unread = self.env['casafolino.mail.message'].search_count([
                ('account_id', '=', a.id),
                ('is_read', '=', False),
                ('state', '=', 'keep'),
                ('direction', '=', 'inbound'),
            ])
            result.append({
                'id': a.id,
                'name': a.name or a.email_address,
                'email': a.email_address or '',
                'color': '#5A6E3A',
                'is_team': False,
                'unread': unread,
                'signature': a.signature_html or '',
                'imap_enabled': a.state == 'connected',
                'imap_status': a.state or '',
            })
        return result

    @api.model
    def get_account_detail(self, *args, **kw):
        account_id = kw.get('account_id')
        if not account_id:
            return {}
        acc = self.browse(int(account_id))
        if not acc.exists():
            return {}
        return {
            'id': acc.id,
            'name': acc.name or '',
            'email': acc.email_address or '',
            'color': '#5A6E3A',
            'signature': acc.signature_html or '',
            'imap_host': acc.imap_host or 'imap.gmail.com',
            'imap_port': acc.imap_port or 993,
            'imap_ssl': acc.imap_use_ssl,
            'imap_enabled': acc.state == 'connected',
            'imap_status': acc.state or '',
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_tls': True,
            'ooo_enabled': False,
            'ooo_subject': '',
            'ooo_message': '',
            'ooo_start': '',
            'ooo_end': '',
        }

    @api.model
    def save_account(self, *args, **kw):
        account_id = kw.get('id') or False
        vals = {
            'name': kw.get('name') or '',
            'email_address': kw.get('email') or '',
            'imap_host': kw.get('imap_host') or 'imap.gmail.com',
            'imap_port': int(kw.get('imap_port') or 993),
            'imap_use_ssl': bool(kw.get('imap_ssl')),
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
    def test_connection(self, *args, **kw):
        account_id = kw.get('account_id')
        if not account_id:
            return {'success': False, 'error': 'Account non trovato'}
        acc = self.browse(int(account_id))
        if not acc.exists():
            return {'success': False, 'error': 'Account non trovato'}
        try:
            acc.action_test_connection()
            return {'success': True, 'message': 'Connessione riuscita'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}

    @api.model
    def sync_now(self, *args, **kw):
        account_id = kw.get('account_id')
        if account_id:
            acc = self.browse(int(account_id))
        else:
            acc = self.search([('state', '=', 'connected')])
        for a in acc:
            a._fetch_emails()
        return {'success': True}
