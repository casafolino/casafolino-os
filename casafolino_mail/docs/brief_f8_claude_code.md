# Brief F8 — Composer Outlook-style + Template WYSIWYG

**Formato:** GSD — **MODALITÀ AUTONOMA TOTALE**
**Owner:** Antonio Folino
**Base:** `fix/mail-v3-f7` (18.0.8.6.0, live in prod 20/04/2026)
**Target:** `casafolino_mail` 18.0.8.6.0 → 18.0.8.7.0
**Branch:** `feat/mail-v3-f8` (da `fix/mail-v3-f7`)
**Tempo stimato:** 7-9 ore autonome
**Tipo:** Composer UX + Template management
**Prev brief:** F2, F2.1, F3, F4, F5, F6, F6.5, F7

---

## 🚀 COME LANCIARE

**Sul Mac (terminale nuovo):**

```bash
cd ~/casafolino-os
git fetch --all
git checkout fix/mail-v3-f7
git pull
claude --dangerously-skip-permissions
```

Poi dentro Code incolla tutto il brief e scrivi "Vai".

---

## ⚠️ 4 REGOLE CRITICHE

1. **MAI fermarsi** — eccezioni: data loss prod, credenziali mancanti, architettura ambigua
2. **Defaults automatici**: naming `mv3_`, IT pro, emoji FA5, pattern esistenti, skip+annota bug pre-esistenti
3. **Auto-escape 60 min** → commit `wip`, skip, avanti
4. **Commit ogni task + push ogni 3-4 commit**

---

## 1. Obiettivo

**Rendere il composer Mail V3 un vero strumento di produttività per il team CasaFolino.** Il team invia decine di email al giorno (buyer, importatori, distributori), in 3 lingue (IT/EN/DE), spesso con template personalizzati. Oggi il composer attuale è minimale (wizard transient Odoo base): toolbar povera, niente emoji, firma come allegato, template selector scomodo.

**Definition of Done:**

Josefina apre il composer. Vede una toolbar Outlook-style con bold/corsivo/link/liste/colore/allineamento visibili. Trascina un'immagine dal desktop → appare inline nel corpo email (non come allegato). Clicca 🙂 → emoji picker. Cambia template con 1 click dal selector a lato con preview live del risultato. La sua firma è già visibile in fondo all'email, modificabile direttamente. Ogni 15 secondi vede "Bozza salvata alle HH:MM" senza dover premere nulla. Quando scrive a un buyer tedesco, il template "Post-fair follow-up DE" è suggerito automaticamente in base al paese partner. Preview "come arriverà al destinatario" disponibile in 1 click.

---

## 2. Contesto da F7

F7 ha fixato i bug di rendering composer (bottoni Rispondi/Tutti/Inoltra/Scrivi ora aprono il wizard). Il wizard attuale (file: `casafolino_mail_compose_wizard.py`, view `mail_v3_compose_wizard_views.xml`) è la base su cui costruire.

**Cosa c'è oggi nel wizard:**
- `to`, `cc`, `bcc`, `subject`, `body_html` (HtmlField nativo Odoo)
- `attachment_ids` (many2many_binary per allegati D&D)
- `template_id` (M2O con dropdown) — prefill via `on_change`
- `signature_id` (M2O con dropdown) — append a body
- `scheduled_send_at` (opzionale)
- `is_scheduled` (Boolean)

**Cosa manca:**
- Toolbar rich editor (HtmlField Odoo default ha solo bold/italic/link)
- Emoji picker inline
- Template selector visibile (non dropdown)
- Preview template con dati partner reali
- Firma editabile inline (non append cieco)
- Inline image D&D nel corpo (non come allegato)
- Indicatore autosave visibile
- Template WYSIWYG editor (attualmente form HTML raw)
- Auto-detect lingua template dal paese partner
- Variabili `{{}}` ricche (attualmente 12, aumentare a 25+)

---

## 3. Scope IN — 8 deliverable

### PRIORITY 1 — Composer base Outlook-style (~3h)

### 3.1 Custom HtmlField toolbar rich (1.5h)

**Approccio**: Odoo 18 `HtmlField` usa Summernote/wysiwyg. È estendibile ma limitato. Per avere Outlook-style serve una toolbar custom più ricca.

**Opzione A (raccomandata)**: estendere il wysiwyg Odoo via `data-wysiwyg-toolbar` param, abilitando tutti i bottoni disponibili:
- Bold, Italic, Underline, Strikethrough
- Font size (selector 8-24pt)
- Font color + Background color
- Ordered list, Unordered list
- Indent increase/decrease
- Alignment (left, center, right, justify)
- Link insert
- Horizontal rule
- Remove format
- Undo/redo

**Opzione B (se A limitata)**: integrare **Quill.js** o **TinyMCE community** via assets bundle. Più potente ma più JS da mantenere.

Preferire A. Testare quali toolbar options sono disponibili. Se insufficienti, passare a B usando Quill.js (lightweight, 45KB).

**File da toccare:**
- `static/src/js/mail_v3/mail_v3_compose_wizard.js` (o file JS che gestisce il wizard)
- `views/mail_v3_compose_wizard_views.xml` → aggiornare `body_html` widget options
- `static/src/scss/mail_v3_composer.scss` → styling Outlook-style (padding, border, bg #fff, toolbar sticky top)

**Layout target (Outlook classic):**
```
┌─────────────────────────────────────────────┐
│ Toolbar: B I U S | font | color | list | …│  ← sticky top
├─────────────────────────────────────────────┤
│ To: ...                                     │
│ Cc: ...                                     │
│ Subject: ...                                │
├─────────────────────────────────────────────┤
│                                             │
│  [corpo email editabile]                    │
│                                             │
│  ---                                        │
│  [firma modificabile inline]                │
│                                             │
├─────────────────────────────────────────────┤
│ 📎 allegati inline                          │
│ [Invia] [Programma] [Bozza salvata HH:MM]  │
└─────────────────────────────────────────────┘
```

### 3.2 Emoji picker inline (0.5h)

**Libreria**: `emoji-mart` (React) oppure `@joeattardi/emoji-button` (vanilla JS, lightweight ~50KB).

Preferire `@joeattardi/emoji-button` per compatibilità con wizard Odoo (no React runtime).

**Implementazione:**
- Bottone 🙂 in toolbar (dopo il gruppo format)
- Click → apre popup con search + categorie
- Click su emoji → inserisce nel body alla posizione cursore
- Caricato lazy (solo quando cliccato)

**Assets**:
- `static/src/lib/emoji-button.min.js` (oppure CDN se permesso)
- Init nel JS wizard: `new EmojiButton({ position: 'bottom-start' })`

### 3.3 Inline image drag-drop (0.5h)

Attualmente D&D → allegato. Vogliamo D&D → inline image nel body.

**Approccio:**
1. Listener `drop` event sul body editor (HtmlField wysiwyg)
2. Se file è immagine (MIME `image/*`): convert a base64 data URL
3. Insert `<img src="data:image/png;base64,...">` alla posizione cursore
4. Mantieni D&D allegati per file non-image (PDF, Word, ecc.)

**Alternativa più robusta**: upload server → ottieni URL → insert `<img src="https://...">`. Evita body HTML pesanti. Richiede endpoint `/cf/mail/v3/upload_inline_image` che salva come `ir.attachment` e ritorna URL pubblico.

Scegliere alternativa robusta (upload server). Base64 inline rompe email troppo grosse.

### 3.4 Autosave indicatore visibile (0.5h)

Autosave già esiste (F5/F6 ha draft autosave cron 86). Va reso visibile.

**Implementazione:**
1. Debounce 15 secondi su ogni change di `body_html` / `subject` → salva via endpoint `/cf/mail/v3/draft/autosave`
2. UI label in basso a destra del composer: "Bozza salvata alle 14:32" (update ogni save)
3. Se save fallisce: "⚠ Errore salvataggio — retry"
4. Quando sta salvando: spinner + "Salvataggio..."

**File:**
- JS wizard: aggiungi debounce + XHR call + state `lastSaveTime`
- XML template: aggiungi div status indicator

---

### PRIORITY 2 — Template selector migliore (~2h)

### 3.5 Template selector visibile + preview live (1h)

Attualmente `template_id` è dropdown nel form. Vogliamo **panel laterale** con tutti i template visibili.

**Layout target:**
```
┌──────────────────┬────────────────────┐
│  TEMPLATE        │  COMPOSER          │
│                  │                    │
│  🇮🇹 Follow-up  │  [Toolbar rich]    │
│  🇮🇹 Offerta    │                    │
│  🇬🇧 Follow-up  │  To: ...           │
│  🇬🇧 Sample     │  Subject: ...      │
│  🇩🇪 Post-fair  │                    │
│  🇪🇸 ...        │  [Body]            │
│                  │                    │
│  + Nuovo         │  [Firma inline]    │
│                  │                    │
│  Filtro lingua   │  [Invia]           │
└──────────────────┴────────────────────┘
```

**UX flow:**
1. Panel laterale SX collapsible (default aperto quando composer nuovo, collapsed quando reply)
2. Hover su template → preview tooltip con primi 200 char del body renderizzato con dati partner
3. Click → applica template (prefill subject + body) + chiude panel automaticamente
4. Badge lingua (IT/EN/DE/ES/FR) + badge categoria
5. Search in alto: filter nome/subject/categoria

**Implementazione:**
- Nuovo componente OWL `MailV3TemplatePanel` in `static/src/js/mail_v3/`
- Endpoint `/cf/mail/v3/templates/list` ritorna template accessibili user + preview rendered
- Click template → JS chiama `render_template()` + aggiorna composer state

### 3.6 Auto-detect lingua template dal partner (0.5h)

Quando user apre composer per rispondere a un buyer tedesco, mostra prima i template `language='de_DE'`.

**Logica:**
1. Leggi `partner.country_id.code` (DE, AT, CH → tedesco; FR, BE, CA → francese; ES, MX → spagnolo; IT, SM → italiano; default EN)
2. Apri template panel con filter pre-selezionato su lingua rilevata
3. Badge "Suggerito per questo contatto" sul template top-match (stessa lingua + categoria post-fair se thread ha keyword fair)

Mappa codici paese → lingua (hardcoded, helper nel model):

```python
COUNTRY_TO_LANG = {
    'IT': 'it_IT', 'SM': 'it_IT', 'VA': 'it_IT',
    'DE': 'de_DE', 'AT': 'de_DE', 'CH': 'de_DE', 'LI': 'de_DE',
    'ES': 'es_ES', 'MX': 'es_ES', 'AR': 'es_ES', 'CL': 'es_ES', 'CO': 'es_ES', 'PE': 'es_ES',
    'FR': 'fr_FR', 'BE': 'fr_FR', 'LU': 'fr_FR', 'MC': 'fr_FR', 'CA': 'fr_FR',
}
# Default: en_US
```

### 3.7 Preview template con dati partner reali (0.5h)

Nel panel laterale, hover template → tooltip con body renderizzato.

Nel composer, dopo applicazione template, badge "👁 Anteprima finale" in alto → apre modal con:
- Subject finale (variabili sostituite)
- Body finale renderizzato
- Destinatario simulato (To: + From: + firma reale)

Endpoint: `/cf/mail/v3/template/<id>/preview?partner_id=X&thread_id=Y` ritorna `{subject, body_html}` già renderizzato.

---

### PRIORITY 3 — Template management avanzato (~2h)

### 3.8 Template WYSIWYG editor + più template + più variabili (2h)

**Parte 1 — Editor WYSIWYG template form (0.5h):**
Attualmente `casafolino_mail_template.body_html` è HtmlField standard. Usiamo stesso toolbar rich della Sezione 3.1.

**Parte 2 — Più variabili (0.5h):**
Aggiungere al `render_template()` queste 15 variabili extra (totale 25+):
```
# Partner extra
{{partner_full_address}}  # via + city + country
{{partner_vat}}
{{partner_company_type}}

# Sales extra  
{{total_orders_ytd}}  # conteggio ordini anno corrente
{{total_revenue_ytd}}  # valore €
{{top_product}}  # prodotto più ordinato

# Thread extra
{{thread_message_count}}
{{thread_first_email_date}}
{{thread_attachment_count}}

# Account extra
{{account_email}}  # account email mittente
{{account_signature_name}}  # nome firma utente corrente

# Utilities
{{current_season}}  # primavera/estate/autunno/inverno
{{months_since_last_contact}}
{{partner_time_zone}}
{{account_manager_name}}  # assegnatario CRM del partner, se presente
```

**Parte 3 — 10 template preconfigurati in più (1h):**

Oltre ai 6 esistenti, aggiungere 10 template default via migration 18.0.8.7.0:

1. **IT — "Invio listino prodotti"** (cat: quote)
2. **IT — "Conferma ordine e spedizione"** (cat: follow_up)
3. **EN — "Price list shipment"** (cat: quote)
4. **EN — "Order confirmation"** (cat: follow_up)
5. **EN — "Sample follow-up after 2 weeks"** (cat: follow_up)
6. **DE — "Musteranfrage Follow-up"** (cat: follow_up)
7. **DE — "Preisliste"** (cat: quote)
8. **ES — "Envío de catálogo"** (cat: quote)
9. **ES — "Seguimiento post-feria"** (cat: post_fair)
10. **FR — "Envoi catalogue"** (cat: quote)

Body HTML con variabili ricche delle Parti 2 sopra.

---

### 3.9 Report f8.md (0.3h)

Template standard + sezioni:
- Feature composer Outlook-style
- Feature template management
- Nuove variabili disponibili
- 10 template default aggiunti
- AC coverage
- Raccomandazioni F9 (WhatsApp, Calendar, Multi-lingua UI switcher, Voice-to-text)

---

## 4. Scope OUT

- ❌ NO modifiche backend intelligence engine
- ❌ NO toccare cron 82-96 (appena stabilizzati in F7)
- ❌ NO modifiche modelli F6 (lead_rule, followup_rule)
- ❌ NO Groq/AI reply changes (F7 ha sistemato)
- ❌ NO WhatsApp/Calendar integration (F9+)
- ❌ NO multi-lingua UI switcher (IT/EN/DE per label UI — F9)
- ❌ NO rifare composer da zero (estendere il wizard transient esistente)

---

## 5. Vincoli Odoo 18

1. `HtmlField` options via `widget="html" options="{...}"`
2. OWL component `static props = ["*"]`
3. Wysiwyg toolbar custom tramite `data-wysiwyg-toolbar` attribute o JS override
4. Inline images: preferire URL server (endpoint upload) vs base64
5. Emoji picker: libreria vanilla JS, no React runtime separato
6. No `attrs=`, sì `invisible=domain`
7. No `<tree>`, sì `<list>`

---

## 6. Acceptance Criteria (18 AC)

### Composer UX
- **AC1** Module 18.0.8.6.0 → 18.0.8.7.0 senza ERROR
- **AC2** Toolbar composer mostra: B / I / U / S / font-size / color / bg-color / list ordered / list unordered / indent / align / link / undo
- **AC3** Click 🙂 in toolbar apre emoji picker
- **AC4** Select emoji inserisce carattere a posizione cursore
- **AC5** Drag immagine dal desktop su body → insert inline (img tag), non attachment
- **AC6** Drag file non-immagine (PDF, Word) → finisce in attachments (comportamento attuale)
- **AC7** Firma visibile inline a fondo body, editabile, non è più append cieco
- **AC8** Indicatore "Bozza salvata alle HH:MM" visibile in basso, updated ogni 15s

### Template selector
- **AC9** Panel laterale SX mostra lista template, collapsible
- **AC10** Hover template → tooltip preview body renderizzato
- **AC11** Click template → applica a composer, closes panel
- **AC12** Search bar filtra template per nome/categoria/lingua
- **AC13** Badge lingua + categoria visibili
- **AC14** Auto-detect lingua: apri composer per partner DE → template de_DE in cima
- **AC15** Bottone 👁 Anteprima finale → modal con subject + body renderizzato + from/to simulati

### Template management
- **AC16** Form template usa WYSIWYG toolbar (come composer)
- **AC17** 15 variabili nuove disponibili (testabili con 1 template demo)
- **AC18** 10 template nuovi precaricati via migration

---

## 7. Deploy path

**Sul Mac**:
```bash
cd ~/casafolino-os && git push origin feat/mail-v3-f8
```

**Sul server EC2 (ssh ubuntu@51.44.170.55)**:

**STAGE FIRST**:
```bash
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo -Fc folinofood_stage > /tmp/stage_pre_f8_$(date +%Y%m%d_%H%M%S).dump && \
cd /home/ubuntu/casafolino-os && \
git fetch --all && \
git checkout feat/mail-v3-f8 && \
git pull && \
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tee /tmp/f8_stage.log | tail -80 && \
grep -E "ERROR|CRITICAL|Traceback" /tmp/f8_stage.log
```

**PROD solo se stage OK**:
```bash
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo -Fc folinofood > /tmp/prod_pre_f8_$(date +%Y%m%d_%H%M%S).dump && \
docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http 2>&1 | tee /tmp/f8_prod.log | tail -80 && \
grep -E "ERROR|CRITICAL|Traceback" /tmp/f8_prod.log && \
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "DELETE FROM ir_attachment WHERE name LIKE '%web.assets%';" && \
docker restart odoo-app && \
sleep 30 && \
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "SELECT name, latest_version, state FROM ir_module_module WHERE name='casafolino_mail';"
```

Expected: `18.0.8.7.0 installed`.

---

## 8. Git workflow

Branch: `feat/mail-v3-f8` da `fix/mail-v3-f7`.

Commits atomici:
```
feat(mail-v3): composer Outlook-style rich toolbar
feat(mail-v3): emoji picker inline in composer
feat(mail-v3): inline image drag-drop via server upload
feat(mail-v3): autosave indicator visible in composer
--- PUSH BATCH 1 ---
feat(mail-v3): template selector panel + preview live
feat(mail-v3): template auto-detect language from partner country
feat(mail-v3): template preview modal with rendered data
--- PUSH BATCH 2 ---
feat(mail-v3): template form WYSIWYG editor
feat(mail-v3): 15 new template variables
feat(mail-v3): 10 new default templates (IT/EN/DE/ES/FR)
chore(mail-v3): manifest bump 18.0.8.7.0 + migration
docs(mail-v3): F8 report
```

Push dopo batch 1 (composer base), batch 2 (template selector), e finale.

---

## 9. Ordine esecuzione

1. `git checkout -b feat/mail-v3-f8 fix/mail-v3-f7`
2. Leggi brief + report_f7.md
3. **§3.1** Toolbar rich → commit
4. **§3.2** Emoji picker → commit
5. **§3.3** Inline image upload → commit
6. **§3.4** Autosave indicator → commit
7. **PUSH BATCH 1**
8. **§3.5** Template panel + preview → commit
9. **§3.6** Auto-detect lingua → commit
10. **§3.7** Preview modal → commit
11. **PUSH BATCH 2**
12. **§3.8 Parte 1** Template WYSIWYG → commit
13. **§3.8 Parte 2** 15 variabili nuove → commit
14. **§3.8 Parte 3** 10 template default (migration) → commit
15. Manifest bump 18.0.8.7.0
16. **§3.9** report_f8.md
17. **PUSH FINALE**

**Totale: ~7-9h autonome.**

---

## 10. Una cosa sola

> F8 trasforma il composer da "wizard Odoo minimale" in "strumento di vita quotidiana" per Josefina, Martina, Maria. Il team invia 40-60 email al giorno. Ogni secondo risparmiato per email = 40 minuti al giorno restituiti al business.
>
> Outlook-style è la metafora familiare. Template WYSIWYG + auto-detect lingua è il moltiplicatore. Preview live evita figuracce con buyer.
>
> MAI fermarti. 4 regole. Vai.
