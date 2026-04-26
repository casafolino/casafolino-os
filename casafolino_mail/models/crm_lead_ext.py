from odoo import models, fields, api
from odoo.exceptions import UserError


class CrmLeadMailHub(models.Model):
    _inherit = 'crm.lead'

    lead_message_ids = fields.One2many(
        'casafolino.mail.message', 'lead_id', string='Email collegate')
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
        """Override: conta email da casafolino.mail.message (Mail Hub)."""
        HubMsg = self.env['casafolino.mail.message']
        for lead in self:
            lead.cf_email_count = HubMsg.search_count([
                ('lead_id', '=', lead.id),
            ])

    def action_import_email_history(self):
        """Importa storico email per il partner di questo lead."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError("Questo lead non ha un contatto associato.")
        return self.partner_id.action_sync_full_email_history()
