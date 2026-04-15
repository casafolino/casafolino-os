import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailTracking(models.Model):
    _name = 'casafolino.mail.tracking'
    _description = 'Email Tracking Events'
    _order = 'event_date desc'

    message_id = fields.Many2one(
        'casafolino.mail.message', string='Email', ondelete='cascade', index=True)
    tracking_token = fields.Char('Token', index=True)
    event_type = fields.Selection([
        ('sent', 'Inviata'),
        ('opened', 'Aperta'),
        ('clicked', 'Link cliccato'),
        ('downloaded', 'Allegato scaricato'),
        ('forwarded', 'Possibile inoltro'),
    ], string='Evento', required=True)
    event_date = fields.Datetime('Data', default=fields.Datetime.now, index=True)
    ip_address = fields.Char('IP')
    user_agent = fields.Char('User Agent')
    country = fields.Char('Paese')
    city = fields.Char('Citta')
    url_clicked = fields.Char('URL cliccato')
    attachment_name = fields.Char('Allegato scaricato')
    partner_id = fields.Many2one('res.partner', string='Partner')
    lead_id = fields.Many2one('crm.lead', string='Trattativa')
    account_id = fields.Many2one('casafolino.mail.account', string='Account')

    @api.model
    def get_tracking_events(self, *args, **kw):
        """Ritorna eventi di tracking per un message_id."""
        message_id = kw.get('message_id')
        if not message_id:
            return []
        events = self.search([('message_id', '=', int(message_id))], order='event_date desc')
        result = []
        for ev in events:
            result.append({
                'id': ev.id,
                'event_type': ev.event_type,
                'event_date': ev.event_date.strftime('%d/%m/%Y %H:%M') if ev.event_date else '',
                'ip_address': ev.ip_address or '',
                'country': ev.country or '',
                'city': ev.city or '',
                'url_clicked': ev.url_clicked or '',
                'attachment_name': ev.attachment_name or '',
            })
        return result

    @api.model
    def get_tracking_summary(self, *args, **kw):
        """Ritorna conteggio eventi per un message_id."""
        message_id = kw.get('message_id')
        if not message_id:
            return {}
        events = self.search([('message_id', '=', int(message_id))])
        summary = {'opens': 0, 'clicks': 0, 'downloads': 0, 'forwards': 0}
        for ev in events:
            if ev.event_type == 'opened':
                summary['opens'] += 1
            elif ev.event_type == 'clicked':
                summary['clicks'] += 1
            elif ev.event_type == 'downloaded':
                summary['downloads'] += 1
            elif ev.event_type == 'forwarded':
                summary['forwards'] += 1
        return summary
