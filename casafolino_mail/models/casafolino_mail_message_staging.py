import base64
import email
import logging
import re

from odoo import models, fields, api
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

# Lista esatta di titoli professionali riconosciuti (case-insensitive)
_ROLE_TITLES = [
    'Export Manager', 'Import Manager', 'Category Manager',
    'Buyer', 'Purchase Manager', 'Procurement Manager', 'Purchasing Manager',
    'Sales Manager', 'Sales Director', 'Key Account Manager',
    'CEO', 'COO', 'CFO',
    'Managing Director', 'General Manager',
    'Owner', 'Founder', 'Co-Founder',
    'Quality Manager', 'Operations Manager', 'Logistics Manager',
    'Marketing Manager', 'Brand Manager',
    'Responsabile Acquisti', 'Directeur Commercial',
    'Geschäftsführer',
]
# Compila pattern: match esatto solo su titoli completi
_ROLE_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(t) for t in _ROLE_TITLES) + r')\b',
    re.IGNORECASE
)

# Parole chiave per detect lingua
_LANG_KEYWORDS = {
    'de_DE': {'sehr', 'geehrte', 'freundlichen', 'grüßen', 'bezüglich', 'anfrage',
              'angebot', 'lieferung', 'bestellung', 'vielen', 'dank', 'bitte'},
    'fr_FR': {'bonjour', 'cordialement', 'merci', 'veuillez', 'salutations',
              'madame', 'monsieur', 'commande', 'livraison', 'produits'},
    'es_ES': {'estimado', 'saludos', 'cordiales', 'gracias', 'pedido',
              'envío', 'productos', 'atentamente', 'buenos', 'días'},
    'it_IT': {'gentile', 'cordiali', 'saluti', 'grazie', 'ordine',
              'spedizione', 'prodotti', 'distinti', 'buongiorno', 'gentilissimo'},
}


class CasafolinoMailMessage(models.Model):
    _name = 'casafolino.mail.message'
    _description = 'Email Staging — Mail Hub Triage'
    _order = 'email_date desc, id desc'

    account_id = fields.Many2one('casafolino.mail.account', string='Account',
                                  required=True, ondelete='cascade')
    message_id_rfc = fields.Char('Message-ID RFC 2822', index=True)
    imap_uid = fields.Char('UID IMAP')
    imap_folder = fields.Char('Cartella IMAP')
    direction = fields.Selection([
        ('inbound', 'Ricevuta'),
        ('outbound', 'Inviata'),
    ], string='Direzione')
    sender_email = fields.Char('Email mittente')
    sender_name = fields.Char('Nome mittente')
    sender_domain = fields.Char('Dominio mittente', compute='_compute_sender_domain',
                                 store=True, index=True)
    recipient_emails = fields.Char('Destinatari')
    cc_emails = fields.Char('CC')
    subject = fields.Char('Oggetto')
    email_date = fields.Datetime('Data email')
    snippet = fields.Text('Anteprima')

    state = fields.Selection([
        ('new', 'Nuova'),
        ('keep', 'Tenuta'),
        ('discard', 'Scartata'),
    ], string='Stato', default='new', index=True)

    partner_id = fields.Many2one('res.partner', string='Contatto')
    match_type = fields.Selection([
        ('exact', 'Email esatta'),
        ('domain', 'Dominio'),
        ('manual', 'Manuale'),
        ('none', 'Nessuno'),
    ], string='Tipo match', default='none')

    body_html = fields.Html('Body HTML', sanitize=False)
    body_downloaded = fields.Boolean('Body scaricato', default=False)
    attachment_ids = fields.One2many('ir.attachment', 'res_id',
                                      string='Allegati',
                                      domain=[('res_model', '=', 'casafolino.mail.message')])
    triage_user_id = fields.Many2one('res.users', string='Triage da')
    triage_date = fields.Datetime('Data triage')
    is_read = fields.Boolean('Letta', default=False)
    is_important = fields.Boolean('Importante', default=False)
    assigned_user_ids = fields.Many2many(
        'res.users', 'casafolino_mail_message_user_rel',
        'message_id', 'user_id', string='Assegnato a')
    lead_id = fields.Many2one('crm.lead', string='Trattativa CRM', ondelete='set null')

    _sql_constraints = [
        ('message_id_unique', 'unique(message_id_rfc)',
         'Email già presente (Message-ID duplicato).'),
    ]

    @api.depends('sender_email')
    def _compute_sender_domain(self):
        for rec in self:
            if rec.sender_email and '@' in rec.sender_email:
                rec.sender_domain = rec.sender_email.split('@')[1].lower().strip()
            else:
                rec.sender_domain = ''

    # ── Triage actions (Step 3) ──────────────────────────────────────

    def action_keep(self):
        """Marca come keep, scarica body, collega a partner."""
        for record in self:
            record.write({
                'state': 'keep',
                'triage_user_id': self.env.user.id,
                'triage_date': fields.Datetime.now(),
            })

            # Scarica body se non ancora fatto
            if not record.body_downloaded:
                try:
                    imap = record.account_id._get_imap_connection()
                    record._download_body_imap(imap, record.imap_folder, record.imap_uid)
                    imap.logout()
                except Exception as e:
                    _logger.error("Error downloading body for %s: %s", record.message_id_rfc, e)

            # Se ha un partner, attiva tracking (email visibili dalla tab Email)
            if record.partner_id:
                if not record.partner_id.mail_tracked:
                    record.partner_id.mail_tracked = True

        # Auto-keep: tutte le email dallo stesso mittente ancora in 'new'
        sender_emails = set()
        for record in self:
            if record.sender_email:
                sender_emails.add(record.sender_email.lower().strip())
        if sender_emails:
            siblings = self.search([
                ('sender_email', 'in', list(sender_emails)),
                ('state', '=', 'new'),
                ('id', 'not in', self.ids),
            ])
            if siblings:
                # Trova il partner_id dal record appena processato per ogni sender
                sender_partner = {}
                for record in self:
                    if record.sender_email and record.partner_id:
                        sender_partner[record.sender_email.lower().strip()] = record.partner_id.id
                for sib in siblings:
                    sib_vals = {
                        'state': 'keep',
                        'triage_user_id': self.env.user.id,
                        'triage_date': fields.Datetime.now(),
                    }
                    pid = sender_partner.get((sib.sender_email or '').lower().strip())
                    if pid and not sib.partner_id:
                        sib_vals['partner_id'] = pid
                        sib_vals['match_type'] = 'exact'
                    sib.write(sib_vals)
                    if not sib.body_downloaded:
                        try:
                            imap = sib.account_id._get_imap_connection()
                            sib._download_body_imap(imap, sib.imap_folder, sib.imap_uid)
                            imap.logout()
                        except Exception as e:
                            _logger.error("Auto-keep body error %s: %s", sib.message_id_rfc, e)

    def action_discard(self):
        """Marca come discard."""
        self.write({
            'state': 'discard',
            'triage_user_id': self.env.user.id,
            'triage_date': fields.Datetime.now(),
        })

    # ── Body download (Step 3) ───────────────────────────────────────

    def _download_body_imap(self, imap, folder_name, uid):
        """Scarica body completo e allegati via IMAP."""
        self.ensure_one()

        status, _ = imap.select('"%s"' % folder_name, readonly=True)
        if status != 'OK':
            return

        # Scarica messaggio completo
        uid_bytes = uid.encode() if isinstance(uid, str) else uid
        status, msg_data = imap.fetch(uid_bytes, '(RFC822)')
        if status != 'OK':
            return

        raw_email = None
        for part in msg_data:
            if isinstance(part, tuple):
                raw_email = part[1]
                break

        if not raw_email:
            return

        msg = email.message_from_bytes(raw_email)

        # Estrai body e allegati
        body_html = ''
        body_text = ''
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                # Allegati
                if 'attachment' in content_disposition or part.get_filename():
                    filename = part.get_filename()
                    if filename:
                        filename = self.env['casafolino.mail.account']._decode_header_value(filename)
                        file_data = part.get_payload(decode=True)
                        if file_data:
                            attachments.append({
                                'name': filename,
                                'datas': base64.b64encode(file_data),
                                'mimetype': content_type,
                            })
                # Body
                elif content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body_html = payload.decode(charset, errors='ignore')
                elif content_type == 'text/plain' and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body_text = payload.decode(charset, errors='ignore')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                if msg.get_content_type() == 'text/html':
                    body_html = payload.decode(charset, errors='ignore')
                else:
                    body_text = payload.decode(charset, errors='ignore')

        # Salva body
        self.write({
            'body_html': body_html or ('<pre>%s</pre>' % body_text),
            'body_downloaded': True,
        })

        # Crea allegati
        for att in attachments:
            self.env['ir.attachment'].create({
                'name': att['name'],
                'datas': att['datas'],
                'mimetype': att['mimetype'],
                'res_model': 'casafolino.mail.message',
                'res_id': self.id,
            })

    # ── Chatter integration (Step 4) ─────────────────────────────────

    def _create_partner_mail_message(self):
        """Crea mail.message nativo nel chatter del partner."""
        self.ensure_one()
        if not self.partner_id or not self.body_html:
            return

        # Evita duplicati
        existing = self.env['mail.message'].search([
            ('message_id', '=', self.message_id_rfc),
            ('res_id', '=', self.partner_id.id),
            ('model', '=', 'res.partner'),
        ], limit=1)
        if existing:
            return

        # Crea mail.message nel chatter — DATA ORIGINALE, non now()
        msg_vals = {
            'model': 'res.partner',
            'res_id': self.partner_id.id,
            'message_type': 'email',
            'subtype_id': self.env.ref('mail.mt_note').id,
            'body': self.body_html,
            'subject': self.subject,
            'email_from': self.sender_email,
            'date': self.email_date,
            'message_id': self.message_id_rfc,
        }
        self.env['mail.message'].sudo().create(msg_vals)

    # ── Blacklist + Quick actions (Step 6) ────────────────────────────

    def action_blacklist_domain(self):
        """Aggiunge il dominio alla blacklist e scarta tutte le email new da quel dominio."""
        Blacklist = self.env['casafolino.mail.blacklist']
        domains_done = set()

        for record in self:
            domain = record.sender_domain
            if domain and domain not in domains_done:
                existing = Blacklist.search([('type', '=', 'domain'), ('value', '=', domain)], limit=1)
                if not existing:
                    Blacklist.create({'type': 'domain', 'value': domain})
                domains_done.add(domain)

        # Scarta TUTTE le email new da questi domini
        if domains_done:
            all_from_domains = self.search([
                ('sender_domain', 'in', list(domains_done)),
                ('state', '=', 'new'),
            ])
            all_from_domains.write({
                'state': 'discard',
                'triage_user_id': self.env.user.id,
                'triage_date': fields.Datetime.now(),
            })

    def _get_contact_email_and_name(self):
        """Ritorna (email, name) del contatto esterno per questa email."""
        self.ensure_one()
        ext_email = self.account_id._get_external_email(
            self.sender_email or '', self.recipient_emails or '')
        # Se l'email esterna è il mittente, usa sender_name
        if ext_email == self.sender_email:
            name = self.sender_name or ext_email
        else:
            name = ext_email
        return ext_email, name

    def action_create_partner(self):
        """Crea un nuovo res.partner arricchito dall'email."""
        self.ensure_one()
        email_addr, name = self._get_contact_email_and_name()

        vals = {
            'name': name or email_addr,
            'email': email_addr,
        }
        self._enrich_partner_vals(vals)

        partner = self.env['res.partner'].create(vals)
        self.write({'partner_id': partner.id, 'match_type': 'manual'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _enrich_partner_vals(self, vals):
        """Arricchisce i vals per la creazione partner con dati estratti dall'email."""
        self.ensure_one()
        email_addr = vals.get('email', '')

        # Estrai company_name dal dominio (se non generica)
        generic_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
            'icloud.com', 'mail.com', 'protonmail.com', 'live.com', 'msn.com',
            'gmx.de', 'web.de', 'libero.it', 'virgilio.it', 'alice.it',
            't-online.de', 'wanadoo.fr', 'orange.fr', 'free.fr',
        }
        if email_addr and '@' in email_addr:
            domain = email_addr.split('@')[1].lower()
            if domain not in generic_domains:
                company_name = domain.split('.')[0].capitalize()
                vals['company_name'] = company_name

        # Estrai body text per analisi
        body_text = ''
        if self.body_html:
            body_text = re.sub(r'<[^>]+>', ' ', self.body_html)
            body_text = re.sub(r'\s+', ' ', body_text).strip()

        # Cerca ruolo/mansione nelle ultime 10 righe (firma) — solo titoli esatti
        if body_text:
            lines = body_text.split('\n')
            signature_block = '\n'.join(lines[-10:]) if len(lines) > 10 else body_text
            role_match = _ROLE_PATTERN.search(signature_block)
            if role_match:
                vals['function'] = role_match.group(0).strip()

        # Detect lingua
        if body_text:
            body_lower = body_text.lower()
            words = set(re.findall(r'\b\w+\b', body_lower))
            best_lang = 'en_US'
            best_score = 0
            for lang, keywords in _LANG_KEYWORDS.items():
                score = len(words & keywords)
                if score > best_score:
                    best_score = score
                    best_lang = lang
            if best_score >= 2:
                vals['lang'] = best_lang

    def action_launch_007(self):
        """Lancia Agente 007 sul partner collegato."""
        self.ensure_one()
        if self.partner_id:
            return self.partner_id.action_enrich_007()

    # ── Parse body from already-fetched message (Step 7) ─────────────

    def _parse_and_save_body(self, msg_obj):
        """Parsa body e allegati da un oggetto email.message già scaricato."""
        self.ensure_one()
        body_html = ''
        body_text = ''
        attachments = []

        if msg_obj.is_multipart():
            for part in msg_obj.walk():
                content_type = part.get_content_type()
                disposition = str(part.get('Content-Disposition', ''))

                if 'attachment' in disposition or part.get_filename():
                    filename = part.get_filename()
                    if filename:
                        filename = self.env['casafolino.mail.account']._decode_header_value(filename)
                        file_data = part.get_payload(decode=True)
                        if file_data:
                            attachments.append({
                                'name': filename,
                                'datas': base64.b64encode(file_data),
                                'mimetype': content_type,
                            })
                elif content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                elif content_type == 'text/plain' and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
        else:
            payload = msg_obj.get_payload(decode=True)
            if payload:
                charset = msg_obj.get_content_charset() or 'utf-8'
                if msg_obj.get_content_type() == 'text/html':
                    body_html = payload.decode(charset, errors='ignore')
                else:
                    body_text = payload.decode(charset, errors='ignore')

        self.write({
            'body_html': body_html or ('<pre>%s</pre>' % body_text),
            'body_downloaded': True,
        })

        for att in attachments:
            self.env['ir.attachment'].create({
                'name': att['name'],
                'datas': att['datas'],
                'mimetype': att['mimetype'],
                'res_model': 'casafolino.mail.message',
                'res_id': self.id,
            })

    # ── Bulk actions ───────────────────────────────────────────────────

    def action_reset_new(self):
        """Rimetti in Da Valutare."""
        self.write({
            'state': 'new',
            'triage_user_id': False,
            'triage_date': False,
        })

    def action_rematch_partner(self):
        """Ri-match automatico per email senza partner (usa logica dominio interno)."""
        for record in self.filtered(lambda r: not r.partner_id):
            partner_id, match_type = record.account_id._match_partner(
                record.sender_email or '', record.recipient_emails or '',
                record.direction or 'inbound')
            if partner_id:
                record.write({'partner_id': partner_id, 'match_type': match_type})

    @api.model
    def _rematch_internal_emails(self):
        """Fix email matchate su partner interni @casafolino.com: resetta e ri-matcha."""
        # Trova tutti i record matchati su partner con email @casafolino.com
        internal_matched = self.search([
            ('partner_id', '!=', False),
            ('partner_id.email', 'ilike', '%@casafolino.com'),
        ])
        _logger.info("Rematch: %d email matchate su partner interni", len(internal_matched))

        count_fixed = 0
        for record in internal_matched:
            # Resetta e ri-matcha con logica corretta
            record.write({'partner_id': False, 'match_type': 'none'})
            partner_id, match_type = record.account_id._match_partner(
                record.sender_email or '', record.recipient_emails or '',
                record.direction or 'inbound')
            if partner_id:
                record.write({'partner_id': partner_id, 'match_type': match_type})
                count_fixed += 1

        _logger.info("Rematch completato: %d/%d ri-matchati su partner esterni",
                      count_fixed, len(internal_matched))
        return count_fixed

    def action_bulk_create_partners(self):
        """Crea contatti da email selezionate senza partner."""
        Partner = self.env['res.partner']
        for record in self.filtered(lambda r: not r.partner_id):
            email_addr, name = record._get_contact_email_and_name()
            if not email_addr:
                continue
            existing = Partner.search([('email', '=ilike', email_addr)], limit=1)
            if existing:
                record.write({'partner_id': existing.id, 'match_type': 'exact'})
            else:
                partner = Partner.create({
                    'name': name or email_addr,
                    'email': email_addr,
                })
                record.write({'partner_id': partner.id, 'match_type': 'manual'})

    def action_bulk_launch_007(self):
        """Lancia Agente 007 su tutti i partner collegati (senza duplicati)."""
        partners_done = set()
        for record in self.filtered(lambda r: r.partner_id):
            if record.partner_id.id not in partners_done:
                try:
                    record.partner_id.action_enrich_007()
                except Exception as e:
                    _logger.warning("007 bulk error partner %s: %s", record.partner_id.id, e)
                partners_done.add(record.partner_id.id)

    def action_mark_important(self):
        """Segna come importante."""
        self.write({'is_important': True})

    def action_mark_read(self):
        """Segna come letto."""
        self.write({'is_read': True})

    def action_mark_unread(self):
        """Segna come non letto."""
        self.write({'is_read': False})

    def action_bulk_delete(self):
        """Elimina selezionati (solo admin)."""
        if not self.env.user.has_group('base.group_system'):
            raise AccessError("Solo gli amministratori possono eliminare.")
        self.unlink()

    def action_discard_domain_no_blacklist(self):
        """Scarta tutto il dominio dei selezionati senza aggiungere alla blacklist."""
        domains = set()
        for record in self:
            if record.sender_domain:
                domains.add(record.sender_domain)
        if domains:
            all_from_domains = self.search([
                ('sender_domain', 'in', list(domains)),
                ('state', '=', 'new'),
            ])
            all_from_domains.write({
                'state': 'discard',
                'triage_user_id': self.env.user.id,
                'triage_date': fields.Datetime.now(),
            })

    def _ensure_body_downloaded(self):
        """Scarica body per i record che non lo hanno ancora."""
        for record in self.filtered(lambda r: not r.body_downloaded):
            try:
                imap = record.account_id._get_imap_connection()
                record._download_body_imap(imap, record.imap_folder, record.imap_uid)
                imap.logout()
            except Exception as e:
                _logger.error("Error downloading body for %s: %s", record.message_id_rfc, e)

    # ── Cron cleanup (Step 8) ────────────────────────────────────────

    @api.model
    def _cron_cleanup_discarded(self):
        """Elimina email scartate più vecchie di 30 giorni."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(days=30)
        old = self.search([('state', '=', 'discard'), ('triage_date', '<', cutoff)])
        count = len(old)
        old.unlink()
        _logger.info("Mail cleanup: %d email scartate eliminate.", count)

    # ── OWL Client API ───────────────────────────────────────────────

    def _msg_to_dict(self, m):
        """Converte un record in dict per il client OWL."""
        return {
            'id': m.id,
            'subject': m.subject or '(nessun oggetto)',
            'from_address': m.sender_email or '',
            'from_name': m.sender_name or m.sender_email or '',
            'snippet': m.snippet or '',
            'date': m.email_date.strftime('%d/%m/%Y %H:%M') if m.email_date else '',
            'date_short': m.email_date.strftime('%d %b') if m.email_date else '',
            'is_read': m.is_read,
            'is_starred': m.is_important,
            'is_archived': False,
            'replied': False,
            'direction': 'in' if m.direction == 'inbound' else 'out',
            'folder': 'INBOX' if m.direction == 'inbound' else 'Sent',
            'has_attachments': bool(m.attachment_ids),
            'attachment_names': ', '.join(m.attachment_ids.mapped('name')) if m.attachment_ids else '',
            'thread_count': 0,
            'partner_id': m.partner_id.id if m.partner_id else False,
            'partner_name': m.partner_id.name if m.partner_id else '',
            'lead_id': False,
            'lead_name': '',
            'assigned_user_id': m.assigned_user_ids[0].id if m.assigned_user_ids else False,
            'assigned_user_name': m.assigned_user_ids[0].name if m.assigned_user_ids else '',
            'tags': [],
            'lead_stage': '',
            'sender_action': False,
            'state': m.state,
        }

    @api.model
    def get_messages(self, *args, **kw):
        """API per il client OWL — ritorna email kept."""
        account_id = kw.get('account_id')
        folder = kw.get('folder') or 'INBOX'
        limit = int(kw.get('limit') or 50)
        offset = int(kw.get('offset') or 0)
        search = kw.get('search') or ''

        # Ownership check: account deve appartenere all'utente
        if account_id and not self.env.user.has_group('base.group_system'):
            acc = self.env['casafolino.mail.account'].browse(int(account_id))
            if not acc.exists() or acc.responsible_user_id.id != self.env.uid:
                return []

        domain = [('state', '=', 'keep')]

        if account_id:
            domain.append(('account_id', '=', account_id))

        if folder == 'Sent':
            domain.append(('direction', '=', 'outbound'))
        elif folder == 'Starred':
            domain.append(('is_important', '=', True))
        elif folder == 'INBOX':
            domain.append(('direction', '=', 'inbound'))

        if search:
            domain += ['|', '|', '|',
                ('subject', 'ilike', search),
                ('sender_email', 'ilike', search),
                ('sender_name', 'ilike', search),
                ('recipient_emails', 'ilike', search),
            ]

        msgs = self.search(domain, limit=limit, offset=offset)
        return [self._msg_to_dict(m) for m in msgs]

    @api.model
    def get_message_detail(self, *args, **kw):
        """API per il client OWL — dettaglio singola email."""
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return {}
        msg = self.browse(int(message_id))
        if not msg.exists():
            return {}

        # Segna come letta
        if not msg.is_read:
            msg.write({'is_read': True})

        # Scarica body se necessario
        if not msg.body_downloaded:
            try:
                imap = msg.account_id._get_imap_connection()
                msg._download_body_imap(imap, msg.imap_folder, msg.imap_uid)
                imap.logout()
            except Exception as e:
                _logger.error("Error downloading body for detail %s: %s", msg.message_id_rfc, e)

        result = self._msg_to_dict(msg)
        result['body_html'] = msg.body_html or ''
        result['to_address'] = msg.recipient_emails or ''
        result['cc_address'] = msg.cc_emails or ''

        # Info partner
        if msg.partner_id:
            p = msg.partner_id
            result['partner_info'] = {
                'id': p.id,
                'name': p.name or '',
                'email': p.email or '',
                'phone': p.phone or '',
                'company': p.parent_id.name if p.parent_id else (p.company_name or ''),
                'job_title': p.function or '',
            }

        return result

    @api.model
    def get_users_list(self, *args, **kw):
        users = self.env['res.users'].search([('share', '=', False)], limit=50)
        return [{'id': u.id, 'name': u.name} for u in users]

    @api.model
    def get_leads_list(self, *args, **kw):
        try:
            leads = self.env['crm.lead'].search([], limit=100, order='create_date desc')
            return [{'id': l.id, 'name': l.name} for l in leads]
        except Exception:
            return []

    @api.model
    def get_tags_list(self, *args, **kw):
        return []

    @api.model
    def do_bulk_action(self, *args, **kw):
        ids = kw.get('ids', [])
        action = kw.get('action', '')
        if not ids or not action:
            return True
        records = self.browse(ids)
        if action == 'mark_read':
            records.write({'is_read': True})
        elif action == 'mark_unread':
            records.write({'is_read': False})
        elif action == 'archive':
            records.action_discard()
        elif action == 'star':
            records.write({'is_important': True})
        elif action == 'unstar':
            records.write({'is_important': False})
        elif action == 'delete':
            records.unlink()
        return True

    @api.model
    def do_toggle_star(self, *args, **kw):
        message_id = kw.get('message_id')
        if not message_id:
            return False
        msg = self.browse(int(message_id))
        msg.write({'is_important': not msg.is_important})
        return msg.is_important

    # ── Lead Email Widget API ────────────────────────────────────────

    @api.model
    def get_lead_emails(self, *args, **kw):
        """Ritorna email collegate a un lead per il widget embedded."""
        lead_id = kw.get('lead_id')
        if not lead_id:
            return []
        msgs = self.search([('lead_id', '=', int(lead_id))], order='email_date desc')
        return [self._msg_to_dict(m) for m in msgs]

    @api.model
    def send_from_lead(self, *args, **kw):
        """Invia email da una trattativa CRM e collegala al lead."""
        lead_id = kw.get('lead_id')
        to_address = kw.get('to_address') or ''
        cc_address = kw.get('cc_address') or ''
        subject = kw.get('subject') or ''
        body = kw.get('body') or ''
        reply_to_id = kw.get('reply_to_id') or False

        if not to_address or not body:
            return {'success': False, 'error': 'Destinatario e corpo obbligatori'}

        # Prendi il primo account dell'utente corrente
        account = self.env['casafolino.mail.account'].search([
            ('responsible_user_id', '=', self.env.uid),
            ('state', '=', 'connected'),
        ], limit=1)
        if not account:
            return {'success': False, 'error': 'Nessun account email configurato'}

        try:
            import smtplib
            import ssl as ssl_lib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg_obj = MIMEMultipart('alternative')
            msg_obj['Subject'] = subject
            msg_obj['From'] = '%s <%s>' % (account.name or account.email_address, account.email_address)
            msg_obj['To'] = to_address
            if cc_address:
                msg_obj['Cc'] = cc_address

            # In-Reply-To se è una risposta
            if reply_to_id:
                orig = self.browse(int(reply_to_id))
                if orig.exists() and orig.message_id_rfc:
                    msg_obj['In-Reply-To'] = orig.message_id_rfc
                    msg_obj['References'] = orig.message_id_rfc

            msg_obj.attach(MIMEText(body, 'html', 'utf-8'))

            recipients = [r.strip() for r in to_address.split(',') if r.strip()]
            if cc_address:
                recipients += [r.strip() for r in cc_address.split(',') if r.strip()]

            # Invio SMTP
            if account.imap_password:
                server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
                server.ehlo()
                server.starttls(context=ssl_lib.create_default_context())
                server.ehlo()
                server.login(account.email_address, account.imap_password)
                server.sendmail(account.email_address, recipients, msg_obj.as_string())
                server.quit()
            else:
                return {'success': False, 'error': 'Password SMTP non configurata'}

            # Crea record email inviata collegata al lead
            self.create({
                'account_id': account.id,
                'message_id_rfc': msg_obj.get('Message-ID', ''),
                'direction': 'outbound',
                'sender_email': account.email_address,
                'sender_name': account.name or '',
                'recipient_emails': to_address,
                'cc_emails': cc_address,
                'subject': subject,
                'email_date': fields.Datetime.now(),
                'body_html': body,
                'body_downloaded': True,
                'state': 'keep',
                'is_read': True,
                'lead_id': int(lead_id) if lead_id else False,
                'triage_user_id': self.env.user.id,
                'triage_date': fields.Datetime.now(),
            })

            return {'success': True}
        except Exception as e:
            _logger.error("send_from_lead error: %s", e)
            return {'success': False, 'error': str(e)[:200]}

    @api.model
    def get_crm_data(self, *args, **kw):
        """Dati per il Lead Modal: market/channel selections, stages, partners, sources."""
        # cf_market selection values dal modello crm.lead (esteso da casafolino_crm_export)
        market_list = []
        channel_list = []
        try:
            lead_fields = self.env['crm.lead'].fields_get(['cf_market', 'cf_channel'])
            if 'cf_market' in lead_fields:
                market_list = [{'value': k, 'name': v}
                               for k, v in lead_fields['cf_market']['selection']]
            if 'cf_channel' in lead_fields:
                channel_list = [{'value': k, 'name': v}
                                for k, v in lead_fields['cf_channel']['selection']]
        except Exception:
            pass

        # Stages CRM
        try:
            stages = self.env['crm.stage'].search([], order='sequence')
            stage_list = [{'id': s.id, 'name': s.name} for s in stages]
        except Exception:
            stage_list = []

        # Partners
        partners = self.env['res.partner'].search([('active', '=', True)], limit=500, order='name')
        partner_list = [{'id': p.id, 'name': p.name, 'email': p.email or '', 'is_company': p.is_company}
                        for p in partners]

        # UTM sources
        try:
            sources = self.env['utm.source'].search([], order='name')
            source_list = [{'id': s.id, 'name': s.name} for s in sources]
        except Exception:
            source_list = []

        return {
            'markets': market_list,
            'channels': channel_list,
            'pipelines': stage_list,
            'partners': partner_list,
            'sources': source_list,
        }

    @api.model
    def create_lead_from_form(self, *args, **kw):
        """Crea lead CRM (crm.lead con campi casafolino_crm_export)."""
        name = kw.get('name') or 'Lead da email'
        partner_id = kw.get('partner_id') or False
        stage_id = kw.get('stage_id') or False
        expected_revenue = kw.get('expected_revenue') or 0
        description = kw.get('description') or ''
        try:
            vals = {
                'name': name,
                'type': 'opportunity',
                'partner_id': int(partner_id) if partner_id else False,
                'contact_name': kw.get('contact_name') or '',
                'function': kw.get('function') or '',
                'email_from': kw.get('email_from') or '',
                'phone': kw.get('phone') or '',
                'stage_id': int(stage_id) if stage_id else False,
                'expected_revenue': float(expected_revenue) if expected_revenue else 0,
                'description': description,
                'source_id': int(kw.get('source')) if kw.get('source') else False,
            }
            # Campi casafolino_crm_export
            if kw.get('cf_market'):
                vals['cf_market'] = kw['cf_market']
            if kw.get('cf_channel'):
                vals['cf_channel'] = kw['cf_channel']
            if kw.get('cf_language'):
                vals['cf_language'] = kw['cf_language']

            lead = self.env['crm.lead'].create(vals)

            # Collega le email selezionate al lead
            message_id = kw.get('message_id') or False
            if message_id:
                msg = self.browse(int(message_id))
                if msg.exists():
                    msg.write({'lead_id': lead.id})

            return {'success': True, 'lead_id': lead.id, 'lead_name': lead.name}
        except Exception as e:
            return {'success': False, 'error': str(e)}
