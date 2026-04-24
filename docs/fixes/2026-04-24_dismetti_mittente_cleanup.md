# Cleanup: Dismiss sender cross-account fix

**Date:** 2026-04-24
**Module:** casafolino_mail

## Code Changes (commit eafc4d5)

### 1. Endpoint dismiss — cross-account propagation
`controllers/mail_v3_controllers.py` `/sender_decision/dismiss`:
- Removed `limit=1` — now finds ALL preferences for the email across user accounts
- Calls `action_dismiss()` on each preference
- Creates missing preferences for accounts that don't have one yet

### 2. Cascade delete — cross-account
`models/casafolino_mail_sender_preference.py` `_cascade_delete_emails()`:
- Collects ALL dismissed account IDs for the sender
- DELETE uses `account_id IN (all_dismissed_ids)` instead of single account
- Updates count on all dismissed preferences

### 3. Thread list filter — sender-based
`controllers/mail_v3_controllers.py` `threads_list()`:
- Changed from: "skip if has_dismissed AND NOT has_keep_message"
- Changed to: "skip if ALL inbound senders are dismissed" (ignores message state)

### 4. Cancel dismiss — cross-account revert
`controllers/mail_v3_controllers.py` `/sender_decision/cancel_dismiss`:
- Now reverts ALL sibling preferences for the email, not just the one with the token

## Stage Deployment

- Module updated: Modules loaded, 0 errors
- Stage had no conflicting preferences (different data from prod)
- 0 cleanup actions needed on stage

## Prod Cleanup Needed

| Metric | Count |
|--------|-------|
| Conflicting senders (dismissed+kept) | 1 (sanafood@bolognafiere.it) |
| Total dismissed senders | 9 |
| Stale dismiss crons (active=true) | 9 |
| Messages from dismissed senders still in DB | 3 |

### Cleanup SQL (to run on prod after code deploy):

```sql
-- 1. Reconcile conflicting preferences
UPDATE casafolino_mail_sender_preference
SET status = 'dismissed', decided_at = NOW(), decided_by_id = 2
WHERE status != 'dismissed'
  AND email IN (
    SELECT email FROM casafolino_mail_sender_preference
    GROUP BY email
    HAVING COUNT(DISTINCT status) > 1 AND 'dismissed' = ANY(array_agg(status))
  );

-- 2. Delete messages from dismissed senders
DELETE FROM casafolino_mail_message
WHERE sender_email IN (
  SELECT DISTINCT email FROM casafolino_mail_sender_preference
  WHERE status = 'dismissed'
);

-- 3. Delete empty threads
DELETE FROM casafolino_mail_thread
WHERE id NOT IN (
  SELECT DISTINCT thread_id FROM casafolino_mail_message
  WHERE thread_id IS NOT NULL
);

-- 4. Deactivate stale dismiss crons
UPDATE ir_cron SET active = false
WHERE cron_name LIKE 'Dismiss cascade:%' AND active = true;
```
