import json
import logging
import re
import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ResPartnerMailExt(models.Model):
    _inherit = 'res.partner'

    # Campi extra tipo HubSpot/Zoho
    cf_job_title = fields.Char('Ruolo / Posizione')

    # ── Agente 007 fields ──
    cf_007_enriched = fields.Boolean('007 Arricchito', default=False)
    cf_007_enriched_date = fields.Datetime('007 Data Arricchimento')
    cf_007_potenziale = fields.Selection([
        ('alto', 'Alto'),
        ('medio', 'Medio'),
        ('basso', 'Basso'),
    ], string='007 Potenziale')
    cf_007_ruolo_commerciale = fields.Selection([
        ('produttore', 'Produttore'), ('distributore', 'Distributore'),
        ('importatore', 'Importatore'), ('retailer', 'Retailer/GDO'),
        ('grossista', 'Grossista'), ('agente', 'Agente/Broker'),
        ('ecommerce', 'E-commerce'), ('horeca', 'HoReCa'), ('altro', 'Altro'),
    ], string='Ruolo commerciale')
    cf_007_note_agente = fields.Text('007 Note Agente')
    cf_007_fatturato = fields.Char('007 Fatturato')
    cf_007_fatturato_anno = fields.Char('007 Anno Fatturato')
    cf_007_trend_ricavi = fields.Char('007 Trend Ricavi')
    cf_007_dipendenti = fields.Char('007 Dipendenti')
    cf_007_mercati = fields.Char('007 Mercati')
    cf_007_certificazioni = fields.Char('007 Certificazioni')
    cf_007_piva = fields.Char('007 P.IVA')
    cf_007_pec = fields.Char('007 PEC')
    cf_007_ragione_sociale = fields.Char('007 Ragione Sociale')
    cf_007_settore = fields.Char('007 Settore')
    cf_007_marchi = fields.Char('007 Marchi')
    cf_007_sito_web = fields.Char('007 Sito Web')
    cf_007_telefono = fields.Char('007 Telefono')
    cf_007_indirizzo = fields.Char('007 Indirizzo')
    cf_007_cap = fields.Char('007 CAP')
    cf_007_citta = fields.Char('007 Città')
    cf_007_codice_fiscale = fields.Char('Codice fiscale')
    cf_007_rea = fields.Char('REA')
    cf_007_forma_giuridica = fields.Char('Forma giuridica')
    cf_007_ateco = fields.Char('Codice ATECO')
    cf_007_ateco_desc = fields.Char('Descrizione ATECO')
    cf_007_capitale_sociale = fields.Char('Capitale sociale')
    cf_007_data_costituzione = fields.Char('Data costituzione')
    cf_007_anzianita = fields.Char('Anzianita azienda')
    cf_007_stato_attivita = fields.Selection([
        ('attiva', 'Attiva'), ('inattiva', 'Inattiva'),
        ('liquidazione', 'In liquidazione'), ('fallita', 'Fallita'), ('sconosciuto', 'Sconosciuto'),
    ], string='Stato attivita')
    cf_007_dimensione = fields.Selection([
        ('micro', 'Microimpresa (<10)'), ('piccola', 'Piccola (10-49)'),
        ('media', 'Media (50-249)'), ('grande', 'Grande (250+)'), ('sconosciuto', 'Sconosciuto'),
    ], string='Dimensione azienda')
    cf_007_canali_vendita = fields.Char('Canali di vendita')
    cf_007_prodotti_interesse = fields.Char('Prodotti CF di interesse')
    cf_007_linkedin_company = fields.Char('LinkedIn azienda')
    cf_007_paese = fields.Char('Paese (007)')
    cf_007_provincia = fields.Char('Provincia')
    cf_007_utile = fields.Char('Utile/Perdita')
    cf_007_enriched_from = fields.Selection([
        ('email', 'Da email'), ('piva', 'Da P.IVA'),
        ('nome_azienda', 'Da nome azienda'), ('nome_persona', 'Da nome persona'),
    ], string='Arricchito da')

    cf_department = fields.Char('Reparto')
    cf_linkedin = fields.Char('LinkedIn')
    cf_instagram = fields.Char('Instagram')
    cf_whatsapp = fields.Char('WhatsApp')
    cf_language = fields.Char('Lingua')
    cf_country_origin = fields.Char('Paese di origine')
    cf_birthday = fields.Date('Data di nascita')
    cf_source = fields.Selection([
        ('fiera', 'Fiera'),
        ('email', 'Email'),
        ('referral', 'Referral'),
        ('web', 'Web'),
        ('cold', 'Cold outreach'),
        ('altro', 'Altro'),
    ], string='Fonte contatto')
    cf_fairs = fields.Char('Fiere frequentate')
    cf_notes = fields.Text('Note private')
    cf_rating = fields.Selection([
        ('1', '★'),
        ('2', '★★'),
        ('3', '★★★'),
        ('4', '★★★★'),
        ('5', '★★★★★'),
    ], string='Valutazione')
    cf_tag_ids = fields.Many2many(
        'cf.contact.tag',
        'cf_partner_tag_rel',
        'partner_id', 'tag_id',
        string='Tag CasaFolino'
    )
    cf_last_contact = fields.Datetime('Ultimo contatto', compute='_compute_last_contact', store=True)
    cf_email_count = fields.Integer('Email totali', compute='_compute_email_count')
    cf_opt_out = fields.Boolean('Opt-out email marketing', default=False)
    cf_gdpr_consent = fields.Boolean('Consenso GDPR', default=False)
    cf_gdpr_date = fields.Date('Data consenso GDPR')

    @api.depends('message_ids')
    def _compute_last_contact(self):
        for p in self:
            msgs = self.env['cf.mail.message'].search([
                ('partner_id', '=', p.id)
            ], order='date desc', limit=1)
            p.cf_last_contact = msgs.date if msgs else False

    def _compute_email_count(self):
        for p in self:
            p.cf_email_count = self.env['cf.mail.message'].search_count([
                ('partner_id', '=', p.id)
            ])

    @api.model
    def get_contact_detail(self, *args, **kw):
        partner_id = kw.get('partner_id')
        if not partner_id:
            return {}
        p = self.browse(int(partner_id))
        if not p.exists():
            return {}
        return {
            'id': p.id,
            'name': p.name or '',
            'email': p.email or '',
            'phone': p.phone or '',
            'mobile': p.mobile or '',
            'company': p.parent_id.name if p.parent_id else (p.company_name or ''),
            'job_title': p.cf_job_title or p.function or '',
            'department': p.cf_department or '',
            'country': p.country_id.name if p.country_id else '',
            'language': p.cf_language or '',
            'linkedin': p.cf_linkedin or '',
            'instagram': p.cf_instagram or '',
            'whatsapp': p.cf_whatsapp or '',
            'source': p.cf_source or '',
            'fairs': p.cf_fairs or '',
            'notes': p.cf_notes or '',
            'rating': p.cf_rating or '',
            'opt_out': p.cf_opt_out,
            'gdpr_consent': p.cf_gdpr_consent,
            'gdpr_date': p.cf_gdpr_date.strftime('%d/%m/%Y') if p.cf_gdpr_date else '',
            'tags': [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in p.cf_tag_ids],
            'email_count': p.cf_email_count,
            'last_contact': p.cf_last_contact.strftime('%d/%m/%Y %H:%M') if p.cf_last_contact else '',
        }

    @api.model
    def save_contact(self, *args, **kw):
        partner_id = kw.get('id')
        vals = {}
        fields_map = {
            'name': 'name', 'email': 'email', 'phone': 'phone', 'mobile': 'mobile',
            'job_title': 'cf_job_title', 'department': 'cf_department',
            'language': 'cf_language', 'linkedin': 'cf_linkedin',
            'instagram': 'cf_instagram', 'whatsapp': 'cf_whatsapp',
            'source': 'cf_source', 'fairs': 'cf_fairs', 'notes': 'cf_notes',
            'rating': 'cf_rating', 'opt_out': 'cf_opt_out',
            'gdpr_consent': 'cf_gdpr_consent',
        }
        for k, v in fields_map.items():
            if k in kw:
                vals[v] = kw[k]

        if kw.get('tag_ids'):
            vals['cf_tag_ids'] = [(6, 0, [int(t) for t in kw['tag_ids']])]

        if partner_id:
            p = self.browse(int(partner_id))
            p.write(vals)
        else:
            p = self.create(vals)
        return {'success': True, 'id': p.id}

    @api.model
    def search_contacts(self, *args, **kw):
        query = kw.get('query') or ''
        tag_ids = kw.get('tag_ids') or []
        limit = int(kw.get('limit') or 30)

        domain = []
        if query:
            domain += ['|', '|', '|',
                ('name', 'ilike', query),
                ('email', 'ilike', query),
                ('cf_job_title', 'ilike', query),
                ('company_name', 'ilike', query),
            ]
        if tag_ids:
            domain.append(('cf_tag_ids', 'in', [int(t) for t in tag_ids]))

        partners = self.search(domain, limit=limit, order='name')
        result = []
        for p in partners:
            result.append({
                'id': p.id,
                'name': p.name or '',
                'email': p.email or '',
                'company': p.parent_id.name if p.parent_id else (p.company_name or ''),
                'job_title': p.cf_job_title or p.function or '',
                'country': p.country_id.name if p.country_id else '',
                'tags': [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in p.cf_tag_ids],
                'email_count': p.cf_email_count,
                'last_contact': p.cf_last_contact.strftime('%d/%m/%Y') if p.cf_last_contact else '',
                'rating': p.cf_rating or '',
            })
        return result

    # ── Agente 007 ──

    def action_enrich_007(self):
        """Multi-source enrichment via Anthropic Claude + web_search tool."""
        api_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.anthropic_api_key', '')
        if not api_key:
            raise ValueError("Anthropic API key non configurata. Vai in Impostazioni > Parametri di sistema > casafolino.anthropic_api_key")

        for partner in self:
            name = partner.name or ''
            email = partner.email or ''
            company = partner.parent_id.name if partner.parent_id else (partner.company_name or '')
            domain_hint = ''
            if email and '@' in email:
                domain_hint = email.split('@')[1]

            prompt = f"""Sei un agente di business intelligence. Devi trovare il MASSIMO delle informazioni su questo contatto/azienda.

CONTATTO:
- Nome: {name}
- Email: {email}
- Azienda: {company}
- Dominio email: {domain_hint}

ISTRUZIONI:
Cerca informazioni su TUTTE queste fonti, in ordine di priorità:

PER AZIENDE ITALIANE:
1. https://aziende.money.it/ — cerca per nome azienda o P.IVA
2. https://registroaziende.it/ — cerca ragione sociale
3. https://www.fatturatoitalia.it/ — cerca fatturato e bilancio
4. https://www.cerved.com o https://atoka.io — dati pubblici aziendali
5. https://www.apollo.io — se hai l'email, cerca il profilo
6. LinkedIn — cerca la pagina aziendale
7. Sito web aziendale — dal dominio email o ricerca diretta
8. Google: cerca "{company or name}" + "fatturato" OR "bilancio" OR "sede legale"

PER AZIENDE NON ITALIANE:
1. LinkedIn — pagina aziendale
2. https://www.apollo.io — profilo aziendale
3. Sito web aziendale
4. Registri commerciali locali del paese
5. Google: cerca informazioni finanziarie e sede

REGOLE:
- Sii AGGRESSIVO nella ricerca: prova più query per ogni fonte
- Estrai il MASSIMO dei dati da ogni fonte
- Se una fonte non risponde, passa alla successiva
- Cerca SEMPRE fatturato, dipendenti, sede legale, P.IVA
- Per il potenziale commerciale, valuta in base a: fatturato, dimensione, settore food/distribuzione

Rispondi SOLO con un JSON valido (nessun testo prima o dopo), con TUTTI questi campi:
{{
    "ragione_sociale": null,
    "piva": null,
    "pec": null,
    "settore": null,
    "fatturato": null,
    "fatturato_anno": null,
    "trend_ricavi": null,
    "dipendenti": null,
    "mercati": null,
    "certificazioni": null,
    "marchi": null,
    "sito_web": null,
    "telefono": null,
    "indirizzo": null,
    "cap": null,
    "citta": null,
    "potenziale": null,
    "ruolo_commerciale": null,
    "note_agente": null,
    "odoo_street": null,
    "odoo_zip": null,
    "odoo_city": null,
    "odoo_phone": null,
    "odoo_website": null,
    "odoo_vat": null
}}

Per ogni campo usa null se non trovi il dato. Per "potenziale" usa: "alto", "medio" o "basso".
Per "note_agente" scrivi un breve riassunto (2-3 frasi) utile per il team commerciale.
I campi odoo_* devono contenere gli stessi dati dei campi corrispondenti, formattati per Odoo (es. indirizzo completo in odoo_street, ecc).
"""

            try:
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 4096,
                        "tools": [{
                            "type": "web_search_20250305",
                            "name": "web_search",
                            "max_uses": 15,
                        }],
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=120,
                )
                response.raise_for_status()
                _logger.info("007 raw response: %s", response.text[:2000])
                result = response.json()

                text_parts = []
                for block in result.get('content', []):
                    if block.get('type') == 'text':
                        text_parts.append(block['text'])

                full_text = '\n'.join(text_parts)
                json_match = re.search(r'\{[\s\S]*\}', full_text)
                if not json_match:
                    _logger.warning("007: no JSON found in response for partner %s", partner.id)
                    continue

                data = json.loads(json_match.group())

                # Determine enrichment source
                enrich_from = 'nome_azienda'
                if company:
                    enrich_from = 'nome_azienda'
                elif email:
                    enrich_from = 'email'
                elif partner.vat:
                    enrich_from = 'piva'
                else:
                    enrich_from = 'nome_persona'

                vals = {
                    'cf_007_enriched': True,
                    'cf_007_enriched_date': fields.Datetime.now(),
                    'cf_007_enriched_from': enrich_from,
                }

                field_map = {
                    'ragione_sociale': 'cf_007_ragione_sociale',
                    'piva': 'cf_007_piva',
                    'pec': 'cf_007_pec',
                    'settore': 'cf_007_settore',
                    'fatturato': 'cf_007_fatturato',
                    'fatturato_anno': 'cf_007_fatturato_anno',
                    'trend_ricavi': 'cf_007_trend_ricavi',
                    'dipendenti': 'cf_007_dipendenti',
                    'mercati': 'cf_007_mercati',
                    'certificazioni': 'cf_007_certificazioni',
                    'marchi': 'cf_007_marchi',
                    'sito_web': 'cf_007_sito_web',
                    'telefono': 'cf_007_telefono',
                    'indirizzo': 'cf_007_indirizzo',
                    'cap': 'cf_007_cap',
                    'citta': 'cf_007_citta',
                    'potenziale': 'cf_007_potenziale',
                    'ruolo_commerciale': 'cf_007_ruolo_commerciale',
                    'note_agente': 'cf_007_note_agente',
                    'codice_fiscale': 'cf_007_codice_fiscale',
                    'rea': 'cf_007_rea',
                    'forma_giuridica': 'cf_007_forma_giuridica',
                    'ateco': 'cf_007_ateco',
                    'ateco_desc': 'cf_007_ateco_desc',
                    'capitale_sociale': 'cf_007_capitale_sociale',
                    'data_costituzione': 'cf_007_data_costituzione',
                    'anzianita': 'cf_007_anzianita',
                    'stato_attivita': 'cf_007_stato_attivita',
                    'dimensione': 'cf_007_dimensione',
                    'canali_vendita': 'cf_007_canali_vendita',
                    'prodotti_interesse': 'cf_007_prodotti_interesse',
                    'linkedin_company': 'cf_007_linkedin_company',
                    'paese': 'cf_007_paese',
                    'provincia': 'cf_007_provincia',
                    'utile': 'cf_007_utile',
                }

                selection_valid = {
                    'cf_007_potenziale': ('alto', 'medio', 'basso'),
                    'cf_007_ruolo_commerciale': ('produttore', 'distributore', 'importatore', 'retailer', 'grossista', 'agente', 'ecommerce', 'horeca', 'altro'),
                    'cf_007_stato_attivita': ('attiva', 'inattiva', 'liquidazione', 'fallita', 'sconosciuto'),
                    'cf_007_dimensione': ('micro', 'piccola', 'media', 'grande', 'sconosciuto'),
                }

                for json_key, odoo_field in field_map.items():
                    val = data.get(json_key)
                    if val:
                        str_val = str(val)
                        if odoo_field in selection_valid and str_val not in selection_valid[odoo_field]:
                            continue
                        if odoo_field == 'cf_007_note_agente' and partner.cf_007_note_agente:
                            vals[odoo_field] = partner.cf_007_note_agente + '\n---\n' + str_val
                        else:
                            vals[odoo_field] = str_val

                # Populate standard Odoo fields if currently empty
                odoo_standard_map = {
                    'odoo_vat': 'vat',
                    'odoo_website': 'website',
                    'odoo_phone': 'phone',
                    'odoo_street': 'street',
                    'odoo_zip': 'zip',
                    'odoo_city': 'city',
                }
                for json_key, odoo_field in odoo_standard_map.items():
                    val = data.get(json_key)
                    if val and not getattr(partner, odoo_field):
                        vals[odoo_field] = str(val)

                # Also update comment (append, don't overwrite)
                agent_note = data.get('note_agente')
                if agent_note:
                    existing_comment = partner.comment or ''
                    if existing_comment:
                        vals['comment'] = existing_comment + '\n\n--- Agente 007 ---\n' + str(agent_note)
                    else:
                        vals['comment'] = '--- Agente 007 ---\n' + str(agent_note)

                # Update ragione_sociale as name if company record and name is empty-ish
                ragione = data.get('ragione_sociale')
                if ragione and partner.is_company and not partner.name:
                    vals['name'] = str(ragione)

                partner.write(vals)
                _logger.info("007: enriched partner %s (%s)", partner.id, partner.name)

            except Exception as e:
                _logger.error("007: error enriching partner %s: %s", partner.id, e)
                raise

        return True

    @api.model
    def rpc_get_007_data(self, *args, **kw):
        partner_id = kw.get('partner_id')
        if not partner_id:
            return {}
        p = self.browse(int(partner_id))
        if not p.exists():
            return {}
        return {
            'enriched': p.cf_007_enriched,
            'enriched_date': p.cf_007_enriched_date.strftime('%d/%m/%Y %H:%M') if p.cf_007_enriched_date else '',
            'potenziale': p.cf_007_potenziale or '',
            'ruolo': p.cf_007_ruolo_commerciale or '',
            'note': p.cf_007_note_agente or '',
            'fatturato': p.cf_007_fatturato or '',
            'fatturato_anno': p.cf_007_fatturato_anno or '',
            'trend': p.cf_007_trend_ricavi or '',
            'dipendenti': p.cf_007_dipendenti or '',
            'mercati': p.cf_007_mercati or '',
            'certificazioni': p.cf_007_certificazioni or '',
            'piva': p.cf_007_piva or '',
            'pec': p.cf_007_pec or '',
            'ragione_sociale': p.cf_007_ragione_sociale or '',
            'settore': p.cf_007_settore or '',
            'marchi': p.cf_007_marchi or '',
            'codice_fiscale': p.cf_007_codice_fiscale or '',
            'rea': p.cf_007_rea or '',
            'forma_giuridica': p.cf_007_forma_giuridica or '',
            'ateco': p.cf_007_ateco or '',
            'capitale_sociale': p.cf_007_capitale_sociale or '',
            'stato_attivita': p.cf_007_stato_attivita or '',
            'dimensione': p.cf_007_dimensione or '',
            'canali_vendita': p.cf_007_canali_vendita or '',
            'prodotti_interesse': p.cf_007_prodotti_interesse or '',
            'linkedin_company': p.cf_007_linkedin_company or '',
            'paese': p.cf_007_paese or '',
            'provincia': p.cf_007_provincia or '',
            'utile': p.cf_007_utile or '',
            'enriched_from': p.cf_007_enriched_from or '',
        }


class CfContactTag(models.Model):
    _name = 'cf.contact.tag'
    _description = 'Tag Contatto CasaFolino'
    _order = 'name'

    name = fields.Char('Nome', required=True)
    color = fields.Char('Colore', default='#5A6E3A')
    category = fields.Selection([
        ('nazione', 'Nazione'),
        ('lingua', 'Lingua'),
        ('fiera', 'Fiera'),
        ('settore', 'Settore'),
        ('ruolo', 'Ruolo'),
        ('altro', 'Altro'),
    ], string='Categoria', default='altro')
    partner_count = fields.Integer('Contatti', compute='_compute_partner_count')

    def _compute_partner_count(self):
        for t in self:
            t.partner_count = self.env['res.partner'].search_count([('cf_tag_ids', 'in', [t.id])])

    @api.model
    def get_all_tags(self, *args, **kw):
        tags = self.search([], order='category, name')
        return [{'id': t.id, 'name': t.name, 'color': t.color, 'category': t.category, 'count': t.partner_count} for t in tags]

    @api.model
    def create_tag(self, *args, **kw):
        name = kw.get('name')
        color = kw.get('color') or '#5A6E3A'
        category = kw.get('category') or 'altro'
        if not name:
            return False
        tag = self.create({'name': name, 'color': color, 'category': category})
        return {'id': tag.id, 'name': tag.name, 'color': tag.color, 'category': tag.category}
