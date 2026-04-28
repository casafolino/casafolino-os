import logging
import re
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

# Patterns to skip autoresponder
_NOREPLY_RE = re.compile(
    r'^(noreply|no-reply|donotreply|do-not-reply)@', re.IGNORECASE
)

# Simple language detection keywords
_LANG_KEYWORDS = {
    'en': {'dear', 'hello', 'hi', 'please', 'thank', 'thanks', 'regards',
           'sincerely', 'best', 'looking forward', 'kind regards'},
    'es': {'hola', 'estimado', 'estimada', 'gracias', 'saludos',
           'cordialmente', 'atentamente', 'por favor', 'buenos dias'},
    'de': {'sehr geehrte', 'hallo', 'bitte', 'danke', 'freundliche',
           'gruesse', 'grüße', 'mit freundlichen'},
    'fr': {'bonjour', 'cher', 'chère', 'merci', 'cordialement',
           'salutations', 'veuillez', "s'il vous plaît"},
}


class CasafolinoMailAutoresponder(models.Model):
    _name = 'casafolino.mail.autoresponder'
    _description = 'Autoresponder Fuori Sede — Mail Hub'
    _order = 'id desc'

    user_id = fields.Many2one(
        'res.users', string='Utente', required=True,
        default=lambda self: self.env.uid, ondelete='cascade', index=True)
    active = fields.Boolean('Attivo', default=False)
    date_start = fields.Date('Data inizio')
    date_end = fields.Date('Data fine')
    subject_prefix = fields.Char(
        'Prefisso oggetto', default='[Fuori sede] ')
    body_html_it = fields.Html(
        'Messaggio italiano', sanitize=False,
        default=lambda self: self._default_body_it())
    body_html_en = fields.Html('Messaggio inglese', sanitize=False)
    body_html_es = fields.Html('Messaggio spagnolo', sanitize=False)
    contact_alternate_id = fields.Many2one(
        'res.users', string='Contatto alternativo',
        help='Chi contattare durante la tua assenza')
    sent_count = fields.Integer(
        'Risposte inviate', compute='_compute_sent_count', store=True)
    sent_ids = fields.One2many(
        'casafolino.mail.autoresponder.sent', 'autoresponder_id',
        string='Log invii')

    _sql_constraints = [
        ('user_unique', 'unique(user_id)',
         'Ogni utente può avere un solo autoresponder'),
    ]

    @api.model
    def _default_body_it(self):
        return (
            '<p>Gentile {{sender_name}},</p>'
            '<p>Grazie per la sua email. Sono attualmente fuori sede '
            'e rientrerò il {{return_date}}.</p>'
            '<p>Per questioni urgenti, può contattare {{contact_alternate}}.</p>'
            '<p>Cordiali saluti,<br/>{{my_name}}</p>'
        )

    @api.depends('sent_ids')
    def _compute_sent_count(self):
        for rec in self:
            rec.sent_count = len(rec.sent_ids)

    # ── Template rendering ─────────────────────────────────────────

    def _render_body(self, sender_name, lang='it'):
        """Render autoresponder body with template variables."""
        self.ensure_one()

        # Pick body by language
        body = ''
        if lang == 'en' and self.body_html_en:
            body = self.body_html_en
        elif lang == 'es' and self.body_html_es:
            body = self.body_html_es
        else:
            body = self.body_html_it or ''

        if not body:
            return ''

        # Build replacements
        user = self.user_id
        return_date = ''
        if self.date_end:
            return_date = self.date_end.strftime('%d/%m/%Y')

        alternate = ''
        if self.contact_alternate_id:
            alt = self.contact_alternate_id
            alternate = alt.name or ''
            if alt.email:
                alternate += ' (%s)' % alt.email

        replacements = {
            '{{sender_name}}': sender_name or 'Gentile Cliente',
            '{{return_date}}': return_date or 'data da definire',
            '{{my_name}}': user.name or '',
            '{{contact_alternate}}': alternate or 'il nostro team',
        }

        result = str(body)
        for key, val in replacements.items():
            result = result.replace(key, val)
        return result

    # ── Anti-loop checks ───────────────────────────────────────────

    def _should_autoreply(self, sender_email, headers_raw=''):
        """Check if autoresponder should reply to this sender.
        Returns True if reply should be sent."""
        self.ensure_one()

        if not self.active:
            return False

        # Check date range
        today = fields.Date.context_today(self)
        if self.date_start and today < self.date_start:
            return False
        if self.date_end and today > self.date_end:
            return False

        sender = (sender_email or '').lower().strip()
        if not sender:
            return False

        # Skip no-reply addresses
        if _NOREPLY_RE.match(sender):
            return False

        # Check headers for mailing list / auto-generated
        headers = (headers_raw or '').lower()
        if 'list-unsubscribe' in headers:
            return False
        if 'auto-submitted' in headers and 'auto-replied' not in headers:
            # auto-submitted: auto-generated → skip
            if 'auto-generated' in headers or 'auto-notified' in headers:
                return False

        # Check precedence header (bulk/list)
        if 'precedence: bulk' in headers or 'precedence: list' in headers:
            return False

        # Already replied to this sender in current period?
        Sent = self.env['casafolino.mail.autoresponder.sent']
        domain = [
            ('autoresponder_id', '=', self.id),
            ('sender_email', '=ilike', sender),
        ]
        if self.date_start:
            domain.append(('sent_at', '>=', fields.Datetime.to_datetime(self.date_start)))
        if Sent.sudo().search_count(domain):
            return False

        return True

    # ── Send autoresponder ─────────────────────────────────────────

    def _send_autoreply(self, message):
        """Queue autoresponder reply for an inbound message.
        message: casafolino.mail.message record."""
        self.ensure_one()
        account = message.account_id
        sender_email = (message.sender_email or '').strip()
        sender_name = message.sender_name or sender_email.split('@')[0]

        # Detect language from body
        lang = self._detect_language(message.body_html or message.body_preview or '')

        body = self._render_body(sender_name, lang=lang)
        if not body:
            _logger.warning(
                "[autoresponder] Empty body for user %s, skipping",
                self.user_id.login)
            return False

        # Build subject
        original_subject = message.subject or ''
        prefix = self.subject_prefix or '[Fuori sede] '
        if original_subject.lower().startswith('re:'):
            subject = '%s%s' % (prefix, original_subject)
        else:
            subject = '%sRe: %s' % (prefix, original_subject)

        # Queue via outbox
        Outbox = self.env['casafolino.mail.outbox'].sudo()
        Outbox.queue_send(
            account_id=account.id,
            to_emails=sender_email,
            subject=subject,
            body_html=body,
            in_reply_to=message.message_id_rfc or '',
            references=message.message_id_rfc or '',
            priority='0',
            source_message_id=message.id,
        )

        # Log sent
        self.env['casafolino.mail.autoresponder.sent'].sudo().create({
            'autoresponder_id': self.id,
            'sender_email': sender_email.lower(),
            'sent_at': fields.Datetime.now(),
            'thread_id': message.thread_id.id if message.thread_id else False,
        })

        _logger.info(
            "[autoresponder] Queued reply to %s for user %s",
            sender_email, self.user_id.login)
        return True

    # ── Language detection ─────────────────────────────────────────

    def _detect_language(self, text):
        """Simple keyword-based language detection. Returns 'it'|'en'|'es'|'de'|'fr'."""
        if not text:
            return 'it'

        # Strip HTML tags for analysis
        clean = re.sub(r'<[^>]+>', ' ', str(text)).lower()

        scores = {}
        for lang, keywords in _LANG_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in clean)
            if score:
                scores[lang] = score

        if not scores:
            return 'it'  # default

        best = max(scores, key=scores.get)
        # Only return non-Italian if confidence is clear
        if best != 'it' and scores.get(best, 0) >= 2:
            return best
        if best == 'it':
            return 'it'
        return 'it'

    # ── Cron: auto-activate/deactivate ─────────────────────────────

    @api.model
    def _cron_autoresponder_activation_check(self):
        """Check autoresponder date ranges and activate/deactivate accordingly."""
        today = fields.Date.context_today(self)
        all_ar = self.sudo().search([])

        activated = 0
        deactivated = 0

        for ar in all_ar:
            if not ar.date_start or not ar.date_end:
                continue

            should_be_active = ar.date_start <= today <= ar.date_end

            if should_be_active and not ar.active:
                ar.active = True
                activated += 1
                _logger.info(
                    "[autoresponder] Auto-activated for user %s (period %s - %s)",
                    ar.user_id.login, ar.date_start, ar.date_end)

            elif not should_be_active and ar.active and today > ar.date_end:
                ar.active = False
                deactivated += 1
                _logger.info(
                    "[autoresponder] Auto-deactivated for user %s (period ended %s)",
                    ar.user_id.login, ar.date_end)

        if activated or deactivated:
            _logger.info(
                "[autoresponder] Cron: %d activated, %d deactivated",
                activated, deactivated)


class CasafolinoMailAutoresponderSent(models.Model):
    _name = 'casafolino.mail.autoresponder.sent'
    _description = 'Autoresponder Sent Log'
    _order = 'sent_at desc'

    autoresponder_id = fields.Many2one(
        'casafolino.mail.autoresponder', string='Autoresponder',
        required=True, ondelete='cascade', index=True)
    sender_email = fields.Char('Email mittente', required=True, index=True)
    sent_at = fields.Datetime('Inviato il', required=True,
                               default=fields.Datetime.now)
    thread_id = fields.Many2one(
        'casafolino.mail.thread', string='Thread',
        ondelete='set null')
