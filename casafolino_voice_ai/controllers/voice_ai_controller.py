import json

from odoo import http
from odoo.http import request


class CasaFolinoVoiceAIController(http.Controller):
    def _check_token(self):
        expected = request.env['ir.config_parameter'].sudo().get_param('casafolino_voice_ai.webhook_token')
        if not expected:
            return True
        auth = request.httprequest.headers.get('Authorization', '')
        return auth == 'Bearer %s' % expected

    def _json_body(self):
        raw = request.httprequest.get_data() or b'{}'
        return json.loads(raw.decode('utf-8'))

    @http.route('/voice_ai/health', type='http', auth='public', methods=['GET'], csrf=False)
    def health(self):
        return request.make_json_response({'ok': True, 'service': 'casafolino_voice_ai'})

    @http.route('/voice_ai/openai/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def openai_webhook(self):
        if not self._check_token():
            return request.make_json_response({'error': 'unauthorized'}, status=401)
        payload = self._json_body()
        event_type = payload.get('type')
        data = payload.get('data') or {}

        if event_type == 'realtime.call.incoming':
            call_id = data.get('call_id') or data.get('id')
            phone = data.get('from') or data.get('caller') or ''
            called_number = data.get('to') or data.get('called_number') or ''
            partner = request.env['res.partner'].sudo().search([
                '|', ('phone', '=', phone), ('mobile', '=', phone),
            ], limit=1)
            number = request.env['casafolino.voice.number'].sudo().search([
                ('phone_number', '=', called_number),
                ('active', '=', True),
            ], limit=1)
            route = request.env['casafolino.voice.routing.rule'].sudo().resolve_inbound_route(
                caller_phone=phone,
                called_number=called_number,
            )
            agent = route.agent_id if route and route.action == 'agent' else number.default_agent_id
            if not agent:
                agent = request.env['casafolino.voice.agent'].sudo().search([
                    ('direction', '=', 'inbound'),
                    ('active', '=', True),
                ], limit=1)
            call = request.env['casafolino.voice.call'].sudo().create({
                'direction': 'inbound',
                'state': 'active',
                'external_call_id': call_id,
                'phone': phone,
                'partner_id': partner.id if partner else False,
                'agent_id': agent.id if agent else False,
                'called_number_id': number.id if number else False,
                'routing_rule_id': route.id if route else False,
                'route_action': route.action if route else 'agent',
            })
            return request.make_json_response({
                'ok': True,
                'call_id': call.id,
                'agent': agent.build_realtime_payload() if agent else {},
                'route': route.build_route_payload() if route else {},
            })

        return request.make_json_response({'ok': True, 'ignored': event_type})

    @http.route('/voice_ai/outbound/enqueue', type='http', auth='public', methods=['POST'], csrf=False)
    def outbound_enqueue(self):
        if not self._check_token():
            return request.make_json_response({'error': 'unauthorized'}, status=401)
        payload = self._json_body()
        partner_id = payload.get('partner_id')
        phone = payload.get('phone')
        reason = payload.get('reason') or 'Follow-up cliente'
        if not partner_id or not phone:
            return request.make_json_response({'error': 'partner_id and phone are required'}, status=400)
        job = request.env['casafolino.voice.outbound.queue'].sudo().create({
            'partner_id': partner_id,
            'phone': phone,
            'reason': reason,
            'language': payload.get('language') or request.env['res.partner'].sudo().browse(partner_id).voice_ai_language or 'auto',
        })
        job.action_check_ready()
        return request.make_json_response({'ok': True, 'job_id': job.id, 'state': job.state})

    @http.route('/voice_ai/outbound/next', type='http', auth='public', methods=['GET'], csrf=False)
    def outbound_next(self):
        if not self._check_token():
            return request.make_json_response({'error': 'unauthorized'}, status=401)
        payload = request.env['casafolino.voice.outbound.queue'].sudo().get_next_ready_job_payload()
        return request.make_json_response({'ok': True, 'job': payload})

    @http.route('/voice_ai/call/outcome', type='http', auth='public', methods=['POST'], csrf=False)
    def call_outcome(self):
        if not self._check_token():
            return request.make_json_response({'error': 'unauthorized'}, status=401)
        payload = self._json_body()
        call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
        if not call.exists():
            return request.make_json_response({'error': 'call not found'}, status=404)
        call.write({
            'state': payload.get('state') or 'completed',
            'outcome': payload.get('outcome') or 'other',
            'summary': payload.get('summary'),
            'next_action': payload.get('next_action'),
            'transcript': payload.get('transcript'),
        })
        if call.outbound_queue_id:
            call.outbound_queue_id.write({'state': 'done' if call.state == 'completed' else call.state})
        return request.make_json_response({'ok': True})
