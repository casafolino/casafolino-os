from odoo import models, fields, api
from odoo.exceptions import UserError


class CrmLeadMailHub(models.Model):
    _inherit = 'crm.lead'

    lead_message_ids = fields.One2many(
        'casafolino.mail.message', 'lead_id', string='Email collegate')
    source_email_id = fields.Many2one(
        'casafolino.mail.message', string='Email di origine',
        ondelete='set null', help='Email da cui è stato creato questo lead')

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
