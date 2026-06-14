# F5 Report — Polish + Productivity Bonus
Date: 2026-04-20
Commits: 4
Push: feat/mail-v3-f5
Version: 18.0.8.3.0 → 18.0.8.4.0

## Completati

### AC1: Module update 18.0.8.3.0 → 18.0.8.4.0
Manifest bumped. Migration runs cleanly.

### AC2: Migration 18.0.8.4.0
- Adds `is_snoozed`, `has_outbound` columns to thread (with indexes)
- Adds `undo_until` to outbox
- Adds `is_scheduled` to draft (with index)
- Adds user preference fields (`mv3_font_size`, `mv3_ai_*`)
- Creates snooze + feedback tables with indexes
- Creates crons 92 (Snooze Checker) + 93 (Scheduled Send)
- Sets 2 config params (`v5_groq_model_default`, `v5_nba_llm_fallback_enabled`)

### AC3: Crons 82/83/84 reactivated
Migration reactivates Mail Sync V2, Silent Partners, AI Classify.

### AC4: Record rules "Mail V3 own *" reactivated
Migration sets `active=true` on all rules matching `%Mail V3%`.

### AC5: Smart Snooze — popup in reading pane
Click 💤 opens popup with 4 presets (Stasera 18:00, Domani 9:00, Lunedì 9:00, +1 settimana) + custom datetime picker + type selector (until_date/until_reply/if_no_reply_by).

### AC6: Thread snoozed sparisce dalla lista
`is_snoozed=True` threads filtered out of default thread list. Appear only in "Snoozed" folder.

### AC7: Cron 92 — Smart Snooze Checker (15min)
Processes all 3 snooze types. `until_date`: checks wake_at. `until_reply`: checks new inbound after snooze. `if_no_reply_by`: checks no reply within deadline_days.

### AC8: Folder "Snoozed" in sidebar
💤 icon in sidebar left. Click shows snoozed threads.

### AC9: Undo Send — toast 10s
After Send in compose wizard, outbox created with `state='undoable'` and `undo_until = NOW + 10s`. UI shows toast with countdown. Cron 90 skips undoable records, transitions expired ones to queued.

### AC10: Click "Annulla" — restore draft
Endpoint `/cf/mail/v3/outbox/<id>/undo` deletes outbox record and restores as draft.

### AC11: Compose dropdown — "Invia ora" / "Programma invio"
Wizard form has `scheduled_send_at` field. "Programma invio" button appears when field is set.

### AC12: Folder "Programmate"
⏰ icon in sidebar. Click loads scheduled drafts via `/cf/mail/v3/scheduled`. Shows as thread-like items with "Programmata: [datetime]" preview.

### AC13: Cron 93 — Scheduled Send Dispatch (1min)
Searches drafts with `is_scheduled=True` and `scheduled_send_at <= NOW`. Converts to outbox via `queue_send()`.

### AC14: Dark mode toggle
🌙/☀️ button in search bar. Toggles `data-theme="dark"` on root div. Full SCSS dark theme with inverted backgrounds, borders, cards.

### AC15: Dark mode saved in res.users
`mail_v3_dark_mode` field toggled via `/cf/mail/v3/user/dark_mode` endpoint. Loaded on startup.

### AC16: Mobile single-pane ≤768px
Media queries hide non-active panels. Navigation state `mobileView = 'list' | 'reading' | 'sidebar'`. Click thread → reading. Back button → list. Sidebar left becomes horizontal strip.

### AC17: Calibration feedback — auto hooks
- NBA dismiss → logs `nba_dismissed` feedback
- Pin Hot / Pin Ignore buttons in sidebar 360 company block → `pinned_hot` / `pinned_ignore`
- Generic endpoint `/cf/mail/v3/partner/<id>/feedback` for all action types

### AC18: Intelligence → Feedback menu
List + form + search views with filters by action/user/date. Action accessible under Partner Intelligence menu.

### AC19: Search respects record rules
Refactored: ORM `search()` first (respects record rules), then SQL full-text only on accessible IDs. Non-admin users see only messages from their accounts.

### AC20: Sent folder filter
`has_outbound` computed stored field on thread. Migration backfills from existing data. Folder 'sent' passes `('has_outbound', '=', True)` domain.

### AC21: Settings drawer — 4 tabs
1. **Firme**: lists all signatures with default badge
2. **Visualizzazione**: reading pane position, density, font size, shortcuts toggle
3. **AI**: reply enabled toggle, temperature slider, model select, Groq test button
4. **Account**: shows account list with status

### AC22: Settings persist
All preferences saved via `/cf/mail/v3/user/preferences/save` to `res_users` fields. Loaded at startup.

### AC23: Unified composer — wizard only
All compose operations (Scrivi/Reply/Forward/AI shortcut) open `casafolino.mail.compose.wizard` via `doAction`. Native `HtmlField` editor + `many2many_binary` for D&D attachments.

### AC24: Drag & drop via native widget
`many2many_binary` widget in wizard form provides native file upload with drag-and-drop built-in by Odoo 18.

### AC25: Analytics dashboard
Client action `cf_mail_v3_analytics` with:
- 4 KPI cards (inbound, outbound, active threads, hot partners)
- Per-account table with response time (color-coded: green <4h, yellow <24h, red >24h)
- Top 10 partners by email volume
- Period filter (7/14/30/60/90 days)
- Menu accessible under Mail CRM → Analytics (admin only)

## Decisioni autonome

1. **Undo via outbox state**: Simpler than separate model. Outbox already processes queue. Added `undoable` state that cron 90 transitions to `queued` after undo window expires.
2. **Snooze as separate model**: Clean separation. Thread only has `is_snoozed` boolean. Snooze records hold the complex wake logic.
3. **Scheduled via draft**: Reuses existing draft model + new `is_scheduled` flag. Cron converts to outbox. Clean separation between user-facing draft and technical outbox.
4. **Mobile detection via window.innerWidth**: Simple CSS-first with JS navigation state. No separate mobile app or framework.
5. **Analytics transient model**: No stored metrics. Computed on-the-fly from message/thread data. Avoids maintenance of materialized views.
6. **Search record rules via two-step**: ORM search first (respects rules), then SQL full-text on allowed IDs. Performance acceptable for V3 beta user count.
7. **Settings save individually**: Each field change triggers immediate save. No "Apply" button needed.
8. **Compose wizard as sole path**: Removed reference to OWL compose component in client. File kept inert for backwards compat.
9. **Feedback helper as static method**: Can be called from anywhere (controller, model) without circular imports.
10. **Bulk snooze uses same popup**: When bulk mode active, snooze popup applies to all selected threads.

## File nuovi (6)

- `models/casafolino_mail_snooze.py` — Snooze model + cron checker (~80 righe)
- `models/casafolino_partner_intelligence_feedback.py` — Feedback model + helper (~55 righe)
- `models/casafolino_mail_response_metric.py` — Analytics transient (~120 righe)
- `migrations/18.0.8.4.0/post-migrate.py` — F5 migration (~130 righe)
- `views/feedback_views.xml` — Search/list/form + actions
- `static/src/js/mail_v3/mail_v3_analytics.js` + `xml/mail_v3_analytics.xml` — Dashboard

## File modificati (16)

- `__manifest__.py` — version 18.0.8.4.0, +feedback_views.xml
- `models/__init__.py` — +3 imports
- `models/casafolino_mail_thread.py` — +is_snoozed, +has_outbound, +_compute_has_outbound
- `models/casafolino_mail_outbox.py` — +undoable state, +undo_until, cron handles transition
- `models/casafolino_mail_draft.py` — +is_scheduled, +_cron_scheduled_send
- `models/casafolino_mail_compose_wizard.py` — +action_schedule, send now uses undoable
- `models/res_users.py` — +4 preference fields (mv3_font_size, mv3_ai_*)
- `controllers/mail_v3_controllers.py` — +15 new endpoints, search rewritten
- `security/ir.model.access.csv` — +5 ACL rows
- `views/menus.xml` — +2 menu items (Feedback, Analytics)
- `views/mail_v3_compose_wizard_views.xml` — +scheduled_send_at field + Schedule button
- `static/src/js/mail_v3/mail_v3_client.js` — Full rewrite: +dark mode, +snooze, +undo, +mobile, +bulk, +settings 4-tab, +scheduled
- `static/src/js/mail_v3/mail_v3_*.js` — Thread list bulk, reading pane snooze, sidebar 360 feedback
- `static/src/xml/mail_v3/*.xml` — All templates updated for F5 features
- `static/src/scss/mail_v3.scss` — +250 lines: dark mode, mobile, snooze, undo, bulk, analytics

## Commits

- `942e58b` feat(mail-v3): F5 backend — snooze, undo send, scheduled, calibration, analytics, search fix
- `df78514` feat(mail-v3): F5 frontend — dark mode, snooze UI, undo toast, mobile, bulk, analytics, settings 4-tab
- `dbc7d38` feat(mail-v3): compose wizard unified — undo send 10s, scheduled send, D&D via native widget
- `(this)` docs(mail-v3): F5 report

## Dipendenze nuove

Nessuna libreria Python esterna aggiunta.

## Cron finali attivi dopo F5

| ID | Nome | Intervallo |
|----|------|------------|
| 82 | Mail Sync V2 | 5 min (riattivato) |
| 83 | Silent Partners | daily (riattivato) |
| 84 | AI Classify | 5 min (riattivato) |
| 85 | Body Fetch | 5 min |
| 86 | Draft Autosave Cleanup | daily |
| 87 | Intelligence Rebuild | hourly |
| 90 | Outbox Process | 2 min |
| 91 | Outbox Cleanup | daily |
| 92 | Smart Snooze Checker | 15 min (NEW) |
| 93 | Scheduled Send Dispatch | 1 min (NEW) |

## Raccomandazioni F6

1. **WhatsApp Business integration** — invio/ricezione messaggi WhatsApp da sidebar
2. **Google Calendar integration** — eventi da email (meeting_request intent) auto-creati
3. **Email templates editor WYSIWYG** — libreria template con variabili + preview
4. **Notifiche desktop browser** — Push notification per email hot/urgent
5. **Pesi Hotness auto-calibrati** — basati su 30gg di calibration feedback data
6. **Multi-lingua UI** — switcher IT/EN/DE con i18n completo
7. **Smart Labels sync Gmail** — bidirezionale con IMAP RENAME (predisposto in F5, richiede cron 88/89 attivi)
8. **Undo send customizable timer** — utente sceglie 5/10/30s nelle settings
