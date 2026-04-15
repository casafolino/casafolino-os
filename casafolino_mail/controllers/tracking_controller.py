import base64
import logging
from urllib.parse import unquote

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# 1x1 transparent PNG pixel
PIXEL = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')


class MailTrackingController(http.Controller):

    def _record_event(self, token, event_type, url_clicked='', attachment_name=''):
        """Record a tracking event and send notification."""
        if not token:
            return
        Tracking = request.env['casafolino.mail.tracking'].sudo()
        Message = request.env['casafolino.mail.message'].sudo()

        msg = Message.search([('tracking_token', '=', token)], limit=1)
        if not msg:
            return

        ip = request.httprequest.remote_addr or ''
        ua = request.httprequest.headers.get('User-Agent', '')

        # Anti-spam: skip duplicate opens from same IP within 5 minutes
        if event_type == 'opened':
            recent = Tracking.search([
                ('tracking_token', '=', token),
                ('event_type', '=', 'opened'),
                ('ip_address', '=', ip),
            ], order='event_date desc', limit=1)
            if recent and recent.event_date:
                from datetime import timedelta
                from odoo import fields as f
                if f.Datetime.now() - recent.event_date < timedelta(minutes=5):
                    return

        # Check for possible forward (different IP/UA from previous opens)
        actual_type = event_type
        if event_type == 'opened':
            prev_opens = Tracking.search([
                ('tracking_token', '=', token),
                ('event_type', 'in', ['opened', 'forwarded']),
            ], limit=1)
            if prev_opens and prev_opens.ip_address and prev_opens.ip_address != ip:
                actual_type = 'forwarded'

        vals = {
            'message_id': msg.id,
            'tracking_token': token,
            'event_type': actual_type,
            'ip_address': ip,
            'user_agent': ua[:500] if ua else '',
            'url_clicked': url_clicked[:500] if url_clicked else '',
            'attachment_name': attachment_name[:200] if attachment_name else '',
            'partner_id': msg.partner_id.id if msg.partner_id else False,
            'lead_id': msg.lead_id.id if msg.lead_id else False,
            'account_id': msg.account_id.id if msg.account_id else False,
        }
        Tracking.create(vals)

        # Send notification to the sender
        try:
            if msg.account_id and msg.account_id.responsible_user_id:
                user = msg.account_id.responsible_user_id
                partner_name = msg.partner_id.name if msg.partner_id else (msg.recipient_emails or '')
                subject = msg.subject or '(senza oggetto)'

                titles = {
                    'opened': 'Email aperta',
                    'forwarded': 'Email inoltrata',
                    'clicked': 'Link cliccato',
                    'downloaded': 'Allegato scaricato',
                }
                messages = {
                    'opened': '%s ha aperto "%s"' % (partner_name, subject),
                    'forwarded': '%s potrebbe aver inoltrato "%s"' % (partner_name, subject),
                    'clicked': '%s ha cliccato un link in "%s"' % (partner_name, subject),
                    'downloaded': '%s ha scaricato "%s" da "%s"' % (partner_name, attachment_name, subject),
                }

                title = titles.get(actual_type, 'Tracking email')
                message = messages.get(actual_type, '')

                request.env['bus.bus']._sendone(
                    user.partner_id, 'mail.simple_notification',
                    {'title': title, 'message': message, 'type': 'info'})
        except Exception as e:
            _logger.warning("Tracking notification error: %s", e)

    @http.route('/mail/track/open/<string:token>',
                type='http', auth='public', csrf=False, methods=['GET'])
    def track_open(self, token, **kw):
        self._record_event(token, 'opened')
        headers = [
            ('Content-Type', 'image/png'),
            ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
            ('Pragma', 'no-cache'),
        ]
        return request.make_response(PIXEL, headers=headers)

    @http.route('/mail/track/click/<string:token>',
                type='http', auth='public', csrf=False, methods=['GET'])
    def track_click(self, token, url='', **kw):
        target_url = unquote(url) if url else '/'
        self._record_event(token, 'clicked', url_clicked=target_url)
        return request.redirect(target_url, code=302)

    @http.route('/mail/track/download/<string:token>/<int:attachment_id>',
                type='http', auth='public', csrf=False, methods=['GET'])
    def track_download(self, token, attachment_id, **kw):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not attachment.exists() or not attachment.datas:
            return request.not_found()
        self._record_event(token, 'downloaded', attachment_name=attachment.name)
        content = base64.b64decode(attachment.datas)
        headers = [
            ('Content-Type', attachment.mimetype or 'application/octet-stream'),
            ('Content-Disposition', 'attachment; filename="%s"' % attachment.name),
        ]
        return request.make_response(content, headers=headers)
