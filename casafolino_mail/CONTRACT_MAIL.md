# casafolino_mail — Contract (post Brief #6.0)

**Last updated:** 2026-05-07 — Brief #6.0 demolizione mirata
**Module version:** 18.0.18.0.0

## Scope corrente del modulo

### Feature attive
- IMAP sync bridge (RAW pipeline: _fetch_folder_raw in casafolino_mail_account.py)
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

### Feature rimosse in Brief #6.0
- Sender policy engine (model casafolino.mail.sender_policy — demolished)
- Triage wizard (model casafolino.mail.triage.wizard — demolished)
- Triage keyboard shortcuts (triage_shortcuts.js — deleted)
- Legacy fetch path (_fetch_folder_legacy — removed, RAW pipeline only)
- Sender policy views + menu entries
- action_blacklist_domain on messages

### Modelli principali (post-demolizione)

| Model | File | Description |
|-------|------|-------------|
| casafolino.mail.account | casafolino_mail_account.py | IMAP accounts, fetch engine |
| casafolino.mail.message | casafolino_mail_message_staging.py | Email messages, AI classifier |
| casafolino.mail.raw | casafolino_mail_raw.py | RAW staging pre-triage |
| casafolino.mail.thread | casafolino_mail_thread.py | Conversation threads |
| casafolino.mail.draft | casafolino_mail_draft.py | Draft emails |
| casafolino.mail.outbox | casafolino_mail_outbox.py | Outbox queue |
| casafolino.mail.folder | casafolino_mail_folder.py | Mail folders |
| casafolino.mail.folder.rule | casafolino_mail_folder_rule.py | Auto-sort rules |
| casafolino.mail.snippet | snippet.py | Reply snippets |
| casafolino.mail.snippet.picker | snippet_picker.py | Snippet picker wizard |
| casafolino.mail.sender.decision | sender_decision.py | Triage decision audit |
| casafolino.mail.sender_preference | casafolino_mail_sender_preference.py | Sender prefs |
| casafolino.mail.sender.filter | sender_filter.py | Email filtering mixin |
| casafolino.mail.sla.partner | sla_partner.py | SLA dashboard |
| casafolino.mail.orphan.partner | orphan_partner.py | Orphan dashboard |
| casafolino.mail.lead.score | lead_score.py | Lead scoring |
| casafolino.mail.lead.rule | casafolino_mail_lead_rule.py | Auto-link rules |
| casafolino.mail.tracking | casafolino_mail_tracking.py | Email tracking |
| casafolino.mail.signature | casafolino_mail_signature.py | Signatures |
| casafolino.mail.template | casafolino_mail_template.py | Email templates |
| casafolino.mail.mass.action.log | casafolino_mail_mass_action_log.py | Mass action logs |

### Crons attivi

| ID | Name | Interval | Method |
|----|------|----------|--------|
| 82 | CasaFolino Mail Sync V2 | 5 min | _cron_fetch_all_accounts |
| 85 | CasaFolino Body Fetch Pending | 10 min | (body download) |
| 110 | CasaFolino Triage RAW | 5 min | _cron_triage_raw |

### Service dependencies (OWL18)

**user** is NOT a service in Odoo 18. Use `import { user } from "@web/core/user"` then `user.userId`.
Do NOT use `useService("user")` — crashes with "Service user is not available".

Injectable services used: `orm`, `action`, `notification`, `dialog` via `useService(...)`.

### Backlog Brief #6.1+

See TODO.md for detailed backlog.
