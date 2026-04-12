import base64
import email
import logging

from odoo import models, fields, api
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


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

            # Se ha un partner, crea nel chatter
            if record.partner_id:
                record._create_partner_mail_message()

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

    def action_create_partner(self):
        """Crea un nuovo res.partner dall'email."""
        self.ensure_one()
        if self.direction == 'inbound':
            email_addr = self.sender_email
            name = self.sender_name or email_addr
        else:
            email_addr = self.recipient_emails.split(',')[0].strip() if self.recipient_emails else ''
            name = email_addr

        partner = self.env['res.partner'].create({
            'name': name or email_addr,
            'email': email_addr,
        })
        self.write({'partner_id': partner.id, 'match_type': 'manual'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }

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
        """Ri-match automatico per email senza partner."""
        Account = self.env['casafolino.mail.account']
        for record in self.filtered(lambda r: not r.partner_id):
            email_to_match = record.sender_email if record.direction == 'inbound' else (
                record.recipient_emails.split(',')[0].strip() if record.recipient_emails else '')
            if not email_to_match:
                continue
            # Match esatto
            partner = self.env['res.partner'].search([('email', '=ilike', email_to_match)], limit=1)
            if partner:
                record.write({'partner_id': partner.id, 'match_type': 'exact'})
                continue
            # Match dominio
            domain = email_to_match.split('@')[1] if '@' in email_to_match else ''
            if domain:
                partner = self.env['res.partner'].search([
                    ('is_company', '=', True),
                    ('website', 'ilike', domain),
                ], limit=1)
                if partner:
                    record.write({'partner_id': partner.id, 'match_type': 'domain'})

    def action_bulk_create_partners(self):
        """Crea contatti da email selezionate senza partner."""
        Partner = self.env['res.partner']
        for record in self.filtered(lambda r: not r.partner_id and r.sender_email):
            existing = Partner.search([('email', '=ilike', record.sender_email)], limit=1)
            if existing:
                record.write({'partner_id': existing.id, 'match_type': 'exact'})
            else:
                partner = Partner.create({
                    'name': record.sender_name or record.sender_email,
                    'email': record.sender_email,
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
