import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """V12.6 post-migrate:
    1. Promote new/review messages to keep (make visible in inbox)
    2. Flip default sender_policy '*' from review to auto_keep
    3. Seed sender_preference records for existing senders
    """
    _logger.info("post-migrate 18.0.12.6.0 — starting inbox unification")

    # ── Step 1: Promote messages ────────────────────────────────
    cr.execute("""
        UPDATE casafolino_mail_message
        SET state = 'keep'
        WHERE state IN ('new', 'review')
          AND account_id IN (SELECT id FROM casafolino_mail_account WHERE active = true)
    """)
    promoted = cr.rowcount
    _logger.info("post-migrate 18.0.12.6.0 — promoted %d messages to keep", promoted)

    # ── Step 2: Disable review catch-all policy ─────────────────
    cr.execute("""
        UPDATE casafolino_mail_sender_policy
        SET action = 'auto_keep'
        WHERE pattern_value = '*' AND action = 'review'
    """)
    policies_updated = cr.rowcount
    _logger.info("post-migrate 18.0.12.6.0 — updated %d catch-all policies", policies_updated)

    # ── Step 3: Seed sender_preference from existing messages ───
    # Create 'kept' for senders that already have keep/auto_keep messages
    cr.execute("""
        INSERT INTO casafolino_mail_sender_preference (email, account_id, status, decided_at, create_uid, write_uid, create_date, write_date)
        SELECT DISTINCT
            LOWER(TRIM(m.sender_email)),
            m.account_id,
            'kept',
            NOW() AT TIME ZONE 'UTC',
            1, 1,
            NOW() AT TIME ZONE 'UTC',
            NOW() AT TIME ZONE 'UTC'
        FROM casafolino_mail_message m
        WHERE m.sender_email IS NOT NULL
          AND m.sender_email != ''
          AND m.state IN ('keep', 'auto_keep')
          AND m.account_id IS NOT NULL
        ON CONFLICT (email, account_id) DO NOTHING
    """)
    kept_created = cr.rowcount
    _logger.info("post-migrate 18.0.12.6.0 — created %d 'kept' sender preferences", kept_created)

    # Create 'pending' for senders that have messages but no keep/auto_keep
    cr.execute("""
        INSERT INTO casafolino_mail_sender_preference (email, account_id, status, create_uid, write_uid, create_date, write_date)
        SELECT DISTINCT
            LOWER(TRIM(m.sender_email)),
            m.account_id,
            'pending',
            1, 1,
            NOW() AT TIME ZONE 'UTC',
            NOW() AT TIME ZONE 'UTC'
        FROM casafolino_mail_message m
        WHERE m.sender_email IS NOT NULL
          AND m.sender_email != ''
          AND m.account_id IS NOT NULL
        ON CONFLICT (email, account_id) DO NOTHING
    """)
    pending_created = cr.rowcount
    _logger.info("post-migrate 18.0.12.6.0 — created %d 'pending' sender preferences", pending_created)

    _logger.info(
        "post-migrate 18.0.12.6.0 — DONE: %d msgs promoted, %d kept prefs, %d pending prefs",
        promoted, kept_created, pending_created
    )
