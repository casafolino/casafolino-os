# Brief F5 — Polish + Productivity Bonus

**Formato:** GSD — **MODALITÀ AUTONOMA TOTALE**
**Owner:** Antonio Folino
**Reference spec:** `docs/mail_v3_spec.md` v1.1
**Base:** `feat/mail-v3-f4` (F2 + F2.1 + F3 merged + F4, version 18.0.8.3.0)
**Target:** `casafolino_mail` 18.0.8.3.0 → 18.0.8.4.0
**Branch:** `feat/mail-v3-f5` (da `feat/mail-v3-f4`)
**Tempo stimato:** 5-6 ore autonome
**Prev brief:** report_f2, report_f2_1, report_f3, report_merged, report_f4

---

## 🚀 COME LANCIARE CODE

**Sul Mac (terminale normale, NON server):**

```bash
cd ~/casafolino-os
git fetch --all
git checkout feat/mail-v3-f4
git pull
claude --dangerously-skip-permissions
```

Poi dentro Code incolla tutto il brief e scrivi "Vai".

---

## ⚠️ 4 REGOLE CRITICHE (come F2/F3/F4)

1. **MAI fermarsi** — 3 eccezioni: data loss prod, credenziali mancanti, spec muta su architettura
2. **11 defaults automatici** per ambiguità (naming `mv3_`, pattern esistenti, UI text IT pro, icone FA5→emoji, colori variabili SCSS, edge case gracefully fail, bug pre-esistenti skip+annota)
3. **Auto-escape 45 min** → commit `wip`, skip, avanti
4. **Commit ogni 30 min + push ogni 3-4 commit**

---

## 1. Obiettivo

Chiudere V3 come **prodotto finito**, non prototipo. F5 è il polish definitivo: 13 feature che trasformano "funziona" in "è un piacere usarlo".

**Definition of Done finale V3:**

Antonio lavora 4 ore in Mail V3, invia 15 email, snoozza 3 thread, archivia 10 in bulk, mercoledì vede email "ripresentate" automaticamente, attiva dark mode la sera, apre su iPhone per check rapido mentre è in macchina, controlla analytics response time del team, premia Josefina per tempi medi <2h. **Non ha bisogno di Gmail** per la giornata lavorativa.

---

## 2. Contesto dopo F4

Branch `feat/mail-v3-f4` contiene tutto fino a qui. Cron attivi dopo F4:
- 85 Body Fetch
- 86 Draft Autosave Cleanup
- 87 Intelligence Rebuild
- 90 Outbox Process
- 91 Outbox Cleanup

**Cron disabilitati da sistemare in F5:**
- 82 Mail Sync V2 (spento stanotte per deploy F2)
- 83 Silent Partners (spento)
- 84 AI Classify (spento)
- 88 IMAP Flag Push (disabilitato by design F3)
- 89 IMAP Flag Pull (disabilitato by design F3)

**Da F4 report — bug/limitazioni note:**
- Compose dual approach (wizard transient + OWL legacy) → da unificare
- Search SQL non rispetta record rules → convertire a ORM
- Sent folder filter predisposto ma non funzionante → implementare
- Settings drawer minimale → completare

---

## 3. Scope IN — 13 deliverable

### 3.1 Smart Snooze (1h)

**Modello:** `casafolino.mail.snooze` (già specificato in spec §3bis.5, mai implementato).

File: `models/casafolino_mail_snooze.py` (new)

```python
class MailSnooze(models.Model):
    _name = 'casafolino.mail.snooze'
    _description = 'Thread snooze for later reappearance'
    _order = 'wake_at asc'

    thread_id = fields.Many2one('casafolino.mail.thread', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    snooze_type = fields.Selection([
        ('until_date', 'Fino a data'),
        ('until_reply', 'Fino a risposta'),
        ('if_no_reply_by', 'Se non risponde entro'),
    ], required=True, default='until_date')
    wake_at = fields.Datetime(string='Risveglia il', index=True)
    deadline_days = fields.Integer(string='Giorni deadline', default=3)
    active = fields.Boolean(default=True, index=True)
    note = fields.Text(string='Nota privata')
```

**Endpoint:**
```python
@route('/cf/mail/v3/thread/<int:thread_id>/snooze', type='json', auth='user')
def snooze_thread(self, thread_id, snooze_type, wake_at=None, deadline_days=3, note=''):
    # Validate + create snooze record
    # Mark thread as snoozed (nuovo campo is_snoozed su thread)
    pass

@route('/cf/mail/v3/snooze/<int:snooze_id>/unsnooze', type='json', auth='user')
def unsnooze(self, snooze_id):
    # Deactivate snooze immediately
    pass
```

**Cron 92 (NEW) Smart Snooze Checker** — ogni 15 min:
- `until_date`: NOW ≥ wake_at → wake
- `until_reply`: nuovo messaggio inbound nel thread dopo snooze → wake
- `if_no_reply_by`: no inbound entro deadline → wake

Wake = set `thread.is_snoozed=False` + notify user via bus + deactivate snooze.

**Campo `is_snoozed`** su `casafolino.mail.thread` (Boolean, indexed). Thread list filtra snoozed di default (nascosti).

**UI — bottone "Snooze" nel reading pane** accanto a Archive. Click apre popup:
- Preset: "Stasera 18:00", "Domani 9:00", "Lunedì 9:00", "Tra 1 settimana"
- Custom date picker
- Tipo snooze: selector 3 opzioni

**Folder "Snoozed" in sidebar SX** — icona 💤 sotto Starred. Click mostra thread snoozed con countdown wake_at.

### 3.2 Undo Send 10s (0.5h)

L'outbox (già in F3) processa ogni 2 min. Flaghiamo un nuovo stato `undoable` per i primi 10 secondi dopo send.

**Modifica `casafolino.mail.outbox`:**
- Nuovo campo `undo_until` (Datetime): `queued_at + 10s`
- State flow: `queued` → `undoable` (per primi 10s) → `sending` → `sent`/`error`
- Cron 90 skippa record in stato `undoable`

**Endpoint:**
```python
@route('/cf/mail/v3/outbox/<int:outbox_id>/undo', type='json', auth='user')
def undo_send(self, outbox_id):
    outbox = env['casafolino.mail.outbox'].browse(outbox_id)
    if outbox.state != 'undoable':
        return {'success': False, 'error': 'Non più annullabile'}
    # Restore to draft + cancel outbox
```

**UI — Toast "Email inviata · Annulla"** dopo click Send, con timer 10s countdown. Click su "Annulla" → ripristina come bozza.

### 3.3 Scheduled Send (0.5h)

Campo `scheduled_send_at` già presente nel modello `casafolino.mail.draft` (F2).

**Compose UI:**
- Bottone "Invia" con dropdown: "Invia ora" / "Programma invio..."
- "Programma" apre popup date/time picker + preset ("Domani 9:00", "Lunedì 9:00", "Custom")
- Draft salvato con `scheduled_send_at` + flag `is_scheduled=True`

**Cron 93 (NEW) Scheduled Send Dispatch** — ogni minuto:
- Cerca draft con `scheduled_send_at <= NOW` e `is_scheduled=True`
- Converte ad outbox con `queue_send()`
- Marca draft `is_scheduled=False`

**Folder "Programmate" in sidebar SX** — icona ⏰ con count. Click mostra lista draft scheduled ordinati per `scheduled_send_at`. Cliccando un draft si apre per edit/annulla scheduling.

### 3.4 Dark Mode (0.3h)

Variabili SCSS già predisposte (report F4 lo conferma). Serve solo:

1. **Attributo HTML** `data-theme="dark"` su `<html>` quando toggle attivo
2. **SCSS** con `[data-theme="dark"] { --bg-reading: #1a1a1a; --text-primary: #e0e0e0; ... }` per tutte le variabili
3. **Toggle button** nell'header Mail V3 (accanto a "Scrivi"): 🌙/☀️
4. **Salva preferenza** in `res.users.mv3_dark_mode` (campo già esiste da F2)
5. **Endpoint PUT** `/cf/mail/v3/user/dark_mode` per toggle + save

### 3.5 Mobile single-pane (0.5h)

**Media query** `@media (max-width: 768px)`:

```scss
@media (max-width: 768px) {
    .mv3-client {
        flex-direction: column;
        
        &__sidebar-left { 
            width: 100%; 
            height: auto;
            flex-direction: row;
            overflow-x: auto;
            padding: 8px;
        }
        
        &__thread-list,
        &__reading-pane,
        &__sidebar-360 {
            width: 100%;
            flex: 1;
        }
    }
    
    // Mobile navigation: show only one panel at a time
    .mv3-client--mobile-view-list .mv3-client__reading-pane,
    .mv3-client--mobile-view-list .mv3-client__sidebar-360 { display: none; }
    
    .mv3-client--mobile-view-reading .mv3-client__thread-list,
    .mv3-client--mobile-view-reading .mv3-client__sidebar-360 { display: none; }
    
    // ... idem per sidebar-360
}
```

**JS navigation state:** `mobileView = 'list' | 'reading' | 'sidebar'`
- Click thread → `mobileView = 'reading'`
- Back arrow in reading → `mobileView = 'list'`
- Tap 📊 in reading → `mobileView = 'sidebar'`

### 3.6 Calibration Mode feedback (0.5h)

**Modello `casafolino.partner.intelligence.feedback`** (già in spec §3bis.2, stub in F2, da completare):

```python
class IntelligenceFeedback(models.Model):
    _name = 'casafolino.partner.intelligence.feedback'
    _description = 'User feedback for hotness/NBA calibration'
    
    partner_id = Many2one('res.partner', required=True, index=True)
    user_id = Many2one('res.users', required=True)
    action_type = Selection([
        ('pinned_hot', 'Pinned hot'),
        ('pinned_ignore', 'Pinned ignore'),
        ('nba_useful', 'NBA utile'),
        ('nba_dismissed', 'NBA ignorato'),
        ('manual_lead_created', 'Lead creato manualmente'),
        ('manual_close', 'Chiuso manualmente'),
    ], required=True)
    hotness_at_action = Integer()
    nba_text_at_action = Char()
    context_json = Text()
    date = Datetime(default=fields.Datetime.now)
```

**Hook automatici** su azioni:
- Click "pin hot" su intelligence → feedback `pinned_hot`
- Click × dismiss NBA → feedback `nba_dismissed`
- Click su NBA action (se implementata) → feedback `nba_useful`
- Create lead da partner intelligence view → feedback `manual_lead_created`

**Report view** `partner.intelligence.feedback`:
- List + kanban con filtri per user/action/date
- Grafico "feedback per NBA rule_id" per capire quali regole funzionano
- Menu sotto "CasaFolino Mail CRM → Intelligence → Feedback"

### 3.7 Search con record rules (0.3h)

Fix bug F4: la search SQL bypassava record rules.

Sostituire query SQL con ORM:
```python
@route('/cf/mail/v3/search', type='json', auth='user')
def search(self, query, limit=50):
    if not query or len(query) < 2:
        return {'results': []}
    
    # Use ORM search (rispetta record rules)
    Message = request.env['casafolino.mail.message']
    
    # Full-text via PG raw sul campo indicizzato, ma filtrato per ORM-accessible IDs
    accessible_ids = Message.search([('state', '=', 'keep')]).ids
    
    if not accessible_ids:
        return {'results': []}
    
    # PostgreSQL full-text search only su IDs accessibili
    cr = request.env.cr
    cr.execute("""
        SELECT id FROM casafolino_mail_message
        WHERE id = ANY(%s)
          AND to_tsvector('simple', coalesce(subject,'')||' '||coalesce(body_plain,'')) 
              @@ plainto_tsquery('simple', %s)
        ORDER BY ts_rank(
            to_tsvector('simple', coalesce(subject,'')||' '||coalesce(body_plain,'')),
            plainto_tsquery('simple', %s)
        ) DESC, email_date DESC
        LIMIT %s
    """, (accessible_ids, query, query, limit))
    
    matched_ids = [r[0] for r in cr.fetchall()]
    messages = Message.browse(matched_ids)
    
    return {
        'results': [{
            'id': m.id,
            'subject': m.subject,
            'from': m.from_email,
            'date': fields.Datetime.to_string(m.email_date),
            'thread_id': m.thread_id.id if m.thread_id else None,
            'snippet': (m.body_plain or '')[:150],
        } for m in messages]
    }
```

### 3.8 Settings Drawer Completo (1h)

Il drawer attuale (F4) mostra solo placeholder. Completiamolo con 4 tab veri:

**Tab "Firme":**
- List di `casafolino.mail.signature` per l'utente corrente
- Form inline per edit (name, body_html con editor, is_default, include_in_reply/forward)
- Bottone "Nuova firma"
- Mark default

**Tab "Visualizzazione":**
- Reading pane position: right / bottom / off
- Thread list density: compact / comfortable / spacious
- Font size: small / medium / large
- Keyboard shortcuts: on/off
- Salva in `res.users` campi `mv3_*`

**Tab "AI Settings":**
- Reply Assistant enabled: on/off
- Temperature slider: 0.1-1.0 (default 0.5)
- Model selection: llama-3.3-70b-versatile / llama-3.1-70b / mixtral-8x7b
- NBA LLM fallback: on/off
- Test button: "Test connessione Groq" che chiama endpoint di verifica

**Tab "Account":**
- Per ogni account: toggle "Notifiche push", "Auto-archive old" (days), Default signature
- Salva in `casafolino.mail.account`

Campi nuovi necessari su `res.users`:
- `mv3_font_size` (Selection small/medium/large)
- `mv3_ai_reply_enabled` (Boolean default True)
- `mv3_ai_temperature` (Float default 0.5)
- `mv3_ai_model` (Char default 'llama-3.3-70b-versatile')

Config param nuovi (global, non per-user):
- `casafolino.mail.v5_groq_model_default`
- `casafolino.mail.v5_nba_llm_fallback_enabled`

### 3.9 Sent folder filter (0.3h)

Bug F4: folder "Inviati" non filtra correttamente.

Fix:
- Aggiungi `has_outbound` computed stored su thread (True se almeno 1 messaggio `direction='outbound'`)
- Indice su `(has_outbound, account_id, last_message_date DESC)`
- Controller `/threads/list` accetta filtro `folder='sent'` → domain `[('has_outbound', '=', True)]`
- Sidebar SX folder "Inviati" chiama endpoint con `folder='sent'`

Analogo per `has_starred`, `has_archived`, `has_deleted` se non già presenti.

### 3.10 Unificazione Composer (0.5h)

Bug F4: 2 composer diversi (wizard transient + OWL legacy).

**Decisione:** wizard transient è più pulito (editor HTML nativo). Manteniamo quello, rimuoviamo OWL legacy.

**Da trasferire dal OWL legacy al wizard:**
- Drag & drop allegati → aggiungere al wizard (usando campi `many2many_binary`)
- Auto-save debounced → wizard può avere `action_autosave()` chiamato ogni 30s via JS
- Signature selector → aggiungere dropdown nel wizard

**Frontend `mail_v3_compose.js`** → rimuovere, redirect tutto su wizard tramite `doAction`.

**Shortcut `c` e bottone "Scrivi" e bottoni Reply/Forward** → aprono tutti wizard transient con pre-fill diverso.

### 3.11 Bulk Actions (0.5h) — BONUS

Sul thread list, permettere:
- Checkbox select per ogni thread
- Checkbox "Seleziona tutto" in header
- Toolbar bulk actions quando ≥1 selezionato: Mark read, Mark unread, Archive, Delete, Snooze, Move to account, Add label
- Keyboard: `x` toggle selection, `Shift+Click` range select

Endpoint `/cf/mail/v3/threads/bulk` accetta action + ids, executes in loop con sudo.

### 3.12 Smart Labels (0.3h) — BONUS

Modello `casafolino.mail.label` già esiste (F3 intelligence_views). Completiamo:
- Sync Gmail labels → Odoo labels (al fetch, popoliamo `gmail_labels` M2M su message)
- Filtro per label in sidebar SX (sotto folder base)
- Bulk "Apply label" in thread list
- Rinomina label da Odoo → propaga su Gmail via IMAP RENAME (richiede cron 88/89 attivi)

### 3.13 Response Time Analytics (1h) — BONUS

Dashboard separata per il team.

**Modello `casafolino.mail.response.metric`** (method-only, calcola on-the-fly):
- Per ogni user_id, calcola:
  - Tempo medio prima risposta ultimi 30gg
  - Numero email gestite ultimi 30gg
  - Thread aperti / chiusi
  - Partner hot seguiti

**View dashboard** accessibile da menu "Mail CRM → Analytics":
- Card con KPI per ciascuno dei 3 account
- Grafico line "Tempo medio risposta 30gg" con trend
- Tabella top 10 partner con response time per partner
- Filtri per date range

**Menu + action** `cf_mail_v3_analytics` visibile solo a `group_mail_v3_admin`.

### 3.14 Riattivazione cron 82/83/84 (0.1h) — BONUS

In migration 18.0.8.4.0 post-migrate:
```python
cr.execute("""
    UPDATE ir_cron SET active = true 
    WHERE id IN (82, 83, 84)
      AND active = false;
""")
_logger.info(f'[mail v3 F5] Reactivated {cr.rowcount} legacy crons')
```

Questo riattiva Mail Sync V2, Silent Partners, AI Classify spenti stanotte per deploy F2.

Anche rule "own" spente manualmente stanotte:
```python
cr.execute("""
    UPDATE ir_rule SET active = true
    WHERE name::text ILIKE '%Mail V3%' AND active = false;
""")
```

---

## 4. Scope OUT — NON fare

- ❌ Toccare modelli F2/F3/F4 se non strettamente necessario
- ❌ Riscrivere intelligence engine (funziona)
- ❌ Modificare record rules (F2.1 OK)
- ❌ Cambiare schema DB pesantemente (solo add columns OK)
- ❌ Rifare frontend da zero (incrementale, non sostituire)
- ❌ Integrazioni esterne nuove (WhatsApp, Calendar, ecc.) → F6+

---

## 5. Vincoli Odoo 18

1. ❌ `attrs=` → ✅ `invisible=domain`
2. ❌ `<tree>` → ✅ `<list>`
3. ❌ `_inherit` in `ir.model.access.csv`
4. OWL: `static props = ["*"]`
5. Cron via migration con `_ensure_cron` idempotent
6. `bleach` per sanitize user HTML
7. Datetime naive UTC

---

## 6. Acceptance Criteria (25 AC)

### Install
- **AC1** Module 18.0.8.3.0 → 18.0.8.4.0 senza ERROR
- **AC2** Migration 18.0.8.4.0 aggiunge tabelle/colonne senza distruggere dati esistenti
- **AC3** Cron 82/83/84 riattivati dopo migration
- **AC4** Record rules "Mail V3 own *" riattivate dopo migration

### Smart Snooze
- **AC5** Click "Snooze" nel reading pane apre popup preset + custom
- **AC6** Thread snoozed sparisce da thread list fino a wake_at
- **AC7** Cron 92 ogni 15min processa wake condition
- **AC8** Folder "Snoozed" in sidebar mostra countdown

### Undo Send
- **AC9** Dopo Send, toast "Annulla" visibile 10s con timer
- **AC10** Click "Annulla" cancella outbox + ripristina draft

### Scheduled Send
- **AC11** Compose ha dropdown "Invia ora" / "Programma invio"
- **AC12** Folder "Programmate" mostra draft scheduled
- **AC13** Cron 93 converte scheduled → outbox all'orario

### Dark Mode
- **AC14** Toggle 🌙/☀️ in header applica data-theme
- **AC15** Preferenza salvata in res.users.mv3_dark_mode

### Mobile
- **AC16** Su viewport ≤768px layout single-pane con navigation back

### Calibration
- **AC17** Feedback creato automaticamente su pin hot/ignore/dismiss NBA
- **AC18** Menu Intelligence → Feedback list view accessibile

### Search + fix
- **AC19** Search rispetta record rules (user non-admin vede solo propri)
- **AC20** Folder "Inviati" filtra thread con `has_outbound=True`

### Settings Drawer
- **AC21** 4 tab (Firme, Visualizzazione, AI, Account) funzionanti
- **AC22** Modifiche salvate persistono tra sessioni

### Composer
- **AC23** Un solo composer (wizard transient) per Scrivi/Reply/Forward/AI shortcut
- **AC24** Drag & drop allegati nel wizard

### Bonus + Analytics
- **AC25** Dashboard Analytics mostra response time + volumes per user/account

---

## 7. Deploy path (esegue Antonio)

**Sul server EC2 (ssh ubuntu@51.44.170.55):**

```bash
cd /home/ubuntu/casafolino-os
git fetch --all
git checkout feat/mail-v3-f5
git pull
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tail -60
docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http 2>&1 | tail -60
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "DELETE FROM ir_attachment WHERE name LIKE '%web.assets%';"
docker restart odoo-app
```

---

## 8. Git workflow

Branch: `feat/mail-v3-f5` da `feat/mail-v3-f4`.

Commits atomici:
```
feat(mail-v3): smart snooze model + cron 92 + UI button
feat(mail-v3): undo send 10s with outbox undoable state
feat(mail-v3): scheduled send with cron 93
feat(mail-v3): dark mode toggle + SCSS themes
feat(mail-v3): mobile responsive single-pane
feat(mail-v3): calibration feedback model + hooks
fix(mail-v3): search rispetta record rules via ORM
fix(mail-v3): sent folder filter + has_outbound computed
feat(mail-v3): settings drawer complete (4 tabs)
refactor(mail-v3): unify composer (wizard only, remove OWL legacy)
feat(mail-v3): bulk actions thread list
feat(mail-v3): smart labels sync Gmail
feat(mail-v3): response time analytics dashboard
chore(mail-v3): migration 18.0.8.4.0 + reactivate crons
docs(mail-v3): F5 report
```

Push ogni 3-4 commit.

---

## 9. Report atteso

File: `casafolino_mail/docs/report_f5.md` stesso template F4.

Raccomandazioni F6:
- WhatsApp Business integration
- Google Calendar integration nativa
- Email templates editor WYSIWYG
- Notifiche desktop browser
- Pesi Hotness auto-calibrati (report calibration 30gg)
- Multi-lingua UI (switcher IT/EN/DE)

---

## 10. Ordine esecuzione

1. `git checkout -b feat/mail-v3-f5`
2. Leggi brief + report precedenti
3. §3.14 Cron + rule riattivazione (quick win, subito)
4. §3.1 Smart Snooze (~1h)
5. §3.2 Undo Send (0.5h)
6. §3.3 Scheduled Send (0.5h)
7. **COMMIT + PUSH batch 1**
8. §3.4 Dark Mode (0.3h)
9. §3.5 Mobile (0.5h)
10. §3.6 Calibration (0.5h)
11. §3.7 Search fix (0.3h)
12. §3.9 Sent folder fix (0.3h)
13. **COMMIT + PUSH batch 2**
14. §3.8 Settings Drawer (1h)
15. §3.10 Unificazione Composer (0.5h)
16. **COMMIT + PUSH batch 3**
17. §3.11 Bulk Actions (0.5h)
18. §3.12 Smart Labels (0.3h)
19. §3.13 Analytics (1h)
20. Manifest bump 18.0.8.4.0
21. Migration post-migrate
22. docs/report_f5.md
23. **COMMIT + PUSH finale**

**Totale: ~5-6h autonome.**

---

## 11. Una cosa sola

> F5 chiude V3 come prodotto finito.
>
> Dopo questo il team lavora in Mail V3 senza guardare Gmail. Se lo trascuri, Mail V3 resta "quasi pronto" a vita.
>
> **MAI fermarti. 4 regole. Vai.**
