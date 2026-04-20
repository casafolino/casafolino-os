# Brief F4 — Productivity + AI Assistant + UI Restyling

**Formato:** GSD — **MODALITÀ AUTONOMA TOTALE**
**Owner:** Antonio Folino
**Reference spec:** `docs/mail_v3_spec.md` v1.1
**Base:** `feat/mail-v3-merged` (F2 + F2.1 + F3 unified, version 18.0.8.2.0)
**Target:** `casafolino_mail` 18.0.8.2.0 → 18.0.8.3.0
**Branch:** `feat/mail-v3-f4` (da `feat/mail-v3-merged`)
**Tempo stimato:** 3-4 ore autonome
**Prev brief:** `docs/report_f2.md`, `docs/report_f2_1.md`, `docs/report_f3.md`, `docs/report_merged.md`

---

## 🚀 COME LANCIARE CODE

**Sul Mac (terminale normale, NON server):**

```bash
cd ~/casafolino-os
git fetch --all
git checkout feat/mail-v3-merged
git pull
claude --dangerously-skip-permissions
```

Poi dentro Code incolla questo brief intero (contenuto da qui in giù) e scrivi "Vai".

---

## ⚠️ 4 REGOLE CRITICHE (come F2/F3)

1. **MAI fermarsi** a chiedere conferme. Solo 3 eccezioni: data loss prod, credenziali mancanti, spec muta su architettura
2. **11 defaults automatici** per ambiguità (naming snake_case `mv3_`, pattern esistenti, UI text IT pro max 30 char, icone FA5 → emoji, colori variabili SCSS esistenti, edge case gracefully fail con log warning, bug pre-esistenti skip+annota, test fail non-F4 skip+annota)
3. **Auto-escape 45 min** feature bloccata → commit `wip`, skip, passa avanti
4. **Commit ogni 30 min + push ogni 3-4 commit** — mai aspettare la fine

---

## 1. Obiettivo

Portare Mail V3 da "client che funziona" a "cockpit commerciale produttivo". Aggiunge 9 feature di produttività, AI assistant, e ristruttura il layout UI per massimizzare lo spazio centrale.

**Definition of Done (test di Lembo aggiornato):**

Antonio apre Mail V3 su schermo 15". Vede:

- **Sidebar SX compatta ~70px** con icone account (3 avatar colorati, cliccabili) + icone azioni globali + icona impostazioni in fondo
- **Lista thread larga ~420px** al centro-sinistra
- **Reading pane flex** centrale molto più grande di prima
- **Sidebar 360° destra 360px** con blocchi: Identità (con Hotness) → **NBA sticky** (Next Best Action dal motore F3) → Relazione → Business → Pipeline → Timeline → Note private → Azioni rapide

Clicca email di Lembo. In 5 secondi vede:
- 🔥 Hot 87, Lead Proposal €8.400
- 🎯 "Follow-up preventivo — silente 5gg" nel NBA block
- Timeline ultime 5 interazioni
- Bottone **"Risposta guidata AI"** nel reading pane
- Clicca → popup con **3 bozze Groq** (Diretta / Relazionale / Proattiva)
- Sceglie una, edita, premi **Cmd+Enter** → invio via outbox

---

## 2. Contesto (stato repo dopo F3 merge)

`feat/mail-v3-merged` contiene:
- ✅ F2 MVP: three-pane, sidebar SX con account list, sidebar 360° base, compose textarea, SMTP retry, 5 blocchi 360°
- ✅ F2.1 hotfix: record rules 4 (account own/admin, message own/admin, draft own/admin)
- ✅ F3: Intelligence engine 20 NBA rules + LLM fallback, Intent detection IT/EN/DE 11 intenti, IMAP flag sync (disabled default), Outbox async SMTP queue, Intelligence views

**Cron già attivi dopo merge:**
- 85 Body Fetch (F0)
- 86 Draft Autosave Cleanup (F2)
- 87 Intelligence Rebuild (F2+F3 merged)
- 90 Outbox Process (F3)
- 91 Outbox Cleanup (F3)

**Disabilitati by design (da abilitare manualmente dopo test):**
- 88 IMAP Flag Push
- 89 IMAP Flag Pull

**Non toccare:**
- Modelli V3 esistenti: `casafolino.mail.thread`, `casafolino.mail.draft`, `casafolino.mail.signature`, `casafolino.partner.intelligence`, `casafolino.mail.outbox`, `casafolino.mail.flag.sync`
- Campi già aggiunti a `casafolino.mail.message`: `thread_id`, `is_read`, `is_starred`, `is_archived`, `is_deleted`, `intent_detected`, `imap_flags_synced`, `reply_to_message_id`
- Record rules F2.1: sono OK, non modificare
- Controller esistenti `/cf/mail/v3/*`: estendere, non rifare

---

## 3. Scope IN — 9 deliverable

### 3.1 UI Restyling — sidebar SX compatta (1h)

**File:** `static/src/js/mail_v3/mail_v3_sidebar_left.js` + `xml` + `scss`

**Trasformare** l'attuale sidebar SX 220px larga in una barra verticale compatta ~70px:

Struttura nuova:
```
┌─────┐
│ 📬  │  ← "Tutti" (icon inbox)
├─────┤
│ AA  │  ← Avatar Antonio (iniziali colorate)
│ JL  │  ← Avatar Josefina  
│ MS  │  ← Avatar Martina
├─────┤
│ 📝  │  ← Bozze
│ ⭐  │  ← Starred
│ 📤  │  ← Inviati
│ 🗑️  │  ← Cestino
├─────┤
│ ... │  spaziatura flex
├─────┤
│ ⚙️  │  ← Impostazioni (click apre drawer)
└─────┘
```

Comportamenti:
- Ogni icona account mostra badge unread count come pallino sovrapposto in alto a destra
- **Hover** su icona account → tooltip con nome completo + email + unread count
- **Click** icona account → filtra lista thread per quell'account (visual: icona attiva colorata)
- **Click "Tutti"** → rimuove filtro
- **Click ⚙️ Impostazioni** → apre drawer modale centrato con tabs: "Account", "Visualizzazione", "Keyboard shortcuts", "Firme", "AI Settings"
- Avatar = cerchio con iniziali (AA/JL/MS) + colore unico per account (Antonio verde #5A6E3A, Josefina arancione #F39C12, Martina viola #9B59B6)

SCSS:
```scss
.mv3-sidebar-left {
    width: 70px;
    flex: 0 0 70px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 16px 0;
    border-right: 1px solid $mv3-border;
    background: #FAFAF8;
}

.mv3-sidebar-left__avatar {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
    color: white;
    cursor: pointer;
    position: relative;
    transition: transform 0.1s;

    &:hover { transform: scale(1.08); }
    &--active { box-shadow: 0 0 0 2px #5A6E3A; }

    &--antonio { background: #5A6E3A; }
    &--josefina { background: #F39C12; }
    &--martina { background: #9B59B6; }
}

.mv3-sidebar-left__badge {
    position: absolute;
    top: -4px;
    right: -4px;
    background: #E74C3C;
    color: white;
    border-radius: 10px;
    font-size: 10px;
    padding: 1px 5px;
    min-width: 18px;
    text-align: center;
}

.mv3-sidebar-left__icon {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #666;
    cursor: pointer;
    border-radius: 8px;

    &:hover { background: #EEE; color: #333; }
    &--active { background: #EEF2E6; color: #5A6E3A; }
}

.mv3-sidebar-left__divider {
    width: 32px;
    height: 1px;
    background: #E0E0E0;
    margin: 8px 0;
}
```

Aggiornare `MailV3Client` template per usare nuova sidebar: passare `accounts`, `selectedAccountId`, callback `onAccountChange(id)`, `onFolderChange(folder)`, `onOpenSettings()`.

### 3.2 Reading pane allargato (0.3h)

Con sidebar SX ridotta a 70px, il reading pane guadagna 150px. Ritarare proporzioni:

```scss
.mv3-client {
    &__sidebar-left   { width: 70px;  flex: 0 0 70px; }    // era 220
    &__thread-list    { width: 420px; flex: 0 0 420px; }   // era 380, +40
    &__reading-pane   { flex: 1; }                          // guadagna resto
    &__sidebar-360    { width: 360px; flex: 0 0 360px; }   // invariata
}
```

Thread list item più leggibile con 420px invece di 380.

### 3.3 NBA block sidebar destra — sticky top (0.5h)

Integrare il motore NBA di F3 (già mergiato) dentro la sidebar 360°.

**File:** nuovo `static/src/js/mail_v3/mail_v3_nba_block.js` + template + aggiungere in `Sidebar360`.

Blocco **sticky** (resta visibile anche scrollando), subito sotto CompanyBlock (Identità):

```xml
<div t-if="data.nba_text" 
     t-att-class="`mv3-nba-block mv3-nba-block--${data.nba_urgency}`">
    <div class="mv3-nba-block__icon">🎯</div>
    <div class="mv3-nba-block__body">
        <div class="mv3-nba-block__label">Next Best Action</div>
        <div class="mv3-nba-block__text" t-out="data.nba_text"/>
        <div t-if="data.nba_from_llm" class="mv3-nba-block__meta">
            <span>🤖 AI suggestion</span>
        </div>
        <div t-elif="data.nba_rule_id" class="mv3-nba-block__meta">
            <span>Regola #<t t-out="data.nba_rule_id"/></span>
        </div>
    </div>
    <button class="mv3-nba-block__dismiss" 
            t-on-click="() => this.dismissNba(data.partner_id)"
            title="Ignora questo suggerimento">×</button>
</div>
```

Colori per urgency (SCSS):
```scss
.mv3-nba-block {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    gap: 10px;
    padding: 12px;
    border-left: 4px solid;
    margin-bottom: 8px;

    &--critical { background: #FFEBEE; border-left-color: #C62828; }
    &--high     { background: #FFF3E0; border-left-color: #E65100; }
    &--medium   { background: #FFF9E6; border-left-color: #F39C12; }
    &--low      { background: #F0F4C3; border-left-color: #9E9D24; }
    &--info     { background: #E3F2FD; border-left-color: #1976D2; }

    &__icon { font-size: 22px; line-height: 1; }
    &__body { flex: 1; min-width: 0; }
    &__label { 
        font-size: 10px; 
        text-transform: uppercase; 
        color: #666; 
        letter-spacing: 0.5px;
    }
    &__text { 
        font-weight: 600; 
        font-size: 14px; 
        line-height: 1.3;
        margin-top: 3px;
    }
    &__meta { 
        font-size: 11px; 
        color: #999; 
        margin-top: 4px;
    }
    &__dismiss {
        background: none;
        border: none;
        font-size: 20px;
        color: #999;
        cursor: pointer;
        line-height: 1;
        padding: 0 4px;
        &:hover { color: #333; }
    }
}
```

**Controller endpoint NUOVO**:
```python
@route('/cf/mail/v3/partner/<int:partner_id>/nba', type='json', auth='user')
def partner_nba(self, partner_id):
    intel = request.env['casafolino.partner.intelligence'].search(
        [('partner_id', '=', partner_id)], limit=1
    )
    if not intel:
        return {'nba_text': None}
    if intel.pinned_ignore:
        return {'nba_text': None}
    return {
        'nba_text': intel.nba_text,
        'nba_urgency': intel.nba_urgency,
        'nba_rule_id': intel.nba_rule_id,
        'nba_from_llm': intel.nba_from_llm,
        'partner_id': partner_id,
    }

@route('/cf/mail/v3/partner/<int:partner_id>/nba/dismiss', type='json', auth='user')
def partner_nba_dismiss(self, partner_id):
    intel = request.env['casafolino.partner.intelligence'].search(
        [('partner_id', '=', partner_id)], limit=1
    )
    if intel:
        # Pin ignore per 24h
        intel.write({'pinned_ignore': True})
    return {'success': True}
```

Estendere endpoint `/cf/mail/v3/partner/<int:id>/sidebar_360` per includere `nba` dentro il payload, così lo carica una volta sola.

### 3.4 Risposta Guidata AI (1h)

**File:** nuovo `static/src/js/mail_v3/mail_v3_reply_assistant.js`.

Flow:
1. User clicca bottone "🤖 Risposta Guidata" nel reading pane (accanto ai bottoni Rispondi/Rispondi tutti/Inoltra)
2. Popup modale si apre con spinner "AI sta elaborando 3 bozze..."
3. Controller chiama Groq con contesto: partner + intent email + last 3 msg del thread
4. 3 bozze tornano come card cliccabili:
   - **Card A — Diretta** (3-4 righe, conferma secca)
   - **Card B — Relazionale** (3-5 righe, richiama storia partner + conferma)
   - **Card C — Proattiva** (4-6 righe, conferma + proposta next step / call)
5. User clicca una card → ComposeWizard si apre pre-filled con quella bozza
6. User edita, invia con Cmd+Enter

**Controller:**
```python
@route('/cf/mail/v3/message/<int:message_id>/reply_assistant', type='json', auth='user')
def reply_assistant(self, message_id):
    import requests, json
    msg = request.env['casafolino.mail.message'].browse(message_id)
    if not msg.exists():
        return {'error': 'Message not found'}
    
    # Get partner context
    partner = msg.partner_id
    intel = request.env['casafolino.partner.intelligence'].search(
        [('partner_id', '=', partner.id)], limit=1
    ) if partner else None
    
    # Get thread history (last 3 messages)
    thread_msgs = []
    if msg.thread_id:
        thread_msgs = msg.thread_id.message_ids.sorted('email_date', reverse=True)[:3]
    
    # Build context
    context = f"""
Azienda: {partner.name if partner else 'Sconosciuto'}
Paese: {partner.country_id.name if partner and partner.country_id else 'N/A'}
Intent email: {msg.intent_detected or 'general'}
Oggetto: {msg.subject or ''}
Body ultima email: {(msg.body_text or msg.body_html or '')[:500]}
Ultimi scambi: {', '.join([(m.subject or '')[:50] for m in thread_msgs])}
"""
    
    prompt = f"""Sei l'assistente email di Antonio Folino, CEO di CasaFolino (food export italiano).
CONTESTO:
{context}

Genera 3 bozze di risposta email in italiano, professionali ma calde.
Formato JSON (solo JSON, nient'altro):
{{
  "bozze": [
    {{"tipo": "Diretta", "testo": "..."}},
    {{"tipo": "Relazionale", "testo": "..."}},
    {{"tipo": "Proattiva", "testo": "..."}}
  ]
}}

Regole:
- Diretta: 3-4 righe, risposta secca al punto
- Relazionale: 4-5 righe, richiamo a storia/contesto, poi risposta
- Proattiva: 5-6 righe, risposta + proposta prossimo step (call, invio materiale, meeting)
- Non firmare (la firma viene aggiunta automaticamente)
- Non inventare date, numeri, prezzi
"""
    
    ICP = request.env['ir.config_parameter'].sudo()
    api_key = ICP.get_param('casafolino.groq_api_key')
    if not api_key:
        return {'error': 'Groq API key not configured'}
    
    try:
        r = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 800,
                'temperature': 0.5,
                'response_format': {'type': 'json_object'},
            },
            timeout=20,
        )
        r.raise_for_status()
        content = r.json()['choices'][0]['message']['content']
        data = json.loads(content)
        return {'bozze': data.get('bozze', [])}
    except Exception as e:
        _logger.error(f'[mail v3] Reply assistant fail: {e}')
        return {'error': str(e)}
```

Frontend: modale popup con 3 card, click → compose pre-filled.

### 3.5 HtmlField compose (0.5h)

Sostituire textarea con editor HTML nativo Odoo. Usare `<field name="body_html" widget="html"/>` se usi form view, oppure component OWL `Wysiwyg` se JSON-based.

Approccio consigliato: **form view transient** invece di full-custom OWL compose. Più stabile e pronto per F5 (undo send, schedule send).

Creare `casafolino.mail.compose.wizard` transient model con:
- `account_id`, `to_emails`, `cc_emails`, `bcc_emails`, `subject`, `body_html` (Html), `attachment_ids`, `in_reply_to_message_id`
- Metodo `action_send()` → crea casafolino.mail.outbox record con `queue_send()`
- Metodo `action_save_draft()` → crea casafolino.mail.draft

Form view con bottoni "Invia", "Salva bozza", "Annulla".

ComposeWizard frontend diventa: click "Scrivi"/"Rispondi" → apre action del wizard con dict pre-filled. Odoo gestisce editor html nativo.

### 3.6 Keyboard shortcuts (0.3h)

**File:** nuovo `static/src/js/mail_v3/mail_v3_shortcuts.js`

Listener globale quando MailV3Client è mounted:

| Tasto | Azione |
|---|---|
| `j` | Thread successivo |
| `k` | Thread precedente |
| `Enter` | Apri thread selezionato |
| `r` | Rispondi |
| `R` (Shift+R) | Rispondi a tutti |
| `f` | Inoltra |
| `a` | Risposta guidata AI |
| `e` | Archivia |
| `#` | Elimina (soft) |
| `s` | Star toggle |
| `u` | Mark unread |
| `c` | Nuovo messaggio |
| `/` | Focus search |
| `Cmd+Enter` | Invia (dentro compose) |
| `?` | Mostra help shortcuts |

`?` apre modale con lista shortcut.

Disabilitare quando focus è in input/textarea/contenteditable.

### 3.7 Full-text search (0.5h)

Search bar in alto sopra thread list. Input debounced 300ms.

**Backend:** sfruttare index GIN già creato in migration F2 su `(subject + body_text)`.

Endpoint `/cf/mail/v3/search`:
```python
@route('/cf/mail/v3/search', type='json', auth='user')
def search(self, query, limit=50):
    if not query or len(query) < 2:
        return {'results': []}
    
    # Use ts_query for full-text search
    cr = request.env.cr
    cr.execute("""
        SELECT m.id, m.subject, m.from_email, m.email_date, m.thread_id,
               ts_rank(to_tsvector('simple', coalesce(subject,'')||' '||coalesce(body_text,'')), 
                       plainto_tsquery('simple', %s)) as rank
        FROM casafolino_mail_message m
        WHERE m.state = 'keep'
          AND to_tsvector('simple', coalesce(subject,'')||' '||coalesce(body_text,'')) 
              @@ plainto_tsquery('simple', %s)
          AND m.account_id IN (
              SELECT id FROM casafolino_mail_account 
              WHERE responsible_user_id = %s OR %s IN (
                  SELECT uid FROM res_groups_users_rel WHERE gid IN (
                      SELECT res_id FROM ir_model_data 
                      WHERE module='casafolino_mail' AND name='group_mail_v3_admin'
                  )
              )
          )
        ORDER BY rank DESC, m.email_date DESC
        LIMIT %s
    """, (query, query, request.env.user.id, request.env.user.id, limit))
    
    rows = cr.dictfetchall()
    return {'results': rows}
```

Frontend: input in thread list header, risultati filtrano la lista (o sostituiscono con risultati ricerca).

### 3.8 Drag & drop allegati (0.3h)

Dentro ComposeWizard: 
- Drop zone che accetta file drag&drop
- Upload async via `/web/binary/upload_attachment` standard Odoo
- Preview thumbnail + nome + size + remove button
- Aggiungi a `attachment_ids`

### 3.9 Note private partner block (0.3h)

Nuovo blocco in sidebar 360°, dopo Timeline.

**Backend:** campo `mv3_private_notes` (Text) su `res.partner`, invisible in form view standard partner. Solo per Mail V3.

**Frontend:** textarea persistente nella sidebar con auto-save su blur (debounced 1s). Endpoint `PUT /cf/mail/v3/partner/<id>/notes`.

---

## 4. Scope OUT — NON fare

- ❌ Smart Snooze (F5)
- ❌ Undo send 10s (F5)
- ❌ Scheduled send (F5)
- ❌ Delega inbox readonly (F5)
- ❌ Dark mode (F5)
- ❌ Mobile single-pane (F5)
- ❌ Calibration mode feedback tracking (F5)
- ❌ Riscrivere modelli F3 (intelligence, outbox, flag_sync)
- ❌ Toccare migration esistenti F2/F3
- ❌ Fix bug pre-esistenti body fetch (scope a parte)

---

## 5. Vincoli Odoo 18 (hard rules)

Stessi di F2/F3:
1. ❌ `attrs=` → ✅ `invisible=domain`
2. ❌ `<tree>` → ✅ `<list>`
3. ❌ `_inherit` in `ir.model.access.csv`
4. OWL: `static props = ["*"]`
5. Cron via migration con `_ensure_cron` idempotent
6. Groq header: `Authorization: Bearer {key}` + `Content-Type: application/json`
7. Body HTML user content → iframe sandboxed
8. `static props = ["*"]` su tutti i componenti OWL nuovi
9. Datetime naive UTC in DB

---

## 6. Acceptance Criteria (20 AC)

### Install
- **AC1** Module update 18.0.8.2.0 → 18.0.8.3.0 senza ERROR
- **AC2** Migration 18.0.8.3.0 post-migrate esiste (anche vuota se non servono modifiche DB)

### Sidebar SX restyling
- **AC3** Sidebar SX larga 70px, icone round con iniziali per account
- **AC4** Click icona account filtra thread list
- **AC5** Icona ⚙️ impostazioni apre drawer modale con tabs
- **AC6** Hover su avatar mostra tooltip con nome completo + unread
- **AC7** Badge unread su avatar quando count > 0

### Reading pane + 360
- **AC8** Reading pane è ≥900px su schermo 1920px (guadagna spazio)
- **AC9** Sidebar 360 ha NBA block sticky subito dopo CompanyBlock
- **AC10** NBA block colorato by urgency (5 varianti CSS)
- **AC11** Click × su NBA chiama endpoint dismiss + rimuove block

### Risposta Guidata
- **AC12** Bottone "🤖 Risposta Guidata" visibile nel reading pane
- **AC13** Click apre modale, mostra spinner, chiama Groq
- **AC14** Groq ritorna 3 bozze (Diretta/Relazionale/Proattiva)
- **AC15** Click su card apre compose pre-filled con quella bozza

### Compose + shortcuts + search + D&D + note
- **AC16** Compose usa HtmlField con editor WYSIWYG nativo
- **AC17** Keyboard shortcuts `j`/`k`/`r`/`a`/`c`/`/`/`?` funzionano
- **AC18** Full-text search trova thread per keyword in subject+body
- **AC19** Drag&drop file su composer aggiunge attachment_id
- **AC20** Note private su partner salvate con debounce 1s

---

## 7. Deploy path (esegue Antonio)

**Sul server EC2 (ssh ubuntu@51.44.170.55):**

```bash
cd /home/ubuntu/casafolino-os
git fetch --all
git checkout feat/mail-v3-f4
git pull

# Copy
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/

# Stage first
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tail -60

# Prod if stage OK
docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http 2>&1 | tail -60

# Clear cache
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "
DELETE FROM ir_attachment WHERE name LIKE '%web.assets%';"

docker restart odoo-app
```

---

## 8. Git workflow

Branch: `feat/mail-v3-f4` da `feat/mail-v3-merged`.

Commits atomici convention-commits:
```
feat(mail-v3): sidebar SX compatta 70px con avatar account
feat(mail-v3): layout proportions + reading pane larger
feat(mail-v3): NBA sticky block in sidebar 360 + controller endpoints
feat(mail-v3): reply assistant AI (3 bozze Groq)
feat(mail-v3): compose wizard transient model + HtmlField editor
feat(mail-v3): keyboard shortcuts j/k/r/a/c/?
feat(mail-v3): full-text search with tsvector GIN index
feat(mail-v3): drag&drop attachments in composer
feat(mail-v3): private notes block partner + endpoint
chore(mail-v3): bump manifest 18.0.8.3.0
docs(mail-v3): F4 report
```

Push ogni 3-4 commit. NO PR.

---

## 9. Report atteso

File: `docs/report_f4.md`

Template:
```markdown
# F4 Report — Productivity + AI + UI Restyling
Date: YYYY-MM-DD
Commits: N
Push: feat/mail-v3-f4

## ✅ Completati
[AC 1-20 con note]

## ⚠️ Incompleti o skipped
[se applicabile]

## 🤖 Decisioni autonome
[lista]

## 📁 File modificati/creati
[breakdown]

## 📝 Commits
[hash + subject]

## 🚀 Raccomandazioni F5
- Smart Snooze
- Undo send
- Scheduled send
- Dark mode
```

---

## 10. Ordine esecuzione

1. `git checkout -b feat/mail-v3-f4`
2. Leggi spec + report precedenti
3. §3.1 Sidebar SX restyling (1h) — questo è il visual più impattante, farlo subito
4. §3.2 Layout proportions (0.3h)
5. **COMMIT + PUSH**
6. §3.3 NBA block sidebar 360 (0.5h)
7. §3.4 Reply Assistant AI (1h)
8. **COMMIT + PUSH**
9. §3.5 HtmlField compose wizard (0.5h)
10. §3.6 Keyboard shortcuts (0.3h)
11. §3.7 Full-text search (0.5h)
12. **COMMIT + PUSH**
13. §3.8 Drag & drop (0.3h)
14. §3.9 Note private (0.3h)
15. Manifest bump 18.0.8.3.0
16. docs/report_f4.md
17. **COMMIT + PUSH FINALE**

**Totale: ~4 ore in autonomia.**

---

## 11. Una cosa sola

> L'obiettivo di F4 è trasformare il client da "funziona" a "è un piacere usarlo".
>
> La sidebar SX compatta + Reading pane allargato + NBA sticky + Risposta Guidata sono i 4 cambiamenti che il team sentirà di più.
>
> Il resto (shortcuts, search, D&D, note) sono quick wins che rendono la UX completa.
>
> **MAI fermarti. 4 regole. Vai.**
