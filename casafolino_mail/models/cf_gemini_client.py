import json
import logging
import re
import requests as req

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CFGeminiClient(models.AbstractModel):
    """Google Gemini AI REST API client helper for Odoo.
    Uses native requests library to communicate with Gemini REST endpoints."""
    _name = 'cf.gemini.client'
    _description = 'Google Gemini AI Client'

    @api.model
    def _get_api_key(self):
        """Get Gemini API Key from ir.config_parameter securely."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'casafolino.gemini_api_key', ''
        )

    @api.model
    def _call_gemini_raw(self, system_instruction, prompt, model="gemini-2.5-flash", temperature=0.1):
        """Call Gemini REST API and return raw response string."""
        api_key = self._get_api_key()
        if not api_key:
            raise UserError("Gemini API Key non configurata in Odoo (casafolino.gemini_api_key).")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        headers = {
            'Content-Type': 'application/json',
        }

        # Build standard Gemini REST payload
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            resp = req.post(url, headers=headers, json=payload, timeout=25)
            if not resp.ok:
                _logger.warning("Gemini API Error %d: %s", resp.status_code, resp.text)
                return ""

            resp_data = resp.json()
            candidates = resp_data.get('candidates', [])
            if not candidates:
                _logger.warning("Gemini API returned no candidates: %s", resp_data)
                return ""

            parts = candidates[0].get('content', {}).get('parts', [])
            if not parts:
                _logger.warning("Gemini API candidate has no parts: %s", candidates[0])
                return ""

            return parts[0].get('text', '').strip()
        except Exception as e:
            _logger.exception("Errore nella chiamata a Gemini: %s", e)
            return ""

    @api.model
    def _call_gemini_json(self, system_instruction, prompt, model="gemini-2.5-flash", temperature=0.1):
        """Call Gemini REST API forcing JSON output and return parsed python dictionary."""
        api_key = self._get_api_key()
        if not api_key:
            raise UserError("Gemini API Key non configurata in Odoo.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        headers = {
            'Content-Type': 'application/json',
        }

        # Build standard Gemini REST payload with responseMimeType: application/json
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            resp = req.post(url, headers=headers, json=payload, timeout=25)
            if not resp.ok:
                _logger.warning("Gemini API JSON Error %d: %s", resp.status_code, resp.text)
                return {}

            resp_data = resp.json()
            candidates = resp_data.get('candidates', [])
            if not candidates:
                return {}

            parts = candidates[0].get('content', {}).get('parts', [])
            if not parts:
                return {}

            content = parts[0].get('text', '').strip()

            # Clean possible markdown block wrappers
            if content.startswith('```'):
                content = re.sub(r'^```\w*\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
                content = content.strip()

            return json.loads(content)
        except json.JSONDecodeError as je:
            _logger.warning("Errore decodifica JSON da Gemini. Risposta raw: %s. Errore: %s", content, je)
            return {}
        except Exception as e:
            _logger.exception("Errore nella chiamata JSON a Gemini: %s", e)
            return {}
