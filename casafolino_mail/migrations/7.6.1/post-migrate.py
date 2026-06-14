import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.6 → 7.6.1: drop SLA view so init() recreates with is_won fix."""
    _logger.info("[mail migration 7.6.1] Drop SLA view for recreation with NULL is_won fix...")
    cr.execute("DROP VIEW IF EXISTS casafolino_mail_sla_partner CASCADE")
    _logger.info("[mail migration 7.6.1] View droppata, sara' ricreata da init().")
