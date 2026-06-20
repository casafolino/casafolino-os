# S5 prereq — assegna gli operatori umani a group_console_operator su -u (update path).
# post_init_hook non rigira su modulo già installato: questa migration garantisce i membri.
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    # Migration script: non è membro del package → import assoluto dell'addon.
    from odoo.addons.casafolino_console_access import _ensure_console_operators
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("[console S5 migration] assegno operatori a group_console_operator")
    _ensure_console_operators(env)
