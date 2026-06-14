import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.4 → 7.5: fix cron AI Classify interval (7.4 usava nome sbagliato)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo()

    # 7.4 cercava 'CasaFolino: AI Classify Pending' ma il nome reale in DB
    # è 'CasaFolino AI Classify - Action' (suffisso aggiunto da Odoo via ir.actions.server)
    _logger.info("[mail migration 7.5] Step 1: fix cron AI Classify interval...")
    cron = Cron.search([('cron_name', 'ilike', 'AI Classify')], limit=1)
    if cron:
        if cron.interval_number != 5 or cron.interval_type != 'minutes':
            cron.write({
                'interval_number': 5,
                'interval_type': 'minutes',
            })
            _logger.info("[mail migration 7.5] Cron AI Classify aggiornato: interval=5 minutes (was %s %s)",
                         cron.interval_number, cron.interval_type)
        else:
            _logger.info("[mail migration 7.5] Cron AI Classify gia' a 5 minuti, skip.")
    else:
        _logger.warning('[mail migration 7.5] Cron AI Classify non trovato '
                        '(nome atteso: "CasaFolino AI Classify - Action"), verificare manualmente')
