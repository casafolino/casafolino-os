from odoo import fields, models


class CfMailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=None):
        # Before super (which unlinks the activity), capture lead refs
        lead_ids = []
        for act in self:
            if act.res_model == 'crm.lead' and act.res_id:
                lead_ids.append(act.res_id)

        res = super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

        if lead_ids:
            leads = self.env['crm.lead'].browse(lead_ids).exists()
            if leads:
                leads.sudo().write({
                    'cf_date_last_contact': fields.Date.context_today(self),
                })

        return res
