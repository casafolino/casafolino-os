from odoo import models, fields, api
from odoo.osv import expression
from odoo.exceptions import UserError


class CrmLeadMailHub(models.Model):
    _inherit = 'crm.lead'

    lead_message_ids = fields.One2many(
        'casafolino.mail.message', 'lead_id', string='Email collegate')
    cf_mail_history_ids = fields.Many2many(
        'casafolino.mail.message', compute='_compute_cf_mail_history_ids',
        string='Storico email CRM')
    source_email_id = fields.Many2one(
        'casafolino.mail.message', string='Email di origine',
        ondelete='set null', help='Email da cui è stato creato questo lead')
    cf_mail_thread_id = fields.Many2one(
        'casafolino.mail.thread', string='Thread Mail Hub',
        ondelete='set null', index=True)
    cf_auto_created = fields.Boolean('Creato automaticamente', default=False)
    cf_mail_lead_rule_id = fields.Many2one(
        'casafolino.mail.lead.rule', string='Regola auto-link',
        ondelete='set null')

    def _compute_cf_email_count(self):
        """Conta tutto lo storico Mail Hub riconducibile al lead."""
        HubMsg = self.env['casafolino.mail.message']
        for lead in self:
            lead.cf_email_count = HubMsg.search_count(
                lead._casafolino_mail_history_domain()
            )

    def _compute_cf_mail_history_ids(self):
        """Mostra lo storico completo: lead, partner, email origine e indirizzi."""
        HubMsg = self.env['casafolino.mail.message']
        for lead in self:
            lead.cf_mail_history_ids = HubMsg.search(
                lead._casafolino_mail_history_domain(),
                order='email_date desc, id desc',
            )

    def _casafolino_mail_history_domain(self):
        self.ensure_one()
        domains = [[('lead_id', '=', self.id)]]
        if self.source_email_id:
            domains.append([('id', '=', self.source_email_id.id)])
        if self.partner_id:
            domains.append([('partner_id', '=', self.partner_id.id)])

        emails = []
        for value in [self.email_from, self.partner_id.email if self.partner_id else False]:
            if value:
                emails.append(value.strip().lower())
        for email in sorted(set(emails)):
            domains.append([
                '|', '|',
                ('sender_email', '=ilike', email),
                ('recipient_emails', 'ilike', email),
                ('cc_emails', 'ilike', email),
            ])
        return expression.OR(domains) if domains else [('id', '=', 0)]

    def action_view_partner_emails(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mail — %s' % (self.display_name or self.name),
            'res_model': 'casafolino.mail.message',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': self._casafolino_mail_history_domain(),
            'context': {
                'default_lead_id': self.id,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
            },
        }

    def action_import_email_history(self):
        """Importa storico email per il partner di questo lead."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError("Questo lead non ha un contatto associato.")
        sync_warning = False
        try:
            self.partner_id.action_sync_full_email_history()
        except UserError as exc:
            sync_warning = str(exc)
        linked = self._casafolino_link_history_to_lead()
        if sync_warning:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Storico email non sincronizzato da Gmail',
                    'message': (
                        '%d email gia disponibili su questo lead. '
                        'Sync IMAP saltato: %s'
                    ) % (linked, sync_warning),
                    'type': 'warning',
                    'sticky': True,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Storico email aggiornato',
                'message': '%d email disponibili su questo lead.' % linked,
                'type': 'success',
            },
        }

    def _casafolino_link_history_to_lead(self):
        """Collega al lead le email dello storico senza rubarle ad altri lead."""
        Message = self.env['casafolino.mail.message'].sudo()
        total = 0
        for lead in self:
            messages = Message.search(lead._casafolino_mail_history_domain())
            to_attach = messages.filtered(lambda msg: not msg.lead_id)
            if to_attach:
                to_attach.write({'lead_id': lead.id})
            total += len(messages)
        return total
