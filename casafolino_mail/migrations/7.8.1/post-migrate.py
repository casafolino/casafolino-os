import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.8.0 → 7.8.1: recalibrate lead score view (idempotente)."""
    _logger.info("[mail migration 7.8.1] Drop lead score view for recreation with recalibrated formula...")
    cr.execute("DROP VIEW IF EXISTS casafolino_mail_lead_score CASCADE")
    _logger.info("[mail migration 7.8.1] View droppata, sara' ricreata da init().")
