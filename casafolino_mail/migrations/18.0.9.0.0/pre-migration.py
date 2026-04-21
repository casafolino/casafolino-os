import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """F9 pre-migration: add account_owner_id on res_partner, populate from user_id."""
    _logger.info("[F9 migration] Adding account_owner_id to res_partner...")

    # Add column if not exists
    cr.execute("""
        ALTER TABLE res_partner
        ADD COLUMN IF NOT EXISTS account_owner_id INTEGER;
    """)

    # Populate from user_id (salesperson) where it exists
    cr.execute("""
        UPDATE res_partner
        SET account_owner_id = user_id
        WHERE user_id IS NOT NULL
          AND account_owner_id IS NULL;
    """)

    cr.execute("SELECT COUNT(*) FROM res_partner WHERE account_owner_id IS NOT NULL")
    count = cr.fetchone()[0]
    _logger.info("[F9 migration] account_owner_id populated on %d partners from user_id", count)
