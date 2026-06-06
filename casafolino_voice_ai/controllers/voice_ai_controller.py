import json
import html
import hmac
import urllib.error
import urllib.request

from odoo import fields, http
from odoo.http import request


class CasaFolinoVoiceAIController(http.Controller):
    def _check_token(self):
        params = request.env['ir.config_parameter'].sudo()
        expected = params.get_param('casafolino_voice_ai.webhook_token')
        if not expected:
            return False
        auth = request.httprequest.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return False
        supplied = auth[7:].strip()
        return hmac.compare_digest(supplied, expected)

    def _json_body(self):
        raw = request.httprequest.get_data() or b'{}'
        return json.loads(raw.decode('utf-8'))

    @http.route('/voice_ai/health', type='http', auth='public', methods=['GET'], csrf=False)
    def health(self):
        return request.make_json_response({'ok': True, 'service': 'casafolino_voice_ai'})

    @http.route('/voice_ai/config', type='http', auth='public', methods=['GET'], csrf=False)
    def bridge_config(self, **kwargs):
        if not self._check_token():
            return request.make_json_response({'error': 'unauthorized'}, status=401)
        params = request.env['ir.config_parameter'].sudo()
        return request.make_json_response({
            'ok': True,
            'public_base_url': params.get_param('casafolino_voice_ai.public_base_url'),
            'realtime_model': params.get_param('casafolino_voice_ai.openai_realtime_model') or 'gpt-realtime-2',
            'realtime_voice': params.get_param('casafolino_voice_ai.openai_voice') or 'cedar',
            'human_transfer_uri': params.get_param('casafolino_voice_ai.human_transfer_uri'),
            'allow_outbound': params.get_param('casafolino_voice_ai.allow_outbound', 'False') == 'True',
            'has_openai_key': bool(params.get_param('casafolino_voice_ai.openai_api_key')),
            'requires_token': params.get_param('casafolino_voice_ai.require_token', 'True') == 'True',
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

    def _inbound_contact_tags(self):
        Tag = request.env.get('cf.contact.tag')
        if Tag is None:
            return []
        tag_ids = []
        for name in ['Centralino telefonico', 'Telefonate inbound']:
            tag = Tag.sudo().search([('name', '=', name)], limit=1)
            if not tag:
                vals = {'name': name}
                if 'category' in Tag._fields:
                    vals['category'] = 'Centralino'
                if 'color' in Tag._fields:
                    vals['color'] = '#3B82F6'
                tag = Tag.sudo().create(vals)
            tag_ids.append(tag.id)
        return tag_ids

    def _save_inbound_contact(self, payload):
        Partner = request.env['res.partner'].sudo()
        partner = self._find_partner(payload)
        first_name = (payload.get('first_name') or '').strip()
        last_name = (payload.get('last_name') or '').strip()
        full_name = (payload.get('name') or payload.get('customer_name') or ' '.join([first_name, last_name]).strip()).strip()
        company_name = (payload.get('company_name') or '').strip()
        email = (payload.get('email') or '').strip()
        phone = (payload.get('phone') or '').strip()
        vals = {}
        if full_name:
            vals['name'] = full_name
        elif company_name:
            vals['name'] = company_name
        if email:
            vals['email'] = email
        if phone:
            vals['phone'] = phone
            vals['mobile'] = phone
        if company_name:
            company = Partner.search([('is_company', '=', True), ('name', '=ilike', company_name)], limit=1)
            if not company:
                company = Partner.create({'name': company_name, 'is_company': True})
            vals['parent_id'] = company.id
            vals['company_name'] = company_name
        if not partner:
            partner = Partner.create(vals or {'name': full_name or company_name or phone or email or 'Contatto centralino'})
        else:
            safe_vals = {key: value for key, value in vals.items() if value}
            if safe_vals:
                partner.write(safe_vals)
        tag_ids = self._inbound_contact_tags()
        if tag_ids and 'cf_tag_ids' in partner._fields:
            partner.write({'cf_tag_ids': [(4, tag_id) for tag_id in tag_ids]})
        call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
        if call.exists():
            call.write({'partner_id': partner.id})
            call.message_post(
                body='Contatto centralino salvato/aggiornato: %s<br/>Telefono: %s<br/>Email: %s<br/>Azienda: %s' % (
                    html.escape(partner.display_name or ''),
                    html.escape(phone or partner.phone or partner.mobile or ''),
                    html.escape(email or partner.email or ''),
                    html.escape(company_name or getattr(partner, 'company_name', '') or ''),
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        return partner

    def _send_inbound_call_email(self, call, payload=None):
        payload = payload or {}
        partner = call.partner_id
        email_to = payload.get('email') or (partner.email if partner else '') or 'antonio@casafolino.com'
        cc_emails = ['martina.sinopoli@casafolino.com', 'commerciale@casafolino.com', 'antonio@casafolino.com']
        cc_emails = [email for email in cc_emails if email and email.lower() != (email_to or '').lower()]
        company = payload.get('company_name') or ''
        if not company and partner:
            company = partner.parent_id.display_name or getattr(partner, 'company_name', '') or ''
        contact = (partner.display_name if partner else '') or payload.get('customer_name') or payload.get('name') or 'N/D'
        phone = payload.get('phone') or call.phone or (partner.phone if partner else '') or (partner.mobile if partner else '') or 'N/D'
        subject = 'Riepilogo chiamata centralino CasaFolino - %s' % (call.name or 'nuova chiamata')
        body_html = """
            <p>Buongiorno,</p>
            <p>grazie per aver contattato CasaFolino. Di seguito trova il riepilogo della chiamata appena gestita dal centralino telefonico.</p>
            <table cellpadding="6" style="border-collapse: collapse;">
                <tr><td><b>Chiamata</b></td><td>%s</td></tr>
                <tr><td><b>Contatto</b></td><td>%s</td></tr>
                <tr><td><b>Azienda</b></td><td>%s</td></tr>
                <tr><td><b>Telefono</b></td><td>%s</td></tr>
                <tr><td><b>Email</b></td><td>%s</td></tr>
                <tr><td><b>Riepilogo</b></td><td>%s</td></tr>
                <tr><td><b>Prossima azione</b></td><td>%s</td></tr>
            </table>
            <p>Il team CasaFolino dara seguito alla richiesta quando necessario.</p>
            <p>Grazie,<br/>CasaFolino</p>
        """ % (
            html.escape(call.name or ''),
            html.escape(contact),
            html.escape(company or 'N/D'),
            html.escape(phone),
            html.escape(email_to or 'N/D'),
            html.escape(payload.get('summary') or call.summary or 'Nessun riepilogo disponibile'),
            html.escape(payload.get('next_action') or call.next_action or 'Nessuna azione indicata'),
        )
        mail = request.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_to': email_to,
            'email_cc': ','.join(cc_emails),
            'email_from': 'Antonio Folino <antonio@casafolino.com>',
            'reply_to': 'antonio@casafolino.com',
            'auto_delete': False,
        })
        mail.send()
        call.message_post(
            body='Email riepilogo centralino inviata a %s, cc %s' % (html.escape(email_to), html.escape(', '.join(cc_emails))),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return mail

    def _lookup_voice_knowledge(self, payload, limit=6):
        Knowledge = request.env['casafolino.voice.knowledge'].sudo()
        query = payload.get('query') or ''
        category = payload.get('category')
        base_domain = [('active', '=', True)]
        if category:
            base_domain.append(('category', '=', category))

        items = Knowledge.browse()
        tokens = [token.strip().lower() for token in query.replace(',', ' ').split() if len(token.strip()) >= 3]
        for token in tokens[:8]:
            token_items = Knowledge.search(base_domain + [
                '|', '|',
                ('title', 'ilike', token),
                ('keywords', 'ilike', token),
                ('content', 'ilike', token),
            ], limit=limit)
            items |= token_items
            if len(items) >= limit:
                break

        if not items and query:
            items = Knowledge.search(base_domain + [
                '|', '|',
                ('title', 'ilike', query),
                ('keywords', 'ilike', query),
                ('content', 'ilike', query),
            ], limit=limit)

        if not items and category:
            items = Knowledge.search(base_domain, limit=limit)

        return {'ok': True, 'results': items[:limit].build_payload()}

    @http.route('/voice_ai/tool/<string:tool_name>', type='http', auth='public', methods=['POST'], csrf=False)
    def tool_dispatch(self, tool_name):
        if not self._check_token():
            return request.make_json_response({'error': 'unauthorized'}, status=401)
        payload = self._json_body()
        partner = self._find_partner(payload)

        if tool_name == 'save_inbound_contact':
            partner = self._save_inbound_contact(payload)
            return request.make_json_response({
                'ok': True,
                'partner_id': partner.id,
                'name': partner.display_name,
                'email': partner.email,
                'phone': partner.phone or partner.mobile,
            })

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
            return request.make_json_response(self._lookup_voice_knowledge(payload))

        if tool_name == 'lookup_order_status':
            SaleOrder = request.env['sale.order'].sudo()
            domain = []
            order_name = payload.get('order_name')
            if order_name and len(order_name.strip()) >= 6:
                domain.append(('name', 'ilike', order_name))
            partner = partner or self._find_partner(payload)
            if partner:
                domain.append(('partner_id', 'child_of', partner.commercial_partner_id.id))
            if not domain:
                return request.make_json_response({
                    'error': 'specific order reference or customer identifier required',
                }, status=400)
            orders = SaleOrder.search(domain, order='date_order desc, id desc', limit=5)
            return request.make_json_response({
                'ok': True,
                'orders': [{
                    'id': order.id,
                    'name': order.name,
                    'customer': order.partner_id.display_name,
                    'state': order.state,
                    'date_order': fields.Datetime.to_string(order.date_order) if order.date_order else False,
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
            self._send_notification_email('create_crm_lead', payload)
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
            if payload.get('email') or payload.get('phone') or payload.get('customer_name') or payload.get('name') or payload.get('company_name'):
                partner = self._save_inbound_contact(payload)
            call.write({
                'state': 'completed' if payload.get('outcome') != 'transferred' else 'transferred',
                'outcome': payload.get('outcome') or 'other',
                'summary': payload.get('summary'),
                'next_action': payload.get('next_action'),
                'ended_at': fields.Datetime.now(),
                'partner_id': partner.id if partner else call.partner_id.id,
            })
            detected_language = payload.get('detected_language')
            if detected_language and call.partner_id and detected_language in ['it-IT', 'en-US', 'fr-FR', 'es-ES', 'de-DE']:
                call.partner_id.voice_ai_language = detected_language
            mail_sent = False
            try:
                self._send_inbound_call_email(call, payload)
                mail_sent = True
            except Exception as exc:
                call.message_post(
                    body='Errore invio email riepilogo centralino: %s' % html.escape(str(exc)),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            return request.make_json_response({'ok': True, 'partner_id': call.partner_id.id if call.partner_id else None, 'mail_sent': mail_sent})

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

        if tool_name == 'create_ticket':
            partner = partner or self._find_partner(payload)
            subject = payload.get('subject') or payload.get('title') or 'Segnalazione da chiamata AI'
            description = payload.get('description') or 'Nessun dettaglio fornito.'
            urgency = payload.get('urgency') or 'normal'
            category = payload.get('category') or 'general'
            
            HelpdeskTicket = request.env.get('helpdesk.ticket')
            if HelpdeskTicket is not None:
                ticket = HelpdeskTicket.sudo().create({
                    'name': subject,
                    'partner_id': partner.id if partner else False,
                    'partner_phone': payload.get('phone') or (partner.phone if partner else False),
                    'partner_email': payload.get('email') or (partner.email if partner else False),
                    'description': description,
                    'priority': '1' if urgency == 'high' else '0',
                })
                call_id = payload.get('call_id')
                if call_id:
                    call = request.env['casafolino.voice.call'].sudo().browse(call_id)
                    if call.exists():
                        ticket.message_post(body='Ticket creato da chiamata vocale AI. Riferimento chiamata: %s' % call.name)
                self._send_notification_email('create_ticket', payload)
                return request.make_json_response({
                    'ok': True,
                    'ticket_id': ticket.id,
                    'ticket_name': ticket.name,
                    'type': 'helpdesk.ticket'
                })
            else:
                lead = request.env['crm.lead'].sudo().create({
                    'name': '[Segnalazione] %s' % subject,
                    'partner_id': partner.id if partner else False,
                    'contact_name': payload.get('contact_name') or payload.get('customer_name') or (partner.name if partner else False),
                    'phone': payload.get('phone') or (partner.phone if partner else False),
                    'email_from': payload.get('email') or (partner.email if partner else False),
                    'description': '%s\n\nCategoria: %s\nUrgenza: %s' % (description, category, urgency),
                    'type': 'lead',
                })
                call_id = payload.get('call_id')
                if call_id:
                    call = request.env['casafolino.voice.call'].sudo().browse(call_id)
                    if call.exists():
                        lead.message_post(body='Segnalazione creata da chiamata vocale AI. Riferimento chiamata: %s' % call.name)
                self._send_notification_email('create_ticket', payload)
                return request.make_json_response({
                    'ok': True,
                    'lead_id': lead.id,
                    'lead_name': lead.name,
                    'type': 'crm.lead'
                })

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

    def _send_notification_email(self, tool_name, payload):
        try:
            subject_text = "Notifica Voice AI: Nuovo Lead creato" if tool_name == 'create_crm_lead' else "Notifica Voice AI: Nuova Segnalazione creata"
            body_html = "<p>Ciao Antonio,<br><br>L'assistente vocale Viola ha gestito una richiesta e ha creato un record in Odoo:</p>"
            if tool_name == 'create_crm_lead':
                body_html += """
                <ul>
                    <li><b>Tipo:</b> Opportunità Commerciale / Lead</li>
                    <li><b>Nome Richiesta:</b> %s</li>
                    <li><b>Cliente/Referente:</b> %s</li>
                    <li><b>Azienda:</b> %s</li>
                    <li><b>Telefono:</b> %s</li>
                    <li><b>Email:</b> %s</li>
                    <li><b>Dettaglio/Interesse:</b> %s</li>
                </ul>
                """ % (
                    payload.get('name') or 'N/D',
                    payload.get('contact_name') or payload.get('customer_name') or 'N/D',
                    payload.get('company_name') or 'N/D',
                    payload.get('phone') or 'N/D',
                    payload.get('email') or 'N/D',
                    payload.get('description') or payload.get('interest') or 'N/D'
                )
            else:
                body_html += """
                <ul>
                    <li><b>Tipo:</b> Segnalazione di Assistenza / Ticket</li>
                    <li><b>Oggetto:</b> %s</li>
                    <li><b>Categoria:</b> %s</li>
                    <li><b>Urgenza:</b> %s</li>
                    <li><b>Telefono:</b> %s</li>
                    <li><b>Email:</b> %s</li>
                    <li><b>Dettaglio Reclamo:</b> %s</li>
                </ul>
                """ % (
                    payload.get('subject') or 'N/D',
                    payload.get('category') or 'N/D',
                    payload.get('urgency') or 'N/D',
                    payload.get('phone') or 'N/D',
                    payload.get('email') or 'N/D',
                    payload.get('description') or 'N/D'
                )
            body_html += "<br><p>Puoi consultare e gestire questo record direttamente all'interno di Odoo.</p>"
            
            mail_values = {
                'subject': subject_text,
                'body_html': body_html,
                'email_to': 'antonio@casafolino.com',
            }
            request.env['mail.mail'].sudo().create(mail_values).send()
        except Exception as e:
            pass

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

    def _chat_tools(self, agent_payload):
        tools = []
        for tool in agent_payload.get('tools') or []:
            tools.append({
                'type': 'function',
                'function': {
                    'name': tool.get('name'),
                    'description': tool.get('description'),
                    'parameters': tool.get('parameters') or {'type': 'object', 'properties': {}},
                },
            })
        return tools

    def _openai_chat(self, messages, tools, model):
        api_key = request.env['ir.config_parameter'].sudo().get_param('casafolino_voice_ai.openai_api_key')
        if not api_key:
            raise ValueError('OpenAI API key not configured')
        payload = json.dumps({
            'model': model or 'gpt-4.1-mini',
            'messages': messages,
            'tools': tools,
            'tool_choice': 'auto',
            'temperature': 0.2,
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=payload,
            headers={
                'Authorization': 'Bearer %s' % api_key,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8')
            raise ValueError('OpenAI error %s: %s' % (exc.code, detail[:500])) from exc

    def _openai_speech(self, text):
        api_key = request.env['ir.config_parameter'].sudo().get_param('casafolino_voice_ai.openai_api_key')
        if not api_key:
            raise ValueError('OpenAI API key not configured')
        payload = json.dumps({
            'model': 'gpt-4o-mini-tts',
            'voice': 'marin',
            'input': text[:4000],
            'response_format': 'mp3',
            'instructions': 'Parla in italiano con tono naturale, professionale e caldo, come un centralinista CasaFolino. Frasi chiare, ritmo telefonico, non teatrale.',
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.openai.com/v1/audio/speech',
            data=payload,
            headers={
                'Authorization': 'Bearer %s' % api_key,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8')
            raise ValueError('OpenAI speech error %s: %s' % (exc.code, detail[:500])) from exc

    def _openai_realtime_client_secret(self, agent, scenario, voice=None):
        api_key = request.env['ir.config_parameter'].sudo().get_param('casafolino_voice_ai.openai_api_key')
        if not api_key:
            raise ValueError('OpenAI API key not configured')
        params = request.env['ir.config_parameter'].sudo()
        knowledge_items = request.env['casafolino.voice.knowledge'].sudo().search([('active', '=', True)], limit=12)
        knowledge_lines = []
        for item in knowledge_items:
            knowledge_lines.append('- %s: %s' % (item.title, item.content[:700]))
        selected_voice = voice or params.get_param('casafolino_voice_ai.openai_voice') or 'cedar'
        if selected_voice not in ['cedar', 'marin', 'coral', 'sage', 'verse', 'alloy', 'ash', 'ballad', 'echo', 'shimmer']:
            selected_voice = 'cedar'
        instructions = '%s\n\nModalita simulatore realtime: questa e una conversazione vocale diretta e deve sembrare una telefonata naturale, non un IVR. Rispondi con tono umano, caldo, commerciale e leggermente conversazionale. Usa micro-pause naturali, frasi brevi, una domanda alla volta. Se il cliente parla sopra, fermati e ascolta. Non leggere elenchi lunghi: proponi una sintesi e poi chiedi cosa interessa approfondire. Non inventare prezzi, disponibilita, tempi di consegna o condizioni commerciali.\n\nScenario formazione: %s\n\nKnowledge approvata CasaFolino:\n%s' % (
            agent._compose_instructions() if agent else 'Sei l assistente vocale CasaFolino.',
            scenario or 'Simulazione libera',
            '\n'.join(knowledge_lines),
        )
        payload = json.dumps({
            'session': {
                'type': 'realtime',
                'model': params.get_param('casafolino_voice_ai.openai_realtime_model') or 'gpt-realtime-2',
                'output_modalities': ['audio'],
                'instructions': instructions,
                'audio': {
                    'input': {
                        'turn_detection': {
                            'type': 'semantic_vad',
                        },
                    },
                    'output': {
                        'voice': selected_voice,
                    },
                },
            },
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.openai.com/v1/realtime/client_secrets',
            data=payload,
            headers={
                'Authorization': 'Bearer %s' % api_key,
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8')
            raise ValueError('OpenAI realtime error %s: %s' % (exc.code, detail[:500])) from exc

    def _execute_voice_tool(self, tool_name, payload):
        partner = self._find_partner(payload)

        if tool_name == 'save_inbound_contact':
            partner = self._save_inbound_contact(payload)
            return {
                'ok': True,
                'partner_id': partner.id,
                'name': partner.display_name,
                'email': partner.email,
                'phone': partner.phone or partner.mobile,
            }

        if tool_name == 'lookup_customer':
            if not partner:
                return {'ok': True, 'customer': None}
            return {
                'ok': True,
                'customer': {
                    'id': partner.id,
                    'name': partner.display_name,
                    'phone': partner.phone or partner.mobile,
                    'email': partner.email,
                    'language': getattr(partner, 'voice_ai_language', 'auto') or 'auto',
                    'outbound_consent': bool(partner.voice_outbound_consent),
                },
            }

        if tool_name == 'lookup_knowledge':
            return self._lookup_voice_knowledge(payload)

        if tool_name == 'lookup_order_status':
            SaleOrder = request.env['sale.order'].sudo()
            domain = []
            order_name = payload.get('order_name')
            if order_name and len(order_name.strip()) >= 6:
                domain.append(('name', 'ilike', order_name))
            partner = partner or self._find_partner(payload)
            if partner:
                domain.append(('partner_id', 'child_of', partner.commercial_partner_id.id))
            if not domain:
                return {'error': 'specific order reference or customer identifier required'}
            orders = SaleOrder.search(domain, order='date_order desc, id desc', limit=5)
            return {
                'ok': True,
                'orders': [{
                    'id': order.id,
                    'name': order.name,
                    'customer': order.partner_id.display_name,
                    'state': order.state,
                    'date_order': fields.Datetime.to_string(order.date_order) if order.date_order else False,
                    'invoice_status': order.invoice_status,
                    'delivery_status': getattr(order, 'delivery_status', False),
                } for order in orders],
            }

        if tool_name == 'create_callback':
            reason = payload.get('reason') or 'Richiamata richiesta da simulazione Voice AI'
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
            return {'ok': True, 'partner_id': partner.id if partner else None}

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
                    payload.get('description') or 'Lead creato da simulazione Voice AI.',
                    payload.get('interest') or '',
                    payload.get('country') or '',
                ),
                'type': 'opportunity',
            })
            self._send_notification_email('create_crm_lead', payload)
            return {'ok': True, 'lead_id': lead.id, 'lead_name': lead.name}

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
                return {'error': 'target not found'}
            message = target.message_post(body=note, subject=summary, message_type='comment', subtype_xmlid='mail.mt_note')
            return {'ok': True, 'message_id': message.id}

        if tool_name == 'create_email_activity':
            subject = payload.get('subject')
            body = payload.get('body')
            lead = request.env['crm.lead'].sudo().browse(payload.get('lead_id'))
            partner = partner or request.env['res.partner'].sudo().browse(payload.get('partner_id'))
            target = lead if lead.exists() else partner if partner.exists() else False
            if not target:
                return {'error': 'partner_id or lead_id required'}
            target.activity_schedule(
                'mail.mail_activity_data_email',
                summary=subject,
                note='%s\n\nEmail destinatario: %s' % (body, payload.get('email') or getattr(target, 'email', '') or ''),
            )
            return {'ok': True}

        if tool_name == 'record_call_outcome':
            call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
            if not call.exists():
                return {'error': 'call not found'}
            if payload.get('email') or payload.get('phone') or payload.get('customer_name') or payload.get('name') or payload.get('company_name'):
                partner = self._save_inbound_contact(payload)
            call.write({
                'state': 'completed' if payload.get('outcome') != 'transferred' else 'transferred',
                'outcome': payload.get('outcome') or 'other',
                'summary': payload.get('summary'),
                'next_action': payload.get('next_action'),
                'ended_at': fields.Datetime.now(),
                'partner_id': partner.id if partner else call.partner_id.id,
            })
            mail_sent = False
            try:
                self._send_inbound_call_email(call, payload)
                mail_sent = True
            except Exception as exc:
                call.message_post(body='Errore invio email riepilogo centralino: %s' % html.escape(str(exc)), message_type='comment', subtype_xmlid='mail.mt_note')
            return {'ok': True, 'partner_id': call.partner_id.id if call.partner_id else None, 'mail_sent': mail_sent}

        if tool_name == 'create_ticket':
            partner = partner or self._find_partner(payload)
            subject = payload.get('subject') or payload.get('title') or 'Segnalazione da chiamata AI'
            description = payload.get('description') or 'Nessun dettaglio fornito.'
            urgency = payload.get('urgency') or 'normal'
            category = payload.get('category') or 'general'
            
            HelpdeskTicket = request.env.get('helpdesk.ticket')
            if HelpdeskTicket is not None:
                ticket = HelpdeskTicket.sudo().create({
                    'name': subject,
                    'partner_id': partner.id if partner else False,
                    'partner_phone': payload.get('phone') or (partner.phone if partner else False),
                    'partner_email': payload.get('email') or (partner.email if partner else False),
                    'description': description,
                    'priority': '1' if urgency == 'high' else '0',
                })
                call_id = payload.get('call_id')
                if call_id:
                    call = request.env['casafolino.voice.call'].sudo().browse(call_id)
                    if call.exists():
                        ticket.message_post(body='Ticket creato da chiamata vocale AI. Riferimento chiamata: %s' % call.name)
                self._send_notification_email('create_ticket', payload)
                return {
                    'ok': True,
                    'ticket_id': ticket.id,
                    'ticket_name': ticket.name,
                    'type': 'helpdesk.ticket'
                }
            else:
                lead = request.env['crm.lead'].sudo().create({
                    'name': '[Segnalazione] %s' % subject,
                    'partner_id': partner.id if partner else False,
                    'contact_name': payload.get('contact_name') or payload.get('customer_name') or (partner.name if partner else False),
                    'phone': payload.get('phone') or (partner.phone if partner else False),
                    'email_from': payload.get('email') or (partner.email if partner else False),
                    'description': '%s\n\nCategoria: %s\nUrgenza: %s' % (description, category, urgency),
                    'type': 'lead',
                })
                call_id = payload.get('call_id')
                if call_id:
                    call = request.env['casafolino.voice.call'].sudo().browse(call_id)
                    if call.exists():
                        lead.message_post(body='Segnalazione creata da chiamata vocale AI. Riferimento chiamata: %s' % call.name)
                self._send_notification_email('create_ticket', payload)
                return {
                    'ok': True,
                    'lead_id': lead.id,
                    'lead_name': lead.name,
                    'type': 'crm.lead'
                }

        if tool_name == 'transfer_to_human':
            call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
            if call.exists():
                call.write({
                    'state': 'transferred',
                    'outcome': 'transferred',
                    'next_action': payload.get('reason'),
                    'ended_at': fields.Datetime.now(),
                })
            return {
                'ok': True,
                'transfer_requested': True,
                'department': payload.get('department') or 'generale',
                'reason': payload.get('reason'),
            }

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
                    'opt_out_reason': payload.get('reason') or 'Opt-out richiesto durante simulazione AI',
                })
            return {'ok': True, 'partner_id': partner.id if partner else None}

        return {'error': 'unknown tool'}

    def _serialize_transcript(self, messages, trace):
        rows = []
        for message in messages:
            role = message.get('role')
            if role in ['system', 'tool']:
                continue
            content = message.get('content') or ''
            if content:
                label = 'Cliente' if role == 'user' else 'Agente'
                rows.append('%s: %s' % (label, content))
        if trace:
            rows.append('\nTool usati:')
            for item in trace:
                rows.append('- %s: %s' % (item.get('name'), json.dumps(item.get('args') or {}, ensure_ascii=False)))
        return '\n'.join(rows)

    @http.route('/voice_ai/simulator', type='http', auth='user', methods=['GET'], csrf=False)
    def simulator_page(self):
        agents = request.env['casafolino.voice.agent'].sudo().search([('active', '=', True)], order='direction, name')
        priority = {
            'commerciale': 0,
            'centralino': 1,
            'assistenza': 2,
            'amministrazione': 3,
            'follow-up': 4,
        }
        agents = agents.sorted(lambda agent: priority.get((agent.name or '').lower().split(' ')[0], 9))
        options = []
        for agent in agents:
            label = '%s - %s' % (agent.name, agent.direction)
            selected = ' selected' if 'commerciale' in (agent.name or '').lower() else ''
            options.append('<option value="%s"%s>%s</option>' % (agent.id, selected, html.escape(label)))
        html_page = """<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Simulatore chiamate Voice AI</title>
  <style>
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #1f2933; }
    header { background: #ffffff; border-bottom: 1px solid #d8dee6; padding: 16px 24px; display: flex; justify-content: space-between; gap: 16px; align-items: center; }
    h1 { margin: 0; font-size: 22px; font-weight: 650; }
    main { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 16px; padding: 16px; max-width: 1440px; margin: 0 auto; }
    aside, section { background: #fff; border: 1px solid #d8dee6; border-radius: 8px; }
    aside { padding: 16px; height: fit-content; }
    label { display: block; font-size: 13px; font-weight: 650; margin: 14px 0 6px; }
    select, input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #c7d0da; border-radius: 6px; padding: 10px; font: inherit; background: #fff; }
    textarea { min-height: 92px; resize: vertical; }
    button { border: 0; border-radius: 6px; padding: 10px 14px; background: #1f5eff; color: #fff; font-weight: 650; cursor: pointer; }
    button.secondary { background: #eef2f7; color: #1f2933; }
    button.realtime { background: #7c3aed; }
    button.danger { background: #b91c1c; }
    button.mic { background: #047857; }
    button.mic.listening { background: #b91c1c; }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .chat { display: flex; flex-direction: column; min-height: 680px; }
    .messages { flex: 1; padding: 18px; overflow: auto; display: flex; flex-direction: column; gap: 12px; }
    .bubble { max-width: 760px; padding: 12px 14px; border-radius: 8px; line-height: 1.45; white-space: pre-wrap; }
    .user { align-self: flex-end; background: #dbeafe; }
    .assistant { align-self: flex-start; background: #f1f5f9; }
    .system { align-self: center; background: #fff7ed; color: #7c2d12; font-size: 13px; }
    .composer { border-top: 1px solid #d8dee6; padding: 14px; display: grid; grid-template-columns: 1fr auto; gap: 10px; }
    .tools { margin-top: 16px; max-height: 260px; overflow: auto; background: #0f172a; color: #dbeafe; border-radius: 6px; padding: 10px; font-size: 12px; white-space: pre-wrap; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    .hint { color: #5b6878; font-size: 13px; line-height: 1.4; }
    .voice-status { margin-top: 12px; padding: 10px; border-radius: 6px; background: #f1f5f9; color: #334155; font-size: 13px; line-height: 1.4; }
    @media (max-width: 900px) { main { grid-template-columns: 1fr; } .chat { min-height: 560px; } }
  </style>
</head>
<body>
  <header>
    <h1>Simulatore chiamate Voice AI</h1>
    <a href="/web" style="color:#1f5eff;text-decoration:none;font-weight:650;">Torna a Odoo</a>
  </header>
  <main>
    <aside>
      <label>Agente</label>
      <select id="agent_id">__VOICE_AGENT_OPTIONS__</select>
      <p class="hint">Per simulare richieste di catalogo, listini, private label o nuovi clienti usa Commerciale CasaFolino.</p>
      <label>Scenario formazione</label>
      <textarea id="scenario" placeholder="Esempio: cliente GDO chiede certificazioni, catalogo e private label al pistacchio"></textarea>
      <label>Telefono simulato</label>
      <input id="phone" value="+390000000000">
      <label>Voce realtime</label>
      <select id="realtime_voice">
        <option value="cedar" selected>Cedar - piu naturale</option>
        <option value="marin">Marin - chiara</option>
        <option value="coral">Coral</option>
        <option value="sage">Sage</option>
        <option value="verse">Verse</option>
      </select>
      <div class="row">
        <button id="start">Avvia chiamata</button>
        <button id="start_realtime" class="realtime" disabled>Realtime disattivato</button>
        <button id="finish" class="secondary" disabled>Chiudi</button>
      </div>
      <div class="row">
        <button id="stop_realtime" class="danger" disabled>Ferma realtime</button>
      </div>
      <div class="row">
        <button id="mic" class="mic" disabled>Parla</button>
        <button id="speak_toggle" class="secondary" type="button">Voce naturale: ON</button>
      </div>
      <div class="voice-status" id="voice_status">Realtime disattivato: questa versione non e abbastanza naturale ne affidabile. Usiamo il simulatore solo come laboratorio testuale finche non riscriviamo persona e bridge.</div>
      <p class="hint">Le simulazioni vengono salvate in Chiamate AI. Se chiedi callback, lead o attivita, possono nascere record reali: usa dati TEST quando ti alleni.</p>
      <div class="tools" id="trace">Tool trace vuoto.</div>
    </aside>
    <section class="chat">
      <div class="messages" id="messages"></div>
      <div class="composer">
        <textarea id="utterance" placeholder="Scrivi o usa Parla..." disabled></textarea>
        <button id="send" disabled>Invia</button>
      </div>
    </section>
  </main>
  <script>
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const state = { callId: null, trace: [], recognition: null, listening: false, speak: true, audio: null, pc: null, dc: null, localStream: null };
    const messages = document.getElementById('messages');
    const trace = document.getElementById('trace');
    const voiceStatus = document.getElementById('voice_status');
    const micButton = document.getElementById('mic');
    const speakToggle = document.getElementById('speak_toggle');
    const utteranceInput = document.getElementById('utterance');
    function setVoiceStatus(text) {
      voiceStatus.textContent = text;
    }
    function add(role, text) {
      const node = document.createElement('div');
      node.className = 'bubble ' + role;
      node.textContent = text;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }
    function fallbackSpeak(text) {
      if (!('speechSynthesis' in window) || !text) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'it-IT';
      utterance.rate = 0.96;
      utterance.pitch = 1;
      window.speechSynthesis.speak(utterance);
    }
    async function speak(text) {
      if (!state.speak || !text) return;
      try {
        if (state.audio) {
          state.audio.pause();
          state.audio = null;
        }
        setVoiceStatus('Genero voce naturale...');
        const res = await fetch('/voice_ai/simulator/speech', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        if (!res.ok) throw new Error('speech HTTP ' + res.status);
        const blob = await res.blob();
        state.audio = new Audio(URL.createObjectURL(blob));
        state.audio.onended = () => setVoiceStatus('Pronto. Premi Parla per continuare.');
        await state.audio.play();
      } catch (err) {
        fallbackSpeak(text);
        setVoiceStatus('Voce browser usata come fallback. Apri da HTTPS se l audio naturale non parte.');
      }
    }
    async function post(url, body) {
      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || ('HTTP ' + res.status));
      return data;
    }
    function stopRealtime() {
      if (state.dc) state.dc.close();
      if (state.pc) state.pc.close();
      if (state.localStream) state.localStream.getTracks().forEach((track) => track.stop());
      state.dc = null;
      state.pc = null;
      state.localStream = null;
      document.getElementById('stop_realtime').disabled = true;
      document.getElementById('start_realtime').disabled = false;
      setVoiceStatus('Realtime fermato.');
    }
    async function startRealtime() {
      if (!window.isSecureContext) {
        setVoiceStatus('Realtime richiede HTTPS. Apri https://erp.casafolino.com/voice_ai/simulator');
        return;
      }
      stopRealtime();
      setVoiceStatus('Apro microfono e connessione realtime...');
      const data = await post('/voice_ai/simulator/realtime/session', {
        agent_id: Number(document.getElementById('agent_id').value),
        scenario: document.getElementById('scenario').value,
        phone: document.getElementById('phone').value,
        voice: document.getElementById('realtime_voice').value
      });
      state.callId = data.call_id;
      add('system', 'Realtime avviato: ' + data.call_name + '. Puoi parlare liberamente.');
      const secret = data.client_secret?.value || data.value;
      if (!secret) throw new Error('Realtime client secret mancante');
      const pc = new RTCPeerConnection();
      const audio = document.createElement('audio');
      audio.autoplay = true;
      pc.ontrack = (event) => {
        audio.srcObject = event.streams[0];
      };
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      stream.getTracks().forEach((track) => pc.addTrack(track, stream));
      const dc = pc.createDataChannel('oai-events');
      dc.onopen = () => {
        setVoiceStatus('Realtime attivo. Parla normalmente: l agente deve interrompersi se parli sopra.');
      };
      dc.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === 'response.output_text.delta' && payload.delta) {
          setVoiceStatus('Agente sta parlando...');
        }
        if (payload.type === 'input_audio_buffer.speech_started') {
          setVoiceStatus('Ti sto ascoltando...');
        }
        if (payload.type === 'response.done') {
          setVoiceStatus('Pronto. Continua pure a parlare.');
        }
        if (payload.type === 'error') {
          add('system', payload.error?.message || 'Errore realtime');
        }
      };
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      const sdpResponse = await fetch('https://api.openai.com/v1/realtime/calls', {
        method: 'POST',
        body: offer.sdp,
        headers: {
          Authorization: 'Bearer ' + secret,
          'Content-Type': 'application/sdp'
        }
      });
      if (!sdpResponse.ok) {
        throw new Error('Realtime SDP failed: HTTP ' + sdpResponse.status);
      }
      await pc.setRemoteDescription({
        type: 'answer',
        sdp: await sdpResponse.text()
      });
      state.pc = pc;
      state.dc = dc;
      state.localStream = stream;
      document.getElementById('start_realtime').disabled = true;
      document.getElementById('stop_realtime').disabled = false;
    }
    async function sendTurn(text) {
      if (!text || !state.callId) return;
      add('user', text);
      document.getElementById('send').disabled = true;
      micButton.disabled = true;
      setVoiceStatus('Agente sta rispondendo...');
      try {
        const data = await post('/voice_ai/simulator/turn', { call_id: state.callId, message: text });
        add('assistant', data.answer || '');
        speak(data.answer || '');
        state.trace = data.trace || [];
        trace.textContent = state.trace.length ? JSON.stringify(state.trace, null, 2) : 'Tool trace vuoto.';
        setVoiceStatus('Pronto. Premi Parla per continuare.');
      } catch (err) {
        add('system', err.message);
        setVoiceStatus(err.message);
      } finally {
        document.getElementById('send').disabled = false;
        micButton.disabled = false;
        utteranceInput.focus();
      }
    }
    function setupRecognition() {
      if (!SpeechRecognition) {
        micButton.disabled = true;
        setVoiceStatus('Il browser non supporta il riconoscimento vocale. Usa Chrome o Edge su HTTPS.');
        return;
      }
      state.recognition = new SpeechRecognition();
      state.recognition.lang = 'it-IT';
      state.recognition.interimResults = true;
      state.recognition.continuous = false;
      state.recognition.onstart = () => {
        state.listening = true;
        micButton.classList.add('listening');
        micButton.textContent = 'Sto ascoltando...';
        setVoiceStatus('Parla ora. Mi fermo quando smetti di parlare.');
      };
      state.recognition.onresult = (event) => {
        let text = '';
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          text += event.results[i][0].transcript;
        }
        utteranceInput.value = text.trim();
      };
      state.recognition.onerror = (event) => {
        setVoiceStatus('Microfono non disponibile: ' + event.error + '. Apri da HTTPS e autorizza il microfono.');
      };
      state.recognition.onend = () => {
        state.listening = false;
        micButton.classList.remove('listening');
        micButton.textContent = 'Parla';
        const text = utteranceInput.value.trim();
        utteranceInput.value = '';
        if (text) sendTurn(text);
        else setVoiceStatus('Non ho sentito una frase. Premi Parla e riprova.');
      };
    }
    document.getElementById('start').onclick = async () => {
      try {
        messages.innerHTML = '';
        state.trace = [];
        trace.textContent = 'Tool trace vuoto.';
        const data = await post('/voice_ai/simulator/start', {
          agent_id: Number(document.getElementById('agent_id').value),
          scenario: document.getElementById('scenario').value,
          phone: document.getElementById('phone').value
        });
        state.callId = data.call_id;
        add('system', 'Chiamata simulata avviata: ' + data.call_name);
        if (data.first_message) add('assistant', data.first_message);
        document.getElementById('utterance').disabled = false;
        document.getElementById('send').disabled = false;
        document.getElementById('finish').disabled = false;
        micButton.disabled = false;
        setVoiceStatus(SpeechRecognition ? 'Pronto. Premi Parla e autorizza il microfono.' : 'Il browser non supporta il riconoscimento vocale. Puoi scrivere.');
        if (data.first_message) speak(data.first_message);
      } catch (err) {
        add('system', err.message);
      }
    };
    document.getElementById('start_realtime').onclick = async () => {
      add('system', 'Realtime disattivato: questa versione non e valida come simulazione telefonica CasaFolino.');
      return;
      try {
        messages.innerHTML = '';
        state.trace = [];
        trace.textContent = 'Tool trace vuoto.';
        await startRealtime();
      } catch (err) {
        add('system', err.message);
        setVoiceStatus(err.message);
        stopRealtime();
      }
    };
    document.getElementById('stop_realtime').onclick = () => stopRealtime();
    document.getElementById('send').onclick = async () => {
      const input = utteranceInput;
      const text = input.value.trim();
      if (!text || !state.callId) return;
      input.value = '';
      sendTurn(text);
    };
    micButton.onclick = () => {
      if (!state.callId) return;
      if (!window.isSecureContext) {
        setVoiceStatus('Il microfono e bloccato perche questa pagina non e HTTPS. Apri https://erp.casafolino.com/voice_ai/simulator');
        return;
      }
      if (!state.recognition) setupRecognition();
      if (!state.recognition) return;
      if (state.listening) {
        state.recognition.stop();
      } else {
        window.speechSynthesis?.cancel();
        state.recognition.start();
      }
    };
    speakToggle.onclick = () => {
      state.speak = !state.speak;
      speakToggle.textContent = state.speak ? 'Voce naturale: ON' : 'Voce naturale: OFF';
      if (!state.speak && 'speechSynthesis' in window) window.speechSynthesis.cancel();
      if (!state.speak && state.audio) state.audio.pause();
    };
    document.getElementById('utterance').addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) document.getElementById('send').click();
    });
    document.getElementById('finish').onclick = async () => {
      if (!state.callId) return;
      await post('/voice_ai/simulator/finish', { call_id: state.callId });
      add('system', 'Chiamata chiusa e salvata.');
      document.getElementById('utterance').disabled = true;
      document.getElementById('send').disabled = true;
      document.getElementById('finish').disabled = true;
      micButton.disabled = true;
      stopRealtime();
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      setVoiceStatus('Chiamata chiusa.');
    };
    setupRecognition();
  </script>
</body>
</html>""".replace('__VOICE_AGENT_OPTIONS__', ''.join(options))
        return request.make_response(html_page, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/voice_ai/simulator/start', type='http', auth='user', methods=['POST'], csrf=False)
    def simulator_start(self):
        payload = self._json_body()
        agent = request.env['casafolino.voice.agent'].sudo().browse(payload.get('agent_id'))
        if not agent.exists():
            agent = request.env['casafolino.voice.agent'].sudo().search([('direction', '=', 'inbound'), ('active', '=', True)], limit=1)
        if not agent:
            return request.make_json_response({'error': 'no active voice agent found'}, status=400)
        scenario = payload.get('scenario') or 'Simulazione libera'
        call = request.env['casafolino.voice.call'].sudo().create({
            'direction': agent.direction,
            'state': 'active',
            'external_call_id': 'web_sim_%s' % fields.Datetime.now(),
            'phone': payload.get('phone'),
            'agent_id': agent.id,
            'route_action': 'agent',
            'summary': 'Simulazione formazione: %s' % scenario,
        })
        call.message_post(body='Simulazione Voice AI avviata da %s.<br/>Scenario: %s' % (
            html.escape(request.env.user.display_name),
            html.escape(scenario),
        ), message_type='comment', subtype_xmlid='mail.mt_note')
        call.transcript = json.dumps({
            'scenario': scenario,
            'messages': [],
            'trace': [],
        }, ensure_ascii=False, indent=2)
        return request.make_json_response({
            'ok': True,
            'call_id': call.id,
            'call_name': call.name,
            'first_message': agent.first_message,
        })

    @http.route('/voice_ai/simulator/realtime/session', type='http', auth='user', methods=['POST'], csrf=False)
    def simulator_realtime_session(self):
        payload = self._json_body()
        agent = request.env['casafolino.voice.agent'].sudo().browse(payload.get('agent_id'))
        if not agent.exists():
            agent = request.env['casafolino.voice.agent'].sudo().search([('direction', '=', 'inbound'), ('active', '=', True)], limit=1)
        if not agent:
            return request.make_json_response({'error': 'no active voice agent found'}, status=400)
        scenario = payload.get('scenario') or 'Simulazione realtime'
        call = request.env['casafolino.voice.call'].sudo().create({
            'direction': agent.direction,
            'state': 'active',
            'external_call_id': 'web_realtime_%s' % fields.Datetime.now(),
            'phone': payload.get('phone'),
            'agent_id': agent.id,
            'route_action': 'agent',
            'summary': 'Simulazione realtime: %s' % scenario,
        })
        try:
            client_secret = self._openai_realtime_client_secret(agent, scenario, voice=payload.get('voice'))
        except ValueError as exc:
            return request.make_json_response({'error': str(exc)}, status=502)
        return request.make_json_response({
            'ok': True,
            'call_id': call.id,
            'call_name': call.name,
            'client_secret': client_secret,
        })

    @http.route('/voice_ai/simulator/turn', type='http', auth='user', methods=['POST'], csrf=False)
    def simulator_turn(self):
        payload = self._json_body()
        call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
        if not call.exists():
            return request.make_json_response({'error': 'call not found'}, status=404)
        agent = call.agent_id
        if not agent:
            return request.make_json_response({'error': 'call has no agent'}, status=400)
        stored = json.loads(call.transcript or '{}')
        messages = stored.get('messages') or []
        trace = stored.get('trace') or []
        if not messages:
            agent_payload = agent.build_realtime_payload()
            messages.append({
                'role': 'system',
                'content': '%s\n\nModalita simulatore formazione: rispondi come in una chiamata telefonica reale. Frasi brevi. Una domanda alla volta. Prima di rispondere su prodotti, formati, certificazioni, mercati, capacita produttiva o private label usa lookup_knowledge. Non inventare prezzi, disponibilita, consegne o condizioni commerciali.' % agent_payload.get('instructions'),
            })
        else:
            agent_payload = agent.build_realtime_payload()
        messages.append({'role': 'user', 'content': payload.get('message') or ''})
        tools = self._chat_tools(agent_payload)
        answer = ''
        for _step in range(8):
            completion = self._openai_chat(messages, tools, 'gpt-4.1-mini')
            message = (completion.get('choices') or [{}])[0].get('message') or {}
            messages.append(message)
            tool_calls = message.get('tool_calls') or []
            if not tool_calls:
                answer = message.get('content') or ''
                break
            for tool_call in tool_calls:
                function = tool_call.get('function') or {}
                name = function.get('name')
                args = json.loads(function.get('arguments') or '{}')
                args['call_id'] = call.id
                result = self._execute_voice_tool(name, args)
                trace.append({'name': name, 'args': args, 'result': result})
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call.get('id'),
                    'name': name,
                    'content': json.dumps(result, ensure_ascii=False),
                })
        if not answer:
            answer = 'Mi scusi, sto impiegando troppo a verificare. Posso farla ricontattare da un collega?'
        stored.update({'messages': messages, 'trace': trace})
        call.write({
            'transcript': json.dumps(stored, ensure_ascii=False, indent=2),
            'summary': self._serialize_transcript(messages, trace)[-3000:],
        })
        return request.make_json_response({'ok': True, 'answer': answer, 'trace': trace})

    @http.route('/voice_ai/simulator/finish', type='http', auth='user', methods=['POST'], csrf=False)
    def simulator_finish(self):
        payload = self._json_body()
        call = request.env['casafolino.voice.call'].sudo().browse(payload.get('call_id'))
        if not call.exists():
            return request.make_json_response({'error': 'call not found'}, status=404)
        call.write({
            'state': 'completed',
            'ended_at': fields.Datetime.now(),
            'outcome': call.outcome or 'other',
        })
        call.message_post(body='Simulazione Voice AI chiusa.', message_type='comment', subtype_xmlid='mail.mt_note')
        return request.make_json_response({'ok': True})

    @http.route('/voice_ai/simulator/speech', type='http', auth='user', methods=['POST'], csrf=False)
    def simulator_speech(self):
        payload = self._json_body()
        text = (payload.get('text') or '').strip()
        if not text:
            return request.make_json_response({'error': 'text required'}, status=400)
        try:
            audio = self._openai_speech(text)
        except ValueError as exc:
            return request.make_json_response({'error': str(exc)}, status=502)
        return request.make_response(audio, headers=[
            ('Content-Type', 'audio/mpeg'),
            ('Cache-Control', 'no-store'),
        ])

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
    def outbound_next(self, **kwargs):
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
