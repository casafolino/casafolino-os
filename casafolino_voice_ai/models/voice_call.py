from odoo import api, fields, models


class CasaFolinoVoiceCall(models.Model):
    _name = 'casafolino.voice.call'
    _description = 'CasaFolino Voice AI Call'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'started_at desc, id desc'

    name = fields.Char(default='New', copy=False, readonly=True)
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], required=True, default='inbound', tracking=True)
    state = fields.Selection([
        ('new', 'New'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('transferred', 'Transferred'),
    ], default='new', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    phone = fields.Char(tracking=True)
    agent_id = fields.Many2one('casafolino.voice.agent', tracking=True)
    routing_rule_id = fields.Many2one('casafolino.voice.routing.rule', string='Routing Rule')
    called_number_id = fields.Many2one('casafolino.voice.number', string='Called Number')
    route_action = fields.Selection([
        ('agent', 'AI Agent'),
        ('ivr', 'IVR Menu'),
        ('queue', 'Queue'),
        ('voicemail', 'Voicemail'),
        ('external', 'External Number'),
        ('callback', 'Callback Request'),
        ('hangup', 'Hangup'),
    ])
    outbound_queue_id = fields.Many2one('casafolino.voice.outbound.queue', string='Outbound Job')
    external_call_id = fields.Char(index=True, copy=False)
    started_at = fields.Datetime(default=fields.Datetime.now, tracking=True)
    ended_at = fields.Datetime(tracking=True)
    duration_seconds = fields.Integer()
    outcome = fields.Selection([
        ('resolved', 'Resolved'),
        ('callback_requested', 'Callback Requested'),
        ('transferred', 'Transferred'),
        ('not_available', 'Not Available'),
        ('opt_out', 'Opt-out'),
        ('failed', 'Failed'),
        ('other', 'Other'),
    ], tracking=True)
    summary = fields.Text()
    next_action = fields.Text()
    transcript = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = sequence.next_by_code('casafolino.voice.call') or 'VOICE-CALL'
        return super().create(vals_list)

    def action_mark_completed(self):
        for call in self:
            call.write({
                'state': 'completed',
                'ended_at': fields.Datetime.now(),
            })

    def action_transfer(self):
        for call in self:
            call.write({
                'state': 'transferred',
                'outcome': 'transferred',
                'ended_at': fields.Datetime.now(),
            })

    def action_create_callback_activity(self):
        for call in self:
            if not call.partner_id:
                continue
            call.partner_id.activity_schedule(
                'mail.mail_activity_data_call',
                summary='Richiamare cliente da chiamata AI',
                note=call.summary or call.next_action or 'Richiamata richiesta dal centralino AI.',
            )

    @api.model
    def cron_send_daily_recap(self):
        from datetime import datetime, time
        today_start = datetime.combine(fields.Date.context_today(self), time.min)
        calls = self.search([('started_at', '>=', today_start)])
        
        if not calls:
            subject = "Recap Giornaliero Centralino AI CasaFolino - Nessuna Chiamata"
            body = "<p>Ciao Antonio,<br><br>Oggi non ci sono state chiamate registrate nel centralino vocale AI.</p>"
        else:
            subject = "Recap Giornaliero Centralino AI CasaFolino - %s Chiamate" % len(calls)
            body = """
            <h2>Recap Giornaliero Centralino Vocale AI Viola</h2>
            <p>Ciao Antonio, ecco il riepilogo delle chiamate gestite oggi da Viola:</p>
            <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th>Codice Chiamata</th>
                    <th>Ora Inizio</th>
                    <th>Cliente / Telefono</th>
                    <th>Direzione</th>
                    <th>Esito</th>
                    <th>Riepilogo / Prossima Azione</th>
                </tr>
            """
            for call in calls:
                customer = call.partner_id.display_name if call.partner_id else call.phone or 'Sconosciuto'
                dir_label = "Entrata (Inbound)" if call.direction == 'inbound' else "Uscita (Outbound)"
                outcome_label = dict(call._fields['outcome'].selection).get(call.outcome, 'Altro') if call.outcome else 'Nessuno'
                body += """
                <tr>
                    <td><b>%s</b></td>
                    <td>%s</td>
                    <td>%s</td>
                    <td>%s</td>
                    <td><span style="padding: 4px; background-color: %s; color: white; border-radius: 4px;">%s</span></td>
                    <td>%s<br><small style="color: #666;">Prossima azione: %s</small></td>
                </tr>
                """ % (
                    call.name,
                    fields.Datetime.context_timestamp(self, call.started_at).strftime('%H:%M:%S'),
                    customer,
                    dir_label,
                    "#28a745" if call.outcome == 'resolved' else "#ffc107" if call.outcome == 'callback_requested' else "#17a2b8" if call.outcome == 'transferred' else "#6c757d",
                    outcome_label,
                    call.summary or 'Nessun riepilogo',
                    call.next_action or 'Nessuna'
                )
            body += "</table><br><p>I dettagli completi sono disponibili nel pannello Odoo Voice AI.</p>"
            
        mail_values = {
            'subject': subject,
            'body_html': body,
            'email_to': 'antonio@casafolino.com',
        }
        self.env['mail.mail'].sudo().create(mail_values).send()
        return True
