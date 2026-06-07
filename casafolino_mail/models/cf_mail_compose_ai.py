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
        account = self._get_user_account()
        signature = self.env['casafolino.mail.signature'].sudo()._ensure_official_for_account(account) if account else False
        signature_html = signature.body_html if signature else self._sig_short(self.env.user)
        if not partner_id:
            return {'signature_html': signature_html, 'reason': 'Firma ufficiale account'}
        partner = self.env['res.partner'].browse(partner_id)
        mail_count = self.env['casafolino.mail.message'].search_count([
            ('partner_id', '=', partner_id)])
        is_intl = partner.country_id and partner.country_id.code != 'IT'
        is_new = mail_count < 5
        if is_new:
            return {
                'signature_html': signature_html,
                'reason': 'Partner nuovo%s' % (' + estero' if is_intl else ''),
            }
        return {
            'signature_html': signature_html,
            'reason': 'Partner fidelizzato%s' % (' + estero' if is_intl else ''),
        }

    @api.model
    def cf_suggest_quick_replies(self, thread_id=None, partner_id=None):
        if not thread_id:
            return {'replies': self._fallback_replies('', partner_id)}
        thread_summary = self._summarize_thread(thread_id, max_messages=5)
        if not thread_summary:
            return {'replies': self._fallback_replies('', partner_id)}
        partner = self.env['res.partner'].browse(partner_id) if partner_id else None
        prompt = (
            "You are not a generic email assistant. You are CasaFolino's senior Export Manager "
            "and Commercial Back Office Manager working for Antonio Folino.\n"
            "Your job is to remove work from Antonio: analyze the opportunity, decide the next "
            "commercial move, identify missing data, and draft an excellent reply.\n\n"
            "Thread (most recent first):\n%s\n"
            "Recipient: %s\n\n"
            "Create 3 operational answer cards. Each card must include:\n"
            "1) an internal action checklist for CasaFolino (2-4 bullets),\n"
            "2) a complete polished email draft ready to send (120-180 words),\n"
            "3) explicit next step: call, qualification data, catalogue/sample/meeting.\n"
            "Do NOT create short SMS-style replies. Do NOT invent prices, dates, certifications, "
            "attachments or promises. If catalogue/price list is useful, say it will be shared "
            "after/with qualification data.\n"
            'Return JSON ONLY: {"replies": [{"short_label": "<3-5 words>", '
            '"text": "<full reply>", "tone": "cordiale|formal|diretto"}]}'
        ) % (thread_summary[:2500], partner.name if partner else 'recipient')
        try:
            data = self._call_groq_json(prompt, max_tokens=1800)
            replies = (data.get('replies') or [])[:3]
            if self._replies_are_too_weak(replies):
                replies = self._fallback_replies(thread_summary, partner_id)
            return {'replies': replies}
        except Exception as e:
            _logger.warning("cf_suggest_quick_replies failed: %s", e)
            return {'replies': self._fallback_replies(thread_summary, partner_id)}

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
        # Prova prima Gemini se configurato
        gemini_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.gemini_api_key', '')
        if gemini_key:
            try:
                system_instruction = "You are a CRM email assistant. Return JSON when asked."
                res = self.env['cf.gemini.client']._call_gemini_json(system_instruction, prompt)
                if res:
                    return res
            except Exception as e:
                _logger.warning("Gemini JSON fallito in composer AI: %s. Procedo con fallback Groq.", e)

        raw = self._call_groq_raw(prompt, max_tokens=max_tokens)
        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            raise ValueError('No JSON in Groq response')
        return json.loads(match.group())

    def _call_groq_raw(self, prompt, max_tokens=600):
        # Prova prima Gemini se configurato
        gemini_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.gemini_api_key', '')
        if gemini_key:
            try:
                system_instruction = "You are a CRM email assistant."
                res = self.env['cf.gemini.client']._call_gemini_raw(system_instruction, prompt)
                if res:
                    return res
            except Exception as e:
                _logger.warning("Gemini RAW fallito in composer AI: %s. Procedo con fallback Groq.", e)

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
        if not thread_id:
            return ''
        Message = self.env['casafolino.mail.message']
        msg = Message.browse(thread_id)
        if msg.exists():
            domain = [('thread_id', '=', msg.thread_id.id)] if msg.thread_id else [('id', '=', msg.id)]
        else:
            domain = [('thread_id', '=', thread_id)]
        msgs = Message.search(domain, limit=max_messages, order='email_date desc')
        if not msgs:
            return ''
        lines = []
        for m in msgs:
            lines.append('From: %s | Subject: %s | %s' % (
                m.sender_email or '?', m.subject or '(no subject)',
                (m.body_plain or m.body_html or '')[:200]))
        return '\n'.join(lines)

    def _fallback_replies(self, context_text='', partner_id=None):
        text = (context_text or '').lower()
        partner = self.env['res.partner'].browse(partner_id) if partner_id else self.env['res.partner']
        name = partner.name if partner and partner.exists() else 'Team'
        if any(token in text for token in ['sample', 'campion', 'taste', 'feedback']):
            return [
                {
                    'short_label': 'Campioni: piano',
                    'text': (
                        'AZIONI INTERNE\n'
                        '- Aprire/aggiornare task campionatura con prodotto, feedback ricevuto e owner.\n'
                        '- Chiedere a produzione/R&D se la modifica e fattibile prima di promettere tempi.\n'
                        '- Pianificare un follow-up scritto con prossimo step e data interna.\n\n'
                        'EMAIL PRONTA\n'
                        'Dear %s,\n\n'
                        'thank you very much for your detailed feedback. We have taken note of each point and I will align internally with our product and production team before confirming the most appropriate next step.\n\n'
                        'To avoid any misunderstanding, I will review the requested adjustments, verify feasibility on our side and then come back to you with a clear update on the next sample version or proposed solution.\n\n'
                        'In the meantime, if there are any priority requirements from your buying or quality team, please share them with us so we can include them in the internal evaluation.\n\n'
                        'Best regards,'
                    ) % name,
                    'tone': 'formal',
                },
                {
                    'short_label': 'Follow-up tecnico',
                    'text': (
                        'AZIONI INTERNE\n'
                        '- Trasformare la mail in task campione con scadenza e responsabile.\n'
                        '- Collegare dossier/lead e allegare eventuali foto o note cliente.\n'
                        '- Preparare una risposta dopo conferma tecnica, senza inventare tempi.\n\n'
                        'EMAIL PRONTA\n'
                        'Dear %s,\n\n'
                        'thank you for sharing these observations. I confirm that we will treat them as an internal technical follow-up, so the next answer you receive from us will be based on a checked position rather than a generic reply.\n\n'
                        'I am forwarding the points to the relevant team and will come back with a structured update covering feasibility, any clarification needed and the next operational step.\n\n'
                        'This way we can keep the project moving while making sure the answer is precise and useful for your team.\n\n'
                        'Best regards,'
                    ) % name,
                    'tone': 'diretto',
                },
            ]
        if any(token in text for token in ['distribut', 'meeting request', 'fine food', 'catalog', 'price list']):
            return [
                {
                    'short_label': 'Qualifica export',
                    'text': (
                        'AZIONI INTERNE\n'
                        '- Trattare come opportunita export/distribuzione e creare o collegare lead.\n'
                        '- Qualificare canale: HORECA, retail, food service, importazione e area UAE.\n'
                        '- Preparare catalogo, ma chiedere prima focus prodotti e profilo distributivo.\n'
                        '- Proporre call/meeting per capire potenziale reale e prossimi step.\n\n'
                        'EMAIL PRONTA\n'
                        'Dear %s,\n\n'
                        'thank you very much for reaching out and for your interest in CasaFolino. Your focus on premium Italian food distribution in the UAE sounds aligned with the type of international partnership we are open to evaluating.\n\n'
                        'Before sending a generic proposal, I would prefer to understand your commercial structure a little better: your main channels (HORECA, retail, food service or gourmet stores), the product categories you are most interested in, and whether you already import Italian specialty food products into the UAE.\n\n'
                        'Once we have this context, we can share the most relevant CasaFolino catalogue selection and discuss the best next step, including a short introductory call or a meeting during Fine Food Australia if convenient.\n\n'
                        'Best regards,'
                    ) % name,
                    'tone': 'formal',
                },
                {
                    'short_label': 'Call + catalogo',
                    'text': (
                        'AZIONI INTERNE\n'
                        '- Inviare risposta calda ma qualificante.\n'
                        '- Allegare catalogo se disponibile, senza listino prima della qualifica.\n'
                        '- Chiedere prodotti target, volumi indicativi e clienti serviti.\n'
                        '- Mettere reminder per follow-up entro 3-5 giorni.\n\n'
                        'EMAIL PRONTA\n'
                        'Dear %s,\n\n'
                        'thank you for your message and for the clear introduction of Noor Al Huda Trading LLC. We would be pleased to explore whether there is a concrete fit between your UAE distribution network and CasaFolino products.\n\n'
                        'To move efficiently, I suggest a short call where we can understand your customer base, the product families you are looking for, and the type of positioning you want to build in the UAE market.\n\n'
                        'In parallel, we can share our catalogue so you can start reviewing the range and identify the categories with the strongest potential for your clients.\n\n'
                        'Please let me know a suitable time for a short introductory call.\n\n'
                        'Best regards,'
                    ) % name,
                    'tone': 'cordiale',
                },
                {
                    'short_label': 'Backoffice dati',
                    'text': (
                        'AZIONI INTERNE\n'
                        '- Richiedere dati azienda e buyer/import manager.\n'
                        '- Verificare se serve creazione anagrafica e dossier UAE.\n'
                        '- Preparare catalogo mirato e successivo task commerciale.\n'
                        '- Non inviare listino completo prima di capire canale e volumi.\n\n'
                        'EMAIL PRONTA\n'
                        'Dear %s,\n\n'
                        'thank you for contacting CasaFolino. We can certainly evaluate the opportunity, and I would like to collect the right information first so that our reply is useful and not generic.\n\n'
                        'Could you please share your company profile, the main customer segments you serve in the UAE, the product categories you are interested in, and any import or labelling requirements we should consider?\n\n'
                        'Based on this information, we will prepare the most relevant CasaFolino catalogue selection and define the next step together, whether that is a call, a meeting or a more focused commercial proposal.\n\n'
                        'Best regards,'
                    ) % name,
                    'tone': 'diretto',
                },
            ]
        return [
            {
                'short_label': 'Rispondi bene',
                'text': (
                    'AZIONI INTERNE\n'
                    '- Capire se e commerciale, logistica, admin o materiali.\n'
                    '- Collegare contatto/lead/dossier prima di archiviare la mail.\n'
                    '- Creare task se esiste una promessa o un follow-up.\n\n'
                    'EMAIL PRONTA\n'
                    'Thank you for your message. I will review the details carefully and come back with the most appropriate next step, so we can move forward in a clear and useful way.'
                ),
                'tone': 'cordiale',
            },
            {
                'short_label': 'Chiedi dettagli',
                'text': 'Could you please share a few more details about your request, including target products, market, timing and any specific requirements?',
                'tone': 'formal',
            },
            {
                'short_label': 'Crea follow-up',
                'text': 'Create a follow-up task with owner, deadline, customer objective and the next promised action.',
                'tone': 'diretto',
            },
        ]

    def _replies_are_too_weak(self, replies):
        if not replies:
            return True
        for reply in replies:
            text = (reply.get('text') or '').strip()
            if len(text) < 450 or 'AZIONI INTERNE' not in text.upper():
                return True
        return False

    def _get_user_account(self):
        return self.env['casafolino.mail.account'].sudo().search([
            ('responsible_user_id', '=', self.env.uid),
            ('active', '=', True),
        ], limit=1)

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
