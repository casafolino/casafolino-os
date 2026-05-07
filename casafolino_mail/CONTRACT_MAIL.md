# casafolino_mail — Contract (post Brief #6.1)

**Last updated:** 2026-05-07 — Brief #6.1 riorientamento ingestion
**Module version:** 18.0.18.0.0

## Scope corrente del modulo

### Feature attive
- IMAP sync bridge (RAW pipeline: _fetch_folder_raw in casafolino_mail_account.py)
- **mail_tracked partner filter** (Brief #6.1): only tracked partners' mail promoted to MESSAGE
- **Body lazy load** (Brief #6.1): body downloaded async by cron 85, not during triage
- **Backfill storico** (Brief #6.1): async one-shot cron on mail_tracked activation
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

### Brief #6.1 — Ingestion flow (deployed 2026-05-07)

#### Fetch → Triage → Promote flow
1. Cron 82 "Mail Sync V2" (5 min) → `_cron_fetch_all_accounts()` → `_fetch_folder_raw()`
2. RAW pipeline: FETCH HEADER+preview → create `casafolino.mail.raw` triage_state='pending'
3. Cron 110 "Triage RAW" (5 min) → `_cron_triage_raw()` → `_triage_single()`
4. `_check_auto_promote()`: requires `res.partner.mail_tracked=True` on matching partner
5. If partner NOT tracked → falls through to AI classifier (may still discard)
6. Promote: creates `casafolino.mail.message` with `fetch_state='pending'`, `body_downloaded=False`
7. Cron 85 "Body Fetch Pending" (10 min) → downloads body+attachments async

#### mail_tracked partner opt-in
- `res.partner.mail_tracked` Boolean (default False, opt-in)
- `res.partner.mail_tracked_since` Datetime (set on activation)
- Activation triggers async backfill via one-shot ir.cron
- Backfill reuses `action_sync_full_email_history()` (full IMAP search per partner)
- UI: tab "Mail Tracking" in partner form + bulk action in list view

#### Body lazy load
- `casafolino.mail.message.body_downloaded` Boolean
- `casafolino.mail.message.fetch_state` Selection (pending/done/error)
- Body downloaded by cron 85 or on-demand when user opens message
- `_download_body_imap()` handles full body + attachments

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

### Service dependencies (OWL18)

**user** is NOT a service in Odoo 18. Use `import { user } from "@web/core/user"` then `user.userId`.
Do NOT use `useService("user")` — crashes with "Service user is not available".

### Backlog Brief #6.2+

See TODO.md for detailed backlog.
