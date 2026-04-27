import email as email_lib
import json
import logging
import re
import requests
from email.utils import parseaddr, parsedate_to_datetime

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartnerMailExt(models.Model):
    _inherit = 'res.partner'

    # Campi extra tipo HubSpot/Zoho
    cf_job_title = fields.Char('Ruolo / Posizione')

    # ── Mail Hub tracking fields ──
    mail_tracked = fields.Boolean('Mail Tracked', default=False,
        help='Se attivo, le nuove email vanno direttamente nel chatter')
    mail_first_sync_done = fields.Boolean('Storico email scaricato', default=False)
    mail_last_sync = fields.Datetime('Ultimo sync email')
    mail_message_count = fields.Integer('Email',
        compute='_compute_mail_message_count')
    partner_message_ids = fields.One2many(
        'casafolino.mail.message', 'partner_id', string='Email')

    # ── Email CRM timeline fields ──
    casafolino_mail_ids = fields.One2many(
        'casafolino.mail.message', 'partner_id', string='Email CRM',
        domain=[('state', 'in', ['keep', 'auto_keep'])])
    casafolino_last_email_date = fields.Datetime(
        'Ultima email CRM', compute='_compute_casafolino_mail_stats', store=True)
    casafolino_email_count = fields.Integer(
        '# Email CRM', compute='_compute_casafolino_mail_stats', store=True)

    # ── CRM fields ──
    cf_role = fields.Selection([
        ('buyer', 'Buyer'), ('category_manager', 'Category Manager'),
        ('import_manager', 'Import Manager'), ('owner', 'Owner/CEO'),
        ('quality', 'Quality Manager'), ('logistics', 'Logistics'),
        ('marketing', 'Marketing'), ('sales', 'Sales'),
        ('procurement', 'Procurement'), ('other', 'Other'),
    ], string='Ruolo acquisto')
    cf_decision_level = fields.Selection([
        ('decision_maker', 'Decision Maker'), ('influencer', 'Influencer'),
        ('gatekeeper', 'Gatekeeper'), ('user', 'User'), ('champion', 'Champion'),
    ], string='Livello decisionale')
    cf_channel = fields.Selection([
        ('fair', 'Fiera'), ('website', 'Sito web'), ('referral', 'Referral'),
        ('linkedin', 'LinkedIn'), ('cold_call', 'Cold call'),
        ('inbound', 'Inbound'), ('other', 'Other'),
    ], string='Canale acquisizione')
    cf_fair_met = fields.Char('Fiera incontro')
    cf_notes_commercial = fields.Text('Note commerciali')
    cf_last_contact_date = fields.Date('Data ultimo contatto')
    cf_contact_frequency = fields.Selection([
        ('weekly', 'Settimanale'), ('monthly', 'Mensile'),
        ('quarterly', 'Trimestrale'), ('yearly', 'Annuale'),
        ('sporadic', 'Sporadico'),
    ], string='Frequenza contatto')

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

    # ── Domini extra per whitelist ingestion ──
    email_domains_extra = fields.Char(
        'Domini email extra',
        help='Domini aggiuntivi separati da virgola (es. aldi-sued.de, aldi.com). '
             'Usati dal filtro ingestion per riconoscere email di questa azienda.',
        groups='sales_team.group_sale_manager',
    )

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

    def _compute_mail_message_count(self):
        for partner in self:
            partner.mail_message_count = self.env['casafolino.mail.message'].search_count([
                ('partner_id', '=', partner.id),
            ])

    @api.depends('casafolino_mail_ids.email_date', 'casafolino_mail_ids.state')
    def _compute_casafolino_mail_stats(self):
        for partner in self:
            msgs = partner.casafolino_mail_ids.filtered(
                lambda m: m.state in ('keep', 'auto_keep'))
            partner.casafolino_email_count = len(msgs)
            dates = msgs.mapped('email_date')
            partner.casafolino_last_email_date = max(dates) if dates else False

    def action_view_casafolino_emails(self):
        """Apre lista email CRM del partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Email CRM — %s' % self.name,
            'res_model': 'casafolino.mail.message',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('state', 'in', ['keep', 'auto_keep'])],
        }

    # ── Sync storico email per contatto (Step 7) ─────────────────────

    def action_sync_full_email_history(self):
        """Scarica tutto lo storico email per questo contatto da tutte le caselle."""
        self.ensure_one()
        if not self.email:
            raise UserError("Il contatto non ha un indirizzo email.")

        accounts = self.env['casafolino.mail.account'].search([('state', '=', 'connected')])
        email_lower = self.email.lower().strip()
        Message = self.env['casafolino.mail.message']

        for account in accounts:
            imap = account._get_imap_connection()
            try:
                folders = []
                if account.fetch_inbox:
                    folders.append(('INBOX', 'inbound'))
                if account.fetch_sent and account.sent_folder:
                    folders.append((account.sent_folder, 'outbound'))

                for folder_name, direction in folders:
                    status, _ = imap.select('"%s"' % folder_name, readonly=True)
                    if status != 'OK':
                        continue

                    # Cerca TUTTE le email da/a questo indirizzo, SENZA limite di data
                    search_criteria = '(OR FROM "%s" TO "%s")' % (email_lower, email_lower)
                    status, msg_ids = imap.search(None, search_criteria)

                    if status != 'OK' or not msg_ids[0]:
                        continue

                    uid_list = msg_ids[0].split()
                    _logger.info("Storico %s in %s: %d email", email_lower, folder_name, len(uid_list))

                    for uid in uid_list:
                        uid_str = uid.decode()

                        # Scarica completo (header + body)
                        status2, msg_data = imap.fetch(uid, '(RFC822)')
                        if status2 != 'OK':
                            continue

                        raw_email = None
                        for part in msg_data:
                            if isinstance(part, tuple):
                                raw_email = part[1]
                                break
                        if not raw_email:
                            continue

                        msg = email_lib.message_from_bytes(raw_email)
                        message_id = msg.get('Message-ID', '').strip()

                        if not message_id:
                            message_id = "<%s-%s-%s@generated>" % (account.email_address, uid_str, folder_name)

                        # Skip se già esiste
                        if Message.search([('message_id_rfc', '=', message_id), ('account_id', '=', account.id)], limit=1):
                            continue

                        # Parsa header
                        sender_name, sender_email_addr = parseaddr(msg.get('From', ''))
                        sender_name = account._decode_header_value(sender_name)
                        sender_email_addr = sender_email_addr.lower().strip() if sender_email_addr else ''

                        subject = account._decode_header_value(msg.get('Subject', ''))
                        try:
                            email_date = parsedate_to_datetime(msg.get('Date', ''))
                        except Exception:
                            email_date = fields.Datetime.now()

                        actual_direction = 'outbound' if sender_email_addr == account.email_address.lower() else 'inbound'

                        # Crea record staging con state=keep e body
                        try:
                            new_msg = Message.create({
                                'account_id': account.id,
                                'message_id_rfc': message_id,
                                'imap_uid': uid_str,
                                'imap_folder': folder_name,
                                'direction': actual_direction,
                                'sender_email': sender_email_addr,
                                'sender_name': sender_name,
                                'recipient_emails': account._extract_emails(msg.get('To', '')),
                                'cc_emails': account._extract_emails(msg.get('Cc', '')),
                                'subject': subject,
                                'email_date': email_date,
                                'state': 'keep',
                                'partner_id': self.id,
                                'match_type': 'exact',
                                'triage_user_id': self.env.user.id,
                                'triage_date': fields.Datetime.now(),
                            })

                            # Parsa body direttamente dal raw già disponibile
                            new_msg._parse_and_save_body(msg)
                            new_msg._create_partner_mail_message()

                            self.env.cr.commit()
                        except Exception as e:
                            _logger.warning("History sync error for %s uid %s: %s", email_lower, uid_str, e)
                            continue

            finally:
                try:
                    imap.logout()
                except Exception:
                    pass

        self.write({
            'mail_tracked': True,
            'mail_first_sync_done': True,
            'mail_last_sync': fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync completato',
                'message': 'Storico email scaricato per %s' % self.email,
                'type': 'success',
            },
        }

    @api.depends('partner_message_ids', 'partner_message_ids.email_date')
    def _compute_last_contact(self):
        for p in self:
            msgs = self.env['casafolino.mail.message'].search([
                ('partner_id', '=', p.id)
            ], order='email_date desc', limit=1)
            p.cf_last_contact = msgs.email_date if msgs else False

    def _compute_email_count(self):
        for p in self:
            p.cf_email_count = self.env['casafolino.mail.message'].search_count([
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
        api_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.groq_api_key', '')
        serper_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.serper_api_key', '')
        if not api_key:
            raise ValueError("Anthropic API key non configurata. Vai in Impostazioni > Parametri di sistema > casafolino.anthropic_api_key")

        for partner in self:
            name = partner.name or ''
            email = partner.email or ''
            company = partner.parent_id.name if partner.parent_id else (partner.company_name or '')
            domain_hint = ''
            if email and '@' in email:
                domain_hint = email.split('@')[1]

            # --- SERPER WEB SEARCH ---
            serper_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.serper_api_key', '')
            search_context = ""
            if serper_key:
                # Determina paese del contatto
                country_code = partner.country_id.code.upper() if partner.country_id else ''
                
                # Fonti per paese
                sources_by_country = {
                    'IT': [
                        f"{company} site:fatturatoitalia.it",
                        f"{company} site:aziende.money.it",
                        f"{company} site:atoka.io",
                        f"{company} fatturato bilancio dipendenti sede legale P.IVA",
                        f"{company} site:linkedin.com/company",
                    ],
                    'DE': [
                        f"{company} site:northdata.de",
                        f"{company} site:bundesanzeiger.de",
                        f"{company} Umsatz Mitarbeiter Adresse",
                        f"{company} site:linkedin.com/company",
                    ],
                    'AT': [
                        f"{company} site:northdata.de",
                        f"{company} Umsatz Mitarbeiter Österreich",
                        f"{company} site:linkedin.com/company",
                    ],
                    'CH': [
                        f"{company} site:northdata.de",
                        f"{company} Umsatz Mitarbeiter Schweiz",
                        f"{company} site:linkedin.com/company",
                    ],
                    'GB': [
                        f"{company} site:companieshouse.gov.uk",
                        f"{company} site:opencorporates.com",
                        f"{company} revenue employees UK",
                        f"{company} site:linkedin.com/company",
                    ],
                    'US': [
                        f"{company} site:opencorporates.com",
                        f"{company} site:dnb.com",
                        f"{company} revenue employees USA",
                        f"{company} site:linkedin.com/company",
                    ],
                    'CA': [
                        f"{company} site:opencorporates.com",
                        f"{company} revenue employees Canada",
                        f"{company} site:linkedin.com/company",
                    ],
                    'FR': [
                        f"{company} site:societe.com",
                        f"{company} site:infogreffe.fr",
                        f"{company} chiffre affaires employés",
                        f"{company} site:linkedin.com/company",
                    ],
                    'ES': [
                        f"{company} site:einforma.com",
                        f"{company} site:axesor.es",
                        f"{company} facturacion empleados España",
                        f"{company} site:linkedin.com/company",
                    ],
                    'PL': [
                        f"{company} site:opencorporates.com",
                        f"{company} przychody pracownicy Polska",
                        f"{company} site:linkedin.com/company",
                    ],
                    'AE': [
                        f"{company} site:opencorporates.com",
                        f"{company} revenue employees UAE Dubai",
                        f"{company} site:linkedin.com/company",
                    ],
                    'AU': [
                        f"{company} site:opencorporates.com",
                        f"{company} revenue employees Australia",
                        f"{company} site:linkedin.com/company",
                    ],
                }
                
                # Fonti internazionali sempre incluse
                universal_queries = [
                    f"{company} site:apollo.io",
                    f"{company} site:crunchbase.com",
                ]
                
                # Seleziona queries per paese (default: ricerca generica)
                queries = sources_by_country.get(country_code, [
                    f"{company} revenue employees headquarters",
                    f"{company} site:opencorporates.com",
                    f"{company} site:linkedin.com/company",
                ])
                
                # Aggiungi sempre le universali
                queries += universal_queries
                
                # Lancia max 4 query Serper
                for q in queries[:4]:
                    try:
                        sr = requests.post(
                            "https://google.serper.dev/search",
                            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                            json={"q": q, "num": 5, "gl": "it", "hl": "it"},
                            timeout=10,
                        )
                        if sr.ok:
                            data = sr.json()
                            for item in data.get("organic", [])[:3]:
                                search_context += f"- {item.get('title','')}: {item.get('snippet','')} ({item.get('link','')})" + "\n"
                    except Exception as e:
                        _logger.warning("Serper error: %s", e)
            # --- END SERPER ---
            prompt = f"""Sei un agente di business intelligence. Analizza il contatto e restituisci un JSON con tutti i dati trovati.
CONTATTO:
- Nome: {name}
- Email: {email}
- Azienda: {company}
- Dominio email: {domain_hint}

RISULTATI RICERCA WEB (usa questi dati come fonte primaria):
{search_context if search_context else "Nessun risultato trovato dalla ricerca web."}

Basandoti sui risultati web sopra, estrai il MASSIMO delle informazioni disponibili.
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
"""

            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "max_tokens": 4096,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=120,
                )
                if not response.ok:
                    raise ValueError(f"API Error {response.status_code}: {response.text}")
                response.raise_for_status()
                _logger.info("007 raw response: %s", response.text[:2000])
                result = response.json()

                full_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
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

    def action_enrich_007_batch(self):
        """Arricchimento batch con rate limiting (2s tra chiamate)."""
        import time
        total = len(self)
        done = 0
        errors = 0
        for partner in self:
            try:
                partner.action_enrich_007()
                done += 1
                _logger.info("007 batch: %d/%d completati", done, total)
            except Exception as e:
                errors += 1
                _logger.error("007 batch: errore su partner %s: %s", partner.id, e)
            time.sleep(2)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Agente 007 Batch completato',
                'message': 'Arricchiti: %d/%d. Errori: %d.' % (done, total, errors),
                'type': 'success' if errors == 0 else 'warning',
                'sticky': True,
            }
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
