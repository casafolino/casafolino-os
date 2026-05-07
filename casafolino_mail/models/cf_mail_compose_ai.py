import json
import logging

import requests as req

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CFMailComposeAI(models.AbstractModel):
    """Brief #6.4 — AI assist endpoints for F8 composer.
    AbstractModel: no DB table, callable via JSON-RPC."""
    _name = 'cf.mail.compose.ai'
    _description = 'AI assist endpoints for F8 composer'

    @api.model
    def cf_suggest_tone(self, thread_id=None, current_body='', partner_id=None):
        if not partner_id:
            return {'suggested_tone': 'cordiale', 'reasoning': '', 'rewrite_hint': ''}
        partner = self.env['res.partner'].browse(partner_id)
        thread_summary = self._summarize_thread(thread_id) if thread_id else ''
        prompt = (
            "You analyze an email context to suggest tone.\n"
            "Recipient: %s (%s), Country: %s\n"
            "Thread: %s\nDraft: %s\n\n"
            "Suggest one tone: formal, cordiale, diretto, urgente.\n"
            'Return JSON ONLY: {"suggested_tone": "<tone>", "reasoning": "<1 sentence>", '
            '"rewrite_hint": "<short hint>"}'
        ) % (partner.name, partner.email or '', partner.country_id.name or 'unknown',
             thread_summary[:500], (current_body or '')[:500])
        try:
            data = self._call_groq_json(prompt)
            return {
                'suggested_tone': data.get('suggested_tone', 'cordiale'),
                'reasoning': data.get('reasoning', ''),
                'rewrite_hint': data.get('rewrite_hint', ''),
            }
        except Exception as e:
            _logger.warning("cf_suggest_tone failed: %s", e)
            return {'suggested_tone': 'cordiale', 'reasoning': '', 'rewrite_hint': ''}

    @api.model
    def cf_detect_language(self, text='', partner_id=None):
        if not text or len(text) < 20:
            return {'detected_lang': '', 'partner_lang': '', 'mismatch': False}
        partner = self.env['res.partner'].browse(partner_id) if partner_id else None
        partner_lang = (partner.lang or 'it_IT')[:2] if partner else 'it'
        detected = self._heuristic_lang_detect(text)
        if not detected:
            try:
                raw = self._call_groq_raw(
                    "Detect language. Return ONLY the ISO code (en/it/es/fr/de):\n\n" + text[:300],
                    max_tokens=10)
                detected = raw.strip().lower()[:2]
            except Exception:
                detected = 'unknown'
        return {
            'detected_lang': detected,
            'partner_lang': partner_lang,
            'mismatch': bool(detected and partner_lang and detected != partner_lang),
        }

    @api.model
    def cf_translate(self, text='', target_lang='it'):
        if not text:
            return {'translated': ''}
        prompt = (
            "Translate this email draft to %s. Preserve business tone and technical terms. "
            "Return ONLY the translated text:\n\n%s"
        ) % (target_lang, text[:3000])
        try:
            translated = self._call_groq_raw(prompt, max_tokens=1500)
            return {'translated': translated.strip()}
        except Exception as e:
            _logger.warning("cf_translate failed: %s", e)
            return {'translated': text}

    @api.model
    def cf_get_signature(self, partner_id=None):
        user = self.env.user
        if not partner_id:
            return {'signature_html': self._sig_short(user), 'reason': 'default'}
        partner = self.env['res.partner'].browse(partner_id)
        mail_count = self.env['casafolino.mail.message'].search_count([
            ('partner_id', '=', partner_id)])
        is_intl = partner.country_id and partner.country_id.code != 'IT'
        is_new = mail_count < 5
        lang = (partner.lang or 'en')[:2] if is_intl else 'it'
        if is_new:
            return {
                'signature_html': self._sig_extended(user, lang),
                'reason': 'Partner nuovo%s' % (' + estero' if is_intl else ''),
            }
        return {
            'signature_html': self._sig_short(user, lang),
            'reason': 'Partner fidelizzato%s' % (' + estero' if is_intl else ''),
        }

    @api.model
    def cf_suggest_quick_replies(self, thread_id=None, partner_id=None):
        if not thread_id:
            return {'replies': []}
        thread_summary = self._summarize_thread(thread_id, max_messages=5)
        if not thread_summary:
            return {'replies': []}
        partner = self.env['res.partner'].browse(partner_id) if partner_id else None
        prompt = (
            "You are an export sales assistant for CasaFolino (Italian gourmet food).\n"
            "Thread (most recent first):\n%s\n"
            "Recipient: %s\n\n"
            "Suggest 2-3 quick reply options (1-3 sentences each, business-appropriate).\n"
            'Return JSON ONLY: {"replies": [{"short_label": "<3-5 words>", '
            '"text": "<full reply>", "tone": "cordiale|formal|diretto"}]}'
        ) % (thread_summary[:1500], partner.name if partner else 'recipient')
        try:
            data = self._call_groq_json(prompt, max_tokens=600)
            return {'replies': (data.get('replies') or [])[:3]}
        except Exception as e:
            _logger.warning("cf_suggest_quick_replies failed: %s", e)
            return {'replies': []}

    @api.model
    def cf_score_snippets(self, snippet_ids=None, context_text='', partner_id=None):
        if not snippet_ids or not context_text:
            return {'scored_ids': [{'id': s, 'score': 0.5, 'why': ''} for s in (snippet_ids or [])]}
        snippets = self.env['casafolino.mail.snippet'].browse(snippet_ids)
        payload = [{'id': s.id, 'name': s.name or '', 'body': (s.body or '')[:200]}
                   for s in snippets if s.exists()]
        if not payload:
            return {'scored_ids': []}
        partner = self.env['res.partner'].browse(partner_id) if partner_id else None
        prompt = (
            "Score these email snippets for relevance.\n"
            "Context: %s\nPartner: %s\nSnippets: %s\n\n"
            'Return JSON ONLY: {"scored": [{"id": <int>, "score": 0.0-1.0, "why": "<short>"}]}\n'
            "Higher = more relevant. Off-topic < 0.3."
        ) % (context_text[:500], partner.name if partner else 'none', json.dumps(payload))
        try:
            data = self._call_groq_json(prompt, max_tokens=400)
            return {'scored_ids': data.get('scored', [])}
        except Exception as e:
            _logger.warning("cf_score_snippets failed: %s", e)
            return {'scored_ids': [{'id': s, 'score': 0.5, 'why': ''} for s in snippet_ids]}

    # === Helpers ===

    def _call_groq_json(self, prompt, max_tokens=600):
        raw = self._call_groq_raw(prompt, max_tokens=max_tokens)
        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            raise ValueError('No JSON in Groq response')
        return json.loads(match.group())

    def _call_groq_raw(self, prompt, max_tokens=600):
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.groq_api_key', '')
        if not api_key:
            raise ValueError('Groq API key not configured')
        resp = req.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': 'Bearer %s' % api_key,
                'Content-Type': 'application/json',
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [
                    {'role': 'system', 'content': 'You are a CRM email assistant. Return JSON when asked.'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.2,
                'max_tokens': max_tokens,
            },
            timeout=30,
        )
        if not resp.ok:
            raise ValueError('Groq %d: %s' % (resp.status_code, resp.text[:200]))
        return resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')

    def _summarize_thread(self, thread_id, max_messages=3):
        msgs = self.env['casafolino.mail.message'].search([
            ('thread_id', '=', thread_id)
        ], limit=max_messages, order='email_date desc')
        if not msgs:
            return ''
        lines = []
        for m in msgs:
            lines.append('From: %s | Subject: %s | %s' % (
                m.sender_email or '?', m.subject or '(no subject)',
                (m.body_plain or m.body_html or '')[:200]))
        return '\n'.join(lines)

    def _heuristic_lang_detect(self, text):
        text_lower = text.lower()
        markers = {
            'it': ['gentile', 'cordiali', 'saluti', 'buongiorno', 'grazie', 'distinti'],
            'en': ['dear', 'kind regards', 'thank you', 'best', 'sincerely', 'thanks'],
            'es': ['estimado', 'saludos', 'gracias', 'cordiales'],
            'fr': ['cordialement', 'merci', 'bonjour', 'salutations'],
            'de': ['sehr geehrte', 'freundlichen', 'danke'],
        }
        scores = {lang: sum(1 for m in mks if m in text_lower) for lang, mks in markers.items()}
        top = max(scores, key=scores.get)
        return top if scores[top] >= 2 else ''

    def _sig_short(self, user, lang='it'):
        name = user.name or ''
        email = user.email or ''
        if lang == 'it':
            return '<p>Cordiali saluti,<br/>%s<br/>%s</p>' % (name, email)
        return '<p>Best regards,<br/>%s<br/>%s</p>' % (name, email)

    def _sig_extended(self, user, lang='it'):
        name = user.name or ''
        email = user.email or ''
        if lang == 'it':
            return (
                '<p>Cordiali saluti,<br/>%s<br/>%s<br/>'
                'CasaFolino Srls Società Benefit<br/>'
                'Tel: +39 0968 1945080 | Web: casafolino.com<br/>'
                'BRC | IFS | Biologico</p>'
            ) % (name, email)
        return (
            '<p>Best regards,<br/>%s<br/>%s<br/>'
            'CasaFolino Srls Società Benefit<br/>'
            'Tel: +39 0968 1945080 | Web: casafolino.com<br/>'
            'BRC | IFS | Organic Certified</p>'
        ) % (name, email)
