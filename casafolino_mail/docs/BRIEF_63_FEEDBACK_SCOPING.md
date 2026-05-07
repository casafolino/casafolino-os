# Brief #6.3 — AI Feedback Loop Scoping

**Data:** 2026-05-07

## Baseline
- Mail positioned (cf_project_id IS NOT NULL): 0
- AI processed: 0
- Partners mail_tracked=True: 38
- System is fresh — no backfill needed yet

## Target files
- models/cf_mail_position_feedback.py (NEW: feedback model)
- models/casafolino_mail_message_staging.py (hook + context injection + threshold)
- models/cf_contact.py (accuracy score + cron)
- views/res_partner_mail_tracking_views.xml (AI accuracy UI)
- models/__init__.py (import new model)
- security/ir.model.access.csv (access for new model)

## Blockers
None.
