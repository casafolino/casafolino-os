import fnmatch
import re
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CasafolinoMailSenderPolicy(models.Model):
    _name = 'casafolino.mail.sender_policy'
    _description = 'Regola triage mittente'
    _order = 'priority desc, id'

    name = fields.Char('Descrizione', required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer('Priorità', default=50,
        help='Più alto = applicato prima. Range consigliato: 10-100')

    pattern_type = fields.Selection([
        ('email_exact', 'Email esatta'),
        ('domain', 'Dominio'),
        ('regex_subject', 'Regex su oggetto'),
    ], string='Tipo pattern', required=True, default='domain')

    pattern_value = fields.Char('Pattern', required=True,
        help='Es: *@rewe-group.at, *newsletter*, user@example.com')

    action = fields.Selection([
        ('auto_keep', 'Tieni automaticamente'),
        ('auto_discard', 'Scarta automaticamente'),
        ('escalate', 'Escalation (review + importante)'),
        ('review', 'Da valutare'),
    ], string='Azione', required=True, default='review')

    default_owner_id = fields.Many2one('res.users', string='Responsabile default')
    match_ai_category = fields.Selection([
        ('commerciale', 'Commerciale'),
        ('admin', 'Amministrativo'),
        ('fornitore', 'Fornitore'),
        ('newsletter', 'Newsletter'),
        ('interno', 'Interno'),
        ('personale', 'Personale'),
        ('spam', 'Spam'),
    ], string='AI Categoria richiesta',
        help='Se valorizzato, la policy matcha solo se AI ha classificato con questa categoria')

    auto_create_partner = fields.Boolean('Crea contatto automaticamente',
        help='Se attivo, crea res.partner se non esiste match')
    notes = fields.Text('Note')

    @api.model
    def match_sender(self, sender_email, subject='', ai_category=None):
        """Trova la prima policy che matcha sender_email o subject.

        Args:
            sender_email: email mittente (lowercase)
            subject: oggetto email

        Returns:
            recordset: la policy che ha matchato, o empty recordset
        """
        sender_email = (sender_email or '').lower().strip()
        sender_domain = sender_email.split('@')[-1] if '@' in sender_email else ''

        policies = self.sudo().search([('active', '=', True)], order='priority desc, id')

        for policy in policies:
            # Se la policy richiede una ai_category specifica, verifica match
            if policy.match_ai_category:
                if ai_category != policy.match_ai_category:
                    continue

            pattern = (policy.pattern_value or '').lower().strip()

            if policy.pattern_type == 'email_exact':
                if pattern == sender_email:
                    return policy

            elif policy.pattern_type == 'domain':
                # Supporta wildcard: *@rewe-group.at, *newsletter*, rewe-group.at
                if '@' in pattern:
                    # Pattern tipo *@domain.com → matcha sull'email completa
                    if fnmatch.fnmatch(sender_email, pattern):
                        return policy
                else:
                    # Pattern tipo *newsletter* o rewe-group.at → matcha sul dominio
                    if fnmatch.fnmatch(sender_domain, pattern):
                        return policy

            elif policy.pattern_type == 'regex_subject':
                try:
                    if re.search(pattern, subject or '', re.IGNORECASE):
                        return policy
                except re.error:
                    _logger.warning("Invalid regex in sender_policy %s: %s",
                                    policy.id, pattern)

        return self.browse()  # empty recordset

    @api.model
    def _cron_backfill_policies(self):
        """Cron 96: safety-net re-evaluation of new/review inbound messages.

        Re-applies active policies to messages still in new/review that may
        have been imported before the matching policy existed.
        """
        Msg = self.env['casafolino.mail.message'].sudo()
        msgs = Msg.search([
            ('state', 'in', ['new', 'review']),
            ('direction', '=', 'inbound'),
        ], limit=2000)

        updated = 0
        for msg in msgs:
            policy = self.match_sender(
                msg.sender_email, msg.subject or '',
                ai_category=getattr(msg, 'ai_category', None))
            if not policy:
                continue
            # Skip if same policy already applied
            if msg.policy_applied_id.id == policy.id:
                continue

            state_map = {
                'auto_keep': 'auto_keep',
                'auto_discard': 'auto_discard',
                'escalate': 'review',
                'review': 'review',
            }
            new_state = state_map.get(policy.action, 'review')
            vals = {'state': new_state, 'policy_applied_id': policy.id}
            if policy.action == 'escalate':
                vals['is_important'] = True
            msg.write(vals)
            updated += 1

        if updated:
            _logger.info("[sender policy] Cron backfill: updated %d messages", updated)
