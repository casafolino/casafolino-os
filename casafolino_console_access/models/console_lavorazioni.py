import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager

_logger = logging.getLogger(__name__)

# Colonne fisse della board = le 4 operative (hr.employee). Antonio/Martina sono
# manager/assegnatori: assegnabili ma senza colonna pool propria.
# Gli id sono per-DB (stage != prod): override via ir.config_parameter, default = prod.
_BOARD_EMPLOYEE_PARAM = 'casafolino.lavorazioni.board_employee_ids'
_BOARD_EMPLOYEE_DEFAULT = '9,6,3,10'  # Maria, Teresa, Anna, Valentina (prod)
ANTONIO_USER_ID = 2

# Stati cf.task "aperti" (in coda / lavorabili): esclude chiuso/annullato.
_OPEN_STATES = ('bozza', 'in_corso', 'taken', 'blocked')

_CONSOLE_MANAGER_GROUP = 'casafolino_console_access.group_console_manager'


class CfTaskConsoleBoard(models.Model):
    """Brief Lavorazioni — board per-assegnatario + Pool + claim, lens su cf.task.
    NON crea un modello nuovo: riusa il lifecycle BackOperation (bo_action_*) e legge
    nativo cf.task (dossier = lente, non duplica). console_api non scrive mai in diretta:
    ogni write passa da metodo gated + sudo + audit."""
    _inherit = 'cf.task'

    # ------------------------------------------------------------- helpers
    def _console_operator_employee(self, operator):
        """res.users (operator_uid Console) → hr.employee, ponte via employee.user_id.
        Ritorna None se nessun employee collegato."""
        emp = self.env['hr.employee'].sudo().search(
            [('user_id', '=', operator.id)], limit=1)
        return emp or None

    def _console_is_manager(self, operator):
        return operator.id == ANTONIO_USER_ID or operator.has_group(_CONSOLE_MANAGER_GROUP)

    def _console_board_employee_ids(self):
        """Id delle operative-colonna, da config param (per-DB), default prod."""
        raw = self.env['ir.config_parameter'].sudo().get_param(
            _BOARD_EMPLOYEE_PARAM, _BOARD_EMPLOYEE_DEFAULT)
        ids = []
        for tok in (raw or '').split(','):
            tok = tok.strip()
            if tok.isdigit():
                ids.append(int(tok))
        return ids or [int(x) for x in _BOARD_EMPLOYEE_DEFAULT.split(',')]

    def _console_task_card(self, task):
        """Card serializzata per la board. Legge nativo cf.task, niente duplicazione."""
        return {
            'id': task.id,
            'name': task.name,
            'state': task.state,
            'isPool': task.bo_is_pool,
            'titolareId': task.bo_titolare_id.id or False,
            'titolareName': task.bo_titolare_id.name or False,
            'assegnataDa': task.bo_assegnata_da_id.name or False,
            'deadline': task.date_deadline and fields.Datetime.to_string(task.date_deadline) or False,
            'priority': task.priority or '0',
            'checkinAt': task.bo_checkin_at and fields.Datetime.to_string(task.bo_checkin_at) or False,
            'checkoutAt': task.bo_checkout_at and fields.Datetime.to_string(task.bo_checkout_at) or False,
            'firmata': task.bo_firmata,
        }

    def _console_task_for_action(self, task_id, operator):
        """Carica la task e applica la regola permessi (Python, come il resto del modulo):
        manager → sempre; altrimenti SOLO il titolare (bo_titolare_id == sua employee).
        Le task in pool si gestiscono via console_task_claim, non qui."""
        task = self.sudo().browse(int(task_id or 0))
        if not task.exists():
            raise UserError(_("Task inesistente."))
        if self._console_is_manager(operator):
            return task
        emp = self._console_operator_employee(operator)
        if emp and task.bo_titolare_id and task.bo_titolare_id.id == emp.id:
            return task
        raise AccessError(_("Non sei il titolare di questa task."))

    def _console_notify_claim(self, task, emp, originator):
        """Notifica in-app (bell) ad Antonio + creatore originale quando una task lascia il pool."""
        recipients = self.env['res.users'].sudo().browse(ANTONIO_USER_ID)
        if originator and originator.exists():
            recipients |= originator
        partner_ids = recipients.mapped('partner_id').ids
        if not partner_ids:
            return
        task.sudo().message_post(
            body=_("Task «%(name)s» presa in carico da %(emp)s (dal pool).",
                   name=task.name, emp=emp.name),
            partner_ids=partner_ids,
            message_type='comment', subtype_xmlid='mail.mt_comment')

    # ------------------------------------------------------------- board
    @api.model
    def console_task_board(self, payload=None):
        """Board manager: colonna Pool + una colonna per operativa, task aperti ordinati
        per scadenza. payload: {operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        Task = self.sudo()
        order = 'date_deadline asc, priority desc, create_date asc'

        pool = Task.search(
            [('bo_is_pool', '=', True), ('state', 'in', _OPEN_STATES)], order=order, limit=300)
        columns = [{
            'key': 'pool', 'kind': 'pool', 'name': 'Pool', 'employeeId': False,
            'count': len(pool), 'cards': [self._console_task_card(t) for t in pool],
        }]

        Emp = self.env['hr.employee'].sudo()
        for eid in self._console_board_employee_ids():
            emp = Emp.browse(eid)
            if not emp.exists():
                continue
            tasks = Task.search(
                [('bo_titolare_id', '=', eid), ('state', 'in', _OPEN_STATES)],
                order=order, limit=300)
            columns.append({
                'key': 'emp-%d' % eid, 'kind': 'assignee', 'name': emp.name,
                'employeeId': eid, 'count': len(tasks),
                'cards': [self._console_task_card(t) for t in tasks],
            })

        _audit(self.env, 'cf.task', [], 'task_board', None, operator)
        return {'ok': True, 'columns': columns}

    @api.model
    def console_task_operator_view(self, payload=None):
        """Vista operatore: Pool (claimabile da chiunque) + le mie task (titolare io).
        Qualsiasi operativa Console, NON manager-only. payload: {operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        emp = self._console_operator_employee(operator)
        Task = self.sudo()
        order = 'date_deadline asc, priority desc, create_date asc'
        pool = Task.search(
            [('bo_is_pool', '=', True), ('state', 'in', _OPEN_STATES)], order=order, limit=200)
        mine = Task.browse()
        if emp:
            mine = Task.search(
                [('bo_titolare_id', '=', emp.id), ('state', 'in', _OPEN_STATES)],
                order=order, limit=200)
        _audit(self.env, 'cf.task', [], 'task_operator_view', None, operator)
        return {
            'ok': True,
            'employeeId': emp.id if emp else False,
            'pool': [self._console_task_card(t) for t in pool],
            'mine': [self._console_task_card(t) for t in mine],
        }

    # ------------------------------------------------------------- claim
    @api.model
    def console_task_claim(self, payload):
        """Prendi in carico una task dal Pool. Qualsiasi operativa del team può fare claim
        su task in pool (indipendentemente da chi l'ha creata). payload: {taskId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        emp = self._console_operator_employee(operator)
        if not emp:
            raise UserError(_("Operatore senza hr.employee collegato: claim impossibile."))
        task = self.sudo().browse(int((payload or {}).get('taskId') or 0))
        if not task.exists():
            raise UserError(_("Task inesistente."))
        if not task.bo_is_pool:
            raise UserError(_("Task non più in pool (già assegnata)."))
        originator = task.originator_id
        task.bo_action_claim(emp.id)
        self._console_notify_claim(task, emp, originator)
        _audit(self.env, 'cf.task', [task.id], 'task_claim', {'bo_titolare_id'}, operator)
        return {'ok': True, **self._console_task_card(task)}

    # ------------------------------------------------------- lifecycle
    @api.model
    def console_task_checkin(self, payload):
        """Check-in: lavorazione iniziata. payload: {taskId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        task = self._console_task_for_action((payload or {}).get('taskId'), operator)
        emp = self._console_operator_employee(operator) or task.bo_titolare_id
        if not emp:
            raise UserError(_("Operatore senza employee per il check-in."))
        task.bo_action_checkin(emp.id)
        _audit(self.env, 'cf.task', [task.id], 'task_checkin', {'state'}, operator)
        return {'ok': True, **self._console_task_card(task)}

    @api.model
    def console_task_checkout(self, payload):
        """Check-out: lavorazione conclusa (timer fermo). payload: {taskId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        task = self._console_task_for_action((payload or {}).get('taskId'), operator)
        task.bo_action_checkout()
        _audit(self.env, 'cf.task', [task.id], 'task_checkout', {'bo_checkout_at'}, operator)
        return {'ok': True, **self._console_task_card(task)}

    @api.model
    def console_task_sign(self, payload):
        """Firma e chiudi (Livello A BackOperation). payload: {taskId, firma?, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        task = self._console_task_for_action((payload or {}).get('taskId'), operator)
        emp = (self._console_operator_employee(operator)
               or task.bo_operatore_id or task.bo_titolare_id)
        if not emp:
            raise UserError(_("Operatore senza employee per la firma."))
        firma = (payload or {}).get('firma') or False
        task.bo_action_sign(emp.id, firma)
        _audit(self.env, 'cf.task', [task.id], 'task_sign', {'state', 'bo_firmata'}, operator)
        return {'ok': True, **self._console_task_card(task)}

    # ------------------------------------------------------- assign (manager)
    @api.model
    def console_task_assign(self, payload):
        """Manager: assegna una task a una persona o lasciala/rimettila in pool.
        payload: {taskId, assignee_employee_id?(null/0 = pool), operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        task = self.sudo().browse(int((payload or {}).get('taskId') or 0))
        if not task.exists():
            raise UserError(_("Task inesistente."))
        emp_id = int((payload or {}).get('assignee_employee_id') or 0) or False
        if emp_id:
            emp = self.env['hr.employee'].sudo().browse(emp_id)
            if not emp.exists():
                raise UserError(_("Operativa inesistente."))
            task.bo_titolare_id = emp.id
            task.bo_assegnata_da_id = operator.id  # non più pool
            task._message_log(
                body=_("Assegnata a %(emp)s da %(op)s.", emp=emp.name, op=operator.name))
        else:
            task.bo_action_to_pool()
        _audit(self.env, 'cf.task', [task.id], 'task_assign',
               {'bo_titolare_id', 'bo_assegnata_da_id'}, operator)
        return {'ok': True, **self._console_task_card(task)}
