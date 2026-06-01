import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CasafolinoTelegramController(http.Controller):
    """Secure JSON-RPC / REST endpoints for Telegram Bot Bridge."""

    def _validate_token(self):
        """Validate token from request header or json params."""
        ICP = request.env['ir.config_parameter'].sudo()
        expected_token = ICP.get_param('casafolino.telegram_bridge_token', '')
        if not expected_token:
            _logger.warning("Telegram controller: casafolino.telegram_bridge_token non configurato in Odoo.")
            return False
            
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1].strip()
            if token == expected_token:
                return True
                
        # Also check JSON body parameters
        try:
            params = request.get_json_data() or {}
            if params.get('token') == expected_token:
                return True
        except Exception:
            pass

        return False

    @http.route('/casafolino_mail/telegram/draft', type='json', auth='public', methods=['POST'], csrf=False)
    def telegram_draft(self, **kw):
        """Endpoint to generate an email reply draft using Gemini."""
        if not self._validate_token():
            return {'success': False, 'error': 'Non autorizzato (Token non valido)'}

        params = request.get_json_data() or {}
        message_id = params.get('message_id')
        instruction = params.get('instruction') or ''

        if not message_id:
            return {'success': False, 'error': 'message_id mancante'}

        Message = request.env['casafolino.mail.message'].sudo()
        msg = Message.browse(int(message_id))
        if not msg.exists():
            return {'success': False, 'error': 'Messaggio non trovato'}

        # Get original email text context
        original_body = msg.body_plain or msg.snippet or ''
        
        # Build prompt for Gemini
        system_instruction = (
            "You are an expert sales assistant for CasaFolino, an Italian artisan gourmet food company.\n"
            "Your task is to write a highly professional, polite, and helpful email reply to the customer's email.\n"
            "Write the reply in the same language as the customer's email (typically Italian or English).\n"
            "Do NOT include any email subject or headers. Output ONLY the email body text. Do not put markdown placeholders like [Your Name] unless necessary, try to sign off as the team or dynamically if context exists. Keep it elegant."
        )

        user_prompt = (
            f"Customer email sender: {msg.sender_name or 'Customer'} <{msg.sender_email or ''}>\n"
            f"Customer email subject: {msg.subject or '(no subject)'}\n"
            f"Customer email body:\n\"\"\"\n{original_body[:3000]}\n\"\"\"\n\n"
        )
        
        if instruction:
            user_prompt += f"USER INSTRUCTIONS for the reply: {instruction}\n\n"
        else:
            user_prompt += "Write a friendly, professional response acknowledging receipt and addressing any questions in the email.\n\n"

        user_prompt += "Draft Response:"

        try:
            draft = request.env['cf.gemini.client']._call_gemini_raw(system_instruction, user_prompt)
            if not draft:
                return {'success': False, 'error': 'Gemini ha restituito una bozza vuota'}
            return {
                'success': True,
                'draft': draft,
                'sender_email': msg.sender_email,
                'subject': f"Re: {msg.subject}" if msg.subject and not msg.subject.startswith('Re:') else msg.subject or 'Re: Email'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/casafolino_mail/telegram/send', type='json', auth='public', methods=['POST'], csrf=False)
    def telegram_send(self, **kw):
        """Endpoint to send the draft email reply."""
        if not self._validate_token():
            return {'success': False, 'error': 'Non autorizzato'}

        params = request.get_json_data() or {}
        message_id = params.get('message_id')
        body = params.get('body')
        to_address = params.get('to_address')
        subject = params.get('subject')

        if not message_id or not body:
            return {'success': False, 'error': 'message_id o body mancante'}

        Message = request.env['casafolino.mail.message'].sudo()
        msg = Message.browse(int(message_id))
        if not msg.exists():
            return {'success': False, 'error': 'Messaggio originale non trovato'}

        to_addr = to_address or msg.sender_email
        sub = subject or (f"Re: {msg.subject}" if msg.subject and not msg.subject.startswith('Re:') else msg.subject or 'Re: Email')

        try:
            # Send using standard Odoo reply method
            # Use msg.account_id.id if exists, else it resolves automatically
            res = Message.send_reply(
                message_id=msg.id,
                to_address=to_addr,
                subject=sub,
                body=body,
                account_id=msg.account_id.id
            )
            if isinstance(res, dict) and not res.get('success', True):
                return {'success': False, 'error': res.get('error', 'Invio fallito')}
                
            # Also mark the original message as read
            msg.write({'is_read': True})
            return {'success': True, 'message': 'Email inviata con successo!'}
        except Exception as e:
            _logger.exception("Telegram SMTP Send Error: %s", e)
            return {'success': False, 'error': str(e)}

    @http.route('/casafolino_mail/telegram/mark_read', type='json', auth='public', methods=['POST'], csrf=False)
    def telegram_mark_read(self, **kw):
        """Endpoint to mark email as read in Odoo."""
        if not self._validate_token():
            return {'success': False, 'error': 'Non autorizzato'}

        params = request.get_json_data() or {}
        message_id = params.get('message_id')

        if not message_id:
            return {'success': False, 'error': 'message_id mancante'}

        Message = request.env['casafolino.mail.message'].sudo()
        msg = Message.browse(int(message_id))
        if not msg.exists():
            return {'success': False, 'error': 'Messaggio non trovato'}

        try:
            msg.write({'is_read': True})
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
