# casafolino_mail — Contract (post Brief #6.2)

**Last updated:** 2026-05-07 — Brief #6.2 UI Posizionatore mail
**Module version:** 18.0.18.0.0

## Scope corrente del modulo

### Feature attive
- IMAP sync bridge (RAW pipeline: _fetch_folder_raw in casafolino_mail_account.py)
- **mail_tracked partner filter** (Brief #6.1): only tracked partners' mail promoted to MESSAGE
- **Body lazy load** (Brief #6.1): body downloaded async by cron 85, not during triage
- **Backfill storico** (Brief #6.1): async one-shot cron on mail_tracked activation
- **Posizionatore mail** (Brief #6.2): AI-assisted positioning to project dossiers
- AI classifier Groq (model: llama-3.3-70b-versatile, param: casafolino.groq_api_key)
- F8 Outlook-style composer (compose_wizard_dialog.js, mail_v3_compose.js)
- Lead scoring TOP 20 dashboard (lead_score.py)
- Snippet library (snippet.py, snippet_picker.py)
- Autoresponder "fuori sede"
- SLA / orphan / lead-scoring dashboards (sla_partner.py, orphan_partner.py)
- Multi-user record rules (Antonio uid=2, Josefina uid=6, Martina uid=8)
- Folders + folder rules (casafolino_mail_folder.py)
- Mass actions (casafolino_mail_mass_action_log.py)
- Sender decision audit trail (sender_decision.py)
- Sender preference / dismissed senders
- Mail threads + reading pane + sidebar 360

### Brief #6.2 — Posizionatore mail (deployed 2026-05-07)

#### New fields on casafolino.mail.message

| Campo | Tipo | Note |
|---|---|---|
| cf_project_id | M2o project.project | Dossier assegnato (vuoto = pending) |
| cf_positioned_at | Datetime | Quando posizionata |
| cf_positioned_by_id | M2o res.users | Chi l'ha posizionata |
| cf_ai_suggestion_ids | M2m project.project | Top 3 candidati AI |
| cf_ai_confidence | Float | 0.0-1.0 confidence top suggestion |
| cf_ai_confidence_band | Selection (computed, stored, indexed) | high/medium/low/none |
| cf_ai_processed | Boolean | True dopo run AI |
| cf_ai_reasoning | Text | Spiegazione AI |
| mail_message_id | M2o mail.message | Reference entry chatter project |

#### Positioning flow
1. Mail ingested (#6.1) with cf_project_id=NULL, cf_ai_processed=False
2. Cron _cron_run_ai_suggestion (batch 20): calls Groq, populates suggestions + confidence
3. User opens menu "Posizionatore mail" → list view filtered
4. **HIGH (>80%):** click "Conferma" inline → instant positioning
5. **MEDIUM (40-80%):** click "Posiziona…" → dialog with AI candidates selectable
6. **LOW (<40%):** dialog shows AI reasoning + manual dossier selector
7. Positioning creates mail.message entry in project chatter (with original email_date!) + sets cf_project_id + reference via mail_message_id

#### Bulk action
"Auto-accetta tutte le ALTE >80%" on list view Action menu.

#### Counter API
- `cf_get_pending_count()` → int
- `cf_get_pending_summary()` → dict {high, medium, low, none, total}

### Brief #6.1 — Ingestion flow (deployed 2026-05-07)

#### Fetch → Triage → Promote flow
1. Cron 82 "Mail Sync V2" (5 min) → `_cron_fetch_all_accounts()` → `_fetch_folder_raw()`
2. RAW pipeline: FETCH HEADER+preview → create `casafolino.mail.raw` triage_state='pending'
3. Cron 110 "Triage RAW" (5 min) → `_cron_triage_raw()` → `_triage_single()`
4. `_check_auto_promote()`: requires `res.partner.mail_tracked=True` on matching partner
5. If partner NOT tracked → falls through to AI classifier (may still discard)
6. Promote: creates `casafolino.mail.message` with `fetch_state='pending'`, `body_downloaded=False`
7. Cron 85 "Body Fetch Pending" (10 min) → downloads body+attachments async

### Feature rimosse in Brief #6.0
- Sender policy engine (demolished)
- Triage wizard + shortcuts (demolished)
- Legacy fetch path (demolished)

### Crons attivi

| ID | Name | Interval | Method |
|----|------|----------|--------|
| 82 | CasaFolino Mail Sync V2 | 5 min | _cron_fetch_all_accounts |
| 85 | CasaFolino Body Fetch Pending | 10 min | _cron_fetch_body_pending |
| 110 | CasaFolino Triage RAW | 5 min | _cron_triage_raw |
| TBD | AI Suggestion Posizionatore | 5 min | _cron_run_ai_suggestion |

### Service dependencies (OWL18)

**user** is NOT a service in Odoo 18. Use `import { user } from "@web/core/user"` then `user.userId`.
Do NOT use `useService("user")` — crashes with "Service user is not available".

### Backlog Brief #6.3+

See TODO.md for detailed backlog.
