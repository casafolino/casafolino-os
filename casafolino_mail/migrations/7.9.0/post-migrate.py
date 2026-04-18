import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.8.1 → 7.9.0: snippet library (idempotente)."""
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Count snippet caricati (seed noupdate=1 li carica al primo install)
    count = env['casafolino.mail.snippet'].search_count([])
    _logger.info("[mail migration 7.9.0] Snippet in libreria: %d", count)
