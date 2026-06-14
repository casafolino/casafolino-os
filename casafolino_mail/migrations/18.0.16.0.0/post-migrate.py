"""V16 migration: multi-user hardening.

- Link casafolino.mail.account → res.users via responsible_user_id
- Verify/create Josefina and Martina users if missing
"""
import logging

_logger = logging.getLogger(__name__)

# Account email → expected user login mapping
ACCOUNT_USER_MAP = {
    'antonio@casafolino.com': 'antonio@casafolino.com',
    'martina.sinopoli@casafolino.com': 'martina.sinopoli@casafolino.com',
    'josefina.lazzaro@casafolino.com': 'josefina.lazzaro@casafolino.com',
}

# Users to create if missing
USERS_TO_ENSURE = [
    {
        'name': 'Martina Sinopoli',
        'login': 'martina.sinopoli@casafolino.com',
        'email': 'martina.sinopoli@casafolino.com',
    },
    {
        'name': 'Josefina Lazzaro',
        'login': 'josefina.lazzaro@casafolino.com',
        'email': 'josefina.lazzaro@casafolino.com',
    },
]


def migrate(cr, version):
    from odoo.api import Environment
    from odoo import SUPERUSER_ID

    env = Environment(cr, SUPERUSER_ID, {})
    Users = env['res.users'].sudo()
    Account = env['casafolino.mail.account'].sudo()

    # ── Step 1: Ensure Josefina and Martina users exist ──────────
    for user_data in USERS_TO_ENSURE:
        existing = Users.search([('login', '=', user_data['login'])], limit=1)
        if existing:
            _logger.info("V16 migration: user %s already exists (id=%d)",
                         user_data['login'], existing.id)
        else:
            new_user = Users.create({
                'name': user_data['name'],
                'login': user_data['login'],
                'email': user_data['email'],
                'groups_id': [(4, env.ref('base.group_user').id)],
            })
            _logger.info("V16 migration: created user %s (id=%d)",
                         user_data['login'], new_user.id)

    # ── Step 2: Link each account to its user via responsible_user_id ─
    accounts = Account.search([])
    linked = 0
    for acc in accounts:
        email = (acc.email_address or '').strip().lower()
        target_login = ACCOUNT_USER_MAP.get(email)
        if not target_login:
            _logger.warning("V16 migration: no user mapping for account %s (id=%d)",
                            email, acc.id)
            continue

        user = Users.search([('login', '=', target_login)], limit=1)
        if not user:
            _logger.warning("V16 migration: user %s not found for account %s",
                            target_login, email)
            continue

        if acc.responsible_user_id.id != user.id:
            acc.write({'responsible_user_id': user.id})
            _logger.info("V16 migration: linked account %s → user %s (id=%d)",
                         email, user.login, user.id)
            linked += 1
        else:
            _logger.info("V16 migration: account %s already linked to %s",
                         email, user.login)

    _logger.info("V16 migration complete: %d accounts linked, %d total accounts",
                 linked, len(accounts))
