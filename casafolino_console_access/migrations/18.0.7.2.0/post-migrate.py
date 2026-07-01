"""Brief Lavorazioni — bridge identita': collega hr.employee.user_id alle operative
che ne erano sprovviste (Teresa, Anna), cosi' il claim risolve operator_uid (res.users)
-> hr.employee via search([('user_id','=',operator_uid)]) per TUTTO il team.

Match per login email (stabile tra stage e prod), NON per id hardcoded: gli id
differiscono tra DB. Idempotente: salta se employee.user_id e' gia' valorizzato o se
employee/user non esistono in questo DB.
"""
import logging

_logger = logging.getLogger(__name__)

# (login res.users, nome hr.employee) delle operative da collegare.
_LINKS = [
    ('teresa.furgiuele@casafolino.com', 'Teresa Furgiuele'),
    ('anna.macri@casafolino.com', 'Anna Macrì'),
]


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    Users = env['res.users'].sudo()
    Emp = env['hr.employee'].sudo()
    for login, emp_name in _LINKS:
        user = Users.search([('login', '=', login)], limit=1)
        if not user:
            _logger.info('[lavorazioni-migr] utente %s assente, skip', login)
            continue
        emp = Emp.search([('name', '=', emp_name), ('user_id', '=', False)], limit=1)
        if not emp:
            _logger.info('[lavorazioni-migr] employee %s assente o gia collegato, skip', emp_name)
            continue
        emp.user_id = user.id
        _logger.info('[lavorazioni-migr] collegato employee %s (id=%s) -> user %s (id=%s)',
                     emp_name, emp.id, login, user.id)
