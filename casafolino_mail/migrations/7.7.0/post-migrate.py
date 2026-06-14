import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.6.1 → 7.7.0: orphan partner view (idempotente)."""
    _logger.info("[mail migration 7.7.0] Step 1: drop orphan partner view for recreation...")
    cr.execute("DROP VIEW IF EXISTS casafolino_mail_orphan_partner CASCADE")
    _logger.info("[mail migration 7.7.0] View droppata, sara' ricreata da init().")

    # Count partner orfani attesi
    cr.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM res_partner p
        JOIN casafolino_mail_message m ON m.partner_id = p.id
            AND m.direction = 'inbound'
            AND m.state IN ('keep', 'auto_keep')
            AND m.email_date >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '90 days'
        WHERE NOT EXISTS (
            SELECT 1 FROM crm_lead l
            JOIN crm_stage s ON s.id = l.stage_id
            WHERE l.partner_id = p.id
              AND l.active = TRUE
              AND l.type = 'opportunity'
              AND COALESCE(s.is_won, FALSE) = FALSE
        )
        AND (p.email IS NULL OR p.email NOT ILIKE '%%@casafolino.com')
        AND p.id NOT IN (SELECT COALESCE(partner_id, 0) FROM res_users)
    """)
    count = cr.fetchone()[0]
    _logger.info("[mail migration 7.7.0] Partner orfani rilevati: %d", count)
