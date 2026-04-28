import json
import logging
import re
import time
from datetime import timedelta

import requests as req

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Blacklist patterns for auto-discard
_NOREPLY_PREFIXES = {'noreply@', 'no-reply@', 'mailer-daemon@', 'postmaster@'}
_DOMAIN_BLACKLIST_RE = re.compile(r'@(notifications\.|newsletters\.)', re.IGNORECASE)
_SUBJECT_DISCARD_RE = re.compile(
    r'\b(unsubscribe|disiscriviti|click.*disiscri)\b', re.IGNORECASE
)


class CasafolinoMailRaw(models.Model):
    _name = 'casafolino.mail.raw'
    _description = 'Email RAW — Pre-triage staging'
    _order = 'fetched_at desc, id desc'

    account_id = fields.Many2one(
        'casafolino.mail.account', string='Account',
        required=True, ondelete='cascade', index=True)
    uid = fields.Char('UID IMAP', required=True)
    message_id = fields.Char('Message-ID RFC', required=True, index=True)
    subject = fields.Char('Oggetto')
    sender_email = fields.Char('Email mittente', index=True)
    sender_name = fields.Char('Nome mittente')
    recipient_emails = fields.Text('Destinatari (CSV)')
    cc_emails = fields.Text('CC (CSV)')
    email_date = fields.Datetime('Data email')
    fetched_at = fields.Datetime('Fetched at', default=fields.Datetime.now, index=True)
    body_preview = fields.Text('Anteprima body (500 char)')
    has_attachments = fields.Boolean('Ha allegati', default=False)
    headers_raw = fields.Text('Header IMAP completi')
    imap_folder = fields.Char('Cartella IMAP')
    direction = fields.Selection([
        ('inbound', 'Ricevuta'),
        ('outbound', 'Inviata'),
    ], string='Direzione')

    triage_state = fields.Selection([
        ('pending', 'In attesa'),
        ('promoted', 'Promossa'),
        ('discarded', 'Scartata'),
        ('error', 'Errore'),
    ], string='Stato triage', default='pending', index=True)
    triage_reason = fields.Char('Motivo triage')
    triage_at = fields.Datetime('Triage at')
    promoted_message_id = fields.Many2one(
        'casafolino.mail.message', string='Messaggio promosso',
        ondelete='set null')
    error_message = fields.Text('Errore')

    _sql_constraints = [
        ('account_message_id_uniq', 'unique(account_id, message_id)',
         'Message-ID duplicato per questo account'),
        ('account_uid_uniq', 'unique(account_id, uid)',
         'UID IMAP duplicato per questo account'),
    ]

    def init(self):
        """Create performance indices."""
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS casafolino_mail_raw_triage_state_idx
            ON casafolino_mail_raw (triage_state)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS casafolino_mail_raw_fetched_at_idx
            ON casafolino_mail_raw (fetched_at)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS casafolino_mail_raw_sender_email_idx
            ON casafolino_mail_raw (sender_email)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS casafolino_mail_raw_account_message_id_idx
            ON casafolino_mail_raw (account_id, message_id)
        """)

    # ── Manual actions (admin) ──────────────────────────────────────

    def action_force_promote(self):
        """Force-promote selected RAW records to MESSAGE."""
        for raw in self.filtered(lambda r: r.triage_state != 'promoted'):
            try:
                self._promote_raw(raw, 'manual_promote', match_type='none')
            except Exception as e:
                raw.write({
                    'triage_state': 'error',
                    'error_message': str(e)[:500],
                    'triage_at': fields.Datetime.now(),
                })

    def action_force_discard(self):
        """Force-discard selected RAW records."""
        self.filtered(lambda r: r.triage_state != 'promoted').write({
            'triage_state': 'discarded',
            'triage_reason': 'manual_discard',
            'triage_at': fields.Datetime.now(),
        })

    # ── Cron: Triage RAW ────────────────────────────────────────────

    @api.model
    def _cron_triage_raw(self):
        """Triage pending RAW records: deterministic rules then AI classifier."""
        pending = self.sudo().search([
            ('triage_state', '=', 'pending'),
        ], limit=100, order='fetched_at asc')

        if not pending:
            return

        _logger.info("[triage] Processing %d pending RAW records", len(pending))

        promoted = 0
        discarded = 0
        errors = 0

        for raw in pending:
            try:
                result = self._triage_single(raw)
                if result == 'promoted':
                    promoted += 1
                elif result == 'discarded':
                    discarded += 1
                else:
                    errors += 1
            except Exception as e:
                raw.write({
                    'triage_state': 'error',
                    'error_message': str(e)[:500],
                    'triage_at': fields.Datetime.now(),
                })
                errors += 1
                _logger.warning("[triage] Error on RAW %d: %s", raw.id, e)
            # Commit after each record
            self.env.cr.commit()

        _logger.info(
            "[triage] Done: %d promoted, %d discarded, %d errors",
            promoted, discarded, errors
        )

    def _triage_single(self, raw):
        """Triage a single RAW record. Returns 'promoted'|'discarded'|'error'."""
        sender = (raw.sender_email or '').lower().strip()

        # ── 3a. Deterministic rules ──

        # AUTO-DISCARD: blacklist patterns
        discard_reason = self._check_auto_discard(raw, sender)
        if discard_reason:
            raw.write({
                'triage_state': 'discarded',
                'triage_reason': discard_reason,
                'triage_at': fields.Datetime.now(),
            })
            return 'discarded'

        # AUTO-PROMOTE: CRM/preference checks
        promote_reason, partner_id, match_type = self._check_auto_promote(raw, sender)
        if promote_reason:
            self._promote_raw(raw, promote_reason, partner_id, match_type)
            return 'promoted'

        # ── 3b. AI classifier ──
        decision, reason = self._ai_classify(raw)

        if decision == 'promote':
            self._promote_raw(raw, 'ai: %s' % reason, match_type='none')
            return 'promoted'
        elif decision == 'discard':
            raw.write({
                'triage_state': 'discarded',
                'triage_reason': 'ai: %s' % reason,
                'triage_at': fields.Datetime.now(),
            })
            return 'discarded'
        else:
            # AI error — already logged
            return 'error'

    def _check_auto_discard(self, raw, sender):
        """Check deterministic auto-discard rules. Returns reason or False."""
        # sender_preference dismissed
        Pref = self.env['casafolino.mail.sender_preference']
        pref = Pref.search([
            ('email', '=ilike', sender),
            ('account_id', '=', raw.account_id.id),
        ], limit=1)
        if pref and pref.status == 'dismissed':
            return 'sender_dismissed'

        # noreply/mailer-daemon
        for prefix in _NOREPLY_PREFIXES:
            if sender.startswith(prefix):
                return 'noreply_sender'

        # notification/newsletter domain
        if _DOMAIN_BLACKLIST_RE.search(sender):
            return 'blacklist_domain'

        # Subject patterns
        if raw.subject and _SUBJECT_DISCARD_RE.search(raw.subject):
            return 'subject_discard_pattern'

        return False

    def _check_auto_promote(self, raw, sender):
        """Check deterministic auto-promote rules. Returns (reason, partner_id, match_type) or (False, False, 'none')."""
        Partner = self.env['res.partner'].sudo()

        # Outbound always promoted
        if raw.direction == 'outbound':
            return ('outbound', False, 'none')

        # sender_preference kept
        Pref = self.env['casafolino.mail.sender_preference']
        pref = Pref.search([
            ('email', '=ilike', sender),
            ('account_id', '=', raw.account_id.id),
        ], limit=1)
        if pref and pref.status == 'kept':
            # Try to find partner
            partner = Partner.search([('email', '=ilike', sender)], limit=1)
            return ('sender_kept', partner.id if partner else False, 'exact' if partner else 'none')

        # Exact email match in CRM
        partner = Partner.search([('email', '=ilike', sender)], limit=1)
        if partner:
            return ('crm_exact', partner.id, 'exact')

        # Domain match from company partner
        if '@' in sender:
            domain = sender.split('@')[-1]
            from .sender_filter import PUBLIC_DOMAINS_BLACKLIST
            if domain not in PUBLIC_DOMAINS_BLACKLIST:
                company = Partner.search([
                    ('is_company', '=', True),
                    ('email', '=ilike', '%@' + domain),
                ], limit=1)
                if company:
                    return ('crm_domain', company.id, 'domain')

        # Thread match (reply to existing MESSAGE)
        if raw.message_id:
            Message = self.env['casafolino.mail.message']
            # Check In-Reply-To or References from headers
            in_reply_to = self._extract_header(raw.headers_raw, 'In-Reply-To')
            references = self._extract_header(raw.headers_raw, 'References')
            ref_ids = []
            if in_reply_to:
                ref_ids.append(in_reply_to.strip())
            if references:
                ref_ids.extend(references.split())
            for ref_id in ref_ids:
                ref_id = ref_id.strip()
                if ref_id and Message.search([('message_id_rfc', '=', ref_id)], limit=1):
                    return ('thread_reply', False, 'none')

        return (False, False, 'none')

    def _extract_header(self, headers_raw, header_name):
        """Extract a header value from raw headers text."""
        if not headers_raw:
            return ''
        pattern = re.compile(
            r'^' + re.escape(header_name) + r':\s*(.+?)(?=\n\S|\Z)',
            re.MULTILINE | re.DOTALL | re.IGNORECASE
        )
        match = pattern.search(headers_raw)
        return match.group(1).strip() if match else ''

    # ── AI Classifier ───────────────────────────────────────────────

    def _ai_classify(self, raw):
        """Call Groq AI to classify email. Returns (decision, reason) or ('error', error_msg)."""
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.groq_api_key', '')
        if not api_key:
            raw.write({
                'triage_state': 'error',
                'error_message': 'Groq API key not configured',
                'triage_at': fields.Datetime.now(),
            })
            _logger.warning("[triage] Groq API key not configured, defaulting to promote")
            return ('promote', 'no_api_key_default_promote')

        system_prompt = (
            "Sei un classificatore email per un CRM food B2B. "
            "Rispondi SOLO con JSON valido nel formato richiesto."
        )
        user_prompt = (
            "Classifica questa email:\n"
            "Mittente: %s <%s>\n"
            "Oggetto: %s\n"
            "Anteprima body: %s\n"
            "Ha allegati: %s\n\n"
            "Rispondi con JSON:\n"
            '{"decision": "promote" | "discard", '
            '"category": "buyer_inquiry" | "partner" | "supplier" | "newsletter" | "spam" | "internal" | "other", '
            '"confidence": 0.0-1.0, '
            '"reason": "breve spiegazione"}'
        ) % (
            raw.sender_name or '',
            raw.sender_email or '',
            raw.subject or '(nessun oggetto)',
            (raw.body_preview or '')[:500],
            'Si' if raw.has_attachments else 'No',
        )

        headers = {
            'Authorization': 'Bearer %s' % api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (CasaFolino Triage RAW)',
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
                    timeout=30,
                )
                if resp.status_code == 429 and attempt == 0:
                    _logger.warning("[triage] Groq 429 rate limit, retry in 20s")
                    time.sleep(20)
                    continue
                if resp.status_code == 429:
                    raw.write({
                        'triage_state': 'error',
                        'error_message': 'Groq rate limit 429',
                        'triage_at': fields.Datetime.now(),
                    })
                    return ('error', 'rate_limit')

                resp.raise_for_status()
                data = resp.json()
                content = data['choices'][0]['message']['content']

                # Parse JSON from response
                content = content.strip()
                if content.startswith('```'):
                    content = re.sub(r'^```\w*\n?', '', content)
                    content = re.sub(r'\n?```$', '', content)
                result = json.loads(content)

                decision = result.get('decision', 'promote')
                confidence = float(result.get('confidence', 0))
                reason = result.get('reason', '')
                category = result.get('category', 'other')

                # D3: confidence < 0.7 → force promote (default permissivo)
                if confidence < 0.7:
                    decision = 'promote'
                    reason = 'low_confidence_%.2f: %s' % (confidence, reason)

                return (decision, '%s (%s)' % (reason, category))

            except (req.RequestException, json.JSONDecodeError, KeyError, ValueError) as e:
                if attempt == 0:
                    continue
                raw.write({
                    'triage_state': 'error',
                    'error_message': 'AI classify error: %s' % str(e)[:300],
                    'triage_at': fields.Datetime.now(),
                })
                _logger.warning("[triage] AI classify error for RAW %d: %s", raw.id, e)
                # Default permissivo: promote on error
                return ('promote', 'ai_error_default_promote')

        return ('promote', 'ai_fallthrough_default_promote')

    # ── Promotion: RAW → MESSAGE ────────────────────────────────────

    def _promote_raw(self, raw, reason, partner_id=False, match_type='none'):
        """Create MESSAGE from RAW, download body via IMAP, update RAW state."""
        Message = self.env['casafolino.mail.message']
        account = raw.account_id

        # Determine direction
        actual_direction = raw.direction or 'inbound'

        # Create MESSAGE record
        vals = {
            'account_id': account.id,
            'message_id_rfc': raw.message_id,
            'imap_uid': raw.uid,
            'imap_folder': raw.imap_folder or 'INBOX',
            'direction': actual_direction,
            'sender_email': raw.sender_email,
            'sender_name': raw.sender_name,
            'recipient_emails': raw.recipient_emails,
            'cc_emails': raw.cc_emails or '',
            'subject': raw.subject,
            'email_date': raw.email_date,
            'state': 'new',
            'partner_id': partner_id or False,
            'match_type': match_type or 'none',
            'fetch_state': 'pending',
        }

        new_msg = Message.create(vals)

        # Download body via IMAP
        imap = None
        try:
            imap = account._get_imap_connection()
            new_msg._download_body_imap(imap, raw.imap_folder or 'INBOX', raw.uid)
        except Exception as e:
            _logger.warning(
                "[triage] Body download failed for RAW %d → MSG %d: %s",
                raw.id, new_msg.id, e
            )
            # MESSAGE stays with fetch_state='pending', cron 85 will retry
        finally:
            if imap:
                try:
                    imap.logout()
                except Exception:
                    pass

        # Auto-create sender preference if new inbound sender
        if actual_direction == 'inbound' and raw.sender_email:
            Pref = self.env['casafolino.mail.sender_preference']
            existing_pref = Pref.search([
                ('email', '=ilike', raw.sender_email),
                ('account_id', '=', account.id),
            ], limit=1)
            if not existing_pref:
                try:
                    Pref.sudo().create({
                        'email': raw.sender_email.lower().strip(),
                        'account_id': account.id,
                        'status': 'pending',
                    })
                except Exception:
                    pass

        # ── V14: Apply folder rules ──
        self._assign_folder(new_msg, raw)

        # ── V18: Autoresponder check ──
        if actual_direction == 'inbound':
            self._check_autoresponder(new_msg, raw)

        raw.write({
            'triage_state': 'promoted',
            'triage_reason': reason,
            'triage_at': fields.Datetime.now(),
            'promoted_message_id': new_msg.id,
        })

    # ── V18: Autoresponder ───────────────────────────────────────

    def _check_autoresponder(self, message, raw):
        """Check if any active autoresponder should reply to this inbound message."""
        try:
            account = raw.account_id
            user = account.responsible_user_id
            if not user:
                return

            AR = self.env['casafolino.mail.autoresponder'].sudo()
            ar = AR.search([
                ('user_id', '=', user.id),
                ('active', '=', True),
            ], limit=1)
            if not ar:
                return

            headers_raw = raw.headers_raw or ''
            if ar._should_autoreply(raw.sender_email, headers_raw):
                ar._send_autoreply(message)
        except Exception as e:
            _logger.warning(
                "[autoresponder] Check failed for RAW %d: %s", raw.id, e)

    # ── V14: Folder assignment ─────────────────────────────────────

    def _assign_folder(self, message, raw):
        """Apply folder rules to a promoted message. First match wins.
        If no rule matches, assign to 'unsorted' folder."""
        Folder = self.env['casafolino.mail.folder']
        Rule = self.env['casafolino.mail.folder.rule']
        account_id = raw.account_id.id

        rules = Rule.search([
            ('account_id', '=', account_id),
            ('active', '=', True),
        ], order='sequence asc, id asc')

        msg_data = {
            'sender_email': raw.sender_email,
            'subject': raw.subject,
            'has_attachments': raw.has_attachments,
        }

        for rule in rules:
            if rule._matches_message(msg_data):
                vals = {'folder_id': rule.folder_id.id}
                if rule.mark_as_read:
                    vals['is_read'] = True
                message.write(vals)
                return

        # No rule matched → unsorted folder
        unsorted = Folder.search([
            ('account_id', '=', account_id),
            ('system_code', '=', 'unsorted'),
        ], limit=1)
        if unsorted:
            message.write({'folder_id': unsorted.id})

    # ── Cron: Cleanup RAW ───────────────────────────────────────────

    @api.model
    def _cron_cleanup_raw(self):
        """Delete processed RAW records older than 48h. Never touch pending."""
        cutoff = fields.Datetime.now() - timedelta(hours=48)

        # Warn about old pending records
        old_pending = self.sudo().search_count([
            ('triage_state', '=', 'pending'),
            ('fetched_at', '<', fields.Datetime.now() - timedelta(hours=6)),
        ])
        if old_pending:
            _logger.warning("[cleanup] %d RAW records pending for >6 hours", old_pending)

        to_delete = self.sudo().search([
            ('triage_state', 'in', ['promoted', 'discarded', 'error']),
            ('fetched_at', '<', cutoff),
        ])
        count = len(to_delete)
        if count:
            to_delete.unlink()
        _logger.info("[cleanup] Deleted %d RAW records older than 48h", count)
