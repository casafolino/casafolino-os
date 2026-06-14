import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Add V3 columns to casafolino_mail_message if not present."""
    _logger.info("pre-migrate 18.0.12.0.0 — adding V3 columns to casafolino_mail_message")

    columns = [
        ("is_starred", "boolean", "false"),
        ("is_deleted", "boolean", "false"),
        ("is_snoozed", "boolean", "false"),
        ("is_archived", "boolean", "false"),
        ("direction_computed", "varchar", "NULL"),
        ("hotness_snapshot", "varchar", "NULL"),
        ("thread_id", "integer", "NULL"),
        ("reply_to_message_id", "integer", "NULL"),
    ]

    for col, dtype, default in columns:
        cr.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'casafolino_mail_message'
                      AND column_name = %s
                ) THEN
                    ALTER TABLE casafolino_mail_message
                        ADD COLUMN {col} {dtype} DEFAULT {default};
                    RAISE NOTICE 'Added column {col}';
                ELSE
                    RAISE NOTICE 'Column {col} already exists';
                END IF;
            END $$;
        """.format(col=col, dtype=dtype, default=default), [col])

    # Create indexes for performance-critical columns
    indexes = [
        ("casafolino_mail_message_is_archived_idx", "is_archived"),
        ("casafolino_mail_message_is_deleted_idx", "is_deleted"),
        ("casafolino_mail_message_thread_id_idx", "thread_id"),
        ("casafolino_mail_message_direction_computed_idx", "direction_computed"),
    ]

    for idx_name, col in indexes:
        cr.execute("""
            CREATE INDEX IF NOT EXISTS {idx}
            ON casafolino_mail_message ({col});
        """.format(idx=idx_name, col=col))

    _logger.info("pre-migrate 18.0.12.0.0 — done")
