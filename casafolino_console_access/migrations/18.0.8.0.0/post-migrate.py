# Brief Regia+Dossier — su update (-u) occulta i menu legacy (Lavagna/Cockpit).
# post_init_hook gira solo all'install; su modulo già installato serve la migration.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.casafolino_console_access import _hide_legacy_menus
    _hide_legacy_menus(env)
