# F10 Report — Fix Sync + Body + Partner 360 + Composer + Layout

**Versione**: `casafolino_mail 18.0.10.0.0`
**Branch**: `feat/mail-v3-f10`
**Data**: 2026-04-21

---

## WP1 — Fix sincronizzazione IMAP

### Diagnostica
```
Crons IMAP PROD (pre-fix):
- 82 (Mail Sync V2): active=true, lastcall=2026-04-21 02:07:20 (~500 min ago)
- 84 (AI Classify):  active=true, lastcall=2026-04-21 02:08:34 (~503 min ago)
- 85 (Body Fetch):   active=true, lastcall=2026-04-21 02:11:20 (~500 min ago)
- 97 (Backfill AI):  active=true, lastcall=NULL (never ran)

Accounts: all state='connected', last_fetch=02:06-02:07
Email gap: account 1=8.7h, account 2=9.6h, account 3=16.6h
```

### Root cause
`docker exec odoo-app odoo -d folinofood_stage --stop-after-init` (F9 stage deploy at 02:07) created a secondary Odoo process inside the running container. When it exited, it disrupted the primary process's cron scheduler thread. Crons showed `active=true` but `nextcall` was frozen in the past.

### Fix
`docker restart odoo-app` restarted the Odoo process with fresh cron thread. All crons resumed immediately:
- Cron 82 lastcall updated to 10:34:31 (1 min ago)
- Cron 85 body fetch processed 19 messages
- Logs confirmed jobs running normally

### Prevention
For future deploys: always `docker restart odoo-app` after any `--stop-after-init` operation, even on a different database.

---

## WP2 — Fix body non renderizzato

### Diagnostica
```
Body missing (last 30 days):
- Account 1: 267/269 (99%) no body
- Account 2: 511/584 (87%) no body
- Account 3: 314/383 (82%) no body
Total: 1092/1236 (88%) missing body

Gabriele Bianchi emails: all body_downloaded=false, fetch_state=pending
```

### Root cause
Same as WP1 — cron 85 (Body Fetch Pending) was frozen. With crons running again, body fetch is processing 19 messages per run (every 10 min). Full catch-up: ~1092/19 = ~58 runs = ~10 hours.

### Fix
- **Cron restart**: cron 85 now actively fetching bodies
- **UI banner**: form view shows "Body non scaricato [Scarica ora]" when `body_downloaded=false`
- **Manual download**: `action_download_body_now()` method for on-demand IMAP fetch per message

---

## WP3 — Partner 360 enrichment da dominio

### Implementation
- **Method**: `action_enrich_from_domain()` on `res.partner`
  - Step 1: Skip if generic domain (gmail, yahoo, etc.)
  - Step 2: Search existing company by domain match (website, email, company_name)
  - Step 3: If found → link as parent_id
  - Step 4: If not found → Serper search + Groq extract company name/country → create company partner
  - Step 5: Link person as child
- **Controller**: `/cf/mail/v3/partner/<id>/enrich_domain` (JSON endpoint)
- **UI**: Sidebar 360 shows "Azienda non identificata [Arricchisci da dominio]" placeholder when person has no parent company
- **Rate limit**: single call per action (manual trigger only)

---

## WP4 — Fix composer

### Root cause
`_openComposeWizard` used `doAction(ir.actions.act_window)` to open Python `casafolino.mail.compose.wizard` as standard Odoo form. This showed basic HTML widget without toolbar, emoji, templates.

OWL `ComposeWizard` component with full Outlook-style toolbar existed but wasn't wired into the action flow.

### Fix
- **New endpoint**: `/cf/mail/v3/compose/prepare` — creates draft via RPC, returns `{draft_id, prefilled}`
- **JS change**: `_openComposeWizard` now calls prepare endpoint, then shows OWL `ComposeWizard` as overlay
- **ComposeWizard imported** into `MailV3Client.components`
- **Overlay UI**: fixed position modal with backdrop, 75vw width, 80vh height
- **Lifecycle**: create draft → show compose → autosave → send → close overlay → refresh threads

Features now available:
- Rich toolbar (bold, italic, underline, strikethrough, lists, alignment, links, HR)
- Font size selector, font color, background color (CasaFolino palette)
- Emoji picker (50+ emojis, searchable)
- Template panel with language filter and hover preview
- Drag & drop file upload + inline image paste
- Autosave every 15 seconds
- Preview modal

---

## WP5 — Redesign layout form messaggio

### Before
```
┌──────────┬─────────────────┬────────────────┬──────────────┐
│ Sidebar  │  Thread List    │ Reading Pane   │ Sidebar 360  │
│  70px    │    420px        │   flex:1       │   360px      │
│          │                 │                │              │
└──────────┴─────────────────┴────────────────┴──────────────┘
```

### After
```
┌──────────┬─────────────────┬──────────────────────────────┐
│ Sidebar  │  Thread List    │      Reading Pane             │
│  70px    │    420px        │        flex:1                 │
│          │                 │                               │
│          │                 ├───────────────────────────────┤
│          │                 │  ▼ 360° Panel (33vh)          │
│          │                 │  [Company][Person][Rel][Biz]  │
│          │                 │  horizontal scroll cards      │
└──────────┴─────────────────┴───────────────────────────────┘
```

### Implementation
- **Main area wrapper**: `.mv3-client__main-area` (flex column)
- **Reading pane**: `flex: 1` (grows to fill available space)
- **Bottom 360 panel**: `height: 33vh`, collapsible via toggle button
- **Collapse state**: `state.panel360Collapsed` (boolean, toggle button with chevron)
- **Horizontal layout**: 360 content blocks displayed as horizontal cards with `flex-wrap: nowrap`, `gap: 16px`, horizontal scroll
- **Compose overlay**: fixed position modal, `z-index: 1050`, backdrop blur

---

## WP6 — Versioning

- **Manifest**: `18.0.9.0.6` → `18.0.10.0.0`

---

## Files modified

| File | WP | Change |
|------|-----|--------|
| `__manifest__.py` | 6 | version bump |
| `models/casafolino_mail_message_staging.py` | 2 | action_download_body_now |
| `models/cf_contact.py` | 3 | action_enrich_from_domain |
| `controllers/mail_v3_controllers.py` | 3,4 | compose/prepare endpoint, enrich_domain endpoint |
| `views/casafolino_mail_hub_views.xml` | 2 | body not downloaded banner |
| `static/src/js/mail_v3/mail_v3_client.js` | 4,5 | ComposeWizard import, compose overlay, panel360 toggle |
| `static/src/xml/mail_v3/mail_v3_client.xml` | 4,5 | compose overlay, main-area wrapper, bottom-360 panel |
| `static/src/xml/mail_v3/mail_v3_sidebar_360.xml` | 3 | company missing placeholder + enrich button |
| `static/src/js/mail_v3/mail_v3_sidebar_360.js` | 3 | enrichFromDomain method |
| `static/src/scss/mail_v3.scss` | 5 | main-area, bottom-360, compose-overlay CSS |
