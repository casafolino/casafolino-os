import json

from odoo import fields, http
from odoo.http import request


class CasaFolinoVoiceAIController(http.Controller):
    def _check_token(self):
        params = request.env['ir.config_parameter'].sudo()
        require_token = params.get_param('casafolino_voice_ai.require_token', 'False') == 'True'
        expected = params.get_param('casafolino_voice_ai.webhook_token')
        if not require_token:
            return True
        if not expected:
            return False
        auth = request.httprequest.headers.get('Authorization', '')
        return auth == 'Bearer %s' % expected

    def _json_body(self):
        raw = request.httprequest.get_data() or b'{}'
        return json.loads(raw.decode('utf-8'))

    @http.route('/voice_ai/health', type='http', auth='public', methods=['GET'], csrf=False)
    def health(self):
        return request.make_json_response({'ok': True, 'service': 'casafolino_voice_ai'})

    @http.route('/voice_ai/config', type='http', auth='public', methods=['GET'], csrf=False)
    def bridge_config(self):
        if not self._check_token():
            return request.make_json_response({'error': 'unauthorized'}, status=401)
        params = request.env['ir.config_parameter'].sudo()
        return request.make_json_response({
            'ok': True,
            'public_base_url': params.get_param('casafolino_voice_ai.public_base_url'),
            'realtime_model': params.get_param('casafolino_voice_ai.openai_realtime_model') or 'gpt-realtime-2',
            'realtime_voice': params.get_param('casafolino_voice_ai.openai_voice') or 'marin',
            'human_transfer_uri': params.get_param('casafolino_voice_ai.human_transfer_uri'),
            'allow_outbound': params.get_param('casafolino_voice_ai.allow_outbound', 'False') == 'True',
            'has_openai_key': bool(params.get_param('casafolino_voice_ai.openai_api_key')),
            'requires_token': params.get_param('casafolino_voice_ai.require_token', 'False') == 'True',
        })

    def _find_partner(self, payload):
        Partner = request.env['res.partner'].sudo()
        partner_id = payload.get('partner_id')
        if partner_id:
            partner = Partner.browse(partner_id)
            if partner.exists():
                return partner
        phone = payload.get('phone')
        email = payload.get('email')
        name = payload.get('name') or payload.get('customer_name')
        domain = []
        if phone:
            domain = ['|', ('phone', '=', phone), ('mobile', '=', phone)]
        elif email:
            domain = [('email', '=', email)]
        elif name:
            domain = [('name', 'ilike', name)]
        return Partner.search(domain, limit=1) if domain else Partner.browse()

    @http.route('/voice_ai/tool/<string:tool_name>', type='http', auth='public', methods=['POST'], csrf=False)
    def tool_dispatch(self, tool_name):
        if not self._check_token():
            return request.make_json_response({'error': 'unauthorized'}, status=401)
        payload = self._json_body()
        partner = self._find_partner(payload)

        if tool_name == 'lookup_customer':
            if not partner:
                return request.make_json_response({'ok': True, 'customer': None})
            return request.make_json_response({
                'ok': True,
                'customer': {
                    'id': partner.id,
                    'name': partner.display_name,
                    'phone': partner.phone or partner.mobile,
                    'email': partner.email,
                    'language': getattr(partner, 'voice_ai_language', 'auto') or 'auto',
                    'outbound_consent': bool(partner.voice_outbound_consent),
                },
            })

        if tool_name == 'create_callback':
            reason = payload.get('reason') or 'Richiamata richiesta da chiamata AI'
            phone = payload.get('phone')
            if partner:
                partner.activity_schedule(
                    'mail.mail_activity_data_call',
                    summary='Richiamata Voice AI',
                    note='%s\nTelefono: %s\nUrgenza: %s' % (reason, phone or '', payload.get('urgency') or 'normal'),
                )
            call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
            if call.exists():
                call.write({
                    'outcome': 'callback_requested',
                    'next_action': reason,
                    'partner_id': partner.id if partner else call.partner_id.id,
                })
            return request.make_json_response({'ok': True, 'partner_id': partner.id if partner else None})

        if tool_name == 'lookup_knowledge':
            query = payload.get('query') or ''
            category = payload.get('category')
            domain = [('active', '=', True)]
            if category:
                domain.append(('category', '=', category))
            if query:
                domain += ['|', '|', ('title', 'ilike', query), ('keywords', 'ilike', query), ('content', 'ilike', query)]
            items = request.env['casafolino.voice.knowledge'].sudo().search(domain, limit=6)
            return request.make_json_response({'ok': True, 'results': items.build_payload()})

        if tool_name == 'lookup_order_status':
            SaleOrder = request.env['sale.order'].sudo()
            domain = []
            order_name = payload.get('order_name')
            if order_name:
                domain.append(('name', 'ilike', order_name))
            partner = partner or self._find_partner(payload)
            if partner:
                domain.append(('partner_id', 'child_of', partner.commercial_partner_id.id))
            if not domain:
                return request.make_json_response({'error': 'order_name or customer identifier required'}, status=400)
            orders = SaleOrder.search(domain, order='date_order desc, id desc', limit=5)
            return request.make_json_response({
                'ok': True,
                'orders': [{
                    'id': order.id,
                    'name': order.name,
                    'customer': order.partner_id.display_name,
                    'state': order.state,
                    'date_order': fields.Datetime.to_string(order.date_order) if order.date_order else False,
                    'amount_total': order.amount_total,
                    'currency': order.currency_id.name,
                    'invoice_status': order.invoice_status,
                    'delivery_status': getattr(order, 'delivery_status', False),
                } for order in orders],
            })

        if tool_name == 'create_call_note':
            note = payload.get('note')
            summary = payload.get('summary') or 'Nota Voice AI'
            target = False
            call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
            lead = request.env['crm.lead'].sudo().browse(payload.get('lead_id'))
            partner = partner or request.env['res.partner'].sudo().browse(payload.get('partner_id'))
            if call.exists():
                target = call
            elif lead.exists():
                target = lead
            elif partner.exists():
                target = partner
            if not target:
                return request.make_json_response({'error': 'target not found'}, status=404)
            message = target.message_post(body=note, subject=summary, message_type='comment', subtype_xmlid='mail.mt_note')
            return request.make_json_response({'ok': True, 'message_id': message.id})

        if tool_name == 'create_crm_lead':
            partner = partner or self._find_partner(payload)
            lead = request.env['crm.lead'].sudo().create({
                'name': payload.get('name'),
                'partner_id': partner.id if partner else False,
                'contact_name': payload.get('contact_name') or payload.get('customer_name'),
                'partner_name': payload.get('company_name'),
                'phone': payload.get('phone'),
                'email_from': payload.get('email'),
                'description': '%s\n\nInteresse: %s\nPaese/area: %s' % (
                    payload.get('description') or 'Lead creato da chiamata Voice AI.',
                    payload.get('interest') or '',
                    payload.get('country') or '',
                ),
                'type': 'opportunity',
            })
            return request.make_json_response({'ok': True, 'lead_id': lead.id, 'lead_name': lead.name})

        if tool_name == 'create_email_activity':
            subject = payload.get('subject')
            body = payload.get('body')
            lead = request.env['crm.lead'].sudo().browse(payload.get('lead_id'))
            partner = partner or request.env['res.partner'].sudo().browse(payload.get('partner_id'))
            target = lead if lead.exists() else partner if partner.exists() else False
            if not target:
                return request.make_json_response({'error': 'partner_id or lead_id required'}, status=400)
            target.activity_schedule(
                'mail.mail_activity_data_email',
                summary=subject,
                note='%s\n\nEmail destinatario: %s' % (body, payload.get('email') or getattr(target, 'email', '') or ''),
            )
            return request.make_json_response({'ok': True})

        if tool_name == 'record_call_outcome':
            call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
            if not call.exists():
                return request.make_json_response({'error': 'call not found'}, status=404)
            call.write({
                'state': 'completed' if payload.get('outcome') != 'transferred' else 'transferred',
                'outcome': payload.get('outcome') or 'other',
                'summary': payload.get('summary'),
                'next_action': payload.get('next_action'),
                'ended_at': fields.Datetime.now(),
            })
            detected_language = payload.get('detected_language')
            if detected_language and call.partner_id and detected_language in ['it-IT', 'en-US', 'fr-FR', 'es-ES', 'de-DE']:
                call.partner_id.voice_ai_language = detected_language
            return request.make_json_response({'ok': True})

        if tool_name == 'opt_out_customer':
            phone = payload.get('phone')
            consent = request.env['casafolino.voice.consent'].sudo().search([
                ('phone', '=', phone),
                ('partner_id', '=', partner.id if partner else False),
            ], limit=1)
            if not consent and partner and phone:
                consent = request.env['casafolino.voice.consent'].sudo().create({
                    'partner_id': partner.id,
                    'phone': phone,
                    'consent_outbound': False,
                    'consent_source': 'manual',
                })
            if consent:
                consent.write({
                    'consent_outbound': False,
                    'opt_out_date': fields.Datetime.now(),
                    'opt_out_reason': payload.get('reason') or 'Opt-out richiesto durante chiamata AI',
                })
            return request.make_json_response({'ok': True, 'partner_id': partner.id if partner else None})

        if tool_name == 'transfer_to_human':
            call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
            if call.exists():
                call.write({
                    'state': 'transferred',
                    'outcome': 'transferred',
                    'next_action': payload.get('reason'),
                    'ended_at': fields.Datetime.now(),
                })
            return request.make_json_response({
                'ok': True,
                'transfer_requested': True,
                'department': payload.get('department') or 'generale',
                'reason': payload.get('reason'),
            })

        return request.make_json_response({'error': 'unknown tool'}, status=404)

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
