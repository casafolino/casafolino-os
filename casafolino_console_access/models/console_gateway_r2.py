import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

# Round 2 — alza il privilegio SOLO dentro metodi gated + sudo (stesso pattern dei metodi
# gateway già in prod). console_api resta a privilegi ridotti via ACL; questi metodi colmano
# i punti rimasti "off/vuoti" della Console v2: nota/task (chatter), Ordini/Campionature
# (sale.order/cf.shipment non visibili a console_api), semaforo SLA (cf.task).
from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager

_logger = logging.getLogger(__name__)

# Modelli su cui la Console può postare nota/pianificare attività (chatter nativo).
_NOTE_MODELS = ('crm.lead', 'res.partner', 'project.project')
# cf.shipment "in corso" = qualunque stato prima della consegna.
_SHIPMENT_TRANSIT = ('creato', 'preparazione', 'etichetta', 'spedito')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class CrmLeadConsoleR2(models.Model):
    """M1/M2/M5 — nota, attività, SLA. Tutto gated _is_console + operatore validato
    (allowlist, anti-spoofing) + sudo interno. console_api NON ha ACL chatter/cf.task:
    il privilegio sale solo qui, controllato."""
    _inherit = 'crm.lead'

    # ---- M1: nota interna attribuita all'operatore (mai a console_api) ----
    @api.model
    def console_post_note(self, payload):
        """payload: {res_model?, res_id, body, operator_uid}. author_id = partner operatore."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))  # raise se non in allowlist
        if not operator or not operator.partner_id:
            raise UserError(_("Operatore senza contatto: impossibile attribuire la nota."))
        res_model = (payload or {}).get('res_model') or 'crm.lead'
        res_id = int((payload or {}).get('res_id') or 0)
        body = ((payload or {}).get('body') or '').strip()
        if res_model not in _NOTE_MODELS:
            raise UserError(_("Modello non ammesso per la nota: %s") % res_model)
        if not res_id or not body:
            raise UserError(_("res_id e body sono obbligatori."))
        rec = self.env[res_model].sudo().browse(res_id)
        if not rec.exists():
            raise UserError(_("Record non trovato."))
        msg = rec.message_post(
            body=body, message_type='comment', subtype_xmlid='mail.mt_note',
            author_id=operator.partner_id.id)
        _audit(self.env, res_model, [res_id], 'post_note', None, operator)
        return {'ok': True, 'id': msg.id}

    # ---- M2: attività futura assegnata all'operatore ----
    @api.model
    def console_schedule_activity(self, payload):
        """payload: {res_model?, res_id, summary, date_deadline(YYYY-MM-DD), operator_uid, activity_type_id?}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        res_model = (payload or {}).get('res_model') or 'crm.lead'
        res_id = int((payload or {}).get('res_id') or 0)
        summary = ((payload or {}).get('summary') or '').strip()
        deadline = (payload or {}).get('date_deadline')
        if res_model not in _NOTE_MODELS:
            raise UserError(_("Modello non ammesso per l'attività: %s") % res_model)
        if not res_id or not summary:
            raise UserError(_("res_id e summary sono obbligatori."))
        if not deadline or not _DATE_RE.match(str(deadline)):
            raise UserError(_("date_deadline (YYYY-MM-DD) obbligatoria."))
        model_row = self.env['ir.model'].sudo().search([('model', '=', res_model)], limit=1)
        if not model_row:
            raise UserError(_("Modello %s non risolto.") % res_model)
        act_type = (payload or {}).get('activity_type_id')
        if not act_type:
            todo = self.env['ir.model.data'].sudo().search(
                [('module', '=', 'mail'), ('name', '=', 'mail_activity_data_todo')], limit=1)
            act_type = todo.res_id if todo else False
        act = self.env['mail.activity'].sudo().create({
            'res_model_id': model_row.id,
            'res_id': res_id,
            'summary': summary,
            'date_deadline': deadline,
            'user_id': operator.id,
            **({'activity_type_id': act_type} if act_type else {}),
        })
        _audit(self.env, res_model, [res_id], 'schedule_activity', None, operator)
        return {'ok': True, 'id': act.id}

    # ---- M5: semaforo SLA reale dai cf.task del lead ----
    @api.model
    def console_lead_sla(self, payload):
        """payload: {leadId, operator_uid}. Ritorna il semaforo (worst dei cf.task aperti)."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)  # SLA del lead = dato CRM (manager-only)
        lead_id = int((payload or {}).get('leadId') or (payload or {}).get('lead_id') or 0)
        if not lead_id:
            raise UserError(_("leadId obbligatorio."))
        tasks = self.env['cf.task'].sudo().search([('lead_id', '=', lead_id)])
        open_tasks = tasks.filtered(lambda t: t.state in ('bozza', 'in_corso'))
        rank = {'green': 0, 'yellow': 1, 'red': 2}
        semaforo = None
        if open_tasks:
            lights = open_tasks.mapped('traffic_light') or ['green']
            semaforo = max(lights, key=lambda c: rank.get(c, 0))
        return {
            'ok': True, 'leadId': lead_id,
            'hasTasks': bool(tasks), 'openCount': len(open_tasks),
            'totalCount': len(tasks),
            'semaforo': semaforo,  # 'green' | 'yellow' | 'red' | None (nessun task aperto)
        }


class ResPartnerConsoleR2(models.Model):
    """M3/M4 — Ordini e Campionature del partner. console_api NON vede sale.order/cf.shipment
    (record-rule) → letti in sudo qui, gated + manager."""
    _inherit = 'res.partner'

    # ---- M3: tutti i sale.order del partner (nessun filtro stato) ----
    @api.model
    def console_partner_orders(self, payload):
        """payload: {partnerId, operator_uid}. Ritorna tutti i sale.order (ordini + campioni)."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        pid = int((payload or {}).get('partnerId') or (payload or {}).get('partner_id') or 0)
        if not pid:
            raise UserError(_("partnerId obbligatorio."))
        has_campione = 'is_campione' in self.env['sale.order']._fields
        orders = self.env['sale.order'].sudo().search(
            [('partner_id', 'child_of', pid)], order='date_order desc, id desc')
        return {'ok': True, 'partnerId': pid, 'orders': [{
            'id': o.id, 'name': o.name, 'amountTotal': o.amount_total, 'state': o.state,
            'dateOrder': str(o.date_order) if o.date_order else None,
            'isCampione': bool(o.is_campione) if has_campione else False,
        } for o in orders]}

    # ---- M4: cf.shipment delle campionature del partner ----
    @api.model
    def console_partner_shipments(self, payload):
        """payload: {partnerId, operator_uid}. Ritorna lo stato shipment per campione."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        pid = int((payload or {}).get('partnerId') or (payload or {}).get('partner_id') or 0)
        if not pid:
            raise UserError(_("partnerId obbligatorio."))
        Sh = self.env['cf.shipment'].sudo()
        sel = dict(Sh._fields['state'].selection)
        shs = Sh.search([('partner_id', 'child_of', pid)], order='create_date desc')
        return {'ok': True, 'partnerId': pid, 'shipments': [{
            'id': s.id, 'name': s.name, 'state': s.state, 'stateLabel': sel.get(s.state, s.state),
            'inTransit': s.state in _SHIPMENT_TRANSIT,
            'carrier': s.carrier or None, 'tracking': s.tracking_code or None,
            'saleOrderId': s.sale_order_id.id or None, 'leadId': s.lead_id.id or None,
        } for s in shs]}
