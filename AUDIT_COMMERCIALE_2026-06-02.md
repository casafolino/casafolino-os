# AUDIT COMMERCIALE — CasaFolino OS
**Data:** 2026-06-02  
**Scope:** CRM, Pipeline, Mail, Campionatura, Fiere, Anagrafiche, Intelligence  
**Tipo:** Read-only audit — baseline per restyling grafico/funzionale  
**Tesi guida:** Pipeline come spina dorsale, mail come azione di fase, partner come pivot ("lens not container")

---

## A. Mappa Moduli

| Modulo | Versione (installed) | Cosa fa | Stato |
|--------|---------------------|---------|-------|
| **casafolino_crm_export** | 18.0.12.3.0 | CRM Export B2B: scoring, rotting, campionature, fiere, card scanner AI, dossier template, list/kanban enriched, compose F8 | **Core — application** |
| **casafolino_mail** | 18.0.19.0.0 | Mail CRM: fetch RAW IMAP → classificazione AI (Groq) → message + cartelle + mass actions + multi-utente, V3 OWL client, compose wizard, snippet, posizionatore, inbox selector | **Core — application** |
| **casafolino_pipeline_control** | 18.0.1.17.0 | Sala Controllo export: follow-up, inbox commerciale, pipeline dashboard, dossier — OWL dashboard unica | **Core — application** |
| **casafolino_initiative** | 18.0.1.0.1 | Iniziative: orchestrazione oggetti (famiglie, atomi, varianti, template, tag campagna) cross-modulo | **Core — application** |
| **casafolino_initiative_dashboard** | 18.0.4.3.1 | Lavagna cockpit OWL: KPI rail, kanban, pannelli mail/todo/activity/calendar, drawer task, timeline | Attivo |
| **casafolino_mail_stats** | 18.0.0.1.0 | Tracking aperture/click/bounce/reply, engagement badge, auto-activity hot leads | Attivo |
| **casafolino_mail_templates** | 18.0.0.1.0 | Template email centralizzati: tag, snippet, wizard fiera | Attivo |
| **casafolino_fair_report** | 18.0.0.1.0 | Report HTML fine fiera: dashboard metriche, engagement, action items | Attivo |
| **casafolino_followup_tuttofood** | 18.0.1.0.0 | Template follow-up Tuttofood 2026 (IT/EN/FR/ES) | Attivo — specifico fiera |
| **casafolino_labels** | 18.0.1.0.0 | Pipeline gestione etichette prodotti | Attivo — application |
| **casafolino_commercial** | 18.0.2.4.1 | GDO, Private Label, Tesoreria, Blocchi Documento — 4 OWL dashboard tesoreria | Attivo — application |
| **casafolino_kpi** | 18.0.1.0.0 | Dashboard KPI unificata (OWL) | Attivo — application |
| **casafolino_voice_ai** | 18.0.8.0.0 | Agenti vocali AI: centralino + follow-up, PBX, consent, outbound queue | Attivo — application |
| **casafolino_crm_360** | 18.0.1.0.0 | (Installato in DB, manifest non trovato nel repo — potenziale modulo legacy o rimosso dal codice) | **Da verificare** |
| **casafolino_project** | 18.0.1.1.0 | Estensione project (checklist, shipment, contact, template) | Attivo |
| **casafolino_workspace** | 18.0.0.7.0 | Config workspace multi-utente | Attivo |
| **casafolino_home** | 18.0.2.4.0 | Scrivanie (commerciale/admin/operativa) | Attivo |

**Totale moduli casafolino installati:** 29 (di cui ~12 nello scope commerciale diretto)

---

## B. Pipeline as-is

### B.1 Stadi CRM

| # | Stage | Seq | is_won | fold | Lead attivi |
|---|-------|-----|--------|------|-------------|
| 15 | Primo Contatto | 10 | No | No | **333** |
| 16 | Interesse | 20 | No | No | 52 |
| 17 | Trattativa | 30 | No | No | 2 |
| 18 | Preventivo | 40 | No | No | 1 |
| 19 | Campionatura | 50 | No | No | 11 |
| 20 | Negoziazione | 60 | No | No | 20 |
| 21 | Vinta | 70 | **Sì** | Sì | 26 |
| 22 | Persa | 80 | No | Sì | 11 |
| 23 | Standby | 90 | No | Sì | 5 |

**Totale lead attivi:** 461  
**Lead senza partner_id:** 45 (9.8%)  
**Lead senza stage:** 0

### B.2 Campi custom su crm.lead

| Campo | Tipo | Stato |
|-------|------|-------|
| `cf_lead_score` | Integer (0-100, computed) | **Quasi vuoto** — solo 1 lead ha score > 0 (avg=15). Formula esiste ma non popola |
| `cf_rotting_days` | Integer (computed) | Tutti "ok" — nessun lead in warning/danger/dead. Soglie implementate ma inefficaci |
| `cf_rotting_state` | Selection (ok/warning/danger/dead) | 461 lead = "ok". Rotting attivo ma probabilmente thresholds troppo alte |
| `cf_forecast_value` | Float (expected_revenue × probability / 100) | Implementato e stored |
| `cf_date_last_contact` / `cf_date_next_followup` | Date | Follow-up tracking presente |
| `cf_fair_id` | M2O → cf.export.fair | Link fiera |
| `cf_initiative_id` | M2O → cf.initiative | Link iniziativa |
| `cf_project_id` | M2O → project.project | Link dossier |
| `cf_mail_thread_id` | M2O → casafolino.mail.thread | Link thread mail |
| `cf_language` | Char | Lingua lead |
| `cf_auto_created` | Boolean | Flag creazione automatica |
| `cf_mail_lead_rule_id` | M2O | Regola mail che ha creato il lead |
| `casafolino_days_since_last_activity` | Integer | Giorni da ultima attività |

### B.3 Cosa manca vs visione "pipeline as backbone"

- **Scoring inefficace:** formula esiste, ma 1 solo lead ha score. Nessun cron di ricalcolo periodico visibile.
- **Rotting non discrimina:** tutti "ok" — soglie da ricalibrare o logica compute da forzare.
- **SLA per fase:** non esiste. Nessun campo "giorni massimi in fase" o "data scadenza fase".
- **Stage evolution log:** non presente (no tabella di storico cambi fase).
- **Automazioni di fase:** auto-standby esiste (cron 125), ma nessuna promozione automatica di fase.
- **72% dei lead sono in "Primo Contatto"** — imbuto molto largo, possibile accumulo non gestito.

---

## C. Mail as-is

### C.1 Account IMAP

| ID | Account | Tipo | Stato |
|----|---------|------|-------|
| 1 | Gmail (fetchmail_server) | IMAP | done |
| 3 | Gmail (fetchmail_server) | IMAP | draft (disabilitato) |

**Account casafolino_mail_account attivi:** 2 (Antonio Folino, Martina Sinopoli)  
**Fetchmail nativo Odoo:** disabilitato (cron 6 = OFF) — sostituito dal sistema custom

### C.2 Cron Mail (attivi)

| ID | Cron | Frequenza | Stato |
|----|------|-----------|-------|
| 82 | **Mail Sync V2** | 5 min | ATTIVO — fetch principale |
| 84 | **AI Classify** | 5 min | ATTIVO — classificazione Groq |
| 83 | **Silent Partners** | 1/giorno | ATTIVO — partner silenti |
| 85 | Body Fetch Pending | 10 min | ATTIVO |
| 110 | Triage RAW | 5 min | ATTIVO |
| 111 | Cleanup RAW | 1/giorno | ATTIVO |
| 117 | Cleanup Trash | 1/giorno | ATTIVO |
| 118 | Cleanup Mass Action Logs | 30 min | ATTIVO |
| 119 | Send Scheduled Drafts | 5 min | ATTIVO |
| 123 | Mail Stats: Rebuild Engagement Cache | 15 min | ATTIVO |
| 124 | Mail Stats: Auto-Activity Hot Leads | 1/ora | ATTIVO |
| 125 | Auto-Standby Lead inattivi | 1/giorno | ATTIVO |
| 138 | AI suggestion mail | 5 min | ATTIVO |
| 139 | Accuracy refresh mail AI | 1/giorno | ATTIVO |
| 99 | Digest Mittenti Fuori-CRM | 1/settimana | ATTIVO |

**Cron backfill partner disabilitati:** ~40+ (proliferazione per partner 5012 e 99373 — debito tecnico)

### C.3 Classificazione AI

**Motore:** Groq (via `cf_gemini_client.py` — nome legacy, usa Groq)  
**Categorie AI attive su casafolino_mail_message:**

| Categoria | Count |
|-----------|-------|
| commerciale | 730 |
| admin | 63 |
| interno | 38 |
| fornitore | 12 |
| newsletter | 6 |
| spam | 4 |
| personale | 3 |

**Campi AI su casafolino_mail_message:** `ai_category`, `ai_sentiment`, `ai_urgency`, `ai_language`, `ai_action_required`, `ai_classified_at`, `ai_raw_response`, `ai_error`, `cf_ai_confidence`, `cf_ai_confidence_band`, `cf_ai_processed`, `cf_ai_reasoning`, `intent_detected`

**Totale messaggi classificati:** 856/1841 (46.5%)  
**Messaggi RAW pendenti:** 29

### C.4 Composer F8

- **ComposeWizardDialog:** dialog OWL standalone, richiamabile da qualsiasi modulo.
- **Funzionalità:** pre-fill to/subject/body, lookup account utente, AI panel, snippet picker.
- **Bottoni-azione di fase:** NON presenti. Il composer è generico (invio libero). Non esistono bottoni tipo "Richiedi Anagrafica", "Invia Listino", "Sollecito", "Invia Preventivo" legati alla fase del lead.
- **AI Reply Assistant:** presente (`mail_v3_reply_assistant.js`) — suggerimenti risposta AI.
- **AI Suggestion cron:** attivo (cron 138, ogni 5 min).

### C.5 Cartelle Mail

6 cartelle × 3 account = 18 record: Inbox, Da smistare, Inviate, Archivio, Cestino, Spam

### C.6 Struttura dati mail

**Due modelli mail coesistono:**
- `casafolino.mail.message` (56 colonne) — modello principale V2/V3, con AI, threading, tracking
- `cf.mail.message` (26 colonne) — modello legacy semplificato, probabilmente V1

### C.7 Funzionalità mail avanzate

| Feature | Stato |
|---------|-------|
| Thread raggruppamento | ESISTE (`casafolino_mail_thread`, 684 thread) |
| Sender decision (dismiss/accept) | ESISTE |
| Autoresponder | ESISTE (tabella) |
| Blacklist | ESISTE |
| Snooze | ESISTE |
| Draft scheduled | ESISTE |
| Mass actions + log | ESISTE |
| Outbox | ESISTE |
| Lead rules (auto-assign) | ESISTE |
| Folder rules | ESISTE |
| SLA partner | ESISTE |
| Orphan partner detection | ESISTE |
| Partner intelligence | ESISTE |
| Response metric | ESISTE |
| Engagement tracking | ESISTE (casafolino_mail_engagement) |
| Snippet clipboard | ESISTE |

---

## D. Campionatura as-is

### D.1 Modello

**`cf.export.sample`** — modello dedicato con:
- Stage pipeline propria (7 stadi: Richiesta Ricevuta → In Preparazione → Spedita → Consegnata → In Valutazione → Feedback Positivo/Negativo)
- Link a `crm.lead` (`lead_id`), `res.partner`, `project.project`, `sale.order`
- Tracciamento: tracking_number, carrier_name, shipping_cost, date_sent/delivered/feedback
- Feedback: feedback_score, feedback_notes, customer_requirements
- Sequenza automatica (`cf.export.sample` sequence)

### D.2 Dati live

| Metrica | Valore |
|---------|--------|
| Totale campioni | 5 |
| Con lead collegato | 5/5 |
| Con progetto/dossier | 0/5 |
| Con tracking spedizione | 0/5 |

### D.3 Gap

- **Collegamento a pipeline:** ESISTE via `lead_id`, ma solo 5 campioni creati.
- **Spedizioni:** modello ha campo tracking ma via `sale_order.picking_ids` (indiretto). Nessuna integrazione diretta con `stock.picking` per campioni.
- **`cf_sample_request`:** esiste un modello separato in `casafolino_initiative_dashboard` — possibile duplicazione con `cf.export.sample`.
- **Stage "Campionatura" nella pipeline CRM:** presente (11 lead), ma non c'è automazione che crei automaticamente un campione quando il lead entra in fase Campionatura.

---

## E. Anagrafiche

### E.1 Numeri

| Metrica | Valore |
|---------|--------|
| Partner attivi totali | 14.500 |
| Aziende (is_company) | 976 |
| Contatti con parent | 333 |
| Partner con mail in hub | 125 |

### E.2 Duplicati potenziali

**Per email domain (aziende):**

| Domain | Aziende duplicate |
|--------|-------------------|
| gmail.com | 35 |
| libero.it | 6 |
| degustabox.com | 4 |
| hotmail.it | 3 |
| + 8 domini con 2 duplicati | |

**Per P.IVA:**

| P.IVA | Duplicati | Note |
|-------|-----------|------|
| `/` | 28 | Placeholder |
| `\` | 22 | Placeholder |
| IT03783120797 | 6 | CasaFolino stessa |
| ESB65894008 | 5 | |
| ATU78172745 | 5 | |
| OO99999999999 | 4 | Placeholder |
| 03783120797 | 4 | Stessa P.IVA senza prefisso |
| + 13 P.IVA con 2-3 duplicati | | |

**Per telefono:** 465 gruppi di telefoni duplicati (pulizia significativa necessaria)

### E.3 Dedup/Match esistente

- **Orphan partner detection:** ESISTE (`casafolino_mail_orphan_partner`) — rileva partner senza lead.
- **Partner intelligence:** ESISTE (`casafolino_partner_intelligence` + `feedback`) — ma non dedup.
- **Merge partner automatico:** NON ESISTE. Nessuna logica di dedup automatica trovata nel codice.
- **Validazione P.IVA:** NON ESISTE. I placeholder `/`, `\`, `OO99999999999` indicano assenza di validazione.

---

## F. Intelligence

| Feature | Stato | Note |
|---------|-------|------|
| **Forecast pesato** | ESISTE | `cf_forecast_value` = revenue × probability/100. Stored, computed. |
| **Lead scoring** | PARZIALE | Formula esiste (`_compute_cf_lead_score`), ma 1 solo lead ha score. Non ricalcolato. |
| **Rotting/stagnant detection** | PARZIALE | Campi e compute presenti, ma tutti "ok". Soglie da calibrare. |
| **Stage evolution dashboard** | NON ESISTE | Nessun log storico cambio stage. Nessuna dashboard evoluzione. |
| **Mail stats settimanali** | PARZIALE | Engagement cache rebuild ogni 15min + digest mittenti fuori-CRM settimanale. Ma nessun report settimanale aggregato visibile. |
| **Pipeline control dashboard** | ESISTE | OWL dashboard con KPI, lane, inbox, follow-up, post-fiera, dossier. Maturo. |
| **Lavagna/cockpit iniziative** | ESISTE | OWL complessa: KPI rail, kanban, mail panel, todo, calendar, timeline. |
| **KPI Dashboard generale** | ESISTE | `casafolino_kpi` — dashboard OWL separata. |
| **AI suggestion mail** | ESISTE | Cron attivo ogni 5min, suggerimenti AI per risposte. |
| **Auto-standby lead inattivi** | ESISTE | Cron giornaliero (125). |
| **Auto-activity hot leads** | ESISTE | Cron orario (124) — crea attività per lead caldi. |
| **Partner intelligence** | ESISTE | Tabella con feedback. |

---

## G. Fiere

### G.1 Modelli

**Due modelli fiera coesistono:**

1. **`cf.export.fair`** (in `casafolino_crm_export`): id, name, date_start, date_end, state, budget, location, country_id, notes
2. **`casafolino.fiera`** (in `casafolino_fair_report`): name, date_start, date_end, status, location, expected_visitors, tag_id, category_id, description, report_recipients, last_report_sent

### G.2 Dati live

| Fiera | Date | Stato | Budget | Location |
|-------|------|-------|--------|----------|
| TUTTOFOOD Milano 2026 | 11-14 Mag 2026 | followup | — | Fiera Milano Rho |

### G.3 Funzionalità fiere

| Feature | Stato |
|---------|-------|
| Registrazione rapida lead (card scanner AI) | ESISTE — OWL widget con OCR/AI per biglietti visita, crea partner+lead+tag fiera |
| Template mail per fiera (IT/EN/FR/ES) | ESISTE — mail_template_sial_*, mail_template_tuttofood_* |
| Fair mail template con cartelle | ESISTE — `cf.fair.mail.template` + folder |
| Wizard template fiera | ESISTE — `mail_template_fair_wizard` |
| Plan fair follow-up wizard | ESISTE — `cf_pipeline_plan_fair_followup_wizard` |
| Fair report HTML (dashboard metriche) | ESISTE — `casafolino_fair_report` + wizard |
| Dashboard ROI fiera | NON ESISTE — nessun calcolo ROI (costi vs ricavi generati da lead fiera) |
| Post-fair pipeline | ESISTE — vista "post_fair" nella pipeline control dashboard |

### G.4 Gap fiere

- **Due modelli fiera** = frammentazione. `cf.export.fair` (operativo) e `casafolino.fiera` (reporting) non collegati.
- **ROI:** budget c'è su `cf.export.fair`, ma nessun calcolo revenue dei lead generati.
- **Registrazione rapida:** funziona ma hardcodata su SIAL Montreal (tag/source hardcoded in `card_scanner.py`).

---

## H. Debito Tecnico

### H.1 Violazioni Odoo 18

| Violazione | Occorrenze | Criticità |
|-----------|-----------|-----------|
| `attrs=` (deprecato Odoo 17+) | **0** | OK |
| `<tree>` (deprecato → `<list>`) | **0** | OK |
| `useService("user")` (pattern errato OWL) | **0** | OK — usa `import { user }` corretto |
| `position="replace"` su `//sheet/group` | **1** (`casafolino_crm_export/views/project_project_views.xml:134`) | WARNING — fragile, può rompere con aggiornamenti Odoo |
| OWL `props = ["*"]` (catch-all) | **~30 componenti** | INFO — funziona ma non tipizza le props |
| Cron via XML | Presenti, ma pattern corretto per Odoo 18 | OK |

### H.2 Problemi architetturali

| Problema | Criticità | Dettaglio |
|----------|-----------|-----------|
| **Backfill cron proliferation** | ALTA | 40+ cron "Backfill mail partner" creati one-shot e mai puliti (disabilitati ma in tabella) |
| **Due modelli mail coesistenti** | MEDIA | `casafolino.mail.message` (V2/V3) e `cf.mail.message` (V1) — possibile confusione |
| **Due modelli fiera** | MEDIA | `cf.export.fair` e `casafolino.fiera` — non collegati |
| **`casafolino_crm_360` fantasma** | MEDIA | Installato in DB ma manifest non nel repo — modulo orfano |
| **Card scanner hardcoded** | BASSA | Tag SIAL e source hardcoded in `card_scanner.py` |
| **cf_gemini_client.py naming** | BASSA | Nome suggerisce Gemini ma usa Groq — confuso |
| **Duplicate Voice AI cron** | BASSA | Cron 149 e 150 identici ("process outbound queue") |
| **P.IVA senza validazione** | MEDIA | `/`, `\`, `OO99999999999` come placeholder — nessun constraint |

### H.3 Codice pulito rispetto a Odoo 18

Il codice è **generalmente conforme** a Odoo 18:
- Nessun `attrs=` deprecato
- Nessun `<tree>` → usa `<list>` correttamente  
- OWL components usano `import { user }` anziché `useService("user")`
- Props dichiarate (anche se con catch-all `["*"]`)

---

## I. GAP ANALYSIS — 14 Mockup

> Nota: i 14 mockup sono riferiti per numero come da brief di restyling.

| # | Mockup | Stato | Note |
|---|--------|-------|------|
| 1 | **Pipeline Kanban enriched** | PARZIALE | Kanban esiste con CSS enriched + widget OWL (card_title, signals_badges, stage_progress, owner_avatar). Manca: colori per rotting/score, SLA visuale, quick-actions di fase |
| 2 | **Pipeline List enriched** | PARZIALE | List view con widget custom esiste. Manca: inline editing, bulk stage change, heatmap days-in-stage |
| 3 | **Lead form 360** | PARZIALE | Form con mail thread, dossier link, fair link, initiative link. Manca: timeline laterale, panel mail integrato, action buttons di fase |
| 4 | **Composer F8 con azioni di fase** | PARZIALE | Composer F8 esiste e funziona. Manca: bottoni-azione di fase (richiedi anagrafica / listino / sollecito / preventivo) |
| 5 | **Inbox commerciale (Mail V3)** | ESISTE | Client OWL completo: sidebar, thread list, reading pane, compose, 360 sidebar, analytics, notifications, folder sidebar |
| 6 | **Partner 360 lens** | PARZIALE | Partner ha mail tracking views, intelligence. Manca: vista unificata "lens" con timeline, score, engagement, deals |
| 7 | **Campionatura pipeline** | PARZIALE | Modello e stage esistono. Manca: kanban visuale, automazione lead→campione, integrazione picking diretta |
| 8 | **Dossier/progetto export** | ESISTE | 93 dossier attivi, 67 campi cf_* su project.project. Dashboard pipeline_control con dossier. Molto maturo |
| 9 | **Fair management** | PARZIALE | Card scanner, template, follow-up wizard, report. Manca: ROI, modello unificato, configurazione dinamica (non hardcoded) |
| 10 | **Stage evolution dashboard** | DA COSTRUIRE | Nessun log storico, nessuna dashboard evoluzione stage, nessun grafico velocità pipeline |
| 11 | **Forecast dashboard** | PARZIALE | Campo `cf_forecast_value` stored. Manca: dashboard dedicata con grafici, proiezioni, confronto periodi |
| 12 | **Mail analytics/stats** | PARZIALE | Engagement badge, cache rebuild, auto-activity. Manca: dashboard aggregata con trend, response time, conversion |
| 13 | **Stagnant/rotting alert** | PARZIALE | Campi e compute presenti. Manca: calibrazione soglie, notifiche, dashboard stagnanti, escalation |
| 14 | **Weekly digest commerciale** | PARZIALE | Digest mittenti fuori-CRM settimanale esiste. Manca: digest completo con KPI, pipeline movement, action items |

**Riepilogo:**

| Stato | Count |
|-------|-------|
| ESISTE | 2 |
| PARZIALE | 10 |
| DA COSTRUIRE | 2 |

---

## J. Raccomandazione Architetturale

### Opzione A: Refactor su moduli esistenti

**Pro:**
- Nessuna migrazione dati
- Continuità operativa
- Meno rischio di regressione
- I moduli core (casafolino_mail, casafolino_crm_export, casafolino_pipeline_control) sono maturi e funzionanti

**Contro:**
- 12+ moduli da coordinare per ogni feature cross-cutting
- Dipendenze circolari già presenti (mail_stats → crm_export → mail)
- Due modelli mail, due modelli fiera = frammentazione che peggiorerà

### Opzione B: Nuovo modulo `casafolino_sales_cockpit`

**Pro:**
- Unifica la visione "pipeline as backbone"
- Entry point unico per il restyling UI
- Può consolidare: stage evolution log, SLA, action buttons, forecast dashboard, stagnant alerts
- Non richiede di toccare i moduli data (mail, crm_export continuano a funzionare)

**Contro:**
- Ancora un modulo in più (N+1)
- Rischio di duplicare logica se non si fa refactor dei moduli sottostanti
- Richiede dipendenza da casafolino_crm_export + casafolino_mail + casafolino_pipeline_control

### Raccomandazione: **Approccio ibrido**

1. **Nuovo modulo `casafolino_sales_cockpit`** come UI layer unico per il restyling — contiene:
   - Stage evolution log (nuovo modello)
   - SLA per fase (configurazione)
   - Action buttons di fase per composer
   - Forecast dashboard
   - Stagnant dashboard
   - Weekly digest aggregato

2. **Refactor chirurgico** sui moduli esistenti:
   - Unificare `cf.export.fair` + `casafolino.fiera` → un solo modello
   - Deprecare `cf.mail.message` (V1) → migrare su `casafolino.mail.message`
   - Pulire 40+ cron backfill orfani
   - Verificare/rimuovere `casafolino_crm_360` dal DB
   - Ricalibrare soglie rotting e scoring
   - Rendere card scanner configurabile (non hardcoded SIAL)
   - Aggiungere constraint P.IVA

3. **NON toccare:**
   - casafolino_mail (V3 è maturo, 19 versioni di iterazione)
   - casafolino_pipeline_control (dashboard funzionante)
   - casafolino_initiative / dashboard (ecosistema complesso ma stabile)

**Rischi principali:**
- Il modulo cockpit diventa "yet another dashboard" se non assorbe pipeline_control
- Scoring e rotting richiedono dati storici che oggi non esistono (stage_log)
- La tesi "partner as lens" richiede un redesign profondo delle viste partner, non solo un modulo in più

---

*Report generato automaticamente tramite audit read-only su codebase e database di produzione.*
