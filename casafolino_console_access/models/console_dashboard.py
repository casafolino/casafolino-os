import logging
import re

import requests

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager
from .console_enrich import _console_groq_json, _clean_str

_logger = logging.getLogger(__name__)

# python-stdnum è dipendenza di base_vat: format-check + VIES SOAP. Fail-soft se assente.
try:
    from stdnum.eu.vat import is_valid as _vat_is_valid, check_vies as _vat_check_vies
except Exception:  # pragma: no cover
    _vat_is_valid = _vat_check_vies = None

SERPER_URL = 'https://google.serper.dev/search'
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_ACTION_TYPES = ('catalogo', 'email', 'follow-up', 'sollecito', 'campione', 'task')

# Brief — mappa autoritativa nomi → record. hr.employee per l'esecuzione campionatura,
# res.users per l'assegnazione di un'attività (mail.activity.user_id).
_QUICKTASK_NAME_MAP = {
    'maria': {'employee_id': 9},
    'teresa': {'employee_id': 6},
    'anna': {'employee_id': 3},
    'valentina': {'employee_id': 10},
    'antonio': {'user_id': 2},
    'martina': {'user_id': 8},
}


class CrmLeadConsoleDashboard(models.Model):
    """Fase 1/2 — Wizard 'da chiamata a preventivo' + Quick-Task NL. Estende il pattern gated
    esistente (_is_console + _require_manager + sudo + _audit). console_api NON scrive mai in diretta:
    ogni write passa da un metodo gated e finisce in casafolino.console.audit (write-log)."""
    _inherit = 'crm.lead'

    # ---------------------------------------------------------------- VAT / dedup / VIES
    def _console_normalize_vat(self, raw):
        """Normalizza la P.IVA: rimuove spazi/punteggiatura, uppercase, prefissa IT se 11 cifre nude."""
        s = re.sub(r'[\s.\-/]', '', (raw or '')).upper()
        country, digits = '', s
        if len(s) >= 3 and s[:2].isalpha():
            country, digits = s[:2], s[2:]
        elif s.isdigit() and len(s) == 11:
            country = 'IT'
        compact = (country + digits) if country else digits
        fmt = False
        if _vat_is_valid and country:
            try:
                fmt = bool(_vat_is_valid(compact))
            except Exception:
                fmt = False
        return {'compact': compact, 'country': country, 'digits': digits, 'formatValid': fmt}

    def _console_vies_check(self, norm):
        """VIES best-effort (python-stdnum, dep di base_vat). Qualsiasi errore/timeout → None.
        Ritorna {valid, name, street, city, zip} per il precompilato della card."""
        if not _vat_check_vies or not norm.get('compact') or not norm.get('country'):
            return None
        try:
            res = _vat_check_vies(norm['compact'])
        except Exception as e:
            _logger.warning('[console vies] %s', e)
            return None

        def _get(obj, attr):
            if isinstance(obj, dict):
                return obj.get(attr)
            return getattr(obj, attr, None)

        valid = bool(_get(res, 'valid'))
        name = (_get(res, 'name') or '').strip()
        addr = _get(res, 'address')
        street = city = zipc = ''
        if addr and isinstance(addr, str):
            parts = [a.strip() for a in addr.replace('\n', ',').split(',') if a.strip()]
            if parts:
                street = parts[0]
            if len(parts) > 1:
                m = re.match(r'(\d{4,5})\s+(.*)', parts[1])
                if m:
                    zipc, city = m.group(1), m.group(2)
                else:
                    city = parts[1]
        return {'valid': valid, 'name': name if name and name != '---' else '',
                'street': street, 'city': city, 'zip': zipc, 'raw': str(addr or '')[:300]}

    @api.model
    def console_vat_lookup(self, payload):
        """Fase 1 Step 1 — normalizza P.IVA, dedup su res.partner.vat (esatto, varie forme) + fuzzy
        su name via ORM ilike (niente SQL/cast manuale), VIES best-effort. NESSUNA scrittura.
        payload: {vat?, name?, operator_uid}. Ritorna candidati esistenti o precompilato se nuova."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        raw = _clean_str((payload or {}).get('vat'))
        name_hint = _clean_str((payload or {}).get('name'))
        if not raw and not name_hint:
            raise UserError(_("P.IVA o ragione sociale obbligatoria."))

        norm = self._console_normalize_vat(raw) if raw else {
            'compact': '', 'country': '', 'digits': '', 'formatValid': False}
        Partner = self.env['res.partner'].sudo()

        candidates = Partner.browse()
        if norm['compact']:
            forms = list({norm['compact'], norm['digits'], (norm['country'] + norm['digits'])})
            forms += [f.lower() for f in forms]
            candidates = Partner.search([('vat', 'in', list(set(forms)))], limit=10)
        if not candidates and name_hint:
            candidates = Partner.search(
                [('name', 'ilike', name_hint), ('is_company', '=', True)], limit=10)

        existing = [{
            'id': p.id, 'name': p.name or '', 'vat': p.vat or '',
            'city': p.city or '', 'country': p.country_id.name or '',
            'email': p.email or '', 'isCompany': p.is_company,
        } for p in candidates]

        vies = prefill = None
        if not existing:
            if norm['compact']:
                vies = self._console_vies_check(norm)
            if vies and vies.get('valid'):
                prefill = {'name': vies.get('name') or name_hint or '', 'vat': norm['compact'],
                           'street': vies.get('street') or '', 'city': vies.get('city') or '',
                           'zip': vies.get('zip') or '', 'country': norm['country'] or ''}
            else:
                prefill = {'name': name_hint or '', 'vat': norm['compact'],
                           'street': '', 'city': '', 'zip': '', 'country': norm['country'] or ''}

        _audit(self.env, 'res.partner', candidates.ids, 'vat_lookup', None, operator)
        return {
            'ok': True, 'normalizedVat': norm['compact'], 'formatValid': norm['formatValid'],
            'isNew': not existing, 'existing': existing, 'vies': vies, 'prefill': prefill,
        }

    # ---------------------------------------------------------------- Agente 007 (read-only)
    @api.model
    def console_enrich_007(self, payload):
        """Fase 1 — arricchimento opzionale Serper+Groq (sito, settore, dimensione) per nuove aziende
        con VIES scarno o extra-UE. NESSUNA scrittura. Fail-soft → campi vuoti.
        payload: {name, vat?, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        name = _clean_str((payload or {}).get('name'))
        if not name:
            raise UserError(_("Ragione sociale obbligatoria per l'arricchimento."))
        vat = _clean_str((payload or {}).get('vat'))

        serper_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.serper_api_key', '')
        ctx = ''
        if serper_key:
            for q in [name, ('%s %s' % (name, vat)).strip()]:
                if not q:
                    continue
                try:
                    sr = requests.post(
                        SERPER_URL,
                        headers={'X-API-KEY': serper_key, 'Content-Type': 'application/json'},
                        json={'q': q, 'num': 5, 'gl': 'it', 'hl': 'it'}, timeout=10)
                    if sr.ok:
                        for it in sr.json().get('organic', [])[:4]:
                            ctx += "- %s: %s (%s)\n" % (
                                it.get('title', ''), it.get('snippet', ''), it.get('link', ''))
                except Exception as e:
                    _logger.warning('[console enrich007] serper %s', e)

        data = _console_groq_json(self.env, (
            "Sei un agente di business intelligence. Dai risultati web estrai i dati dell'azienda. "
            "Rispondi SOLO JSON: {\"sito\":\"\",\"settore\":\"\",\"dimensione\":\"\",\"citta\":\"\","
            "\"paese\":\"\"}. Campo vuoto se ignoto.\n\nAzienda: %s\nP.IVA: %s\n\nWEB:\n%s"
            % (name, vat or '-', ctx or 'nessun risultato web')))
        out = {k: _clean_str((data or {}).get(k))
               for k in ('sito', 'settore', 'dimensione', 'citta', 'paese')}
        _audit(self.env, 'res.partner', [], 'enrich_007', None, operator)
        return {'ok': True, 'enrichment': out, 'usedWeb': bool(ctx)}

    # ---------------------------------------------------------------- Quick-Task NL
    def _console_resolve_assignee(self, raw_name):
        """Nome → {name, userId, employeeId}. Mappa autoritativa Brief + fallback ricerca reale.
        Non risolto → None (la card chiede correzione manuale, mai write a vuoto)."""
        nm = (raw_name or '').strip().lower()
        if not nm:
            return None
        first = nm.split()[0]
        hit = _QUICKTASK_NAME_MAP.get(nm) or _QUICKTASK_NAME_MAP.get(first)
        Emp = self.env['hr.employee'].sudo()
        Usr = self.env['res.users'].sudo()
        user_id = (hit or {}).get('user_id')
        employee_id = (hit or {}).get('employee_id')
        disp = raw_name.strip().title()

        if employee_id:
            emp = Emp.browse(employee_id)
            if emp.exists():
                disp = emp.name or disp
                if not user_id and emp.user_id:
                    user_id = emp.user_id.id
        if user_id and not employee_id:
            usr = Usr.browse(user_id)
            if usr.exists():
                disp = usr.name or disp
                emp = Emp.search([('user_id', '=', user_id)], limit=1)
                employee_id = emp.id if emp else employee_id
        if not hit:
            emp = Emp.search([('name', 'ilike', first)], limit=1)
            if emp:
                employee_id, disp = emp.id, emp.name
                user_id = emp.user_id.id if emp.user_id else user_id
            else:
                usr = Usr.search([('name', 'ilike', first), ('share', '=', False)], limit=1)
                if usr:
                    user_id, disp = usr.id, usr.name
        if not user_id and not employee_id:
            return None
        return {'name': disp, 'userId': user_id, 'employeeId': employee_id}

    @api.model
    def console_parse_quicktask(self, payload):
        """Fase 2 — frase libera → Groq → {assignee, action_type, object_ref, due_date}. SOLO parsing,
        NESSUNA scrittura. Assignee/action non risolti → needsReview=True (card per correzione).
        payload: {text, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        text = _clean_str((payload or {}).get('text'))
        if not text:
            raise UserError(_("Scrivi un'istruzione."))
        today = fields.Date.context_today(self)
        data = _console_groq_json(self.env, (
            "Estrai da questa istruzione operativa italiana i campi per instradarla. "
            "action_type deve essere uno di [catalogo,email,follow-up,sollecito,campione,task]. "
            "due_date in formato YYYY-MM-DD (oggi e' %s; vuoto se non indicata). assignee = solo il "
            "nome proprio della persona. object_ref = oggetto/cliente/prodotto citato. "
            "Rispondi SOLO JSON: {\"assignee\":\"\",\"action_type\":\"\",\"object_ref\":\"\","
            "\"due_date\":\"\",\"quantity\":null}.\n\nIstruzione: %s" % (today, text)))
        assignee_raw = _clean_str((data or {}).get('assignee'))
        action = _clean_str((data or {}).get('action_type')).lower()
        if action not in _ACTION_TYPES:
            action = ''
        due = _clean_str((data or {}).get('due_date'))
        if due and not _DATE_RE.match(due):
            due = ''
        resolved = self._console_resolve_assignee(assignee_raw) if assignee_raw else None
        qty = (data or {}).get('quantity')
        try:
            qty = float(qty) if qty not in (None, '', 'null') else None
        except (TypeError, ValueError):
            qty = None
        _audit(self.env, 'cf.task', [], 'parse_quicktask', None, operator)
        return {
            'ok': True, 'text': text,
            'assignee': {'raw': assignee_raw, 'resolved': resolved},
            'actionType': action,
            'objectRef': _clean_str((data or {}).get('object_ref')),
            'dueDate': due, 'quantity': qty,
            'needsReview': not (resolved and action),
        }

    @api.model
    def console_quicktask_commit(self, payload):
        """Fase 2 — scrive SOLO dopo conferma della card (eventualmente editata). Instrada per
        action_type ai metodi già esistenti, sempre audited. console_api non scrive mai in diretta.
        payload: {action_type, assignee_user_id?, assignee_employee_id?, partner_id?, lead_id?,
                  summary?, due_date?, lines?:[{productId,qty}], operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        action = _clean_str((payload or {}).get('action_type')).lower()
        if action not in _ACTION_TYPES:
            raise UserError(_("action_type non valido: %s") % action)
        partner_id = int((payload or {}).get('partner_id') or 0) or False
        lead_id = int((payload or {}).get('lead_id') or 0) or False
        summary = _clean_str((payload or {}).get('summary'))
        due = _clean_str((payload or {}).get('due_date'))
        user_id = int((payload or {}).get('assignee_user_id') or 0) or operator.id
        emp_id = int((payload or {}).get('assignee_employee_id') or 0) or False

        # --- attività commerciale (catalogo/email/follow-up/sollecito) → mail.activity ---
        if action in ('catalogo', 'email', 'follow-up', 'sollecito'):
            res_model = 'crm.lead' if lead_id else 'res.partner'
            res_id = lead_id or partner_id
            if not res_id:
                raise UserError(_("Serve un partner o un lead per l'attività."))
            if not summary:
                summary = {'catalogo': _("Invia catalogo"), 'email': _("Invia email"),
                           'follow-up': _("Follow-up"), 'sollecito': _("Sollecito")}.get(action, action)
            model_row = self.env['ir.model'].sudo().search([('model', '=', res_model)], limit=1)
            todo = self.env['ir.model.data'].sudo().search(
                [('module', '=', 'mail'), ('name', '=', 'mail_activity_data_todo')], limit=1)
            act = self.env['mail.activity'].sudo().create({
                'res_model_id': model_row.id, 'res_id': res_id,
                'summary': summary, 'user_id': user_id,
                'date_deadline': due if (due and _DATE_RE.match(due)) else fields.Date.context_today(self),
                **({'activity_type_id': todo.res_id} if todo else {}),
            })
            _audit(self.env, res_model, [res_id], 'quicktask:%s' % action,
                   {'mail.activity'}, operator)
            return {'ok': True, 'kind': 'activity', 'id': act.id, 'assigneeUid': user_id,
                    'resModel': res_model, 'resId': res_id}

        # --- campione → campionatura (cf.shipment) via metodo gated esistente ---
        if action == 'campione':
            lines = []
            for l in (payload or {}).get('lines') or []:
                pid = l.get('productId') or l.get('product_id')
                if pid:
                    lines.append({'productId': int(pid), 'qty': float(l.get('qty') or 1)})
            if not lines:
                raise UserError(_("Seleziona almeno un prodotto per il campione."))
            if not (partner_id or lead_id):
                raise UserError(_("Serve un partner o un lead per la campionatura."))
            res = self.env['cf.shipment'].console_crea_campionatura({
                'partnerId': partner_id or None, 'leadId': lead_id or None, 'lines': lines,
                'assignees': ({'creazione': emp_id} if emp_id else None),
                'operator_uid': operator.id,
            })
            return {'ok': True, 'kind': 'campionatura', **(res or {})}

        # --- task produzione/operativo → cf.task ---
        if not summary:
            raise UserError(_("Titolo task obbligatorio."))
        task_vals = {'name': summary, 'originator_id': operator.id}
        if partner_id:
            task_vals['partner_id'] = partner_id
        if lead_id:
            task_vals['lead_id'] = lead_id
        task = self.env['cf.task'].sudo().create(task_vals)
        _audit(self.env, 'cf.task', [task.id], 'quicktask:task', None, operator)
        return {'ok': True, 'kind': 'task', 'id': task.id, 'name': task.name}


class SaleOrderConsoleQuote(models.Model):
    """Fase 1 Step 4 — quotazione bozza dalla Console. Solo draft, mai confermata. Gated + audit."""
    _inherit = 'sale.order'

    @api.model
    def console_create_quotation(self, payload):
        """Crea sale.order in stato draft con le righe dei prodotti scelti. Default Incoterm EXW.
        payload: {partnerId, leadId?, lines:[{productId,qty}], operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        partner_id = int((payload or {}).get('partnerId') or 0)
        if not partner_id:
            raise UserError(_("Cliente obbligatorio per la quotazione."))
        order_lines = []
        for l in (payload or {}).get('lines') or []:
            pid = l.get('productId') or l.get('product_id')
            if not pid:
                continue
            order_lines.append((0, 0, {
                'product_id': int(pid), 'product_uom_qty': float(l.get('qty') or 1)}))
        if not order_lines:
            raise UserError(_("Aggiungi almeno un prodotto alla quotazione."))

        vals = {'partner_id': partner_id, 'order_line': order_lines}
        incoterm = self.env['account.incoterms'].sudo().search([('code', '=', 'EXW')], limit=1)
        if incoterm and 'incoterm' in self._fields:
            vals['incoterm'] = incoterm.id
        lead_id = int((payload or {}).get('leadId') or 0)
        if lead_id and 'opportunity_id' in self._fields:
            vals['opportunity_id'] = lead_id

        order = self.sudo().create(vals)  # state di default = 'draft' → mai confermato
        _audit(self.env, 'sale.order', [order.id], 'create_quotation',
               {'partner_id', 'order_line'}, operator)
        return {'ok': True, 'orderId': order.id, 'name': order.name,
                'state': order.state, 'amountTotal': order.amount_total}
