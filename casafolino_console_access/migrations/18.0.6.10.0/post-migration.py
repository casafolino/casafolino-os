# Brief 5 — assegna i manager al group_console_manager all'update (-u).
# post_init_hook gira solo all'install; su update serve la migration.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.casafolino_console_access import _ensure_console_managers
    _ensure_console_managers(env)
