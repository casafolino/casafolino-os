from odoo import models, fields, api


class CrmLeadMailHub(models.Model):
    _inherit = 'crm.lead'

    lead_message_ids = fields.One2many(
        'casafolino.mail.message', 'lead_id', string='Email collegate')
    source_email_id = fields.Many2one(
        'casafolino.mail.message', string='Email di origine',
        ondelete='set null', help='Email da cui è stato creato questo lead')

    # F6: Auto-link fields
    cf_mail_thread_id = fields.Many2one('casafolino.mail.thread',
        string='Thread Mail V3', ondelete='set null', index=True)
    cf_auto_created = fields.Boolean('Auto-created F6', default=False)
    cf_mail_lead_rule_id = fields.Many2one('casafolino.mail.lead.rule',
        string='Regola auto-link', ondelete='set null')

    def _compute_cf_email_count(self):
        """Override: conta email da casafolino.mail.message (Mail Hub)."""
        HubMsg = self.env['casafolino.mail.message']
        for lead in self:
            lead.cf_email_count = HubMsg.search_count([
                ('lead_id', '=', lead.id),
            ])

    def action_open_mail_v3_thread(self):
        """Open linked Mail V3 thread."""
        self.ensure_one()
        if not self.cf_mail_thread_id:
            return
        return {
            'type': 'ir.actions.client',
            'tag': 'cf_mail_v3_client',
            'params': {'open_thread_id': self.cf_mail_thread_id.id},
        }
