import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Initialize default values for new V3 fields on existing records."""
    _logger.info("post-migrate 18.0.11.1.0: setting defaults on V3 fields")

    cr.execute("""
        UPDATE casafolino_mail_message
        SET is_starred = FALSE
        WHERE is_starred IS NULL;
    """)
    _logger.info("post-migrate: is_starred defaults set (%d rows)", cr.rowcount)

    cr.execute("""
        UPDATE casafolino_mail_message
        SET is_archived = FALSE
        WHERE is_archived IS NULL;
    """)
    _logger.info("post-migrate: is_archived defaults set (%d rows)", cr.rowcount)

    cr.execute("""
        UPDATE casafolino_mail_message
        SET is_deleted = FALSE
        WHERE is_deleted IS NULL;
    """)
    _logger.info("post-migrate: is_deleted defaults set (%d rows)", cr.rowcount)

    cr.execute("""
        UPDATE casafolino_mail_message
        SET is_snoozed = FALSE
        WHERE is_snoozed IS NULL;
    """)
    _logger.info("post-migrate: is_snoozed defaults set (%d rows)", cr.rowcount)

    # Backfill direction_computed from direction
    cr.execute("""
        UPDATE casafolino_mail_message
        SET direction_computed = direction
        WHERE direction_computed IS NULL AND direction IS NOT NULL;
    """)
    _logger.info("post-migrate: direction_computed backfilled (%d rows)", cr.rowcount)
