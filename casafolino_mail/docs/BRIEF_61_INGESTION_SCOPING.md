# Brief #6.1 — Ingestion Riorientamento Scoping

**Data:** 2026-05-07
**Module version pre:** 18.0.18.0.0

## Pipeline IMAP attuale (post #6.0)

### Fetch flow
1. Cron ID 82 "CasaFolino Mail Sync V2" → `_cron_fetch_all_accounts()` (5 min)
2. `_fetch_emails()` → `_fetch_folder()` → `_fetch_folder_raw()`
3. RAW pipeline: FETCH HEADER+500byte preview → create `casafolino.mail.raw` with triage_state='pending'
4. Cron ID 110 "CasaFolino Triage RAW" → `_cron_triage_raw()` (5 min)
5. `_triage_single()` → `_check_auto_discard()` or `_check_auto_promote()` → `_promote_raw()`
6. Promoted RAW → creates `casafolino.mail.message` record

### Key discovery: mail_tracked already exists
- `res.partner.mail_tracked` Boolean (cf_contact.py line 21) — already in DB
- `res.partner.mail_first_sync_done` Boolean
- `res.partner.mail_last_sync` Datetime
- `res.partner.mail_message_count` Integer computed
- `action_sync_full_email_history()` method exists (full IMAP search per partner)
- NO views/UI for mail_tracked yet — no tab, no bulk action

### What needs to be done

**Phase 1 — mail_tracked UI + mail_tracked_since**
- Add `mail_tracked_since` field (timestamp of activation)
- Create `views/res_partner_mail_tracking_views.xml` with tab + bulk action
- Add to manifest

**Phase 2 — Filter RAW triage by mail_tracked**
- Modify `_check_auto_promote` in `casafolino_mail_raw.py` to require `mail_tracked=True` on partner
- If partner found but NOT mail_tracked → discard with reason 'partner_not_tracked'
- This filters at triage time (not fetch time) — cleaner, preserves existing fetch + dedup

**Phase 3 — Body lazy load**
- Add `body_downloaded` Boolean to `casafolino.mail.message`
- Add `action_download_body()` method
- On promote from RAW: set body_downloaded=False
- Add UI indicator in list view

**Phase 4 — Backfill on tracking activation**
- Enhance `write()` override: mail_tracked False→True triggers backfill
- Reuse existing `action_sync_full_email_history()` via cron one-shot
- Add `mail_tracked_since` timestamp

## Files to modify

| File | Changes |
|------|---------|
| models/cf_contact.py | Add mail_tracked_since, write() override, _schedule_backfill |
| models/casafolino_mail_raw.py | _check_auto_promote: require mail_tracked=True |
| models/casafolino_mail_message_staging.py | Add body_downloaded field + lazy load methods |
| views/res_partner_mail_tracking_views.xml | NEW: tab + bulk action |
| __manifest__.py | Add view to data list |

## Files NOT to touch
- static/src/js/mail_v3/*.js (F8 composer, reading pane, etc.)
- models/casafolino_mail_account.py (fetch engine stays as-is)
- AI classifier methods in message_staging
- lead_score.py, sla_partner.py, orphan_partner.py

## Blockers
None.
