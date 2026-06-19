from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

CONSOLE_GROUP = 'casafolino_console_access.group_console_api'


def _is_console(env):
    """True se l'utente corrente è il service-user console (portal scoped)."""
    return env.user.has_group(CONSOLE_GROUP)


def _audit(env, model, res_ids, action, fields_touched=None):
    env['casafolino.console.audit'].sudo().create({
        'user_id': env.user.id,
        'login': env.user.login,
        'model': model,
        'res_ids': str(res_ids)[:255],
        'action': action,
        'fields_touched': (','.join(sorted(fields_touched))[:255]) if fields_touched else False,
    })


class CasafolinoMailMessageGateway(models.Model):
    """Gateway triage: l'unico modo per console_api di scrivere su una mail.
    Scrive SOLO il campo `state` (mai body/contenuto), valida lo stato, logga l'audit.
    L'ACL di console_api su casafolino.mail.message è READ-ONLY → niente write diretta."""
    _inherit = 'casafolino.mail.message'

    # stati triage ammessi (allineati alla selection del modello)
    _CONSOLE_TRIAGE_STATES = ('new', 'review', 'keep', 'auto_keep', 'discard', 'auto_discard')

    def console_triage(self, state):
        """Chiamato via JSON-RPC dall'utente portal: browse(ids).console_triage(state).
        Scrive solo state via sudo. Mai un write(model, vals) generico."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console può usare console_triage."))
        if state not in self._CONSOLE_TRIAGE_STATES:
            raise UserError(_("Stato triage non valido: %s") % state)
        if not self.ids:
            return {'ok': False, 'error': 'no records'}
        # self è già filtrato dalle record-rule di lettura dell'utente
        ids = self.ids
        self.sudo().write({'state': state})  # SOLO state — body invariato
        _audit(self.env, 'casafolino.mail.message', ids, 'triage:%s' % state, {'state'})
        return {'ok': True, 'count': len(ids), 'state': state}

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
        if not to or '@' not in to:
            raise UserError(_("Destinatario non valido."))

        # 1-2. email ammesse dal record linkato + account mittente
        allowed = set()
        account = self.env['casafolino.mail.account']
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

        # 4. kill-switch server-side (default False). Disattivabile all'istante senza deploy.
        enabled = self.env['ir.config_parameter'].sudo().get_param('casafolino.console_send_enabled', 'False')
        live = str(enabled).strip().lower() in ('true', '1', 'yes')

        common = {
            'account_id': account.id,
            'user_id': account.responsible_user_id.id,
            'to_emails': to,
            'subject': subject,
            'body_html': body,
            'source_message_id': int(src_id) if src_id else False,
        }

        if not live:
            # PHASE A: bozza, NESSUN invio (state='draft' → il cron legacy non la tocca).
            draft = self.env['casafolino.mail.outbox'].sudo().create(dict(common, state='draft'))
            self._console_audit_send(draft.id, 'send:draft', to, account, None)
            return {'ok': True, 'phase': 'A', 'draft_id': draft.id,
                    'account': account.name, 'state': 'draft', 'to': to}

        # PHASE B LIVE: invia via ir.mail_server (NO smtplib raw, NO stato 'queued' del cron legacy).
        server = self.env['ir.mail_server'].sudo().search(
            [('smtp_user', '=', account.email_address)], limit=1)
        if not server:
            raise UserError(_("Nessun ir.mail_server mappato per %s.") % account.email_address)
        import uuid as _uuid
        message_id = '<%s@casafolino.com>' % _uuid.uuid4().hex[:20]
        IMS = self.env['ir.mail_server'].sudo()
        message = IMS.build_email(
            email_from=account.email_address,
            email_to=[to],
            subject=subject,
            body=body or '',
            subtype='html',
            message_id=message_id,
        )
        # invio esplicito via QUEL server (acc.1→id1, acc.2→id2)
        IMS.send_email(message, mail_server_id=server.id)
        rec = self.env['casafolino.mail.outbox'].sudo().create(
            dict(common, state='sent', sent_at=fields.Datetime.now(), message_id_rfc=message_id))
        self._console_audit_send(rec.id, 'send:sent', to, account, server.id)
        return {'ok': True, 'phase': 'B', 'outbox_id': rec.id, 'account': account.name,
                'state': 'sent', 'to': to, 'server_id': server.id, 'mail_server': server.name}

    def _console_audit_send(self, outbox_id, action, to, account, server_id):
        self.env['casafolino.console.audit'].sudo().create({
            'user_id': self.env.user.id, 'login': self.env.user.login,
            'model': 'casafolino.mail.outbox', 'res_ids': str([outbox_id]),
            'action': action,
            'fields_touched': ('to=%s;account=%s%s' % (
                to, account.name, (';server=%s' % server_id) if server_id else ''))[:255],
        })


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
