import logging

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

CONSOLE_GROUP = 'casafolino_console_access.group_console_api'
# S5 — allowlist unica degli operatori umani (login casafolinoerp + attribution send/reply).
CONSOLE_OPERATOR_GROUP = 'casafolino_console_access.group_console_operator'


def _is_console(env):
    """True se l'utente corrente è il service-user console (portal scoped)."""
    return env.user.has_group(CONSOLE_GROUP)


def _audit(env, model, res_ids, action, fields_touched=None, operator=None):
    env['casafolino.console.audit'].sudo().create({
        'user_id': env.user.id,
        'login': env.user.login,
        'model': model,
        'res_ids': str(res_ids)[:255],
        'action': action,
        'fields_touched': (','.join(sorted(fields_touched))[:255]) if fields_touched else False,
        'operator_uid': operator.id if operator else False,
        'operator_login': operator.login if operator else False,
    })


class CasafolinoMailMessageGateway(models.Model):
    """Gateway triage: l'unico modo per console_api di scrivere su una mail.
    Scrive SOLO il campo `state` (mai body/contenuto), valida lo stato, logga l'audit.
    L'ACL di console_api su casafolino.mail.message è READ-ONLY → niente write diretta."""
    _inherit = 'casafolino.mail.message'

    # stati triage ammessi (allineati alla selection del modello). 'trash' = Cestino soft
    # (recuperabile, MAI unlink fisico): la riga resta, esce solo dall'inbox.
    _CONSOLE_TRIAGE_STATES = ('new', 'review', 'keep', 'auto_keep', 'discard', 'auto_discard', 'trash')

    def console_triage(self, state, operator_uid=None):
        """Chiamato via JSON-RPC dall'utente portal: browse(ids).console_triage(state).
        Scrive solo state via sudo (bulk-safe su tutti gli ids, ogni msg mantiene la sua
        casella). Mai un write(model, vals) generico, mai unlink. operator_uid (S5) =
        attribution umana validata contro group_console_operator."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console può usare console_triage."))
        if state not in self._CONSOLE_TRIAGE_STATES:
            raise UserError(_("Stato triage non valido: %s") % state)
        if not self.ids:
            return {'ok': False, 'error': 'no records'}
        operator = self._resolve_operator(operator_uid)  # valida allowlist o vuoto
        # self è già filtrato dalle record-rule di lettura dell'utente
        ids = self.ids
        self.sudo().write({'state': state})  # SOLO state — body invariato, nessun unlink
        _audit(self.env, 'casafolino.mail.message', ids, 'triage:%s' % state, {'state'}, operator)
        return {'ok': True, 'count': len(ids), 'state': state}

    # ── Blocca mittente / Scarta sempre (sender_policy auto_discard + sweep) ──

    _DEFAULT_NEVER_BLOCK = 'gmail.com,outlook.com,hotmail.com,yahoo.com,casafolino.com'

    def _console_never_block(self):
        raw = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino_pipeline_control.never_block_domains', self._DEFAULT_NEVER_BLOCK)
        return [d.strip().lower() for d in (raw or '').split(',') if d.strip()]

    def console_block_sender_info(self, operator_uid=None):
        """Info per il dialog di conferma: dominio, se libero (denylist), conteggio in coda."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console può usare console_block_sender_info."))
        self.ensure_one()
        self._resolve_operator(operator_uid)
        email = (self.sender_email or '').lower().strip()
        domain = email.split('@')[-1] if '@' in email else ''
        is_free = domain in self._console_never_block()
        M = self.env['casafolino.mail.message'].sudo()
        q = [('state', 'in', ['new', 'review'])]
        q_domain = M.search_count(q + [('sender_email', '=ilike', '%@' + domain)]) if domain else 0
        q_email = M.search_count(q + [('sender_email', '=ilike', email)]) if email else 0
        return {
            'ok': True, 'sender_email': email, 'domain': domain,
            'is_free_domain': is_free, 'queue_count_domain': q_domain, 'queue_count_email': q_email,
        }

    def console_block_sender(self, scope='domain', operator_uid=None):
        """browse(ids).console_block_sender(scope, operator_uid): crea sender_policy
        auto_discard (idempotente) per il dominio/indirizzo dei messaggi, poi sweep
        retroattivo new/review → discard. Domini liberi → solo email_exact."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console può usare console_block_sender."))
        if not self.ids:
            return {'ok': False, 'error': 'no records'}
        operator = self._resolve_operator(operator_uid)
        Policy = self.env['casafolino.mail.sender_policy'].sudo()
        M = self.env['casafolino.mail.message'].sudo()
        never = self._console_never_block()
        patterns = {}  # (ptype, pvalue) -> set(msg ids selezionati)
        for m in self.sudo():
            email = (m.sender_email or '').lower().strip()
            domain = email.split('@')[-1] if '@' in email else ''
            if scope == 'domain' and domain and domain not in never:
                key = ('domain', domain)
            else:
                key = ('email_exact', email)
            if key[1]:
                patterns.setdefault(key, set()).add(m.id)
        if not patterns:
            return {'ok': False, 'error': 'mittente mancante'}
        results = []
        total_retro = 0
        swept_ids = []
        for (ptype, pvalue), sel in patterns.items():
            existing = Policy.search([
                ('action', '=', 'auto_discard'),
                ('pattern_type', '=', ptype),
                ('pattern_value', '=ilike', pvalue),
            ], limit=1)
            if existing:
                policy = existing
                created = False
                if not policy.active:
                    policy.active = True
            else:
                policy = Policy.create({
                    'name': 'Blocco %s' % pvalue,
                    'pattern_type': ptype,
                    'pattern_value': pvalue,
                    'action': 'auto_discard',
                    'priority': 90,
                    'active': True,
                })
                created = True
            match = [('sender_email', '=ilike', '%@' + pvalue)] if ptype == 'domain' \
                else [('sender_email', '=ilike', pvalue)]
            retro = M.search([('state', 'in', ['new', 'review'])] + match) | M.browse(list(sel)).exists()
            retro = retro.filtered(lambda x: x.state in ('new', 'review'))
            if retro:
                retro.write({
                    'state': 'discard', 'is_archived': True,
                    'policy_applied_id': policy.id,
                    'triage_user_id': operator.id if operator else self.env.uid,
                    'triage_date': fields.Datetime.now(),
                })
                swept_ids += retro.ids
            total_retro += len(retro)
            _logger.info("[blocca-mittente] pattern=%s:%s creata=%s scartate_retroattive=%s operator=%s",
                         ptype, pvalue, created, len(retro), operator.id if operator else False)
            results.append({'pattern_type': ptype, 'pattern_value': pvalue,
                            'created': created, 'retro': len(retro)})
        _audit(self.env, 'casafolino.mail.message', swept_ids,
               'block_sender:%s' % scope, {'state', 'policy_applied_id'}, operator)
        return {'ok': True, 'results': results, 'retro_total': total_retro, 'swept_ids': swept_ids}

    def console_mark_read(self, is_read, operator_uid=None):
        """Segna letto/non-letto in bulk. Scrive SOLO is_read via sudo, audita con operatore.
        Mai unlink, mai write generico (ACL console_api read-only sul modello)."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console può usare console_mark_read."))
        if not self.ids:
            return {'ok': False, 'error': 'no records'}
        operator = self._resolve_operator(operator_uid)
        ids = self.ids
        flag = bool(is_read)
        self.sudo().write({'is_read': flag})  # SOLO is_read
        _audit(self.env, 'casafolino.mail.message', ids, 'mark_read:%s' % (1 if flag else 0), {'is_read'}, operator)
        return {'ok': True, 'count': len(ids), 'is_read': flag}

    # 'trash' = stato Cestino soft (recuperabile). Aggiunto qui (non in casafolino_mail) per
    # tenere il concetto Console nell'addon Console. set default su ondelete = mai vincoli duri.
    state = fields.Selection(
        selection_add=[('trash', 'Cestino')],
        ondelete={'trash': 'set default'},
    )

    def _resolve_operator(self, operator_uid):
        """S5 — ATTRIBUTION. Risolve l'operatore umano dallo uid e valida l'allowlist.
        operator_uid è SEPARATO dall'account mittente: registra CHI ha operato, non cambia
        chi invia. Vuoto/0/None → nessuna attribution (retro-compatibile, rollback-friendly).
        Non-allowlist → rifiuta (il gateway non si fida di uid arbitrari)."""
        if not operator_uid:
            return self.env['res.users']
        try:
            uid = int(operator_uid)
        except (TypeError, ValueError):
            raise UserError(_("operator_uid non valido: %s") % operator_uid)
        user = self.env['res.users'].sudo().browse(uid)
        if not user.exists():
            raise UserError(_("operator_uid %s inesistente.") % uid)
        group = self.env.ref(CONSOLE_OPERATOR_GROUP, raise_if_not_found=False)
        if not group or user not in group.sudo().users:
            raise UserError(_("operator_uid %s non è in Console Operator (allowlist).") % uid)
        return user

    @api.model
    def console_library(self):
        """Libreria invii CURATA: materiali approvati (cataloghi/brochure/listini) allegabili in
        sicurezza dal composer. Sudo+gated: nessun ACL nuovo a console_api."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        mats = self.env['casafolino.mail.material'].sudo().search([
            ('state', '=', 'approved'), ('active', '=', True),
            ('delivery_type', '=', 'file'), ('file_data', '!=', False),
        ], order='category, name')
        # Brief 12 — dimensione + flag asLink (item oltre soglia → inviato come link, non allegato).
        ICP = self.env['ir.config_parameter'].sudo()
        threshold = int(float(ICP.get_param('casafolino.console_doc_attach_max_mb', 20) or 20) * 1024 * 1024)
        Att = self.env['ir.attachment'].sudo()
        out = []
        for m in mats:
            att = Att.search([('res_model', '=', 'casafolino.mail.material'),
                              ('res_field', '=', 'file_data'), ('res_id', '=', m.id)], limit=1)
            size = att.file_size if att else 0
            out.append({'id': m.id, 'name': m.name, 'category': m.category,
                        'language': m.language, 'fileName': m.file_name or m.name,
                        'sizeMb': round((size or 0) / 1024 / 1024, 1), 'asLink': bool(size and size > threshold)})
        return out

    @api.model
    def console_templates(self):
        """Template mail multilingua (oggetto+corpo) inseribili nel composer."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        tpls = self.env['casafolino.mail.template'].sudo().search([], order='language, name')
        return [{'id': t.id, 'name': t.name, 'description': t.description or '',
                 'subject': t.subject or '', 'bodyHtml': t.body_html or '',
                 'language': t.language} for t in tpls]

    def _console_material_attachments(self, material_ids):
        """Allegati DALLA LIBRERIA CURATA: solo materiali approvati. Legge file_data (no ref
        arbitrario a ir.attachment) → crea attachment freschi. Anti-exfiltration mantenuto."""
        Att = self.env['ir.attachment'].sudo()
        out = Att.browse()
        if not material_ids:
            return out
        Mat = self.env['casafolino.mail.material'].sudo()
        for mid in material_ids:
            m = Mat.browse(int(mid))
            if not m.exists() or m.state != 'approved' or not m.active or not m.file_data:
                raise UserError(_("Materiale %s non in libreria invii (approvato).") % mid)
            out |= Att.create({
                'name': m.file_name or (m.name + '.pdf'), 'datas': m.file_data,
                'mimetype': 'application/octet-stream',
                'res_model': 'casafolino.mail.outbox', 'res_id': 0,
                'description': 'console library material %s' % m.id,
            })
        return out

    @staticmethod
    def _console_emails(raw):
        """Normalizza CC/BCC (stringa o lista) → lista email valide, dedup."""
        if not raw:
            return []
        import re
        parts = re.split(r'[,;\s]+', raw) if isinstance(raw, str) else list(raw)
        out = []
        for p in parts:
            e = (p or '').strip().lower()
            if e and '@' in e and e not in out:
                out.append(e)
        return out

    @api.model
    def console_send(self, payload):
        """Gateway SEND. PHASE A = SOLO DRAFT (nessun invio reale).
        - valida il destinatario contro l'email del record linkato (no destinatari arbitrari)
        - risolve l'account mittente dal messaggio sorgente (responsible_user_id → account)
        - crea una BOZZA outbox (state='draft' → il cron NON la invia)
        - audita. console_api NON ha create/write diretto su mail.mail/mail.message/outbox.
        payload: {to, subject, body, sourceMessageId?, leadId?, partnerId?}"""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api può usare console_send."))
        to = (payload.get('to') or '').strip().lower()
        subject = payload.get('subject') or ''
        body = payload.get('body') or ''
        src_id = payload.get('sourceMessageId')
        lead_id = payload.get('leadId')
        partner_id = payload.get('partnerId')
        account_explicit = payload.get('accountId')
        operator = self._resolve_operator(payload.get('operator_uid'))  # S5 attribution
        if not to or '@' not in to:
            raise UserError(_("Destinatario non valido."))

        # COMPOSE (Nuova mail da zero): casella scelta esplicitamente, nessuna source.
        # Destinatario nuovo deliberato → niente allowlist (resta bozza con kill-switch False;
        # cap/dedup/burst restano quando live). Diverso dal reply: il guard anti-arbitrario
        # serve a non far deragliare le risposte, non a vietare un compose intenzionale.
        compose = bool(account_explicit) and not src_id

        # 1-2. email ammesse dal record linkato + account mittente
        allowed = set()
        account = self.env['casafolino.mail.account']
        if compose:
            account = self.env['casafolino.mail.account'].sudo().browse(int(account_explicit))
            if not account.exists():
                raise UserError(_("Casella mittente inesistente."))
        else:
            if src_id:
                src = self.sudo().browse(int(src_id))
                if not src.exists():
                    raise UserError(_("Messaggio sorgente inesistente."))
                if src.sender_email:
                    allowed.add(src.sender_email.strip().lower())
                if src.partner_id and src.partner_id.email:
                    allowed.add(src.partner_id.email.strip().lower())
                account = src.account_id
            if partner_id:
                p = self.env['res.partner'].sudo().browse(int(partner_id))
                if p.exists() and p.email:
                    allowed.add(p.email.strip().lower())
            if lead_id:
                lead = self.env['crm.lead'].sudo().browse(int(lead_id))
                if lead.exists():
                    if lead.email_from:
                        allowed.add(lead.email_from.strip().lower())
                    if lead.partner_id and lead.partner_id.email:
                        allowed.add(lead.partner_id.email.strip().lower())
            if to not in allowed:
                raise UserError(_("Destinatario %s fuori dal record linkato (ammessi: %s).")
                                % (to, ', '.join(sorted(allowed)) or 'nessuno'))

        # 3. account mittente + responsible_user_id mappato
        if not account:
            raise UserError(_("Account mittente non risolto (manca sourceMessageId)."))
        if not account.responsible_user_id:
            raise UserError(_("Account %s senza responsible_user_id mappato.") % account.name)

        # 4. delega al SEND CORE condiviso (kill-switch, ir.mail_server, build/send, audit).
        return self._console_outbound(account, to, subject, body,
                                      int(src_id) if src_id else False, 'send',
                                      operator=operator, attachments=payload.get('attachments'),
                                      material_ids=payload.get('materialIds'),
                                      cc=payload.get('cc'), bcc=payload.get('bcc'))

    # ── Allegati: SOLO upload nuovi dal composer. ANTI-EXFILTRATION. ──
    _MAX_ATTACHMENTS = 10
    _MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10MB/file

    def _console_attachments(self, attachments, action):
        """Crea ir.attachment FRESCHI dagli upload del composer ({filename, content(b64), mimetype}).
        ANTI-EXFILTRATION: rifiuta qualsiasi riferimento a ir.attachment esistenti (id/res_id/...):
        non si deve poter allegare per id un documento interno e spedirlo fuori. Ritorna recordset."""
        import base64
        Att = self.env['ir.attachment'].sudo()
        out = Att.browse()
        if not attachments:
            return out
        if len(attachments) > self._MAX_ATTACHMENTS:
            raise UserError(_("Troppi allegati (max %s).") % self._MAX_ATTACHMENTS)
        for a in attachments:
            if not isinstance(a, dict):
                raise UserError(_("Allegato non valido."))
            if any(k in a for k in ('id', 'attachment_id', 'res_id', 'res_model')):
                raise UserError(_("Riferimenti ad allegati esistenti non ammessi (solo upload nuovi)."))
            fname = (a.get('filename') or '').strip()
            content = a.get('content')
            if not fname or not content:
                raise UserError(_("Allegato senza nome o contenuto."))
            try:
                raw = base64.b64decode(content, validate=True)
            except Exception:
                raise UserError(_("Allegato %s: base64 non valido.") % fname)
            if len(raw) > self._MAX_ATTACHMENT_BYTES:
                raise UserError(_("Allegato %s troppo grande (max 10MB).") % fname)
            out |= Att.create({
                'name': fname, 'datas': content,
                'mimetype': a.get('mimetype') or 'application/octet-stream',
                'res_model': 'casafolino.mail.outbox', 'res_id': 0,  # scoped al path console
                'description': 'console %s upload' % action,
            })
        return out

    # ── SEND CORE — UNICO, security-critical. Usato da console_send E console_reply (no fork). ──
    def _console_outbound(self, account, to, subject, body, source_id, action,
                          in_reply_to=None, references=None, parent_msg=None, guards=True,
                          operator=None, attachments=None, material_ids=None, cc=None, bcc=None):
        """Invio centralizzato. kill-switch CONDIVISO casafolino.console_send_enabled:
        False → bozza outbox (state='draft', nessun invio); True → invio reale via ir.mail_server
        (mai smtplib raw, mai stato 'queued'). attachments = upload nuovi; material_ids = libreria
        curata; cc/bcc = recipienti aggiuntivi (anti-exfiltration mantenuto)."""
        enabled = self.env['ir.config_parameter'].sudo().get_param('casafolino.console_send_enabled', 'False')
        live = str(enabled).strip().lower() in ('true', '1', 'yes')
        # upload nuovi + libreria curata (entrambi → ir.attachment freschi, mai ref per id arbitrario)
        att_recs = self._console_attachments(attachments, action) | self._console_material_attachments(material_ids)
        cc_list = self._console_emails(cc)
        bcc_list = self._console_emails(bcc)

        common = {
            'account_id': account.id,
            'user_id': account.responsible_user_id.id,
            'to_emails': to,
            'cc_emails': ', '.join(cc_list),
            'bcc_emails': ', '.join(bcc_list),
            'subject': subject,
            'body_html': body,
            'source_message_id': source_id or False,
            'in_reply_to': in_reply_to or '',
            'references': references or '',
        }
        parent_id = parent_msg.id if parent_msg else None

        if not live:
            draft = self.env['casafolino.mail.outbox'].sudo().create(dict(common, state='draft'))
            if att_recs:
                draft.write({'attachment_ids': [(6, 0, att_recs.ids)]})
                att_recs.write({'res_id': draft.id})
            self._console_audit_outbound(draft.id, '%s:draft' % action, to, account, None, parent_id, operator)
            return {'ok': True, 'phase': 'A', 'draft_id': draft.id, 'account': account.name,
                    'state': 'draft', 'to': to, 'parent_msg_id': parent_id, 'in_reply_to': in_reply_to,
                    'attachments': len(att_recs)}

        # S4 SPONDE: cap giornaliero + dedup + burst PRIMA dell'invio reale.
        # Bloccato → ricade su bozza (state='draft', nessun invio) + audit del blocco.
        if guards:
            block = self._console_send_guard(account, to, body)
            if block:
                draft = self.env['casafolino.mail.outbox'].sudo().create(dict(common, state='draft'))
                self._console_audit_outbound(draft.id, '%s:%s' % (action, block), to, account, None, parent_id, operator)
                _logger.warning("[console guard] %s bloccato per %s → %s (bozza %s)", action, to, block, draft.id)
                return {'ok': False, 'blocked': block, 'phase': 'A', 'draft_id': draft.id,
                        'account': account.name, 'state': 'draft', 'to': to, 'parent_msg_id': parent_id}

        # LIVE via ir.mail_server (acc.1→id1, acc.2→id2)
        server = self.env['ir.mail_server'].sudo().search(
            [('smtp_user', '=', account.email_address)], limit=1)
        if not server:
            raise UserError(_("Nessun ir.mail_server mappato per %s.") % account.email_address)
        import uuid as _uuid
        message_id = '<%s@casafolino.com>' % _uuid.uuid4().hex[:20]
        IMS = self.env['ir.mail_server'].sudo()
        headers = {'In-Reply-To': in_reply_to} if in_reply_to else None
        import base64
        # Odoo 18 build_email itera (fname, fcontent, mime) → 3-tuple obbligatoria (la docstring
        # dice "pairs" ma il codice no). Bug latente dal Brief 3, emerso col primo invio LIVE+allegati.
        att_tuples = [(a.name, base64.b64decode(a.datas), a.mimetype or 'application/octet-stream')
                      for a in att_recs]
        message = IMS.build_email(
            email_from=account.email_address, email_to=[to], subject=subject,
            body=body or '', subtype='html', message_id=message_id,
            email_cc=cc_list or None, email_bcc=bcc_list or None,
            references=references or False, headers=headers,
            attachments=att_tuples or None,
        )
        IMS.send_email(message, mail_server_id=server.id)
        rec = self.env['casafolino.mail.outbox'].sudo().create(
            dict(common, state='sent', sent_at=fields.Datetime.now(), message_id_rfc=message_id))
        if att_recs:
            rec.write({'attachment_ids': [(6, 0, att_recs.ids)]})
            att_recs.write({'res_id': rec.id})
        # thread-link dell'outbound nel thread originale (parent_id + thread)
        if parent_msg:
            try:
                self.env['casafolino.mail.message'].sudo().create({
                    'account_id': account.id, 'message_id_rfc': message_id, 'direction': 'outbound',
                    'sender_email': account.email_address, 'sender_name': account.name,
                    'recipient_emails': to, 'subject': subject, 'email_date': fields.Datetime.now(),
                    'body_html': body, 'body_downloaded': True, 'state': 'keep', 'fetch_state': 'done',
                    'is_read': True, 'reply_to_message_id': parent_msg.id,
                    'thread_id': parent_msg.thread_id.id if parent_msg.thread_id else False,
                    'partner_id': parent_msg.partner_id.id if parent_msg.partner_id else False,
                })
            except Exception as e:
                _logger.warning("[console_reply] outbound thread-link error: %s", e)
        self._console_audit_outbound(rec.id, '%s:sent' % action, to, account, server.id, parent_id, operator)
        return {'ok': True, 'phase': 'B', 'outbox_id': rec.id, 'account': account.name,
                'state': 'sent', 'to': to, 'server_id': server.id, 'mail_server': server.name,
                'parent_msg_id': parent_id, 'message_id': message_id}

    @api.model
    def console_reply(self, payload):
        """Gateway REPLY in-thread. Destinatario = MITTENTE del messaggio originale (non free-form),
        threading via In-Reply-To/References = message_id originale + reply_to_message_id (parent).
        Delega al send core _console_outbound (kill-switch condiviso, ir.mail_server).
        payload: {messageId | messageIdRfc, body, subject?, to?(validato == mittente)}"""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api può usare console_reply."))
        body = payload.get('body') or ''
        operator = self._resolve_operator(payload.get('operator_uid'))  # S5 attribution
        msg_id = payload.get('messageId')
        msg_rfc = payload.get('messageIdRfc')
        if msg_id:
            orig = self.sudo().browse(int(msg_id))
        elif msg_rfc:
            orig = self.sudo().search([('message_id_rfc', '=', msg_rfc)], limit=1)
        else:
            raise UserError(_("messageId o messageIdRfc richiesto."))
        if not orig or not orig.exists():
            raise UserError(_("Messaggio originale inesistente."))
        # destinatario = mittente originale (NON free-form)
        sender = (orig.sender_email or '').strip().lower()
        if not sender or '@' not in sender:
            raise UserError(_("Messaggio originale senza email mittente valida."))
        to_req = (payload.get('to') or '').strip().lower()
        if to_req and to_req != sender:
            raise UserError(_("Reply: destinatario %s diverso dal mittente originale %s.") % (to_req, sender))
        # account dalla casella del messaggio originale
        account = orig.account_id
        if not account:
            raise UserError(_("Account non risolto dal messaggio originale."))
        if not account.responsible_user_id:
            raise UserError(_("Account %s senza responsible_user_id mappato.") % account.name)
        subject = payload.get('subject') or ('Re: %s' % (orig.subject or ''))
        ref = orig.message_id_rfc or None
        return self._console_outbound(account, sender, subject, body, orig.id, 'reply',
                                      in_reply_to=ref, references=ref, parent_msg=orig,
                                      operator=operator, attachments=payload.get('attachments'),
                                      material_ids=payload.get('materialIds'),
                                      cc=payload.get('cc'), bcc=payload.get('bcc'))

    def _console_audit_outbound(self, outbox_id, action, to, account, server_id, parent_msg_id=None,
                                operator=None):
        # S5: l'operatore umano (attribution) è separato da user_id = console_api (service-user).
        meta = 'to=%s;account=%s' % (to, account.name)
        if server_id:
            meta += ';server_id=%s' % server_id
        if parent_msg_id:
            meta += ';parent_msg_id=%s' % parent_msg_id
        if operator:
            meta += ';operator=%s' % operator.login
        self.env['casafolino.console.audit'].sudo().create({
            'user_id': self.env.user.id, 'login': self.env.user.login,
            'model': 'casafolino.mail.outbox', 'res_ids': str([outbox_id]),
            'action': action, 'fields_touched': meta[:255],
            'operator_uid': operator.id if operator else False,
            'operator_login': operator.login if operator else False,
        })

    # ── S4 sponde: cap giornaliero / dedup / burst ──────────────────────────
    @staticmethod
    def _norm_body(body):
        import re
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body or '')).strip().lower()

    def _console_send_guard(self, account, to, body):
        """Ritorna None se OK, altrimenti il motivo blocco: cap_blocked/dedup_blocked/burst_blocked.
        Soglie da ir.config_parameter (0 = controllo disattivato)."""
        from datetime import timedelta
        ICP = self.env['ir.config_parameter'].sudo()
        Audit = self.env['casafolino.console.audit'].sudo()
        Outbox = self.env['casafolino.mail.outbox'].sudo()
        now = fields.Datetime.now()

        # CAP giornaliero: invii reali odierni (send:sent + reply:sent) — circuit breaker.
        cap = int(ICP.get_param('casafolino.console_send_cap_daily', '40') or 0)
        if cap > 0:
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            sent_today = Audit.search_count([
                ('action', 'in', ['send:sent', 'reply:sent']),
                ('create_date', '>=', day_start),
            ])
            if sent_today >= cap:
                return 'cap_blocked'

        # DEDUP: stesso destinatario + body normalizzato entro la finestra.
        dedup_min = int(ICP.get_param('casafolino.console_send_dedup_minutes', '30') or 0)
        if dedup_min > 0 and to:
            target = self._norm_body(body)
            recent = Outbox.search([
                ('to_emails', '=', to), ('state', '=', 'sent'),
                ('sent_at', '>=', now - timedelta(minutes=dedup_min)),
            ])
            if any(self._norm_body(r.body_html) == target for r in recent):
                return 'dedup_blocked'

        # BURST: N invii/ora allo stesso destinatario.
        burst = int(ICP.get_param('casafolino.console_send_burst_per_hour', '3') or 0)
        if burst > 0 and to:
            cnt = Outbox.search_count([
                ('to_emails', '=', to), ('state', '=', 'sent'),
                ('sent_at', '>=', now - timedelta(hours=1)),
            ])
            if cnt >= burst:
                return 'burst_blocked'
        return None

    # ── S4 monitoring: digest giornaliero dall'audit ────────────────────────
    @api.model
    def _cron_console_send_digest(self):
        """Digest invii del giorno dall'audit, recapitato ad antonio@ via _console_outbound
        (stesso path vetato; guards off → il digest non consuma il cap)."""
        from collections import Counter
        ICP = self.env['ir.config_parameter'].sudo()
        now = fields.Datetime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        rows = self.env['casafolino.console.audit'].sudo().search([('create_date', '>=', day_start)])
        by_action = Counter(r.action for r in rows)
        sent = by_action.get('send:sent', 0) + by_action.get('reply:sent', 0)
        blocks = sum(v for k, v in by_action.items() if 'blocked' in (k or ''))
        cap = ICP.get_param('casafolino.console_send_cap_daily', '40')
        # S5 — breakdown invii reali per operatore umano (attribution).
        by_operator = Counter(
            (r.operator_login or '(nessun operatore)')
            for r in rows if r.action in ('send:sent', 'reply:sent')
        )
        _logger.info("[console digest] %s: %s invii reali (cap %s), %s blocchi, operatori=%s",
                     day_start.date(), sent, cap, blocks, dict(by_operator))

        body = '<h3>CasaFolino Console — digest %s</h3>' % day_start.date()
        body += '<p>Invii reali (send+reply): <b>%s</b> / cap %s</p>' % (sent, cap)
        body += '<p>Blocchi totali: <b>%s</b></p>' % blocks
        body += '<p><b>Per operatore (invii reali):</b></p><ul>'
        for op in sorted(by_operator):
            body += '<li>%s: %s</li>' % (op, by_operator[op])
        body += '</ul><p><b>Per azione:</b></p><ul>'
        for k in sorted(by_action):
            body += '<li>%s: %s</li>' % (k, by_action[k])
        body += '</ul>'

        acc1 = self.env['casafolino.mail.account'].sudo().browse(1)
        if acc1.exists() and acc1.responsible_user_id:
            try:
                self.sudo()._console_outbound(
                    acc1, 'antonio@casafolino.com', 'Console digest %s' % day_start.date(),
                    body, False, 'digest', guards=False)
            except Exception as e:
                _logger.warning("[console digest] invio fallito: %s", e)
        return {'date': str(day_start.date()), 'sent': sent, 'blocks': blocks, 'cap': cap}


class CrmLeadConsoleAudit(models.Model):
    """crm.lead: console_api scrive via ACL diretta scoped → qui logghiamo l'audit."""
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.su and _is_console(self.env):
            _audit(self.env, 'crm.lead', records.ids, 'create')
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.su and self.ids and _is_console(self.env):
            _audit(self.env, 'crm.lead', self.ids, 'write', set(vals.keys()))
        return res


class ResPartnerConsoleAudit(models.Model):
    """res.partner: idem crm.lead."""
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.su and _is_console(self.env):
            _audit(self.env, 'res.partner', records.ids, 'create')
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.su and self.ids and _is_console(self.env):
            _audit(self.env, 'res.partner', self.ids, 'write', set(vals.keys()))
        return res


class CasafolinoMailOutboxDraft(models.Model):
    """Aggiunge lo stato 'draft' all'outbox: il cron _cron_process_outbox invia solo
    'queued' → una bozza creata dal gateway (Phase A) NON viene mai inviata."""
    _inherit = 'casafolino.mail.outbox'

    state = fields.Selection(
        selection_add=[('draft', 'Bozza (console)')],
        ondelete={'draft': 'set default'},
    )
