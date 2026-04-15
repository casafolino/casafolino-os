import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# 1x1 transparent PNG
_PIXEL = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')

_NO_CACHE = [
    ('Content-Type', 'image/png'),
    ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
    ('Pragma', 'no-cache'),
]


class CfMailTrackingController(http.Controller):

    @http.route('/cf/track/open/<string:token>',
                type='http', auth='public', csrf=False)
    def track_open(self, token, **kw):
        try:
            self._record(token, 'opened')
        except Exception as e:
            _logger.warning("track_open error: %s", e)
        return request.make_response(_PIXEL, headers=_NO_CACHE)

    @http.route('/cf/track/click/<string:token>',
                type='http', auth='public', csrf=False)
    def track_click(self, token, url='', **kw):
        from urllib.parse import unquote
        target = unquote(url) if url else '/'
        try:
            self._record(token, 'clicked', url_clicked=target)
        except Exception as e:
            _logger.warning("track_click error: %s", e)
        return request.redirect(target, code=302)

    @http.route('/cf/track/download/<string:token>/<int:attachment_id>',
                type='http', auth='public', csrf=False)
    def track_download(self, token, attachment_id, **kw):
        att = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not att.exists() or not att.datas:
            return request.not_found()
        try:
            self._record(token, 'downloaded', attachment_name=att.name)
        except Exception as e:
            _logger.warning("track_download error: %s", e)
        content = base64.b64decode(att.datas)
        return request.make_response(content, headers=[
            ('Content-Type', att.mimetype or 'application/octet-stream'),
            ('Content-Disposition', 'attachment; filename="%s"' % att.name),
        ])

    def _record(self, token, event_type, url_clicked='', attachment_name=''):
        """Record tracking event. All errors caught by caller."""
        if not token:
            return
        Tracking = request.env['casafolino.mail.tracking'].sudo()
        Msg = request.env['casafolino.mail.message'].sudo()

        msg = Msg.search([('tracking_token', '=', token)], limit=1)
        if not msg:
            _logger.info("Tracking: no message for token %s", token[:20])
            return

        ip = request.httprequest.remote_addr or ''
        ua = (request.httprequest.headers.get('User-Agent') or '')[:500]

        # Skip duplicate opens from same IP within 5 min
        if event_type == 'opened':
            from datetime import timedelta
            from odoo import fields as f
            recent = Tracking.search([
                ('tracking_token', '=', token),
                ('event_type', '=', 'opened'),
                ('ip_address', '=', ip),
            ], order='event_date desc', limit=1)
            if recent and recent.event_date and (f.Datetime.now() - recent.event_date) < timedelta(minutes=5):
                return

        # Detect forward (different IP)
        actual = event_type
        if event_type == 'opened':
            prev = Tracking.search([
                ('tracking_token', '=', token),
                ('event_type', 'in', ['opened', 'forwarded']),
            ], limit=1)
            if prev and prev.ip_address and prev.ip_address != ip:
                actual = 'forwarded'

        Tracking.create({
            'message_id': msg.id,
            'tracking_token': token,
            'event_type': actual,
            'ip_address': ip,
            'user_agent': ua,
            'url_clicked': (url_clicked or '')[:500],
            'attachment_name': (attachment_name or '')[:200],
            'partner_id': msg.partner_id.id if msg.partner_id else False,
            'lead_id': msg.lead_id.id if msg.lead_id else False,
            'account_id': msg.account_id.id if msg.account_id else False,
        })

        # Notify sender
        if msg.account_id and msg.account_id.responsible_user_id:
            user = msg.account_id.responsible_user_id
            pname = msg.partner_id.name if msg.partner_id else (msg.recipient_emails or 'Qualcuno')
            subj = msg.subject or ''
            titles = {'opened': 'Email aperta', 'forwarded': 'Possibile inoltro',
                      'clicked': 'Link cliccato', 'downloaded': 'Allegato scaricato'}
            msgs = {
                'opened': '%s ha aperto "%s"' % (pname, subj),
                'forwarded': '%s potrebbe aver inoltrato "%s"' % (pname, subj),
                'clicked': '%s ha cliccato un link in "%s"' % (pname, subj),
                'downloaded': '%s ha scaricato "%s" da "%s"' % (pname, attachment_name, subj),
            }
            request.env['bus.bus'].sudo()._sendone(
                user.partner_id, 'mail.simple_notification',
                {'title': titles.get(actual, 'Tracking'), 'message': msgs.get(actual, ''), 'type': 'info'})
