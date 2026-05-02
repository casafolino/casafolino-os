from odoo import api, fields, models


class CasafolinoMailMessage(models.Model):
    _inherit = 'casafolino.mail.message'

    mail_tracking_status = fields.Selection([
        ('none', 'Nessuno'),
        ('sent', 'Inviata'),
        ('open', 'Aperta'),
        ('reply', 'Risposta'),
        ('bounce', 'Bounce'),
    ], string='Tracking', compute='_compute_mail_tracking_status', store=False)

    mail_tracking_open_date = fields.Datetime(
        'Data Apertura', compute='_compute_mail_tracking_status', store=False)

    @api.depends('direction', 'partner_id')
    def _compute_mail_tracking_status(self):
        for msg in self:
            msg.mail_tracking_status = 'none'
            msg.mail_tracking_open_date = False
            if msg.direction != 'outbound' or not msg.partner_id:
                continue
            trace = self.env['mailing.trace'].search([
                ('model', '=', 'res.partner'),
                ('res_id', '=', msg.partner_id.id),
                ('email', '=ilike', msg.partner_id.email or ''),
            ], order='create_date desc', limit=1)
            if trace:
                msg.mail_tracking_status = trace.trace_status if trace.trace_status in (
                    'sent', 'open', 'reply', 'bounce') else 'sent'
                msg.mail_tracking_open_date = trace.open_datetime
