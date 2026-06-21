import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

# Riusa il pattern S5 già testato del gateway mail: gate console + audit + attribution.
# _resolve_operator vive come metodo su casafolino.mail.message (usa solo self.env):
# lo richiamiamo via env['casafolino.mail.message']._resolve_operator(uid) → niente duplicazione.
from .console_gateway import _is_console, _audit

_logger = logging.getLogger(__name__)


def _operator(env, operator_uid):
    """Risolve+valida l'operatore umano (allowlist group_console_operator) riusando
    la logica S5 esistente. operator_uid arriva SEMPRE dalla sessione (server-side):
    il route Next scarta quello del client e inietta quello del JWT."""
    op = env['casafolino.mail.message']._resolve_operator(operator_uid)
    if not op:
        raise UserError(_("Operatore non identificato (login Console richiesto)."))
    return op


class CfShipmentConsole(models.Model):
    """Gateway Console per la campionatura. ESPONE la logica già in prod
    (cf.shipment.crea_campionatura) — non la riscrive. Tutto gated _is_console +
    sudo per le scritture + audit con operatore. console_api resta read-only via ACL."""
    _inherit = 'cf.shipment'

    @api.model
    def console_crea_campionatura(self, payload):
        """Lancia la campionatura dalla Console. Originatore = operatore (sessione),
        MAI il service-user console_api.
        payload: {partnerId?, leadId?, lines:[{productId, qty}],
                  assignees?:{coordinazione,creazione,logistica}, carrier?, operator_uid}
        """
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api può lanciare la campionatura."))
        operator = _operator(self.env, payload.get('operator_uid'))

        raw_lines = payload.get('lines') or []
        lines = []
        for l in raw_lines:
            pid = l.get('productId') or l.get('product_id')
            if not pid:
                continue
            qty = l.get('qty') or l.get('product_uom_qty') or 1
            lines.append({'product_id': int(pid), 'product_uom_qty': float(qty)})
        if not lines:
            raise UserError(_("Aggiungi almeno un prodotto con quantità."))

        assignees = None
        raw_assignees = payload.get('assignees') or {}
        if raw_assignees:
            assignees = {k: int(v) for k, v in raw_assignees.items() if v}

        res = self.sudo().crea_campionatura(
            partner_id=int(payload['partnerId']) if payload.get('partnerId') else None,
            lead_id=int(payload['leadId']) if payload.get('leadId') else None,
            lines=lines,
            assignees=assignees,
            carrier=(payload.get('carrier') or None),
        )
        # Override originatore: crea_campionatura usa env.user (= console_api) come default
        # sul cf.task. Qui registriamo CHI ha lanciato (attribution umana).
        self.env['cf.task'].sudo().browse(res['task_id']).write(
            {'originator_id': operator.id})
        _audit(self.env, 'cf.shipment', [res['shipment_id']],
               'crea_campionatura', {'order_id', 'task_id', 'shipment_id'}, operator)
        res['ok'] = True
        return res

    @api.model
    def console_search_products(self, query, limit=20):
        """Picker prodotti: catalogo vendibile, read-only (sudo, niente ACL nuovo)."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        q = (query or '').strip()
        domain = [('sale_ok', '=', True)]
        if q:
            domain = ['&', ('sale_ok', '=', True),
                      '|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
        prods = self.env['product.product'].sudo().search(
            domain, limit=min(int(limit or 20), 50), order='name')
        return [{'id': p.id, 'name': p.display_name,
                 'code': p.default_code or '', 'uom': p.uom_id.name or ''}
                for p in prods]

    @api.model
    def console_get_campionatura_timeline(self, shipment_id):
        """Vista timeline: step task (ruolo/assegnatario/stato/semaforo) + spedizione."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        sh = self.sudo().browse(int(shipment_id))
        if not sh.exists():
            raise UserError(_("Spedizione inesistente."))
        return sh._console_timeline_dict()

    @api.model
    def console_campionatura_defaults(self):
        """Per il wizard: assegnatari di default per ruolo (da param) + lista operatori
        selezionabili (allowlist group_console_operator) per l'override."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        ICP = self.env['ir.config_parameter'].sudo()
        defaults = {}
        for role in ('coordinazione', 'creazione', 'logistica'):
            uid = int(ICP.get_param('casafolino_campionatura.user_%s' % role, 0) or 0)
            u = self.env['res.users'].sudo().browse(uid) if uid else None
            defaults[role] = {'uid': u.id, 'name': u.name} if (u and u.exists()) else False
        group = self.env.ref(
            'casafolino_console_access.group_console_operator', raise_if_not_found=False)
        operators = []
        if group:
            for u in group.sudo().users.sorted('name'):
                operators.append({'uid': u.id, 'name': u.name})
        return {'defaults': defaults, 'operators': operators}

    def _console_timeline_dict(self):
        self.ensure_one()
        task = self.task_id
        steps = [{
            'stepId': s.id, 'role': s.role, 'name': s.name or '',
            'assignee': s.user_id.name or '', 'assigneeUid': s.user_id.id,
            'state': s.state, 'trafficLight': s.traffic_light,
            'hours': round(s.elapsed_work_hours or 0.0, 1),
            'checkin': fields.Datetime.to_string(s.checkin_dt) if s.checkin_dt else None,
            'checkout': fields.Datetime.to_string(s.checkout_dt) if s.checkout_dt else None,
        } for s in task.step_ids.sorted('sequence')]
        return {
            'shipmentId': self.id, 'name': self.name,
            'partner': self.partner_id.name or '',
            'shipmentState': self.state,
            'carrier': self.carrier or '', 'tracking': self.tracking_code or '',
            'orderId': self.sale_order_id.id,
            'sampleCode': self.sale_order_id.sample_code or '',
            'taskId': task.id, 'taskState': task.state,
            'taskTrafficLight': task.traffic_light,
            'steps': steps,
        }


class CfTaskStepConsole(models.Model):
    """Superficie operatore: liste/azioni sui PROPRI step. Ownership server-side
    (step.user_id == operatore della sessione) — anti-spoof come S5."""
    _inherit = 'cf.task.step'

    def _console_owned_step(self, step_id, operator):
        """Browse + verifica ownership (lo step deve essere dell'operatore)."""
        step = self.sudo().browse(int(step_id))
        if not step.exists():
            raise UserError(_("Step inesistente."))
        if step.user_id.id != operator.id:
            raise AccessError(_("Questo step non è assegnato a te."))
        return step

    @api.model
    def console_list_my_steps(self, payload=None):
        """Step aperti dell'operatore (da_fare/in_corso) con contesto task+shipment.
        Base pulita e queryabile per i display futuri (V2).
        payload: {operator_uid} (iniettato server-side dalla sessione)."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        steps = self.sudo().search([
            ('user_id', '=', operator.id),
            ('state', 'in', ['da_fare', 'in_corso']),
            ('task_id.state', '=', 'in_corso'),
        ], order='task_id, sequence')
        out = []
        Ship = self.env['cf.shipment'].sudo()
        for s in steps:
            sh = Ship.search([('task_id', '=', s.task_id.id)], limit=1)
            out.append({
                'stepId': s.id, 'role': s.role, 'name': s.name or '',
                'state': s.state, 'trafficLight': s.traffic_light,
                'hours': round(s.elapsed_work_hours or 0.0, 1),
                'taskId': s.task_id.id, 'taskName': s.task_id.name or '',
                'partner': s.task_id.partner_id.name or '',
                'isLogistica': s.role == 'logistica',
                'canCheckin': s.state == 'da_fare',
                'shipmentId': sh.id if sh else False,
                'carrier': (sh.carrier or '') if sh else '',
                'tracking': (sh.tracking_code or '') if sh else '',
                'shipmentState': sh.state if sh else '',
            })
        return out

    @api.model
    def console_step_checkin(self, payload):
        """Check-in sul proprio step. payload: {stepId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, payload.get('operator_uid'))
        step = self._console_owned_step(payload.get('stepId'), operator)
        step.action_checkin()
        _audit(self.env, 'cf.task.step', [step.id], 'step_checkin', {'state'}, operator)
        return {'ok': True, 'stepId': step.id, 'state': step.state}

    @api.model
    def console_step_confirm(self, payload):
        """Conferma sul proprio step. Logistica: tracking_code+carrier vengono scritti
        sulla spedizione PRIMA del confirm (la transizione esistente li pretende → senza
        di essi action_confirm solleva UserError, gestito a UI).
        payload: {stepId, trackingCode?, carrier?, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, payload.get('operator_uid'))
        step = self._console_owned_step(payload.get('stepId'), operator)
        if step.state not in ('da_fare', 'in_corso'):
            raise UserError(_("Step già chiuso."))

        if step.role == 'logistica':
            tracking = (payload.get('trackingCode') or '').strip()
            carrier = (payload.get('carrier') or '').strip()
            sh = self.env['cf.shipment'].sudo().search(
                [('task_id', '=', step.task_id.id)], limit=1)
            if sh:
                vals = {}
                if tracking:
                    vals['tracking_code'] = tracking
                if carrier:
                    vals['carrier'] = carrier
                if vals:
                    sh.write(vals)

        # campionatura hook: avanza la cf.shipment; logistica senza tracking → UserError
        step.action_confirm()
        _audit(self.env, 'cf.task.step', [step.id], 'step_confirm', {'state'}, operator)
        return {'ok': True, 'stepId': step.id, 'state': step.state}

    @api.model
    def console_step_remind(self, payload):
        """Sollecito manuale sullo step (dal semaforo rosso in timeline).
        payload: {stepId, operator_uid}. Qualsiasi operatore in allowlist può sollecitare."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, payload.get('operator_uid'))
        step = self.sudo().browse(int(payload.get('stepId')))
        if not step.exists():
            raise UserError(_("Step inesistente."))
        step.action_remind()
        _audit(self.env, 'cf.task.step', [step.id], 'step_remind', None, operator)
        return {'ok': True, 'stepId': step.id}
