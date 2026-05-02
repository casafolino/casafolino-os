from odoo import api, models


class MailingTrace(models.Model):
    _inherit = 'mailing.trace'

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('trace_status', 'open_datetime', 'links_click_datetime')):
            keys = set()
            for t in self:
                if t.model and t.res_id:
                    keys.add((t.model, t.res_id))
            if keys:
                self.env['casafolino.mail.engagement']._rebuild_cache_partial(keys)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        keys = set()
        for t in records:
            if t.model and t.res_id:
                keys.add((t.model, t.res_id))
        if keys:
            self.env['casafolino.mail.engagement']._rebuild_cache_partial(keys)
        return records
