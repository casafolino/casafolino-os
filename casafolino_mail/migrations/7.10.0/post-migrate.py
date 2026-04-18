import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.9.0 → 7.10.0: sender decision triage (idempotente)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    count = env['casafolino.mail.sender.decision'].search_count([])
    _logger.info("[mail migration 7.10.0] Sender decision records esistenti: %d", count)
