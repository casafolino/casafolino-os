# Fix: SAVEPOINT wrap for RAW duplicate inserts

**Date**: 2026-04-27
**Severity**: Critical (prod sync blocked 11+ hours)
**Branch**: `fix/raw-savepoint-hotfix`
**Commit**: `856ef8e` (server) / applied via `git am` on Mac

## Symptom

- Sync badge showed "Sync: 272 min fa" (red)
- Cron 82 (Mail Sync V2) `failure_count` reached 146
- All 3 accounts (Antonio, Martina, Josefina) stopped syncing at 15:01 UTC on 2026-04-26
- `last_successful_fetch_datetime` frozen for 11+ hours

## Root cause

`_fetch_folder_raw()` in `casafolino_mail_account.py` inserts fetched emails into `casafolino_mail_raw` table:

```python
# BEFORE (broken)
try:
    Raw.create(vals)
    new_count += 1
except Exception as e:
    _logger.warning("Error creating RAW record: %s", e)
    continue
```

When a duplicate UID is encountered (unique constraint `casafolino_mail_raw_account_uid_uniq` on `(account_id, uid)`), PostgreSQL puts the transaction into "aborted" state. The `except` catches the Python exception but does NOT rollback the failed SQL statement. Every subsequent SQL command in the same transaction fails with:

```
current transaction is aborted, commands ignored until end of transaction block
```

This cascades: all remaining emails in the batch fail, all other accounts fail, the cron marks as failed. Repeats every 5 minutes.

## Why duplicates occur

The fetch uses `IMAP SEARCH (SINCE date)` which returns all emails since `last_fetch_datetime`. Emails already in `casafolino_mail_raw` are checked via `message_id` dedup, but the IMAP `uid` field can collide when:
- Same email fetched in a previous partial run
- `message_id` dedup passes (different message_id) but same UID (IMAP server reuses UIDs)

## Fix

Wrap `Raw.create()` in a PostgreSQL SAVEPOINT via Odoo's `self.env.cr.savepoint()`:

```python
# AFTER (fixed)
try:
    with self.env.cr.savepoint():
        Raw.create(vals)
    new_count += 1
except Exception as e:
    _logger.warning("Skip duplicate RAW uid=%s account=%s: %s",
                    vals.get("uid"), vals.get("account_id"), e)
    continue
```

The SAVEPOINT ensures that if the INSERT fails, only that savepoint is rolled back — the outer transaction remains valid and can continue processing.

## Verification

After fix applied + container restart:

| Account | Result |
|---------|--------|
| Antonio (id=1) | `last_successful_fetch_datetime = 21:07:29` — synced |
| Martina (id=2) | `last_successful_fetch_datetime = 21:07:50` — 15 new + 8 sent fetched, 33 dedup skipped |
| Josefina (id=3) | `last_successful_fetch_datetime = 21:07:40` — synced |
| Cron 82 | `failure_count = 0`, completed in 37.7s |

Log output confirms graceful skip:
```
WARNING: Skip duplicate RAW uid=4258 account=2: duplicate key value violates unique constraint "casafolino_mail_raw_account_uid_uniq"
```

## Additional context

This commit also syncs all deployed production code (V15 through V17.1) into git. The repository was behind the deployed code — many files existed only on the server's `/docker/enterprise18/addons/custom/` directory.

## SQL fixes applied during investigation

```sql
-- Set last_fetch_uid for accounts (prevents re-scanning old UIDs)
UPDATE casafolino_mail_account SET last_fetch_uid = '18727' WHERE id = 1;
UPDATE casafolino_mail_account SET last_fetch_uid = '18707' WHERE id = 2;
UPDATE casafolino_mail_account SET last_fetch_uid = '18711' WHERE id = 3;

-- Reset cron failure counter
UPDATE ir_cron SET failure_count = 0, first_failure_date = NULL, nextcall = NOW() WHERE id = 82;
```

Note: `last_fetch_uid` is not used by the fetch logic (which uses SINCE date), but was set as part of initial investigation.
