import json
import logging
import re

import requests as req

from odoo import api, models

_logger = logging.getLogger(__name__)


class CFAIRouter(models.AbstractModel):
    _name = 'cf.ai.router'
    _description = 'CasaFolino AI provider router'

    @api.model
    def provider_status(self):
        ICP = self.env['ir.config_parameter'].sudo()
        openai_key = self._openai_key()
        gemini_key = ICP.get_param('casafolino.gemini_api_key', '').strip()
        groq_key = ICP.get_param('casafolino.groq_api_key', '').strip()
        if openai_key:
            primary = 'OpenAI'
        elif gemini_key:
            primary = 'Gemini'
        elif groq_key:
            primary = 'Groq'
        else:
            primary = 'Non configurata'
        return {
            'configured': bool(openai_key or gemini_key or groq_key),
            'primary': primary,
            'openai': bool(openai_key),
            'gemini': bool(gemini_key),
            'groq': bool(groq_key),
            'openai_model': ICP.get_param('casafolino.ai_openai_model', '').strip() or 'gpt-4.1-mini',
            'gemini_model': ICP.get_param('casafolino.ai_gemini_model', '').strip() or 'gemini-2.5-flash',
            'groq_model': ICP.get_param('casafolino.ai_groq_model', '').strip() or 'llama-3.3-70b-versatile',
        }

    @api.model
    def call_json(self, system_instruction, prompt, purpose='generic', max_tokens=700, temperature=0.1):
        raw = self.call_raw(system_instruction, prompt, purpose=purpose, max_tokens=max_tokens, temperature=temperature)
        if isinstance(raw, dict):
            return raw
        match = re.search(r'\{[\s\S]*\}', raw or '')
        if not match:
            raise ValueError('No JSON in AI response')
        return json.loads(match.group())

    @api.model
    def call_raw(self, system_instruction, prompt, purpose='generic', max_tokens=700, temperature=0.1):
        status = self.provider_status()
        errors = []
        if status.get('openai'):
            try:
                return self._call_openai_raw(system_instruction, prompt, max_tokens=max_tokens, temperature=temperature)
            except Exception as exc:
                errors.append('OpenAI: %s' % str(exc)[:180])
                _logger.warning("CasaFolino AI OpenAI failed for %s: %s", purpose, exc)
        if status.get('gemini'):
            try:
                return self.env['cf.gemini.client']._call_gemini_raw(
                    system_instruction,
                    prompt,
                    model=status.get('gemini_model') or 'gemini-2.5-flash',
                    temperature=temperature,
                )
            except Exception as exc:
                errors.append('Gemini: %s' % str(exc)[:180])
                _logger.warning("CasaFolino AI Gemini failed for %s: %s", purpose, exc)
        if status.get('groq'):
            try:
                return self._call_groq_raw(system_instruction, prompt, max_tokens=max_tokens, temperature=temperature)
            except Exception as exc:
                errors.append('Groq: %s' % str(exc)[:180])
                _logger.warning("CasaFolino AI Groq failed for %s: %s", purpose, exc)
        raise ValueError('AI provider non configurato o non disponibile: %s' % ' | '.join(errors))

    def _openai_key(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return (
            ICP.get_param('casafolino.openai_api_key', '').strip()
            or ICP.get_param('casafolino_ai.openai_api_key', '').strip()
            or ICP.get_param('casafolino_voice_ai.openai_api_key', '').strip()
        )

    def _call_openai_raw(self, system_instruction, prompt, max_tokens=700, temperature=0.1):
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = self._openai_key()
        if not api_key:
            raise ValueError('OpenAI API key not configured')
        model = ICP.get_param('casafolino.ai_openai_model', '').strip() or 'gpt-4.1-mini'
        resp = req.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': 'Bearer %s' % api_key,
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_instruction},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': temperature,
                'max_tokens': max_tokens,
            },
            timeout=35,
        )
        if not resp.ok:
            raise ValueError('OpenAI %d: %s' % (resp.status_code, resp.text[:240]))
        return resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')

    def _call_groq_raw(self, system_instruction, prompt, max_tokens=700, temperature=0.1):
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('casafolino.groq_api_key', '').strip()
        if not api_key:
            raise ValueError('Groq API key not configured')
        model = ICP.get_param('casafolino.ai_groq_model', '').strip() or 'llama-3.3-70b-versatile'
        resp = req.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': 'Bearer %s' % api_key,
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_instruction},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': temperature,
                'max_tokens': max_tokens,
            },
            timeout=35,
        )
        if not resp.ok:
            raise ValueError('Groq %d: %s' % (resp.status_code, resp.text[:240]))
        return resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
