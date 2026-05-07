# Brief #6.2 — Posizionatore Mail Scoping

**Data:** 2026-05-07

## DB State
- casafolino_mail_message: no cf_project_id column yet → must add
- project.project with cf_status_dossier: 60 records (dossier universe)
- Messages with partner_id: 1876

## New fields on casafolino.mail.message
- cf_project_id (M2o project.project)
- cf_positioned_at (Datetime)
- cf_positioned_by_id (M2o res.users)
- cf_ai_suggestion_ids (M2m project.project via relay table)
- cf_ai_confidence (Float 0.0-1.0)
- cf_ai_confidence_band (Selection computed stored indexed)
- cf_ai_processed (Boolean)
- cf_ai_reasoning (Text)
- mail_message_id (M2o mail.message — chatter reference)

## Groq API pattern (reuse from casafolino_mail_raw.py:295-380)
- Endpoint: https://api.groq.com/openai/v1/chat/completions
- Model: llama-3.3-70b-versatile
- Key: ir.config_parameter casafolino.groq_api_key
- Pattern: requests.post with headers + JSON payload, temperature=0.1
- Max 2 retry attempts

## Files to create/modify
- models/casafolino_mail_message_staging.py (add fields + methods)
- views/posizionatore_views.xml (NEW: list + form + action + menu + bulk)
- static/src/posizionatore/posizionatore.scss (NEW: styling)
- __manifest__.py (add view + scss)
- security/ir.model.access.csv (relay table access if needed)

## Files NOT to touch
- static/src/js/mail_v3/* (F8 composer, reading pane, etc.)
- AI classifier in casafolino_mail_raw.py (reused as pattern, not modified)
- casafolino_crm_export/* (dashboard 360° tab Mail stays placeholder)

## Blockers
None.
