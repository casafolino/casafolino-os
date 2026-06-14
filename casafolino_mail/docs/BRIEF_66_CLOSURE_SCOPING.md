# Brief #6.6 — Closure Scoping

**Data:** 2026-05-07

## Volume
- Total messages: 2977
- Pending AI (partner_id + not processed): 0
- Already AI processed: 0
- Positioned: 0
- Note: all messages pre-date #6.2 fields, so cf_ai_processed defaults to False
  but most have partner_id=NULL (pre-#6.1 mail_tracked filter)

## Deprecated residuals
- Banner [DEPRECATED] in views/static: 0 matches (clean)

## Crons
| ID | Name | Active | Interval |
|----|------|--------|----------|
| 82 | Mail Sync V2 | t | 5 min |
| 85 | Body Fetch Pending | t | 10 min |
| 110 | Triage RAW | t | 5 min |
| 6 | Fetchmail Service | f | 5 min |
| 98 | Auto-Attach Lead | f | 15 min |

AI suggestion + accuracy refresh crons NOT yet created via UI.

## Files to modify
- models/casafolino_mail_message_staging.py (backfill method)
- docs/MAIL_MODULE_v6.md (NEW: master architecture document)
- CONTRACT_MAIL.md (final update)
- TODO.md (final update)

## Blockers
None. Backfill will be minimal since most mail has no partner_id (pre-#6.1).
