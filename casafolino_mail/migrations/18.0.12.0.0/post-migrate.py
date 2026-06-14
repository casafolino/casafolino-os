import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Initialize default values for V3 columns and compute direction_computed."""
    _logger.info("post-migrate 18.0.12.0.0 — initializing V3 defaults")

    # Set direction_computed from existing direction field
    cr.execute("""
        UPDATE casafolino_mail_message
        SET direction_computed = direction
        WHERE direction_computed IS NULL
          AND direction IS NOT NULL;
    """)
    updated = cr.rowcount
    _logger.info("post-migrate 18.0.12.0.0 — direction_computed set for %d rows", updated)

    # Ensure boolean fields have proper defaults (not NULL)
    for col in ('is_starred', 'is_deleted', 'is_snoozed', 'is_archived'):
        cr.execute("""
            UPDATE casafolino_mail_message
            SET {col} = false
            WHERE {col} IS NULL;
        """.format(col=col))

    # NOTE: res_partner.email_domains_extra already exists from V11 — not touched here

    _logger.info("post-migrate 18.0.12.0.0 — done")
