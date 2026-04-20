import hashlib
import json
import logging
import re

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

_SUBJECT_PREFIX_RE = re.compile(
    r'^\s*(Re|R|Fwd|FW|Fw|AW|SV|VS|RE|Rif|RIF)\s*:\s*',
    re.IGNORECASE,
)


class CasafolinoMailThread(models.Model):
    _name = 'casafolino.mail.thread'
    _description = 'Thread conversazione — Mail V3'
    _order = 'last_message_date desc'

    thread_key = fields.Char('Thread Key', index=True, required=True)
    account_id = fields.Many2one('casafolino.mail.account', string='Account',
                                  required=True, ondelete='cascade', index=True)
    subject = fields.Char('Oggetto originale')
    subject_normalized = fields.Char('Oggetto normalizzato', index=True)
    participant_emails = fields.Text('Partecipanti (JSON)')
    partner_ids = fields.Many2many('res.partner', 'casafolino_mail_thread_partner_rel',
                                    'thread_id', 'partner_id', string='Partner')
    first_message_date = fields.Datetime('Prima email')
    last_message_date = fields.Datetime('Ultima email', index=True)
    message_count = fields.Integer('N. messaggi', compute='_compute_aggregates', store=True)
    unread_count = fields.Integer('Non letti', compute='_compute_aggregates', store=True)
    has_attachments = fields.Boolean('Ha allegati', compute='_compute_aggregates', store=True)
    is_archived = fields.Boolean('Archiviato', compute='_compute_is_archived', store=True)
    state_aggregate = fields.Selection([
        ('all_keep', 'Tutti keep'),
        ('mixed', 'Misti'),
        ('all_discard', 'Tutti discard'),
    ], string='Stato aggregato', default='all_keep')
    hotness_snapshot = fields.Integer('Hotness snapshot', default=0)
    is_snoozed = fields.Boolean('Snoozed', default=False, index=True)
    has_outbound = fields.Boolean('Ha outbound', compute='_compute_has_outbound', store=True)
    message_ids = fields.One2many('casafolino.mail.message', 'thread_id', string='Messaggi')

    _sql_constraints = [
        ('thread_key_account_unique', 'UNIQUE(thread_key, account_id)',
         'Thread key must be unique per account'),
    ]

    @api.depends('message_ids', 'message_ids.state', 'message_ids.is_read',
                 'message_ids.body_downloaded', 'message_ids.is_deleted')
    def _compute_aggregates(self):
        for thread in self:
            msgs = thread.message_ids.filtered(lambda m: not m.is_deleted)
            thread.message_count = len(msgs)
            thread.unread_count = len(msgs.filtered(lambda m: not m.is_read))
            thread.has_attachments = any(m.body_downloaded and m.attachment_ids for m in msgs)

    @api.depends('message_ids', 'message_ids.direction')
    def _compute_has_outbound(self):
        for thread in self:
            thread.has_outbound = any(
                m.direction == 'outbound' for m in thread.message_ids if not m.is_deleted
            )

    @api.depends('message_ids.is_archived')
    def _compute_is_archived(self):
        for thread in self:
            msgs = thread.message_ids.filtered(lambda m: not m.is_deleted)
            thread.is_archived = bool(msgs) and all(m.is_archived for m in msgs)

    @staticmethod
    def _normalize_subject(subject):
        """Rimuove prefissi Re:/Fwd:/etc e normalizza."""
        if not subject:
            return ''
        cleaned = _SUBJECT_PREFIX_RE.sub('', subject)
        while _SUBJECT_PREFIX_RE.search(cleaned):
            cleaned = _SUBJECT_PREFIX_RE.sub('', cleaned)
        return cleaned.strip().lower()

    @staticmethod
    def _compute_thread_key_hash(subject_norm, participants_sorted, account_id):
        """SHA256[:16] di subject_norm + participants + account_id."""
        raw = f"{subject_norm}|{participants_sorted}|{account_id}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

    @api.model
    def _upsert_from_message(self, message):
        """Idempotent: trova o crea thread per questo messaggio, assegna thread_id."""
        if not message or not message.account_id:
            return

        subject_norm = self._normalize_subject(message.subject)
        if not subject_norm:
            subject_norm = '(no subject)'

        # Raccogli partecipanti
        participants = set()
        if message.sender_email:
            participants.add(message.sender_email.lower().strip())
        if message.recipient_emails:
            for e in message.recipient_emails.split(','):
                e = e.strip().lower()
                if e:
                    participants.add(e)
        participants_sorted = ','.join(sorted(participants))

        account_id = message.account_id.id
        thread_key = self._compute_thread_key_hash(subject_norm, participants_sorted, account_id)

        # Cerca thread esistente con stesso subject normalizzato e account
        # Usa subject_normalized per matching più robusto (ignora differenze partecipanti CC)
        thread = self.search([
            ('subject_normalized', '=', subject_norm),
            ('account_id', '=', account_id),
        ], limit=1)

        email_date = message.email_date or fields.Datetime.now()

        if thread:
            # Aggiorna thread esistente
            vals = {}
            if not thread.first_message_date or email_date < thread.first_message_date:
                vals['first_message_date'] = email_date
            if not thread.last_message_date or email_date > thread.last_message_date:
                vals['last_message_date'] = email_date

            # Aggiorna partecipanti
            try:
                existing = json.loads(thread.participant_emails or '[]')
            except (json.JSONDecodeError, TypeError):
                existing = []
            merged = sorted(set(existing) | participants)
            vals['participant_emails'] = json.dumps(merged)

            # Partner link
            if message.partner_id and message.partner_id.id not in thread.partner_ids.ids:
                vals['partner_ids'] = [(4, message.partner_id.id)]

            # Hotness snapshot
            if message.partner_id:
                intel = self.env['casafolino.partner.intelligence'].search([
                    ('partner_id', '=', message.partner_id.id)
                ], limit=1)
                if intel:
                    vals['hotness_snapshot'] = intel.hotness_score

            if vals:
                thread.write(vals)
        else:
            # Crea nuovo thread
            partner_ids = [(4, message.partner_id.id)] if message.partner_id else []
            hotness = 0
            if message.partner_id:
                intel = self.env['casafolino.partner.intelligence'].search([
                    ('partner_id', '=', message.partner_id.id)
                ], limit=1)
                if intel:
                    hotness = intel.hotness_score

            thread = self.create({
                'thread_key': thread_key,
                'account_id': account_id,
                'subject': message.subject or '(no subject)',
                'subject_normalized': subject_norm,
                'participant_emails': json.dumps(sorted(participants)),
                'partner_ids': partner_ids,
                'first_message_date': email_date,
                'last_message_date': email_date,
                'hotness_snapshot': hotness,
            })

        # Assegna thread_id al messaggio (write diretto per evitare ricorsione)
        if message.thread_id != thread:
            message.with_context(skip_thread_upsert=True).write({'thread_id': thread.id})

        return thread

    def _recompute_aggregates(self):
        """Force recompute dei campi aggregati."""
        self._compute_aggregates()
        self._compute_is_archived()
