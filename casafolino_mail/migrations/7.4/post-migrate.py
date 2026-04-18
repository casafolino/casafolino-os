import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.3 → 7.4: fix AI classify cron interval (rate limit Groq free tier)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo()

    # ── 1. Update cron interval: 10 min → 5 min ──
    _logger.info("[mail migration 7.4] Step 1: update cron AI Classify interval...")
    cron = Cron.search([('cron_name', '=', 'CasaFolino: AI Classify Pending')], limit=1)
    if cron:
        cron.write({
            'interval_number': 5,
            'interval_type': 'minutes',
        })
        _logger.info("[mail migration 7.4] Cron AI Classify aggiornato: 5 min interval.")
    else:
        _logger.warning("[mail migration 7.4] Cron AI Classify non trovato, skip.")

    # ── 2. Reset ai_error per messaggi con "Rate limit 429" (retry con nuova logica) ──
    _logger.info("[mail migration 7.4] Step 2: reset ai_error rate limit per retry...")
    cr.execute("""
        UPDATE casafolino_mail_message
        SET ai_error = NULL
        WHERE ai_error = 'Rate limit 429'
          AND ai_classified_at IS NULL
    """)
    reset_count = cr.rowcount
    _logger.info("[mail migration 7.4] Reset %d messaggi con ai_error rate limit.", reset_count)
