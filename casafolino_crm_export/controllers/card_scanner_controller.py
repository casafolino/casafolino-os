import base64
import json
import logging
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

COUNTRY_LANG_MAP = {
    'FR': 'fr_FR', 'MC': 'fr_FR', 'BE': 'fr_FR',
    'IT': 'it_IT',
    'DE': 'de_DE', 'AT': 'de_DE', 'CH': 'de_DE',
    'ES': 'es_ES', 'MX': 'es_ES', 'AR': 'es_ES', 'CL': 'es_ES',
    'CO': 'es_ES', 'PE': 'es_ES',
    'CA': 'en_US',
}
FR_CITIES = {'montréal', 'montreal', 'québec', 'quebec'}
DEFAULT_LANG = 'en_US'


class CardScannerController(http.Controller):

    @http.route('/casafolino/crm/card-scanner/init', type='json', auth='user', methods=['POST'])
    def scanner_init(self):
        fairs = request.env['cf.export.fair'].search([], order='date_start desc, id desc')
        fair_rows = []
        default_fair_id = False
        default_fair = request.env.ref(
            'casafolino_crm_export.cf_export_fair_tuttofood_2026',
            raise_if_not_found=False,
        )
        for fair in fairs:
            template_count = request.env['cf.fair.mail.template'].search_count([
                ('fair_id', '=', fair.id),
                ('auto_send_on_card_scan', '=', True),
                ('active', '=', True),
            ])
            fair_rows.append({
                'id': fair.id,
                'name': fair.name,
                'template_count': template_count,
            })
            if default_fair and fair.id == default_fair.id:
                default_fair_id = fair.id
            elif not default_fair_id and fair.state in ('active', 'followup', 'confirmed'):
                default_fair_id = fair.id
        if not default_fair_id and fair_rows:
            default_fair_id = fair_rows[0]['id']
        return {
            'fairs': fair_rows,
            'default_fair_id': default_fair_id,
        }

    @http.route('/casafolino/crm/card-scan', type='json', auth='user', methods=['POST'])
    def scan_card(self, image_data):
        """OCR a business card image via Groq Vision. Returns extracted JSON."""
        api_key = request.env['ir.config_parameter'].sudo().get_param(
            'casafolino.groq_api_key', ''
        )
        if not api_key:
            return {'error': 'Groq API key non configurata', 'data': {}}

        try:
            payload = {
                'model': 'llama-3.2-90b-vision-preview',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': (
                                'Extract all information from this business card image. '
                                'Return ONLY valid JSON with these keys: '
                                'first_name, last_name, email, phone, mobile, company, '
                                'job_title, country, city, address, website, preferred_language. '
                                'preferred_language must be one of it_IT, en_US, fr_FR, es_ES, de_DE. '
                                'Use null for missing fields. No markdown, no explanation.'
                            ),
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{image_data}',
                            },
                        },
                    ],
                }],
                'temperature': 0.1,
                'max_tokens': 500,
            }
            resp = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                json=payload,
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'User-Agent': 'Mozilla/5.0 (CasaFolino Card Scanner)',
                },
                timeout=15,
            )
            resp.raise_for_status()
            raw = resp.json()['choices'][0]['message']['content']
            # Strip markdown fences if present
            raw = raw.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            data = json.loads(raw)
        except requests.Timeout:
            _logger.warning('Groq Vision timeout')
            return {'error': 'timeout', 'data': {}}
        except Exception as e:
            _logger.warning('Groq Vision error: %s', e)
            return {'error': str(e), 'data': {}}

        # Guess language from country
        lang = data.get('preferred_language') or DEFAULT_LANG
        if lang not in {'it_IT', 'en_US', 'fr_FR', 'es_ES', 'de_DE'}:
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
    def confirm_card(self, form_data, image_data, language='en_US', send_email=True, fair_id=None):
        """Create partner + lead + send follow-up email."""
        try:
            result = request.env['crm.lead'].create_from_card_scan(
                form_data, image_data, language, send_email, fair_id,
            )
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
            'austria': 'AT', 'österreich': 'AT', 'switzerland': 'CH', 'schweiz': 'CH',
            'mexico': 'MX', 'méxico': 'MX', 'argentina': 'AR', 'chile': 'CL',
            'colombia': 'CO', 'peru': 'PE', 'perú': 'PE',
        }
        return aliases.get(country_name.lower(), '')
