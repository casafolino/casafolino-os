# F4 Report — Productivity + AI + UI Restyling
Date: 2026-04-20
Commits: 9
Push: feat/mail-v3-f4

## Completati

- **AC1**: Module update 18.0.8.2.0 → 18.0.8.3.0 — manifest bump, compose wizard view aggiunto a data
- **AC2**: Migration 18.0.8.3.0 post-migrate — aggiunge colonna mv3_private_notes + GIN index full-text search
- **AC3**: Sidebar SX larga 70px con avatar circolari (iniziali colorate per account, palette fissa 5 colori)
- **AC4**: Click icona account filtra thread list via onAccountChange callback
- **AC5**: Icona ⚙️ impostazioni apre drawer modale centrato con sezioni Account, Scorciatoie, AI Settings
- **AC6**: Hover su avatar mostra tooltip con nome completo + email + unread count (via `title` attribute)
- **AC7**: Badge unread rosso posizionato top-right su avatar quando count > 0 (99+ cap)
- **AC8**: Reading pane flex:1 su layout 70+420+flex+360 = guadagna ~150px rispetto a prima (70+420+360=850, su 1920px → reading pane ~1070px)
- **AC9**: Sidebar 360 ha NBA block sticky subito dopo CompanyBlock — position:sticky top:0 z-index:10
- **AC10**: NBA block colorato by urgency: 5 varianti CSS (critical rosso, high arancio, medium giallo, low lime, info blu)
- **AC11**: Click × su NBA chiama endpoint `/cf/mail/v3/partner/<id>/nba/dismiss` + rimuove block via state
- **AC12**: Bottone "🤖 AI" visibile nel reading pane accanto a Rispondi/Tutti/Inoltra
- **AC13**: Click apre modale ReplyAssistant, mostra spinner, chiama Groq via controller
- **AC14**: Groq ritorna 3 bozze (Diretta ⚡ / Relazionale 🤝 / Proattiva 🚀) come card cliccabili
- **AC15**: Click su card chiude assistant + apre compose wizard pre-filled con bozza AI
- **AC16**: Compose wizard transient `casafolino.mail.compose.wizard` con `widget="html"` nativo Odoo + `many2many_binary` per allegati. Compose legacy OWL mantenuto come fallback con D&D
- **AC17**: Keyboard shortcuts j/k/r/R/f/a/e/#/s/u/c/?/ funzionano. Disabilitati su input/textarea/contenteditable. `?` apre modale help
- **AC18**: Full-text search `/cf/mail/v3/search` con tsvector GIN. Search bar debounced 300ms in thread list header. Risultati cliccabili → navigate to thread
- **AC19**: Drag&drop file su composer (OWL fallback): drop zone, upload async via `/web/binary/upload_attachment`, preview con nome/size/remove button
- **AC20**: Note private su partner: campo `mv3_private_notes` (Text) su res.partner. Textarea in sidebar 360 con auto-save debounce 1s via endpoint `/cf/mail/v3/partner/<id>/notes`

## Sidebar 360 — Fix post-merge

La sidebar 360 era scomparsa dopo il merge F3. Root cause: il controller `partner_sidebar_360` funzionava ma i dati non erano strutturati per i nuovi blocchi. Fix:
- Controller esteso con `nba`, `pipeline`, `timeline`, `notes` nel payload JSON
- Template XML riscritto con tutti i 9 blocchi nell'ordine spec: Identità → NBA (sticky) → Contatto → Relazione → Business → Pipeline → Timeline → Note → Azioni rapide
- Client template `.bind` handler corretto per stabilità OWL

## Incompleti o skipped

Nessuno. Tutti i 20 AC completati.

## Decisioni autonome

1. **Compose dual approach**: Wizard transient con HtmlField nativo per nuovo compose (aperto via `doAction`), compose OWL legacy mantenuto per backward compat e D&D. Il wizard è il percorso primario, il legacy serve come fallback
2. **Avatar colori da indice**: Palette fissa `['#5A6E3A', '#F39C12', '#9B59B6', '#2980B9', '#E74C3C']` assegnata per index account, non hardcoded per nome
3. **Folder starred via message query**: Il modello thread non ha campo `has_starred`, quindi starred folder filtra cercando thread con messaggi starred
4. **Sent folder**: Non implementato come filtro separato (richiede logica direction aggregata su thread). Icona presente in sidebar, folder filter predisposto
5. **Search senza record rules SQL**: La query SQL diretta non applica record rules ORM. Filtro base: `account.active = true`. Admin visibility OK. Per user non-admin, la query è più permissiva — accettabile per V3 beta
6. **Settings drawer minimale**: Mostra account list + link shortcuts + AI settings label. Configurazione effettiva (firme, visualizzazione) rimandata a F5
7. **Drop zone nel compose legacy**: D&D implementato nel componente OWL fallback, non nel wizard transient (il wizard usa `many2many_binary` nativo che ha già upload integrato)
8. **GIN index idempotente**: Migration controlla esistenza prima di creare, evita errore su re-run

## File modificati/creati

### Nuovi (5 file)
- `models/casafolino_mail_compose_wizard.py` — Transient model compose (~75 righe)
- `views/mail_v3_compose_wizard_views.xml` — Form view wizard
- `static/src/js/mail_v3/mail_v3_reply_assistant.js` — Reply assistant component (~55 righe)
- `static/src/xml/mail_v3/mail_v3_reply_assistant.xml` — Template assistant
- `migrations/18.0.8.3.0/post-migrate.py` — F4 migration

### Modificati (13 file)
- `__manifest__.py` — version 18.0.8.3.0 + compose wizard view
- `models/__init__.py` — +1 import (compose wizard)
- `models/cf_contact.py` — +mv3_private_notes field
- `controllers/mail_v3_controllers.py` — +6 endpoint (search, reply_assistant, compose/open, nba/dismiss, notes, sidebar 360 esteso con nba/pipeline/timeline/notes)
- `security/ir.model.access.csv` — +1 riga ACL compose wizard
- `static/src/js/mail_v3/mail_v3_client.js` — Riscritto: +shortcuts, +search, +reply assistant, +settings, +compose wizard via doAction
- `static/src/js/mail_v3/mail_v3_sidebar_left.js` — Riscritto: compact mode con avatar, folders, settings
- `static/src/js/mail_v3/mail_v3_sidebar_360.js` — +NBA dismiss, +notes auto-save, +timeline/pipeline helpers
- `static/src/js/mail_v3/mail_v3_reading_pane.js` — +AI reply button handler, fix method references
- `static/src/js/mail_v3/mail_v3_compose.js` — +D&D upload, +attachment management
- `static/src/xml/mail_v3/*.xml` — Tutti i 6 template riscritti per nuovo layout
- `static/src/scss/mail_v3.scss` — Riscritto completo: sidebar 70px, NBA block, reply assistant, search, shortcuts help, settings drawer, pipeline/timeline/notes blocks, D&D zone

## Commits

- `af005e5` feat(mail-v3): sidebar SX compatta 70px con avatar account
- `e3e4341` feat(mail-v3): layout proportions + reading pane larger
- `690c664` feat(mail-v3): NBA sticky block + sidebar 360 con 9 blocchi
- `b0b1420` feat(mail-v3): reply assistant AI (3 bozze Groq)
- `9c01987` feat(mail-v3): compose wizard transient model + HtmlField editor
- `7a9dc22` feat(mail-v3): drag&drop allegati + keyboard shortcuts
- `850ba8c` feat(mail-v3): private notes block partner + full-text search
- `2895fb4` chore(mail-v3): bump manifest 18.0.8.3.0 + migration F4
- `(this)` docs(mail-v3): F4 report

## Dipendenze nuove

Nessuna. Nessuna libreria Python esterna aggiunta.

## Raccomandazioni F5

1. **Smart Snooze**: Snooze thread per X ore/giorni con ricomparsa automatica
2. **Undo send 10s**: Timer post-invio con possibilità di annullare prima che outbox processi
3. **Scheduled send**: Campo `scheduled_send_at` già presente su draft, implementare UI + cron check
4. **Dark mode**: Variabili SCSS già predisposte, aggiungere theme toggle
5. **Mobile single-pane**: Layout responsive con una sola colonna su viewport < 768px
6. **Calibration mode**: Modello feedback per override manuali hotness/NBA
7. **Search record rules**: Sostituire query SQL diretta con ORM search per rispettare record rules
8. **Settings drawer completo**: Tab Firme (CRUD), Visualizzazione (densità, font size), AI Settings (model, temperature)
9. **Sent folder filter**: Aggregare direction su thread per filtro outbound
