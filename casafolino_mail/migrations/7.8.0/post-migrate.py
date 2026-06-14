import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.7.0 → 7.8.0: lead scoring view (idempotente)."""
    _logger.info("[mail migration 7.8.0] Step 1: drop lead score view for recreation...")
    cr.execute("DROP VIEW IF EXISTS casafolino_mail_lead_score CASCADE")
    _logger.info("[mail migration 7.8.0] View droppata, sara' ricreata da init().")

    # Count partner attesi e score medio
    cr.execute("""
        SELECT COUNT(DISTINCT m.partner_id)
        FROM casafolino_mail_message m
        JOIN res_partner p ON p.id = m.partner_id
        WHERE m.direction = 'inbound'
          AND m.state IN ('keep', 'auto_keep')
          AND m.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '90 days'
          AND (p.email IS NULL OR p.email NOT ILIKE '%%@casafolino.com')
    """)
    count = cr.fetchone()[0]
    _logger.info("[mail migration 7.8.0] Partner con email IN 90gg (candidati scoring): %d", count)
