from odoo import models, fields, api


class CrmLeadMailHub(models.Model):
    _inherit = 'crm.lead'

    lead_message_ids = fields.One2many(
        'casafolino.mail.message', 'lead_id', string='Email collegate')

    def _compute_cf_email_count(self):
        """Override: conta email da casafolino.mail.message (Mail Hub)."""
        HubMsg = self.env['casafolino.mail.message']
        for lead in self:
            lead.cf_email_count = HubMsg.search_count([
                ('lead_id', '=', lead.id),
            ])
