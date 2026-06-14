import logging

_logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def migrate(cr, version):
    """Backfill thread_id on casafolino_mail_message via casafolino.mail.thread._upsert_from_message.

    This runs as post-migrate so the ORM environment is available.
    Idempotent: skips messages that already have thread_id.
    """
    _logger.info("post-migrate 18.0.12.3.0 — starting thread_id backfill")

    # Count messages needing backfill
    cr.execute("""
        SELECT COUNT(*) FROM casafolino_mail_message
        WHERE thread_id IS NULL AND is_deleted IS NOT TRUE
    """)
    total = cr.fetchone()[0]
    _logger.info("post-migrate 18.0.12.3.0 — %d messages need thread_id backfill", total)

    if total == 0:
        _logger.info("post-migrate 18.0.12.3.0 — nothing to backfill, done")
        return

    # We need ORM access for _upsert_from_message — use env from cr
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    Message = env['casafolino.mail.message']
    Thread = env['casafolino.mail.thread']

    processed = 0
    errors = 0
    offset = 0

    while True:
        # Fetch batch of messages without thread_id
        messages = Message.search([
            ('thread_id', '=', False),
            ('is_deleted', '!=', True),
        ], limit=BATCH_SIZE, order='email_date asc')

        if not messages:
            break

        for msg in messages:
            try:
                Thread._upsert_from_message(msg)
                processed += 1
            except Exception as e:
                errors += 1
                _logger.warning(
                    "post-migrate 18.0.12.3.0 — thread upsert failed for message %s: %s",
                    msg.id, e
                )

        # Commit batch to avoid long transaction
        cr.commit()
        offset += len(messages)
        _logger.info(
            "post-migrate 18.0.12.3.0 — backfilled %d/%d messages (%d errors)",
            processed, total, errors
        )

    _logger.info(
        "post-migrate 18.0.12.3.0 — thread_id backfill complete: "
        "%d processed, %d errors out of %d total",
        processed, errors, total
    )
