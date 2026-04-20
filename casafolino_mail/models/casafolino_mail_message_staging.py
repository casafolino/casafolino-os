import base64
import email
import json
import logging
import re
import time
import uuid

import requests as req

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
        ('auto_keep', 'Tenuta (auto)'),
        ('keep', 'Tenuta'),
        ('auto_discard', 'Scartata (auto)'),
        ('discard', 'Scartata'),
        ('review', 'Da valutare'),
    ], string='Stato', default='new', index=True)

    policy_applied_id = fields.Many2one('casafolino.mail.sender_policy',
        string='Regola applicata', ondelete='set null')

    partner_id = fields.Many2one('res.partner', string='Contatto')
    match_type = fields.Selection([
        ('exact', 'Email esatta'),
        ('domain', 'Dominio'),
        ('manual', 'Manuale'),
        ('none', 'Nessuno'),
    ], string='Tipo match', default='none')

    body_html = fields.Html('Body HTML', sanitize=False)
    body_plain = fields.Text('Body testo')
    body_downloaded = fields.Boolean('Body scaricato', default=False)

    # ── AI Classifier fields ────────────────────────────────────────
    ai_category = fields.Selection([
        ('commerciale', 'Commerciale'),
        ('admin', 'Amministrativo'),
        ('fornitore', 'Fornitore'),
        ('newsletter', 'Newsletter'),
        ('interno', 'Interno'),
        ('personale', 'Personale'),
        ('spam', 'Spam'),
    ], string='AI Categoria')
    ai_sentiment = fields.Selection([
        ('positive', 'Positivo'),
        ('neutral', 'Neutro'),
        ('negative', 'Negativo'),
    ], string='AI Sentiment')
    ai_language = fields.Selection([
        ('it', 'Italiano'),
        ('en', 'English'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
        ('es', 'Español'),
        ('other', 'Altro'),
    ], string='AI Lingua')
    ai_urgency = fields.Selection([
        ('high', 'Alta'),
        ('medium', 'Media'),
        ('low', 'Bassa'),
    ], string='AI Urgenza')
    ai_action_required = fields.Boolean('AI Action Required', default=False)
    ai_classified_at = fields.Datetime('AI Classificato il')
    ai_raw_response = fields.Text('AI Risposta raw')
    ai_error = fields.Char('AI Errore')
    fetch_state = fields.Selection([
        ('pending', 'In coda'),
        ('done', 'Scaricato'),
        ('error', 'Errore'),
    ], string='Fetch stato', default='pending', index=True)
    fetch_error_msg = fields.Text('Errore fetch')
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
    tracking_token = fields.Char('Tracking Token', index=True)
    tracking_ids = fields.One2many('casafolino.mail.tracking', 'message_id', string='Tracking')
    tracking_open_count = fields.Integer(compute='_compute_tracking_counts', string='Aperture')
    tracking_click_count = fields.Integer(compute='_compute_tracking_counts', string='Click')
    thread_key = fields.Char('Thread Key', index=True, compute='_compute_thread_key', store=True)

    # ── Mail V3 fields ─────────────────────────────────────────────
    thread_id = fields.Many2one('casafolino.mail.thread', string='Thread V3',
                                 ondelete='set null', index=True)
    is_starred = fields.Boolean('Importante V3', default=False)
    is_archived = fields.Boolean('Archiviata', default=False, index=True)
    is_deleted = fields.Boolean('Eliminata (soft)', default=False, index=True)
    reply_to_message_id = fields.Many2one('casafolino.mail.message',
                                           string='In risposta a',
                                           ondelete='set null')
    direction_computed = fields.Selection([
        ('inbound', 'Ricevuta'),
        ('outbound', 'Inviata'),
    ], string='Direzione V3', compute='_compute_direction_v3', store=True)

    @api.depends('direction')
    def _compute_direction_v3(self):
        for rec in self:
            rec.direction_computed = rec.direction or 'inbound'

    # ── Mail V3 actions ────────────────────────────────────────────

    def action_mark_read(self):
        self.write({'is_read': True})

    def action_mark_unread(self):
        self.write({'is_read': False})

    def action_archive(self):
        self.write({'is_archived': True})

    def action_unarchive(self):
        self.write({'is_archived': False})

    def action_delete_soft(self):
        self.write({'is_deleted': True})

    def action_restore(self):
        self.write({'is_deleted': False})

    def action_toggle_star(self):
        for rec in self:
            rec.is_starred = not rec.is_starred

    _SUBJECT_PREFIX_RE = re.compile(
        r'^\s*(Re|R|Fwd|FW|Fw|AW|SV|VS|RE|Rif|RIF)\s*:\s*',
        re.IGNORECASE,
    )

    _sql_constraints = []

    def init(self):
        """Partial unique index: dedup solo per message_id_rfc non vuoti."""
        # Drop old constraints if they exist
        self.env.cr.execute("""
            ALTER TABLE casafolino_mail_message
            DROP CONSTRAINT IF EXISTS casafolino_mail_message_message_id_unique;
        """)
        self.env.cr.execute("""
            ALTER TABLE casafolino_mail_message
            DROP CONSTRAINT IF EXISTS casafolino_mail_message_message_id_account_unique;
        """)
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS casafolino_mail_message_rfc_account_uniq
            ON casafolino_mail_message (message_id_rfc, account_id)
            WHERE message_id_rfc IS NOT NULL AND message_id_rfc != ''
        """)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_thread_upsert'):
            Thread = self.env['casafolino.mail.thread']
            for rec in records:
                if rec.state in ('keep', 'auto_keep'):
                    try:
                        Thread._upsert_from_message(rec)
                    except Exception as e:
                        _logger.warning('[mail v3] Thread upsert fail msg %s: %s', rec.id, e)
        return records

    @api.depends('sender_email')
    def _compute_sender_domain(self):
        for rec in self:
            if rec.sender_email and '@' in rec.sender_email:
                rec.sender_domain = rec.sender_email.split('@')[1].lower().strip()
            else:
                rec.sender_domain = ''

    def _apply_sender_policy(self):
        """Applica la prima sender_policy che matcha a questo messaggio."""
        self.ensure_one()
        Policy = self.env['casafolino.mail.sender_policy']
        policy = Policy.match_sender(self.sender_email, self.subject or '',
                                     ai_category=self.ai_category)
        if not policy:
            return

        vals = {'policy_applied_id': policy.id}

        if policy.action == 'auto_keep':
            vals['state'] = 'auto_keep'
        elif policy.action == 'auto_discard':
            vals['state'] = 'auto_discard'
        elif policy.action == 'escalate':
            vals['state'] = 'review'
            vals['is_important'] = True
        else:  # review
            vals['state'] = 'review'

        if policy.auto_create_partner and not self.partner_id:
            partner = self.env['res.partner'].search(
                [('email', '=ilike', self.sender_email)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': self.sender_name or self.sender_email,
                    'email': self.sender_email,
                })
            vals['partner_id'] = partner.id
            vals['match_type'] = 'exact'

        self.write(vals)

    # ── AI Classifier — Groq ────────────────────────────────────────

    _GROQ_VALID_CATEGORIES = {'commerciale', 'admin', 'fornitore', 'newsletter', 'interno', 'personale', 'spam'}
    _GROQ_VALID_SENTIMENTS = {'positive', 'neutral', 'negative'}
    _GROQ_VALID_LANGUAGES = {'it', 'en', 'de', 'fr', 'es', 'other'}
    _GROQ_VALID_URGENCIES = {'high', 'medium', 'low'}

    def _get_body_text_for_ai(self):
        """Estrae testo plain dal messaggio per il classifier AI (max 2000 char)."""
        self.ensure_one()
        text = ''
        if self.body_plain:
            text = self.body_plain
        elif self.body_html:
            text = re.sub(r'<[^>]+>', ' ', self.body_html)
            text = re.sub(r'\s+', ' ', text).strip()
        elif self.snippet:
            text = self.snippet
        return (text or '')[:2000]

    def _classify_with_groq(self):
        """Classifica questa email con Groq API. Non solleva mai eccezioni."""
        self.ensure_one()

        # Check abilitazione
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino_mail.ai_classifier_enabled', '0')
        if enabled != '1':
            return

        # Skip se già classificato
        if self.ai_classified_at:
            return

        # Estrai testo
        body_text = self._get_body_text_for_ai()
        if not body_text and not self.subject:
            self.write({'ai_error': 'No body content'})
            return

        # API key
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.groq_api_key', '')
        if not api_key:
            self.write({'ai_error': 'Groq API key not configured'})
            return

        system_prompt = (
            "You are an email classifier for CasaFolino, an Italian artisan gourmet food company "
            "(B2B export, GDO retail, private label). Classify each email with JSON output only, no prose."
        )
        user_prompt = (
            "Classify this email:\n"
            "Subject: %s\n"
            "Body (first 2000 chars): %s\n\n"
            "Return ONLY valid JSON in this exact format:\n"
            '{"category": "commerciale|admin|fornitore|newsletter|interno|personale|spam", '
            '"sentiment": "positive|neutral|negative", '
            '"language": "it|en|de|fr|es|other", '
            '"urgency": "high|medium|low", '
            '"action_required": true|false}\n\n'
            "Rules:\n"
            '- "commerciale" = buyer, distributor, retailer, customer requests, trade fairs\n'
            '- "admin" = invoices, bank, tax, legal, HR, logistics docs\n'
            '- "fornitore" = suppliers, raw materials, packaging, ingredients\n'
            '- "newsletter" = marketing, promotional, mass mailing\n'
            '- "interno" = internal @casafolino.com addresses\n'
            '- "personale" = personal matters\n'
            '- "spam" = unsolicited promotional, phishing\n'
            '- urgency="high" when: explicit deadlines <7 days, complaints, legal matters, payments overdue\n'
            '- action_required=true when recipient must reply or take action'
        ) % (self.subject or '(no subject)', body_text or '(empty)')

        headers = {
            'Authorization': 'Bearer %s' % api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (CasaFolino Mail V2)',
        }
        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': 0.1,
            'max_tokens': 200,
        }

        for attempt in range(2):
            try:
                resp = req.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=15,
                )

                if resp.status_code == 429 and attempt == 0:
                    _logger.warning("Groq rate limit (429) for message %s, retry in 20s...", self.id)
                    time.sleep(20)
                    continue

                if resp.status_code == 429:
                    self.write({'ai_error': 'Rate limit 429 dopo retry'})
                    _logger.warning("Groq rate limit (429) for message %s after retry, skip", self.id)
                    return

                if resp.status_code == 403 and attempt == 0:
                    _logger.warning("Groq 403 (Cloudflare?) for message %s, retry...", self.id)
                    time.sleep(1)
                    continue

                if resp.status_code != 200:
                    self.write({'ai_error': 'HTTP %s' % resp.status_code})
                    _logger.warning("Groq HTTP %s for message %s: %s",
                                    resp.status_code, self.id, resp.text[:300])
                    return

                # Parse risposta
                raw = resp.json()
                content = raw.get('choices', [{}])[0].get('message', {}).get('content', '')

                # Gestisci wrapper ```json ... ```
                content = content.strip()
                if content.startswith('```'):
                    content = re.sub(r'^```\w*\n?', '', content)
                    content = re.sub(r'\n?```$', '', content)
                    content = content.strip()

                data = json.loads(content)

                vals = {
                    'ai_classified_at': fields.Datetime.now(),
                    'ai_raw_response': content,
                    'ai_error': False,
                }

                cat = (data.get('category') or '').lower().strip()
                if cat in self._GROQ_VALID_CATEGORIES:
                    vals['ai_category'] = cat

                sent = (data.get('sentiment') or '').lower().strip()
                if sent in self._GROQ_VALID_SENTIMENTS:
                    vals['ai_sentiment'] = sent

                lang = (data.get('language') or '').lower().strip()
                if lang in self._GROQ_VALID_LANGUAGES:
                    vals['ai_language'] = lang

                urg = (data.get('urgency') or '').lower().strip()
                if urg in self._GROQ_VALID_URGENCIES:
                    vals['ai_urgency'] = urg

                if isinstance(data.get('action_required'), bool):
                    vals['ai_action_required'] = data['action_required']

                self.write(vals)
                return

            except json.JSONDecodeError as e:
                self.write({
                    'ai_error': 'JSON parse error: %s' % str(e)[:100],
                    'ai_raw_response': content if 'content' in dir() else '',
                    'ai_classified_at': fields.Datetime.now(),
                })
                return
            except req.exceptions.Timeout:
                self.write({'ai_error': 'Timeout 15s'})
                _logger.warning("Groq timeout for message %s", self.id)
                return
            except Exception as e:
                self.write({'ai_error': str(e)[:200]})
                _logger.error("Groq classify error for message %s: %s", self.id, e)
                return

        # Se arriviamo qui: 2 tentativi falliti (403 retry)
        self.write({'ai_error': 'Cloudflare 403 after retry'})

    def _compute_tracking_counts(self):
        for rec in self:
            events = self.env['casafolino.mail.tracking'].search([('message_id', '=', rec.id)])
            rec.tracking_open_count = len(events.filtered(lambda e: e.event_type in ('opened', 'forwarded')))
            rec.tracking_click_count = len(events.filtered(lambda e: e.event_type == 'clicked'))

    @staticmethod
    def _normalize_subject(subject):
        """Strip Re:/Fwd:/R:/FW:/AW:/SV:/VS:/Rif: prefixes recursively, lowercase, strip."""
        if not subject:
            return ''
        s = subject.strip()
        prefix_re = re.compile(r'^\s*(Re|R|Fwd|FW|Fw|AW|SV|VS|RE|Rif|RIF)\s*:\s*', re.IGNORECASE)
        prev = None
        while s != prev:
            prev = s
            s = prefix_re.sub('', s).strip()
        return s.lower()

    @api.depends('subject', 'account_id')
    def _compute_thread_key(self):
        for rec in self:
            norm = self._normalize_subject(rec.subject)
            aid = rec.account_id.id if rec.account_id else 0
            rec.thread_key = '%s::%s' % (norm, aid) if norm else ''

    # ── Quick Convert → CRM Lead ────────────────────────────────────

    def action_create_lead(self):
        """Crea un crm.lead pre-compilato da questa email."""
        self.ensure_one()

        # Assicura partner
        partner = self.partner_id
        if not partner and self.sender_email:
            partner = self.env['res.partner'].search(
                [('email', '=ilike', self.sender_email)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': self.sender_name or self.sender_email,
                    'email': self.sender_email,
                })
                self.partner_id = partner

        # Determina salesperson dalla policy o utente corrente
        user_id = self.env.user.id
        if self.policy_applied_id and self.policy_applied_id.default_owner_id:
            user_id = self.policy_applied_id.default_owner_id.id

        lead_vals = {
            'name': self.subject or 'Email da %s' % self.sender_email,
            'partner_id': partner.id if partner else False,
            'email_from': self.sender_email,
            'description': (self.body_html or self.snippet or '')[:3000],
            'user_id': user_id,
            'source_email_id': self.id,
        }

        # UTM source "Email" se esiste
        try:
            lead_vals['source_id'] = self.env.ref('utm.utm_source_email').id
        except Exception:
            pass

        lead = self.env['crm.lead'].create(lead_vals)
        self.write({'lead_id': lead.id, 'state': 'keep'})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead creato',
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Triage actions (Step 3) ──────────────────────────────────────

    def action_keep(self):
        """Marca come keep (non-bloccante). Il body viene scaricato dal cron."""
        now = fields.Datetime.now()
        uid = self.env.user.id

        # Marca tutti i record selezionati come keep + pending fetch
        for record in self:
            vals = {
                'state': 'keep',
                'triage_user_id': uid,
                'triage_date': now,
            }
            if not record.body_downloaded:
                vals['fetch_state'] = 'pending'
            else:
                vals['fetch_state'] = 'done'
            record.write(vals)

            # Se ha un partner, attiva tracking
            if record.partner_id and not record.partner_id.mail_tracked:
                record.partner_id.sudo().mail_tracked = True

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
                sender_partner = {}
                for record in self:
                    if record.sender_email and record.partner_id:
                        sender_partner[record.sender_email.lower().strip()] = record.partner_id.id
                for sib in siblings:
                    sib_vals = {
                        'state': 'keep',
                        'triage_user_id': uid,
                        'triage_date': now,
                    }
                    if not sib.body_downloaded:
                        sib_vals['fetch_state'] = 'pending'
                    else:
                        sib_vals['fetch_state'] = 'done'
                    pid = sender_partner.get((sib.sender_email or '').lower().strip())
                    if pid and not sib.partner_id:
                        sib_vals['partner_id'] = pid
                        sib_vals['match_type'] = 'exact'
                    sib.write(sib_vals)

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
            'fetch_state': 'done',
            'fetch_error_msg': False,
        })

        # Crea allegati (resiliente a errori PIL/corrupted files)
        for att in attachments:
            try:
                self.env['ir.attachment'].create({
                    'name': att['name'],
                    'datas': att['datas'],
                    'mimetype': att['mimetype'],
                    'res_model': 'casafolino.mail.message',
                    'res_id': self.id,
                })
            except Exception as e:
                _logger.warning(
                    "Allegato corrotto skippato per %s: %s — %s",
                    self.message_id_rfc, att.get('name', '?'), e
                )

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

    # ── Domain discard + Quick actions ────────────────────────────

    def action_blacklist_domain(self):
        """Crea sender_policy auto_discard per il dominio e scarta le email new."""
        Policy = self.env['casafolino.mail.sender_policy'].sudo()
        domains_done = set()

        for record in self:
            domain = record.sender_domain
            if domain and domain not in domains_done:
                existing = Policy.search([
                    ('pattern_type', '=', 'domain'),
                    ('pattern_value', '=', domain),
                    ('action', '=', 'auto_discard'),
                ], limit=1)
                if not existing:
                    Policy.create({
                        'name': 'Auto-discard: %s' % domain,
                        'pattern_type': 'domain',
                        'pattern_value': domain,
                        'action': 'auto_discard',
                        'priority': 70,
                    })
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

        partner = self.env['res.partner'].sudo().create(vals)
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

    def action_open_snippet_picker(self):
        """Apre wizard selezione snippet per questa email."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Seleziona Snippet',
            'res_model': 'casafolino.mail.snippet.picker',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

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
        Partner = self.env['res.partner'].sudo()
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

    # ── Cron AI classify pending ────────────────────────────────────

    @api.model
    def _cron_ai_classify_pending(self):
        """Classifica messaggi non ancora processati dall'AI. Max 25 per run, 2.5s tra chiamate."""
        pending = self.search([
            ('ai_classified_at', '=', False),
            '|', ('ai_error', '=', False), ('ai_error', '=', ''),
        ], limit=25, order='email_date desc')

        if not pending:
            return

        _logger.info("AI classify cron: %d messaggi da classificare", len(pending))
        classified = 0
        for idx, msg in enumerate(pending):
            try:
                msg._classify_with_groq()
                if msg.ai_classified_at:
                    classified += 1
                    # Re-apply policy solo se il messaggio è ancora in state='new'
                    if msg.state == 'new':
                        msg._apply_sender_policy()
            except Exception as e:
                _logger.warning("AI classify cron error msg %s: %s", msg.id, e)
            self.env.cr.commit()
            # Rate limit: ~24 req/min (well under Groq free tier 30 req/min)
            if idx < len(pending) - 1:
                time.sleep(2.5)

        _logger.info("AI classify cron completato: %d/%d classificati", classified, len(pending))

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

    @api.model
    def _cron_fetch_pending_bodies(self):
        """Cron: scarica body per messaggi keep con fetch_state=pending. Max 50 per run."""
        pending = self.search([
            ('state', '=', 'keep'),
            ('fetch_state', '=', 'pending'),
            ('body_downloaded', '=', False),
        ], limit=50, order='triage_date asc')

        if not pending:
            return

        _logger.info("Cron fetch bodies: %d messaggi in coda", len(pending))

        # Raggruppa per account per riutilizzare la connessione IMAP
        by_account = {}
        for msg in pending:
            aid = msg.account_id.id
            if aid not in by_account:
                by_account[aid] = []
            by_account[aid].append(msg)

        for account_id, msgs in by_account.items():
            account = self.env['casafolino.mail.account'].browse(account_id)
            imap = None
            try:
                imap = account._get_imap_connection()
            except Exception as e:
                _logger.error("Cron fetch: connessione IMAP fallita per %s: %s", account.email_address, e)
                for msg in msgs:
                    msg.write({
                        'fetch_state': 'error',
                        'fetch_error_msg': 'Connessione IMAP fallita: %s' % str(e)[:200],
                    })
                continue

            for msg in msgs:
                try:
                    msg._download_body_imap(imap, msg.imap_folder, msg.imap_uid)
                    # _download_body_imap sets fetch_state='done' on success
                except Exception as e:
                    _logger.warning("Cron fetch body error %s: %s", msg.message_id_rfc, e)
                    msg.write({
                        'fetch_state': 'error',
                        'fetch_error_msg': str(e)[:500],
                    })
                # Commit dopo ogni messaggio per non perdere progresso
                self.env.cr.commit()

            try:
                imap.logout()
            except Exception:
                pass

        _logger.info("Cron fetch bodies completato: %d messaggi processati", len(pending))

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
            'tracking_open_count': m.tracking_open_count,
            'tracking_click_count': m.tracking_click_count,
            'has_tracking': bool(m.tracking_token),
        }

    @api.model
    def get_messages(self, *args, **kw):
        """API per il client OWL — ritorna email kept."""
        account_id = kw.get('account_id')
        folder = kw.get('folder') or 'INBOX'
        limit = int(kw.get('limit') or 50)
        offset = int(kw.get('offset') or 0)
        search = kw.get('search') or ''

        domain = [('state', '=', 'keep')]

        # Account filter: SEMPRE applicato tranne quando esplicitamente 'all'
        if account_id and str(account_id) != 'all':
            domain.append(('account_id', '=', int(account_id)))
            # Ownership check per non-admin
            if not self.env.user.has_group('base.group_system'):
                acc = self.env['casafolino.mail.account'].browse(int(account_id))
                if not acc.exists() or acc.responsible_user_id.id != self.env.uid:
                    return []
        elif str(account_id) == 'all':
            # "Tutti": filtra per account dell'utente
            user_accounts = self.env['casafolino.mail.account'].search([
                ('active', '=', True), ('responsible_user_id', '=', self.env.uid)])
            domain.append(('account_id', 'in', user_accounts.ids))
        else:
            # account_id mancante/falsy: filtra per account dell'utente (mai mostrare tutto)
            user_accounts = self.env['casafolino.mail.account'].search([
                ('active', '=', True), ('responsible_user_id', '=', self.env.uid)])
            domain.append(('account_id', 'in', user_accounts.ids))

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
    def get_threaded_messages(self, *args, **kw):
        """Return messages grouped by thread_key for the mail hub list view."""
        account_id = kw.get('account_id')
        folder = kw.get('folder') or 'INBOX'
        search = kw.get('search') or ''
        thread_limit = int(kw.get('thread_limit') or 50)
        thread_offset = int(kw.get('thread_offset') or 0)
        hide_internal = kw.get('hide_internal') or False

        domain = [('state', '=', 'keep')]

        # Account filter: SEMPRE applicato tranne quando esplicitamente 'all'
        if account_id and str(account_id) != 'all':
            domain.append(('account_id', '=', int(account_id)))
            # Ownership check per non-admin
            if not self.env.user.has_group('base.group_system'):
                acc = self.env['casafolino.mail.account'].browse(int(account_id))
                if not acc.exists() or acc.responsible_user_id.id != self.env.uid:
                    return {'threads': [], 'has_more': False, 'total': 0}
        else:
            # 'all' o falsy: filtra per account dell'utente (mai mostrare tutto senza filtro)
            user_accounts = self.env['casafolino.mail.account'].search([
                ('active', '=', True), ('responsible_user_id', '=', self.env.uid)])
            domain.append(('account_id', 'in', user_accounts.ids))

        if folder == 'Sent':
            domain.append(('direction', '=', 'outbound'))
        elif folder == 'Starred':
            domain.append(('is_important', '=', True))
        elif folder == 'INBOX':
            domain.append(('direction', '=', 'inbound'))

        if hide_internal:
            domain.append(('sender_email', 'not ilike', '%@casafolino.com'))

        if search:
            domain += ['|', '|', '|',
                ('subject', 'ilike', search),
                ('sender_email', 'ilike', search),
                ('sender_name', 'ilike', search),
                ('recipient_emails', 'ilike', search),
            ]

        # Fetch enough messages to fill threads
        fetch_limit = (thread_limit + thread_offset) * 8
        msgs = self.search(domain, limit=fetch_limit, order='email_date desc, id desc')

        # Group by thread_key
        thread_map = {}
        thread_order = []
        for m in msgs:
            key = m.thread_key or ('__single_%s' % m.id)
            if key not in thread_map:
                thread_map[key] = []
                thread_order.append(key)
            thread_map[key].append(m)

        # Build thread summaries
        threads = []
        for key in thread_order:
            group = thread_map[key]
            group_sorted = sorted(group, key=lambda m: (m.email_date or fields.Datetime.now(), m.id))
            latest = group_sorted[-1]
            unread_count = sum(1 for m in group if not m.is_read)
            is_starred = any(m.is_important for m in group)
            has_attachments = any(bool(m.attachment_ids) for m in group)

            # Lead info
            lead_name = ''
            lead_id = False
            for m in group:
                if m.lead_id:
                    lead_id = m.lead_id.id
                    lead_name = m.lead_id.name
                    break

            # Assigned user
            assigned_user_name = ''
            assigned_user_id = False
            for m in reversed(group_sorted):
                if m.assigned_user_ids:
                    assigned_user_id = m.assigned_user_ids[0].id
                    assigned_user_name = m.assigned_user_ids[0].name
                    break

            # Child messages
            child_msgs = []
            for m in group_sorted:
                child_msgs.append({
                    'id': m.id,
                    'from_name': m.sender_name or m.sender_email or '',
                    'from_address': m.sender_email or '',
                    'date': m.email_date.strftime('%d/%m/%Y %H:%M') if m.email_date else '',
                    'date_short': m.email_date.strftime('%d %b') if m.email_date else '',
                    'is_read': m.is_read,
                    'is_starred': m.is_important,
                    'snippet': m.snippet or '',
                    'direction': 'in' if m.direction == 'inbound' else 'out',
                    'subject': m.subject or '(nessun oggetto)',
                    'has_attachments': bool(m.attachment_ids),
                })

            threads.append({
                'thread_key': key,
                'subject': latest.subject or '(nessun oggetto)',
                'message_count': len(group),
                'unread_count': unread_count,
                'is_starred': is_starred,
                'has_attachments': has_attachments,
                'last_date': latest.email_date.strftime('%d/%m/%Y %H:%M') if latest.email_date else '',
                'last_date_short': latest.email_date.strftime('%d %b') if latest.email_date else '',
                'last_sender_name': latest.sender_name or latest.sender_email or '',
                'last_sender_address': latest.sender_email or '',
                'last_snippet': latest.snippet or '',
                'last_direction': 'in' if latest.direction == 'inbound' else 'out',
                'last_msg_id': latest.id,
                'tags': [],
                'lead_id': lead_id,
                'lead_name': lead_name,
                'assigned_user_id': assigned_user_id,
                'assigned_user_name': assigned_user_name,
                'sender_action': False,
                'messages': child_msgs,
            })

        # Paginate
        total_threads = len(threads)
        paginated = threads[thread_offset:thread_offset + thread_limit]
        has_more = (thread_offset + thread_limit) < total_threads

        return {
            'threads': paginated,
            'has_more': has_more,
            'total': total_threads,
        }

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

        # Scarica body on-demand se non ancora fatto (non bloccante per il cron)
        if not msg.body_downloaded:
            try:
                imap = msg.account_id._get_imap_connection()
                msg._download_body_imap(imap, msg.imap_folder, msg.imap_uid)
                imap.logout()
            except Exception as e:
                _logger.error("Error downloading body for detail %s: %s", msg.message_id_rfc, e)
                msg.write({
                    'fetch_state': 'error',
                    'fetch_error_msg': str(e)[:500],
                })

        result = self._msg_to_dict(msg)
        result['body_html'] = msg.body_html or ''
        result['to_address'] = msg.recipient_emails or ''
        result['cc_address'] = msg.cc_emails or ''

        # Allegati
        result['attachments'] = []
        for att in msg.attachment_ids:
            result['attachments'].append({
                'id': att.id,
                'name': att.name,
                'mimetype': att.mimetype or '',
                'size': att.file_size or 0,
            })

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

        # Tracking events
        result['tracking_events'] = []
        if msg.tracking_token:
            events = self.env['casafolino.mail.tracking'].search(
                [('message_id', '=', msg.id)], order='event_date desc')
            for ev in events:
                result['tracking_events'].append({
                    'event_type': ev.event_type,
                    'event_date': ev.event_date.strftime('%d/%m/%Y %H:%M') if ev.event_date else '',
                    'country': ev.country or '',
                    'city': ev.city or '',
                    'url_clicked': ev.url_clicked or '',
                    'attachment_name': ev.attachment_name or '',
                    'ip_address': ev.ip_address or '',
                })

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

    # ── RPC methods called by OWL client ─────────────────────────────

    @api.model
    def rpc_keep_sender(self, *args, **kw):
        """Tieni mittente: marca tutte le email new dallo stesso sender come keep."""
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return {'success': False}
        msg = self.browse(int(message_id))
        if not msg.exists() or not msg.sender_email:
            return {'success': False}
        addr = msg.sender_email.strip().lower()
        # Keep all new emails from this sender on this account
        siblings = self.search([
            ('sender_email', '=ilike', addr),
            ('state', '=', 'new'),
            ('account_id', '=', msg.account_id.id),
        ])
        if siblings:
            siblings.action_keep()
        return {'success': True, 'action': 'keep', 'email': addr}

    @api.model
    def rpc_exclude_sender(self, *args, **kw):
        """Escludi mittente: aggiungi a blacklist email e scarta tutte le sue email."""
        message_id = kw.get('message_id') or (args[1] if len(args) > 1 else None)
        if not message_id:
            return {'success': False}
        msg = self.browse(int(message_id))
        if not msg.exists() or not msg.sender_email:
            return {'success': False}
        addr = msg.sender_email.strip().lower()
        # Crea sender_policy auto_discard per questa email
        Policy = self.env['casafolino.mail.sender_policy'].sudo()
        existing = Policy.search([
            ('pattern_type', '=', 'email_exact'),
            ('pattern_value', '=', addr),
        ], limit=1)
        if not existing:
            Policy.create({
                'name': 'Block: %s' % addr,
                'pattern_type': 'email_exact',
                'pattern_value': addr,
                'action': 'auto_discard',
                'priority': 90,
            })
        # Discard ALL emails from this sender (new + keep)
        to_discard = self.search([
            ('sender_email', '=ilike', addr),
            ('state', 'in', ['new', 'keep']),
        ])
        if to_discard:
            to_discard.action_discard()
        return {'success': True, 'action': 'exclude', 'email': addr}

    @api.model
    def rpc_search_partners(self, *args, **kw):
        """Cerca partner per il pannello arricchimento."""
        query = kw.get('query') or ''
        if not query or len(query) < 2:
            return []
        partners = self.env['res.partner'].search(
            [('name', 'ilike', query)], limit=10, order='name')
        return [{'id': p.id, 'name': p.name, 'email': p.email or ''} for p in partners]

    @api.model
    def rpc_save_enrichment(self, *args, **kw):
        """Salva nota arricchimento sul messaggio."""
        message_id = kw.get('message_id')
        partner_id = kw.get('partner_id')
        note = kw.get('note') or ''
        if not message_id:
            return {'success': False}
        msg = self.browse(int(message_id))
        if not msg.exists():
            return {'success': False}
        vals = {}
        if partner_id:
            vals['partner_id'] = int(partner_id)
            vals['match_type'] = 'manual'
        msg.write(vals)
        return {'success': True}

    @api.model
    def advanced_search(self, *args, **kw):
        """Ricerca avanzata email."""
        query = kw.get('query') or ''
        domain = [('state', '=', 'keep')]
        if query:
            domain += ['|', '|', '|',
                ('subject', 'ilike', query),
                ('sender_email', 'ilike', query),
                ('sender_name', 'ilike', query),
                ('recipient_emails', 'ilike', query)]
        date_from = kw.get('date_from')
        date_to = kw.get('date_to')
        if date_from:
            domain.append(('email_date', '>=', date_from))
        if date_to:
            domain.append(('email_date', '<=', date_to + ' 23:59:59'))
        account_id = kw.get('account_id')
        if account_id and str(account_id) != 'all':
            domain.append(('account_id', '=', int(account_id)))
        else:
            # 'all' o mancante: filtra per account dell'utente
            user_accounts = self.env['casafolino.mail.account'].search([
                ('active', '=', True), ('responsible_user_id', '=', self.env.uid)])
            domain.append(('account_id', 'in', user_accounts.ids))
        msgs = self.search(domain, limit=100, order='email_date desc')
        return [self._msg_to_dict(m) for m in msgs]

    @api.model
    def create_tag(self, *args, **kw):
        return False

    @api.model
    def do_add_tag(self, *args, **kw):
        return []

    @api.model
    def do_remove_tag(self, *args, **kw):
        return []

    @api.model
    def do_assign(self, *args, **kw):
        """Assegna email a un utente."""
        message_id = kw.get('message_id')
        user_id = kw.get('user_id')
        if not message_id:
            return ''
        msg = self.browse(int(message_id))
        if msg.exists() and user_id:
            msg.sudo().write({'assigned_user_ids': [(4, int(user_id))]})
            user = self.env['res.users'].browse(int(user_id))
            return user.name if user.exists() else ''
        elif msg.exists():
            msg.sudo().write({'assigned_user_ids': [(5,)]})
        return ''

    @api.model
    def do_link_lead(self, *args, **kw):
        """Collega email a un lead."""
        message_id = kw.get('message_id')
        lead_id = kw.get('lead_id')
        if not message_id:
            return False
        msg = self.browse(int(message_id))
        if msg.exists():
            msg.write({'lead_id': int(lead_id) if lead_id else False})
        return True

    @api.model
    def do_snooze(self, *args, **kw):
        return True

    @api.model
    def save_draft(self, *args, **kw):
        return {'success': True}

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
        elif action == 'keep_for_all':
            return self.action_keep_for_all(message_ids=ids)
        return True

    @api.model
    def do_toggle_star(self, *args, **kw):
        message_id = kw.get('message_id')
        if not message_id:
            return False
        msg = self.browse(int(message_id))
        msg.write({'is_important': not msg.is_important})
        return msg.is_important

    @api.model
    def action_keep_for_all(self, *args, **kw):
        """Tieni email per tutti gli account — accesso cross-account con sudo."""
        message_ids = kw.get('message_ids') or []
        if not message_ids:
            return {'success': False, 'error': 'Nessuna email selezionata'}

        messages = self.browse(message_ids)
        sender_emails = set()
        for msg in messages:
            if msg.sender_email:
                sender_emails.add(msg.sender_email.lower().strip())

        if not sender_emails:
            return {'success': False, 'error': 'Nessun mittente trovato'}

        # Usa sudo per accedere a email di tutti gli account
        SudoMsg = self.sudo()
        Partner = self.env['res.partner'].sudo()

        total_kept = 0
        for sender in sender_emails:
            # Trova o crea partner per questo mittente
            partner = Partner.search([('email', '=ilike', sender)], limit=1)

            # Trova tutte le email new di questo mittente su TUTTI gli account
            all_new = SudoMsg.search([
                ('sender_email', '=ilike', sender),
                ('state', '=', 'new'),
            ])

            if not partner and all_new:
                # Crea partner una sola volta
                first = all_new[0]
                partner = Partner.create({
                    'name': first.sender_name or sender,
                    'email': sender,
                })

            for record in all_new:
                record.write({
                    'state': 'keep',
                    'triage_user_id': self.env.uid,
                    'triage_date': fields.Datetime.now(),
                    'partner_id': partner.id if partner else False,
                    'match_type': 'exact' if partner else 'none',
                })
                if not record.body_downloaded:
                    try:
                        imap = record.account_id._get_imap_connection()
                        record._download_body_imap(imap, record.imap_folder, record.imap_uid)
                        imap.logout()
                    except Exception as e:
                        _logger.error("keep_for_all body error %s: %s", record.message_id_rfc, e)
                if partner and not partner.mail_tracked:
                    partner.mail_tracked = True
                total_kept += 1

        return {'success': True, 'count': total_kept, 'senders': list(sender_emails)}

    # ── Lead Email Widget API ────────────────────────────────────────

    @api.model
    def get_lead_emails(self, *args, **kw):
        """Ritorna email collegate a un lead per il widget embedded."""
        lead_id = kw.get('lead_id')
        if not lead_id:
            return []
        msgs = self.search([('lead_id', '=', int(lead_id))], order='email_date desc')
        return [self._msg_to_dict(m) for m in msgs]

    @staticmethod
    def _compress_image(content, filename):
        """Comprimi immagine se > 500KB. Ritorna (content_bytes, filename, mimetype)."""
        import io
        if len(content) <= 512000:
            return content, filename, None
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            # Converti RGBA/palette in RGB per JPEG
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            # Ridimensiona se troppo grande
            if max(img.size) > 1920:
                img.thumbnail((1920, 1920), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=75, optimize=True)
            compressed = buf.getvalue()
            new_name = filename.rsplit('.', 1)[0] + '.jpg' if '.' in filename else filename + '.jpg'
            _logger.info("Image compressed: %s %dKB -> %dKB",
                         filename, len(content) // 1024, len(compressed) // 1024)
            return compressed, new_name, 'image/jpeg'
        except Exception as e:
            _logger.warning("Image compression failed for %s: %s", filename, e)
            return content, filename, None

    @staticmethod
    def _inject_tracking(body_html, token, base_url):
        """Inject tracking pixel and rewrite links in HTML body."""
        from urllib.parse import quote
        if not body_html or not token:
            return body_html

        # 1. Rewrite links (but not mailto: or internal erp links)
        import re
        def rewrite_link(match):
            url = match.group(1)
            if url.startswith('mailto:') or 'erp.casafolino.com' in url:
                return match.group(0)
            tracked = '%s/cf/track/click/%s?url=%s' % (base_url, token, quote(url, safe=''))
            return 'href="%s"' % tracked

        tracked_body = re.sub(r'href="([^"]+)"', rewrite_link, body_html)

        # 2. Append tracking pixel
        pixel = '<img src="%s/cf/track/open/%s" width="1" height="1" style="display:none" />' % (base_url, token)
        if '</body>' in tracked_body:
            tracked_body = tracked_body.replace('</body>', pixel + '</body>')
        else:
            tracked_body = tracked_body + pixel

        return tracked_body

    @api.model
    def _build_and_send_email(self, account, to_address, cc_address, subject, body,
                               reply_to_id=False, attachments=None, attachment_ids=None):
        """Helper: costruisce email MIME con allegati e invia via SMTP."""
        import smtplib
        import ssl as ssl_lib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders as email_encoders

        _IMAGE_MIMES = {'image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff'}

        msg_obj = MIMEMultipart('mixed')
        generated_msg_id = '<%s@casafolino.com>' % uuid.uuid4()
        tracking_token = str(uuid.uuid4())
        msg_obj['Message-ID'] = generated_msg_id
        msg_obj['Subject'] = subject
        msg_obj['From'] = '%s <%s>' % (account.name or account.email_address, account.email_address)
        msg_obj['To'] = to_address
        if cc_address:
            msg_obj['Cc'] = cc_address

        if reply_to_id:
            orig = self.browse(int(reply_to_id))
            if orig.exists() and orig.message_id_rfc:
                msg_obj['In-Reply-To'] = orig.message_id_rfc
                msg_obj['References'] = orig.message_id_rfc

        # Inject tracking pixel + rewrite links
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'http://erp.casafolino.com:4589')
        # Ensure external URL (not localhost)
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            base_url = 'http://erp.casafolino.com:4589'
        tracked_body = self._inject_tracking(body, tracking_token, base_url)
        msg_obj.attach(MIMEText(tracked_body, 'html', 'utf-8'))

        # Allegati dal PC (base64)
        att_records = []
        for att in (attachments or []):
            fname = att.get('filename', 'file')
            content = base64.b64decode(att.get('content_base64', ''))
            mimetype = att.get('mimetype', 'application/octet-stream')

            # Comprimi immagini > 500KB
            if mimetype in _IMAGE_MIMES and len(content) > 512000:
                content, fname, new_mime = self._compress_image(content, fname)
                if new_mime:
                    mimetype = new_mime

            maintype, subtype = mimetype.split('/', 1) if '/' in mimetype else ('application', 'octet-stream')
            part = MIMEBase(maintype, subtype)
            part.set_payload(content)
            email_encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=fname)
            msg_obj.attach(part)
            att_records.append(self.env['ir.attachment'].create({
                'name': fname,
                'datas': base64.b64encode(content),
                'mimetype': mimetype,
            }))

        # Allegati da Odoo (ids) — comprimi immagini se necessario
        for att_id in (attachment_ids or []):
            ir_att = self.env['ir.attachment'].browse(int(att_id))
            if ir_att.exists() and ir_att.datas:
                content = base64.b64decode(ir_att.datas)
                mimetype = ir_att.mimetype or 'application/octet-stream'
                fname = ir_att.name

                if mimetype in _IMAGE_MIMES and len(content) > 512000:
                    content, fname, new_mime = self._compress_image(content, fname)
                    if new_mime:
                        mimetype = new_mime

                maintype, subtype = mimetype.split('/', 1) if '/' in mimetype else ('application', 'octet-stream')
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                email_encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=fname)
                msg_obj.attach(part)
                att_records.append(ir_att)

        recipients = [r.strip() for r in to_address.split(',') if r.strip()]
        if cc_address:
            recipients += [r.strip() for r in cc_address.split(',') if r.strip()]

        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        server.ehlo()
        server.starttls(context=ssl_lib.create_default_context())
        server.ehlo()
        server.login(account.email_address, account.imap_password)
        server.sendmail(account.email_address, recipients, msg_obj.as_string())
        server.quit()

        return msg_obj, att_records, tracking_token, tracked_body

    @api.model
    def send_reply(self, *args, **kw):
        """Invia email dal client principale."""
        to_address = kw.get('to_address') or ''
        cc_address = kw.get('cc_address') or ''
        bcc_address = kw.get('bcc_address') or ''
        subject = kw.get('subject') or ''
        body = kw.get('body') or ''
        account_id = kw.get('account_id') or None
        message_id = kw.get('message_id') or False
        attachments = kw.get('attachments') or []
        attachment_ids = kw.get('attachment_ids') or []

        if not to_address or not body:
            return {'success': False, 'error': 'Destinatario o corpo mancante'}

        account = None
        if account_id:
            account = self.env['casafolino.mail.account'].browse(int(account_id))
        if not account or not account.exists():
            account = self.env['casafolino.mail.account'].search([
                ('responsible_user_id', '=', self.env.uid),
                ('state', '=', 'connected'),
            ], limit=1)
        if not account:
            return {'success': False, 'error': 'Nessun account configurato'}
        if not account.imap_password:
            return {'success': False, 'error': 'Password SMTP non configurata'}

        try:
            msg_obj, att_records, tracking_token, tracked_body = self._build_and_send_email(
                account, to_address, cc_address, subject, body,
                reply_to_id=message_id, attachments=attachments,
                attachment_ids=attachment_ids)

            # Eredita lead_id dall'email originale
            inherited_lead_id = False
            if message_id:
                orig = self.browse(int(message_id))
                if orig.exists() and orig.lead_id:
                    inherited_lead_id = orig.lead_id.id

            sent_msg = self.create({
                'account_id': account.id,
                'message_id_rfc': msg_obj.get('Message-ID', ''),
                'tracking_token': tracking_token,
                'direction': 'outbound',
                'sender_email': account.email_address,
                'sender_name': account.name or '',
                'recipient_emails': to_address,
                'cc_emails': cc_address,
                'subject': subject,
                'email_date': fields.Datetime.now(),
                'body_html': tracked_body,
                'body_downloaded': True,
                'state': 'keep',
                'is_read': True,
                'lead_id': inherited_lead_id,
                'triage_user_id': self.env.user.id,
                'triage_date': fields.Datetime.now(),
            })
            for att_rec in att_records:
                att_rec.write({'res_model': 'casafolino.mail.message', 'res_id': sent_msg.id})

            # Create initial tracking event
            self.env['casafolino.mail.tracking'].sudo().create({
                'message_id': sent_msg.id,
                'tracking_token': tracking_token,
                'event_type': 'sent',
                'account_id': account.id,
                'partner_id': sent_msg.partner_id.id if sent_msg.partner_id else False,
            })

            return {'success': True}
        except Exception as e:
            _logger.error("send_reply error: %s", e)
            return {'success': False, 'error': str(e)[:200]}

    @api.model
    def send_from_lead(self, *args, **kw):
        """Invia email da una trattativa CRM e collegala al lead."""
        lead_id = kw.get('lead_id')
        to_address = kw.get('to_address') or ''
        cc_address = kw.get('cc_address') or ''
        subject = kw.get('subject') or ''
        body = kw.get('body') or ''
        reply_to_id = kw.get('reply_to_id') or False
        attachments = kw.get('attachments') or []
        attachment_ids = kw.get('attachment_ids') or []

        if not to_address or not body:
            return {'success': False, 'error': 'Destinatario e corpo obbligatori'}

        account = self.env['casafolino.mail.account'].search([
            ('responsible_user_id', '=', self.env.uid),
            ('state', '=', 'connected'),
        ], limit=1)
        if not account:
            return {'success': False, 'error': 'Nessun account email configurato'}
        if not account.imap_password:
            return {'success': False, 'error': 'Password SMTP non configurata'}

        try:
            msg_obj, att_records, tracking_token, tracked_body = self._build_and_send_email(
                account, to_address, cc_address, subject, body,
                reply_to_id=reply_to_id, attachments=attachments,
                attachment_ids=attachment_ids)

            sent_msg = self.create({
                'account_id': account.id,
                'message_id_rfc': msg_obj.get('Message-ID', ''),
                'tracking_token': tracking_token,
                'direction': 'outbound',
                'sender_email': account.email_address,
                'sender_name': account.name or '',
                'recipient_emails': to_address,
                'cc_emails': cc_address,
                'subject': subject,
                'email_date': fields.Datetime.now(),
                'body_html': tracked_body,
                'body_downloaded': True,
                'state': 'keep',
                'is_read': True,
                'lead_id': int(lead_id) if lead_id else False,
                'triage_user_id': self.env.user.id,
                'triage_date': fields.Datetime.now(),
            })

            # Collega allegati al record
            for att_rec in att_records:
                att_rec.write({
                    'res_model': 'casafolino.mail.message',
                    'res_id': sent_msg.id,
                })

            # Create initial tracking event
            self.env['casafolino.mail.tracking'].sudo().create({
                'message_id': sent_msg.id,
                'tracking_token': tracking_token,
                'event_type': 'sent',
                'account_id': account.id,
                'partner_id': sent_msg.partner_id.id if sent_msg.partner_id else False,
                'lead_id': int(lead_id) if lead_id else False,
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

    # ── Attachment + Template API ────────────────────────────────────

    @api.model
    def get_odoo_attachments(self, *args, **kw):
        """Cerca allegati: da modulo documents se installato, altrimenti da ir.attachment."""
        search_term = kw.get('search') or ''
        limit = int(kw.get('limit') or 30)

        # Check se modulo documents è installato
        docs_installed = bool(self.env['ir.module.module'].search([
            ('name', '=', 'documents'), ('state', '=', 'installed')
        ], limit=1))

        if docs_installed:
            try:
                domain = []
                if search_term:
                    domain.append(('name', 'ilike', search_term))
                docs = self.env['documents.document'].search(
                    domain, limit=limit, order='create_date desc')
                result = []
                for d in docs:
                    att_id = d.attachment_id.id if d.attachment_id else False
                    result.append({
                        'id': att_id,
                        'doc_id': d.id,
                        'name': d.name or '',
                        'mimetype': d.mimetype or '',
                        'size': d.attachment_id.file_size if d.attachment_id else 0,
                        'folder': d.folder_id.name if hasattr(d, 'folder_id') and d.folder_id else '',
                        'source': 'documents',
                    })
                return result
            except Exception as e:
                _logger.warning("documents module error, falling back to ir.attachment: %s", e)

        # Fallback: ir.attachment
        domain = [
            ('res_model', 'in', [False, '', 'res.partner', 'crm.lead',
                                  'product.template', 'casafolino.mail.message',
                                  ]),
            ('type', '=', 'binary'),
        ]
        if search_term:
            domain.append(('name', 'ilike', search_term))
        atts = self.env['ir.attachment'].search(domain, limit=limit, order='create_date desc')
        return [{
            'id': a.id,
            'name': a.name,
            'mimetype': a.mimetype or '',
            'size': a.file_size or 0,
            'folder': '',
            'source': 'attachment',
        } for a in atts]

    @api.model
    def attach_from_url(self, *args, **kw):
        """Scarica file da URL e crea ir.attachment."""
        import requests as req
        url = kw.get('url') or ''
        filename = kw.get('filename') or 'attachment'
        if not url:
            return {'success': False, 'error': 'URL mancante'}
        try:
            resp = req.get(url, timeout=30, allow_redirects=True)
            if resp.ok:
                att = self.env['ir.attachment'].create({
                    'name': filename,
                    'datas': base64.b64encode(resp.content),
                    'mimetype': resp.headers.get('Content-Type', 'application/octet-stream'),
                })
                return {'success': True, 'id': att.id, 'name': att.name,
                        'size': len(resp.content), 'mimetype': att.mimetype}
            else:
                # Salva come link
                att = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'url',
                    'url': url,
                })
                return {'success': True, 'id': att.id, 'name': att.name,
                        'size': 0, 'mimetype': 'url'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:200]}

    @api.model
    def get_templates(self, *args, **kw):
        """Templates non più disponibili (vecchio stack rimosso)."""
        return []
