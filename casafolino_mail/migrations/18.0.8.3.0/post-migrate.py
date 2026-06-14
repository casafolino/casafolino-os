"""F4 post-migrate: add mv3_private_notes column, tsvector index for search."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('[mail v3] F4 post-migrate start (version=%s)', version)

    # ── 1. Add mv3_private_notes column if missing ──
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'res_partner' AND column_name = 'mv3_private_notes'
    """)
    if not cr.fetchone():
        cr.execute("ALTER TABLE res_partner ADD COLUMN mv3_private_notes TEXT")
        _logger.info('[mail v3] Added mv3_private_notes column to res_partner')

    # ── 2. Ensure tsvector GIN index for full-text search ──
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_cf_mail_msg_fts
        ON casafolino_mail_message
        USING GIN(to_tsvector('simple', coalesce(subject,'')||' '||coalesce(body_plain,'')))
    """)
    _logger.info('[mail v3] Ensured GIN index idx_cf_mail_msg_fts exists')

    _logger.info('[mail v3] F4 post-migrate complete')
