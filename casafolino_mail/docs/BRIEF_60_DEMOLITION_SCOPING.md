# Brief #6.0 — Demolition Scoping

**Data:** 2026-05-07
**Module version pre:** 18.0.17.1.1

## Target 1: Sender Policy Engine

### Files
| File | What to remove | Lines est. |
|------|----------------|-----------|
| models/casafolino_mail_sender_policy.py | ENTIRE FILE (model casafolino.mail.sender_policy) | 100 |
| models/casafolino_mail_message_staging.py | `policy_applied_id` field, `_apply_sender_policy()`, `action_blacklist_domain()`, call at line ~1201 | ~80 |
| models/casafolino_mail_account.py | `_load_exclude_rules()`, `use_allowlist` field | ~25 |
| models/casafolino_mail_lead_rule.py | Reference to sender_policy | ~5 |
| models/triage_wizard.py | action_triage_ignore_sender/domain (creates sender_policy) — FULL FILE removed in Target 2 | — |
| models/sender_decision.py | `sender_policy_id` field only (model stays — used for triage decisions audit) | 2 |
| views/casafolino_mail_policy_views.xml | ENTIRE FILE (sender policy CRUD views) | ~100 |
| __init__.py | Seed sender_policy section in _post_init_hook | ~20 |

### DB Impact
- Table `casafolino_mail_sender_policy`: 433 records → DROP entire table via migration
- Column `casafolino_mail_message.policy_applied_id` → DROP
- Column `casafolino_mail_sender_decision.sender_policy_id` → DROP
- Column `casafolino_mail_account.use_allowlist` → DROP

## Target 2: Triage States UI

### Files
| File | What to remove | Lines est. |
|------|----------------|-----------|
| models/triage_wizard.py | ENTIRE FILE (transient model casafolino.mail.triage.wizard) | 220 |
| views/triage_wizard_views.xml | ENTIRE FILE (wizard form + action) | ~90 |
| static/src/js/triage_shortcuts.js | ENTIRE FILE (keyboard shortcuts 1-5) | ~40 |
| views/menus.xml | Menu entries for triage wizard + sender policy | ~5 |
| views/casafolino_mail_hub_views.xml | References to state/triage filters | partial |
| views/casafolino_mail_raw_views.xml | triage_state filters/columns | partial |

### DB Impact
- Table `casafolino_mail_triage_wizard`: 0 records (transient, safe to drop)
- Column `casafolino_mail_raw.triage_state` → KEEP (used by RAW pipeline promotion logic)
- Column `casafolino_mail_message.state` → KEEP (used pervasively by F8, AI classifier, dashboards)

### NOTE: What stays regarding states
- `casafolino.mail.message.state` field: STAYS — used by F8 composer, AI classifier, thread list, dashboards
- `casafolino.mail.raw.triage_state` field: STAYS — used by RAW pipeline (_cron_triage_raw)
- `sender_decision` model: STAYS (audit trail, 0 records but good schema)

## Target 3: Fetch Totale (Legacy)

### Files
| File | What to remove | Lines est. |
|------|----------------|-----------|
| models/casafolino_mail_account.py | `_fetch_folder_legacy()` method | ~150 |

### What stays
- `_cron_fetch_all_accounts()` — STAYS (dispatches to RAW pipeline)
- `_fetch_emails()` — STAYS (called by cron, calls _fetch_folder)
- `_fetch_folder()` — MODIFIED to always use RAW, remove legacy branch
- `_fetch_folder_raw()` — STAYS (RAW pipeline)
- Cron ID 82 "CasaFolino Mail Sync V2": STAYS ACTIVE
- Cron ID 110 "CasaFolino Triage RAW": STAYS ACTIVE

## Features PRESERVED (DO NOT TOUCH)

| Feature | Key files |
|---------|-----------|
| AI classifier Groq | casafolino_mail_message_staging.py (_classify_with_ai*) |
| F8 Outlook-style composer | mail_v3_compose.js, compose_wizard_dialog.js, mail_v3_compose.xml |
| IMAP sync bridge (RAW pipeline) | casafolino_mail_account.py (_fetch_folder_raw, _fetch_emails) |
| Lead scoring TOP 20 | lead_score.py, lead_score_views.xml |
| Snippet library | snippet.py, snippet_picker.py, snippet_views.xml, snippet_clipboard.js |
| Autoresponder | casafolino_mail_message_staging.py (autoresponder logic) |
| SLA dashboard | sla_partner.py, sla_partner_views.xml |
| Orphan dashboard | orphan_partner.py, orphan_partner_views.xml |
| Multi-user record rules | security/ir_rules.xml, res_users.py |
| Folders | casafolino_mail_folder.py, casafolino_mail_folder_rule.py |
| Mass actions | casafolino_mail_mass_action_log.py |
| Mail V3 UI (thread list, reading pane, sidebar, etc.) | all mail_v3/*.js and mail_v3/*.xml |
| Sender decision model | sender_decision.py (audit trail, stays minus sender_policy_id field) |

## DB Volumes

| Table | Rows |
|-------|------|
| casafolino_mail_message | 2949 |
| casafolino_mail_sender_policy | 433 |
| casafolino_mail_raw | 423 |
| casafolino_mail_sender_decision | 0 |
| casafolino_mail_triage_wizard | 0 |

## Blockers
None identified. All targets are cleanly separable with careful surgery.
