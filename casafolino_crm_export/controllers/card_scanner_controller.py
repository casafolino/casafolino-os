import base64
import json
import logging
import os

import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

COUNTRY_LANG_MAP = {
    'FR': 'fr_FR', 'MC': 'fr_FR', 'BE': 'fr_FR',
    'CA': 'en_US',
}
FR_CITIES = {'montréal', 'montreal', 'québec', 'quebec'}
DEFAULT_LANG = 'en_US'


class CardScannerController(http.Controller):

    # Map base64 magic prefix → MIME (widget posts raw base64, no data-URL header).
    _IMG_PREFIX_MIME = {
        '/9j/': 'image/jpeg',
        'iVBOR': 'image/png',
        'R0lGOD': 'image/gif',
        'UklGR': 'image/webp',
    }

    def _detect_media_type(self, image_data):
        for prefix, mime in self._IMG_PREFIX_MIME.items():
            if image_data.startswith(prefix):
                return mime
        return 'image/jpeg'

    @http.route('/casafolino/crm/card-scan', type='json', auth='user', methods=['POST'])
    def scan_card(self, image_data):
        """OCR a business card image via Anthropic Claude vision. Returns extracted JSON.
        Allineato alla PWA scanner: provider Anthropic, modello claude-sonnet-4-6,
        immagine base64 → JSON. Chiave da env ANTHROPIC_API_KEY (mai loggata),
        fallback ir.config_parameter casafolino.anthropic_api_key."""
        api_key = os.environ.get('ANTHROPIC_API_KEY') or request.env[
            'ir.config_parameter'].sudo().get_param('casafolino.anthropic_api_key', '')
        if not api_key:
            return {'error': 'ANTHROPIC_API_KEY non configurata', 'data': {}}

        try:
            payload = {
                'model': 'claude-sonnet-4-6',
                'max_tokens': 1024,
                'temperature': 0,
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': self._detect_media_type(image_data),
                                'data': image_data,
                            },
                        },
                        {
                            'type': 'text',
                            'text': (
                                'Extract all information from this business card image. '
                                'Return ONLY valid JSON with these keys: '
                                'first_name, last_name, email, phone, mobile, company, '
                                'job_title, country, city, address, website. '
                                'Use null for missing fields. No markdown, no explanation.'
                            ),
                        },
                    ],
                }],
            }
            resp = requests.post(
                'https://api.anthropic.com/v1/messages',
                json=payload,
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                timeout=45,
            )
            resp.raise_for_status()
            raw = resp.json()['content'][0]['text'].strip()
            # Strip markdown fences if present
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            data = json.loads(raw)
        except requests.Timeout:
            _logger.warning('Anthropic Vision timeout')
            return {'error': 'timeout', 'data': {}}
        except Exception as e:
            _logger.warning('Anthropic Vision error: %s', e)
            return {'error': str(e), 'data': {}}

        # Guess language from country
        lang = DEFAULT_LANG
        country_raw = (data.get('country') or '').strip()
        city_raw = (data.get('city') or '').strip().lower()
        country_code = self._guess_country_code(country_raw)
        if country_code:
            lang = COUNTRY_LANG_MAP.get(country_code, DEFAULT_LANG)
            if country_code == 'CA' and city_raw in FR_CITIES:
                lang = 'fr_FR'

        data['suggested_lang'] = lang
        data['country_code'] = country_code
        return {'error': None, 'data': data}

    @http.route('/casafolino/crm/card-confirm', type='json', auth='user', methods=['POST'])
    def confirm_card(self, form_data, image_data, language='en_US', send_email=True):
        """Create partner + lead + send follow-up email."""
        try:
            result = request.env['crm.lead'].create_from_card_scan({
                'form_data': form_data,
                'image_data': image_data,
                'language': language,
                'send_email': send_email,
            })
            return result
        except Exception as e:
            _logger.exception('Card confirm error')
            return {'success': False, 'error': str(e)}

    def _guess_country_code(self, country_name):
        """Best-effort country name → ISO code."""
        if not country_name:
            return ''
        country_name = country_name.strip()
        # Try direct match
        country = request.env['res.country'].sudo().search(
            ['|', ('name', '=ilike', country_name), ('code', '=ilike', country_name)],
            limit=1,
        )
        if country:
            return country.code
        # Common aliases
        aliases = {
            'usa': 'US', 'united states': 'US', 'u.s.a.': 'US', 'u.s.': 'US',
            'uk': 'GB', 'united kingdom': 'GB', 'england': 'GB',
            'france': 'FR', 'canada': 'CA', 'belgium': 'BE', 'belgique': 'BE',
            'monaco': 'MC', 'italy': 'IT', 'italia': 'IT',
            'germany': 'DE', 'deutschland': 'DE', 'spain': 'ES', 'españa': 'ES',
        }
        return aliases.get(country_name.lower(), '')
