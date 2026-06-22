import logging

from odoo import api, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager

_logger = logging.getLogger(__name__)


class ResPartnerConsoleSync(models.Model):
    """Brief 21 — sync mail on-demand per contatto: recupera anche le mail PRE-cutoff di un
    indirizzo (la sync schedulata copre solo il post-aprile). Riusa l'ingestion casafolino_mail
    (fetch_address_history), dedup su message_id_rfc. Manager-only + audit."""
    _inherit = 'res.partner'

    @api.model
    def console_sync_partner_mail(self, payload):
        """Fetch IMAP mirato sull'indirizzo del contatto, senza SINCE. payload:
        {partnerId?|email?, operator_uid}. Ritorna quante mail nuove sono state ingerite."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        email = ''
        partner = self.env['res.partner']
        if (payload or {}).get('partnerId'):
            partner = self.env['res.partner'].sudo().browse(int(payload['partnerId']))
            email = (partner.email or '').strip().lower()
        if not email:
            email = ((payload or {}).get('email') or '').strip().lower()
        if not email or '@' not in email:
            raise UserError(_("Contatto senza email valida da sincronizzare."))

        # esegue per ogni casella attiva (il dedup message_id_rfc evita doppioni); l'ingestion
        # collega da sola il partner per email esatta. sudo: serve l'accesso alle credenziali IMAP.
        Account = self.env['casafolino.mail.account'].sudo()
        accounts = Account.search([('active', '=', True)])
        total = 0
        for acc in accounts:
            try:
                total += acc.fetch_address_history(email)
            except Exception as e:
                _logger.warning("[console sync] account %s error: %s", acc.email_address, e)

        _audit(self.env, 'res.partner', [partner.id] if partner else [], 'sync_partner_mail:%d' % total, None, operator)
        return {'ok': True, 'newCount': total, 'email': email,
                'partnerId': partner.id if partner else False}
