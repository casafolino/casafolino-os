"""V14: Create system folders + assign existing messages to 'Da smistare'."""
import logging

_logger = logging.getLogger(__name__)

SYSTEM_FOLDERS = [
    ('inbox', 'Inbox', 1, '\U0001f4e5'),
    ('unsorted', 'Da smistare', 2, '\u26a0\ufe0f'),
    ('sent', 'Inviate', 3, '\U0001f4e4'),
    ('archive', 'Archivio', 4, '\U0001f5c4'),
    ('trash', 'Cestino', 5, '\U0001f5d1'),
    ('spam', 'Spam', 6, '\U0001f6ab'),
]


def migrate(cr, version):
    _logger.info("[V14 migration] Starting folder migration...")

    # 1. Ensure folder_id column exists on casafolino_mail_message
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'casafolino_mail_message' AND column_name = 'folder_id'
    """)
    if not cr.fetchone():
        cr.execute("""
            ALTER TABLE casafolino_mail_message
            ADD COLUMN folder_id INTEGER
            REFERENCES casafolino_mail_folder(id) ON DELETE SET NULL
        """)
        cr.execute("""
            CREATE INDEX IF NOT EXISTS casafolino_mail_message_folder_id_idx
            ON casafolino_mail_message (folder_id)
        """)

    # 2. Get all accounts
    cr.execute("SELECT id FROM casafolino_mail_account WHERE active = true")
    account_ids = [row[0] for row in cr.fetchall()]
    _logger.info("[V14 migration] Found %d active accounts", len(account_ids))

    total_folders_created = 0
    for account_id in account_ids:
        for code, name, seq, icon in SYSTEM_FOLDERS:
            # Check if exists
            cr.execute("""
                SELECT id FROM casafolino_mail_folder
                WHERE account_id = %s AND system_code = %s
            """, (account_id, code))
            if cr.fetchone():
                continue
            cr.execute("""
                INSERT INTO casafolino_mail_folder
                    (name, account_id, sequence, icon, is_system, system_code, color,
                     create_uid, write_uid, create_date, write_date)
                VALUES (%s, %s, %s, %s, true, %s, 0, 1, 1, now(), now())
            """, (name, account_id, seq, icon, code))
            total_folders_created += 1

    _logger.info("[V14 migration] Created %d system folders", total_folders_created)

    # 3. Assign existing messages without folder_id to 'unsorted'
    for account_id in account_ids:
        cr.execute("""
            SELECT id FROM casafolino_mail_folder
            WHERE account_id = %s AND system_code = 'unsorted'
        """, (account_id,))
        row = cr.fetchone()
        if not row:
            continue
        unsorted_id = row[0]

        cr.execute("""
            UPDATE casafolino_mail_message
            SET folder_id = %s
            WHERE account_id = %s AND (folder_id IS NULL)
        """, (unsorted_id, account_id))
        updated = cr.rowcount
        if updated:
            _logger.info(
                "[V14 migration] Account %d: %d messages → 'Da smistare'",
                account_id, updated)

    _logger.info("[V14 migration] Folder migration complete.")
