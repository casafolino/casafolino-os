import email
import imaplib
import logging
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CasafolinoMailAccount(models.Model):
    _name = 'casafolino.mail.account'
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
    fetch_inbox = fields.Boolean('Scarica INBOX', default=True)
    fetch_sent = fields.Boolean('Scarica Sent', default=True)
    company_domain = fields.Char('Dominio aziendale', default='casafolino.com',
        help='Email da questo dominio sono considerate interne')

    # ── Connection helpers ────────────────────────────────────────────

    def _get_imap_connection(self):
        """Apre connessione IMAP SSL a Gmail."""
        self.ensure_one()
        try:
            if self.imap_use_ssl:
                imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                imap = imaplib.IMAP4(self.imap_host, self.imap_port)
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
                'last_fetch_datetime': fields.Datetime.now(),
                'state': 'connected',
                'error_message': False,
            })

            _logger.info(
                "Mail fetch %s: %d nuove, %d duplicate, %d blacklisted",
                self.email_address, total_new, total_skip, total_blacklist
            )

        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})
            _logger.error("Mail fetch error %s: %s", self.email_address, e)
            raise
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    def _fetch_folder(self, imap, folder_name, direction):
        """Fetch di una singola cartella IMAP."""
        Blacklist = self.env['casafolino.mail.blacklist']
        Message = self.env['casafolino.mail.message']

        new_count = 0
        skip_count = 0
        blacklist_count = 0

        # Seleziona la cartella (readonly)
        status, data = imap.select('"%s"' % folder_name, readonly=True)
        if status != 'OK':
            _logger.warning("Cannot select folder %s: %s", folder_name, data)
            return 0, 0, 0

        # Costruisci criterio di ricerca — formato data IMAP: 01-Jan-2025
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

        # Processa in batch da 50
        batch_size = 50
        for i in range(0, len(uid_list), batch_size):
            batch = uid_list[i:i + batch_size]

            for uid in batch:
                uid_str = uid.decode()

                # Scarica solo header (no body — snippet viene dal Subject)
                status2, header_data = imap.fetch(uid, '(BODY.PEEK[HEADER])')
                if status2 != 'OK':
                    continue

                # Parsa gli header
                raw_header = None
                for part in header_data:
                    if isinstance(part, tuple):
                        raw_header = part[1]
                        break

                if not raw_header:
                    continue

                msg = email.message_from_bytes(raw_header)

                # Estrai Message-ID
                message_id = msg.get('Message-ID', '').strip()
                if not message_id:
                    message_id = "<%s-%s-%s@generated>" % (self.email_address, uid_str, folder_name)

                # Deduplicazione: skip se Message-ID già esiste
                existing = Message.search([('message_id_rfc', '=', message_id), ('account_id', '=', self.id)], limit=1)
                if existing:
                    skip_count += 1
                    continue

                # Estrai mittente
                sender_name, sender_email = parseaddr(msg.get('From', ''))
                sender_name = self._decode_header_value(sender_name)
                sender_email = sender_email.lower().strip() if sender_email else ''

                # Check blacklist
                if sender_email and Blacklist.is_blacklisted(sender_email):
                    blacklist_count += 1
                    continue

                # Estrai destinatari
                to_raw = msg.get('To', '')
                cc_raw = msg.get('Cc', '')
                recipient_emails = self._extract_emails(to_raw)
                cc_emails = self._extract_emails(cc_raw)

                # Estrai oggetto
                subject = self._decode_header_value(msg.get('Subject', '(nessun oggetto)'))

                # Estrai data
                date_str = msg.get('Date', '')
                try:
                    email_date = parsedate_to_datetime(date_str)
                except Exception:
                    email_date = fields.Datetime.now()

                # Determina direction effettiva
                actual_direction = direction
                if direction == 'inbound' and sender_email == self.email_address.lower():
                    actual_direction = 'outbound'

                # Matching con res.partner
                partner_id, match_type = self._match_partner(
                    sender_email, recipient_emails, actual_direction
                )

                # Crea record staging
                vals = {
                    'account_id': self.id,
                    'message_id_rfc': message_id,
                    'imap_uid': uid_str,
                    'imap_folder': folder_name,
                    'direction': actual_direction,
                    'sender_email': sender_email,
                    'sender_name': sender_name,
                    'recipient_emails': recipient_emails,
                    'cc_emails': cc_emails,
                    'subject': subject,
                    'email_date': email_date,
                    'state': 'new',
                    'partner_id': partner_id,
                    'match_type': match_type,
                }

                # Email inviate → sempre keep (le hai inviate tu)
                if actual_direction == 'outbound':
                    vals['state'] = 'keep'
                # Se il partner è tracked, scarica subito body e metti in keep
                elif partner_id:
                    partner = self.env['res.partner'].browse(partner_id)
                    if partner.mail_tracked:
                        vals['state'] = 'keep'

                try:
                    new_msg = Message.create(vals)
                    new_count += 1

                    # Se stato keep (partner tracked), scarica body
                    if new_msg.state == 'keep':
                        new_msg._download_body_imap(imap, folder_name, uid_str)

                except Exception as e:
                    _logger.warning("Error creating mail message: %s", e)
                    continue

            # Aggiorna last_fetch_datetime e committa ogni batch
            self.write({
                'last_fetch_datetime': fields.Datetime.now(),
                'state': 'connected',
                'error_message': False,
            })
            self.env.cr.commit()
            _logger.info("Batch %d: %d nuove fin qui", i // batch_size + 1, new_count)

        return new_count, skip_count, blacklist_count

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
                'signature': '',
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
            'signature': '',
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
