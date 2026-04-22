import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Add 5 new V3 fields to casafolino_mail_message (idempotent)."""
    _logger.info("pre-migrate 18.0.11.1.0: adding V3 fields to casafolino_mail_message")

    cr.execute("""
        ALTER TABLE casafolino_mail_message
            ADD COLUMN IF NOT EXISTS thread_id INTEGER,
            ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_snoozed BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS reply_to_message_id INTEGER,
            ADD COLUMN IF NOT EXISTS direction_computed VARCHAR,
            ADD COLUMN IF NOT EXISTS hotness_snapshot VARCHAR;
    """)

    # Index on is_deleted for soft-delete filtering
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_casafolino_mail_message_is_deleted
        ON casafolino_mail_message (is_deleted)
        WHERE is_deleted = TRUE;
    """)

    # Index on direction_computed for fast inbox/sent queries
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_casafolino_mail_message_direction_computed
        ON casafolino_mail_message (direction_computed);
    """)
