import json
import logging
import re

import requests

from odoo import api, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager  # manager-only (Brief 5)

_logger = logging.getLogger(__name__)

GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'


def _console_groq_json(env, prompt):
    """Helper LLM ASTRATTO (Brief 8): manda il prompt a Groq e ritorna un dict dal JSON.
    Sostituibile (Claude/altro) cambiando SOLO questa funzione. Fail-soft: qualsiasi errore
    o output non-JSON → {} (mai eccezione, mai testo free-form propagato). Niente si scrive qui."""
    key = env['ir.config_parameter'].sudo().get_param('casafolino.groq_api_key', '')
    if not key:
        _logger.warning('[console enrich] groq_api_key assente → niente estrazione IA.')
        return {}
    model = env['ir.config_parameter'].sudo().get_param(
        'casafolino.mail.v5_groq_model_default', 'llama-3.3-70b-versatile')
    try:
        resp = requests.post(
            GROQ_URL,
            headers={'Authorization': 'Bearer %s' % key, 'Content-Type': 'application/json'},
            json={'model': model, 'max_tokens': 1024, 'temperature': 0,
                  'messages': [{'role': 'user', 'content': prompt}]},
            timeout=60,
        )
        if not resp.ok:
            _logger.warning('[console enrich] groq %s: %s', resp.status_code, resp.text[:300])
            return {}
        content = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        m = re.search(r'\{[\s\S]*\}', content or '')
        if not m:
            return {}
        return json.loads(m.group())
    except Exception as e:
        _logger.warning('[console enrich] estrazione fallita: %s', e)
        return {}


def _clean_str(v):
    """Solo stringhe non vuote; tutto il resto (None/dict/numeri spuri) scartato. Anti free-form."""
    if not isinstance(v, str):
        return ''
    s = v.strip()
    if not s or s.lower() in ('null', 'none', 'n/a', '-'):
        return ''
    return s[:200]


class ResPartnerConsoleEnrich(models.Model):
    """Brief 8 — crea contatto/azienda da mail con arricchimento IA + dedup. Manager-only.
    enrich NON scrive (propone), create scrive SOLO dati revisionati dal manager."""
    _inherit = 'res.partner'

    @api.model
    def console_enrich_contact(self, payload):
        """Estrae da firma(body)+dominio via Groq, valida, e calcola i candidati dedup.
        NON scrive. Body assente → solo dominio (zero campi inventati).
        payload: {mailId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        mail = self.env['casafolino.mail.message'].sudo().browse(int((payload or {}).get('mailId') or 0))
        if not mail.exists():
            raise UserError(_("Mail inesistente."))

        sender_email = (mail.sender_email or '').strip().lower()
        sender_name = mail.sender_name or ''
        domain = sender_email.split('@')[1] if '@' in sender_email else ''
        body = mail.body_html or ''
        has_body = bool(body and len(body) > 40)

        # base SEMPRE da dati certi del mittente (mai inventati)
        proposed = {
            'contatto': {'nome': sender_name, 'ruolo': '', 'email': sender_email, 'telefono': ''},
            'azienda': {'nome': '', 'dominio': domain},
            'indirizzo': {'via': '', 'cap': '', 'citta': '', 'paese': ''},
        }
        source = 'domain'

        if has_body:
            text = re.sub(r'<[^>]+>', ' ', body)
            text = re.sub(r'\s+', ' ', text)[:4000]
            prompt = (
                "Estrai i dati di contatto dalla FIRMA di questa email. Rispondi SOLO con JSON valido, "
                "niente testo. Usa stringhe vuote se un dato non è presente NELLA FIRMA (non inventare).\n"
                'Schema: {"contatto":{"nome":"","ruolo":"","email":"","telefono":""},'
                '"azienda":{"nome":"","dominio":""},'
                '"indirizzo":{"via":"","cap":"","citta":"","paese":""}}\n\n'
                "Mittente: %s <%s>\nDominio: %s\n\nEMAIL:\n%s" % (sender_name, sender_email, domain, text)
            )
            data = _console_groq_json(self.env, prompt)
            if data:
                source = 'signature'
                c = data.get('contatto') or {}
                a = data.get('azienda') or {}
                ind = data.get('indirizzo') or {}
                proposed['contatto'] = {
                    'nome': _clean_str(c.get('nome')) or sender_name,
                    'ruolo': _clean_str(c.get('ruolo')),
                    'email': _clean_str(c.get('email')) or sender_email,
                    'telefono': _clean_str(c.get('telefono')),
                }
                proposed['azienda'] = {
                    'nome': _clean_str(a.get('nome')),
                    'dominio': _clean_str(a.get('dominio')) or domain,
                }
                proposed['indirizzo'] = {
                    'via': _clean_str(ind.get('via')), 'cap': _clean_str(ind.get('cap')),
                    'citta': _clean_str(ind.get('citta')), 'paese': _clean_str(ind.get('paese')),
                }

        # ── DEDUP ──────────────────────────────────────────────────────────
        Partner = self.env['res.partner'].sudo()
        contacts, companies = [], []
        seen = set()
        # contatto: email esatta = candidato FORTE
        if sender_email:
            for p in Partner.search([('email', '=ilike', sender_email)], limit=5):
                if p.id in seen:
                    continue
                seen.add(p.id)
                contacts.append({'id': p.id, 'name': p.name or '', 'email': p.email or '',
                                 'company': p.parent_id.name or '', 'strength': 'strong'})
        # azienda: stesso dominio + is_company = suggerimento
        if domain:
            for p in Partner.search([('email', '=ilike', '%@' + domain), ('is_company', '=', True)], limit=5):
                companies.append({'id': p.id, 'name': p.name or '', 'domain': domain, 'strength': 'domain'})
        # azienda: nome simile (dall'estrazione) = suggerimento
        comp_name = proposed['azienda']['nome']
        if comp_name and len(comp_name) >= 3:
            for p in Partner.search([('name', 'ilike', comp_name), ('is_company', '=', True)], limit=5):
                if not any(x['id'] == p.id for x in companies):
                    companies.append({'id': p.id, 'name': p.name or '', 'domain': '', 'strength': 'name'})

        _audit(self.env, 'res.partner', [mail.id], 'enrich_contact:%s' % source, None, operator)
        return {
            'mailId': mail.id, 'hasBody': has_body, 'source': source,
            'proposed': proposed,
            'dedupCandidates': {'contacts': contacts, 'companies': companies},
        }

    @api.model
    def console_create_contact(self, payload):
        """Scrive res.partner SOLO con dati revisionati dal manager. Con linkPartnerId →
        collega all'esistente (niente duplicato). payload: {data, linkPartnerId?, linkCompanyId?,
        linkLeadId?, mailId?, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        Partner = self.env['res.partner'].sudo()

        link_partner = int((payload or {}).get('linkPartnerId') or 0)
        if link_partner:
            # COLLEGA: nessun nuovo partner. Eventuale link mail→partner per contesto.
            p = Partner.browse(link_partner)
            if not p.exists():
                raise UserError(_("Partner da collegare inesistente."))
            mail_id = int((payload or {}).get('mailId') or 0)
            if mail_id:
                self.env['casafolino.mail.message'].sudo().browse(mail_id).write({'partner_id': p.id})
            _audit(self.env, 'res.partner', [p.id], 'create_contact:link', None, operator)
            return {'ok': True, 'linked': True, 'partnerId': p.id, 'name': p.name}

        data = (payload or {}).get('data') or {}
        c = data.get('contatto') or {}
        a = data.get('azienda') or {}
        ind = data.get('indirizzo') or {}
        name = _clean_str(c.get('nome'))
        if not name:
            raise UserError(_("Nome contatto obbligatorio."))

        # azienda: collega esistente (linkCompanyId) o crea nuova se ha un nome
        company = Partner.browse(int((payload or {}).get('linkCompanyId') or 0))
        company = company if company.exists() else Partner.browse()
        if not company and _clean_str(a.get('nome')):
            company = Partner.create({
                'name': _clean_str(a.get('nome')), 'is_company': True,
                'website': ('https://' + a['dominio']) if _clean_str(a.get('dominio')) else False,
                'street': _clean_str(ind.get('via')) or False,
                'zip': _clean_str(ind.get('cap')) or False,
                'city': _clean_str(ind.get('citta')) or False,
            })

        vals = {
            'name': name, 'is_company': False,
            'email': _clean_str(c.get('email')) or False,
            'phone': _clean_str(c.get('telefono')) or False,
            'function': _clean_str(c.get('ruolo')) or False,
            'parent_id': company.id if company else False,
            'street': _clean_str(ind.get('via')) or False,
            'zip': _clean_str(ind.get('cap')) or False,
            'city': _clean_str(ind.get('citta')) or False,
        }
        contact = Partner.create(vals)

        mail_id = int((payload or {}).get('mailId') or 0)
        if mail_id:
            self.env['casafolino.mail.message'].sudo().browse(mail_id).write({'partner_id': contact.id})
        lead_id = int((payload or {}).get('linkLeadId') or 0)
        if lead_id:
            self.env['crm.lead'].sudo().browse(lead_id).write({'partner_id': contact.id})

        _audit(self.env, 'res.partner', [contact.id], 'create_contact:new', set(vals.keys()), operator)
        return {'ok': True, 'linked': False, 'partnerId': contact.id, 'name': contact.name,
                'companyId': company.id if company else False}
