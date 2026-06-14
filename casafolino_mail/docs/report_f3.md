# F3 Report — Intelligence Engine + Intent Detection + Async SMTP
Date: 2026-04-20
Branch: feat/mail-v3-f3 (from main)
Base version: 7.11.0 → 18.0.8.1.0

## Scope

F3 builds on main (v7.11.0), indipendente da F2/F2.1. Aggiunge intelligence engine, intent detection, IMAP flag sync bidirezionale, e async SMTP queue.

## Completati

### AC1: Partner Intelligence Model (NEW)
- `casafolino_partner_intelligence.py` — modello `casafolino.partner.intelligence`
- Hotness score 0-100 con 5 componenti: revenue (30%), activity (25%), pipeline (20%), freshness (15%), strategic boost (10%)
- Revenue: scala log su fatturato 12 mesi (1K→30, 10K→60, 50K→90, 100K+→100)
- Activity: email keep + ordini + activities ultimi 90 giorni
- Pipeline: max(stage_weight × probability) su lead aperti
- Freshness: interpolazione giorni dall'ultima email keep
- Strategic: boost da tag (GDO, DACH, ExportVIP → 100; Prospect → 70)
- Tier computed: hot (80+), warm (60-79), active (40-59), cold (20-39), dormant (<20)
- Pinned hot/ignore flags per override manuale

### AC2: NBA Engine — 20 regole + LLM fallback
- 20 regole business ordinate per priorita:
  - Critical (1-5): pagamento scaduto, reclamo senza risposta, lead stale hot, ordini pending, email urgente
  - High (6-10): partner caldo silente, riordino, follow-up fiera, nuovo contatto inattivo, action required
  - Medium (11-15): upsell top buyer, dormant reactivation, sentiment in calo, info mancanti, lead da qualificare
  - Low/Info (16-20): compleanno, 007 mancante, GDPR consent, review trimestrale, momentum positivo
- Ogni regola: condition_fn (lambda su context dict) + template italiano con placeholder
- LLM fallback via Groq (llama-3.3-70b) quando nessuna regola matcha
- Campi: nba_text, nba_urgency (critical/high/medium/low/info), nba_rule_id, nba_from_llm

### AC3: Intent Detection — keyword matcher IT/EN/DE
- Campo `intent_detected` su casafolino.mail.message (Selection, 11 valori)
- Intenti: request_quote, order, complaint, follow_up, intro, info_request, meeting_request, payment, shipping, thank_you, other
- Keyword matcher trilingue (IT/EN/DE) con ~8-10 keyword per intent per lingua
- Score-based: intent con piu keyword match vince
- Eseguito dopo AI classify nel fetch flow (non-blocking)

### AC4: IMAP Flag Sync bidirezionale
- `casafolino_mail_flag_sync.py` — modello abstract `casafolino.mail.flag.sync`
- Push: marca \Seen su IMAP per messaggi letti in Odoo (batch 200, per cartella)
- Pull: legge flag \Seen da IMAP per messaggi ultimi 7 giorni (batch 500)
- Campo `imap_flags_synced` su message model
- Config param `casafolino.mail.v3_sync_flags_enabled` (default False)
- Cron push ogni 5 min, pull ogni 10 min (disabilitati di default)

### AC5: Async SMTP Queue
- `casafolino_mail_outbox.py` — modello `casafolino.mail.outbox`
- API `queue_send()` per accodare email
- State machine: queued → sending → sent | error
- Retry automatico (3 tentativi max)
- MIME construction completa (HTML body, firma, allegati, In-Reply-To, References)
- IMAP APPEND a cartella Sent dopo invio
- Crea record casafolino.mail.message outbound per tracking
- Cron ogni 2 min (batch 20 email)
- Cleanup automatico sent >30 giorni

### AC6: UI Updates
- Search view: filtri intent (preventivo, ordine, reclamo, follow-up) + group by intent
- List view: colonna Intent con badge colorato (verde ordine/preventivo, rosso reclamo, blu info/meeting)
- Form view: nuovo tab "AI & Intent" con intent + tutti i campi AI classification
- Intelligence views: list + form + search per Partner Intelligence
- Outbox views: list + form per coda invio
- Menu: "Partner Intelligence" (seq 4) e "Coda Invio" (seq 10) nel menu Mail CRM

### AC7: Security
- ACL: intelligence read per user, full CRUD per admin
- ACL: outbox read/write/create per user, full per admin

### AC8: Migration 18.0.8.1.0
- 5 cron creati via post-migrate (idempotenti con ilike check):
  - Intelligence Rebuild (hourly)
  - IMAP Flag Push (5min, disabled)
  - IMAP Flag Pull (10min, disabled)
  - Outbox Process (2min)
  - Outbox Cleanup (daily)
- 3 config parameters inizializzati
- Initial intelligence rebuild per top 200 partners
- 5 SQL indexes su intent, imap_flags_synced, intelligence

### AC9: Manifest bump 7.11.0 → 18.0.8.1.0
- Nuove dipendenze: sale, account, contacts

## File

### Nuovi (6 file)
- `models/casafolino_partner_intelligence.py` — Intelligence + NBA engine (~430 righe)
- `models/casafolino_mail_flag_sync.py` — IMAP flag sync bidirezionale (~150 righe)
- `models/casafolino_mail_outbox.py` — Async SMTP queue (~230 righe)
- `views/intelligence_views.xml` — Views per intelligence + outbox
- `migrations/18.0.8.1.0/post-migrate.py` — F3 migration
- `docs/report_f3.md` — questo report

### Modificati (5 file)
- `models/__init__.py` — +3 import (intelligence, flag_sync, outbox)
- `models/casafolino_mail_message_staging.py` — +intent_detected field, +imap_flags_synced field, +_detect_intent() method con keyword matcher
- `models/casafolino_mail_account.py` — +_detect_intent() call nel fetch flow
- `__manifest__.py` — version bump, +depends (sale, account, contacts), +intelligence_views.xml
- `security/ir.model.access.csv` — +4 righe ACL (intelligence, outbox)
- `views/casafolino_mail_hub_views.xml` — +intent filters/column/tab, +AI tab in form
- `views/menus.xml` — +2 menu (Intelligence, Coda Invio)

## Decisioni autonome

1. **F3 indipendente da F2**: Intelligence model creato ex novo su main, non dipende da thread/draft/signature V3
2. **NBA rules hardcoded**: 20 regole Python, non modello DB. Piu rapido da iterare, meno overhead. Se servono regole dinamiche → F4
3. **Intent come Selection non Char**: 11 valori fissi, piu pulito per filtri/group-by
4. **Flag sync disabled di default**: Evita problemi con IMAP non configurato. Abilitare via config param
5. **Outbox model separato da draft**: Outbox e queue tecnica, draft e composizione utente. Separazione netta
6. **LLM fallback opzionale**: Config param `v3_nba_llm_fallback`. Se disabilitato, nba_text resta vuoto quando nessuna regola matcha
7. **Migration version jump**: 7.11.0 → 18.0.8.1.0 (allineamento con schema Odoo 18)

## Dipendenze nuove

- `sale` (gia installato — serve per revenue/order queries in intelligence)
- `account` (gia installato — serve per invoice queries in intelligence)
- `contacts` (gia installato — serve per partner enrichment)

Nessuna libreria Python esterna aggiunta.

## Raccomandazioni F4

1. **HtmlField compose**: Sostituire textarea con editor HTML nativo Odoo
2. **NBA model DB**: Se servono regole personalizzabili per utente, migrare da hardcoded a modello `casafolino.nba.rule`
3. **Calibration mode**: Modello feedback per override manuali dell'intelligence
4. **Intent LLM**: Aggiungere intent detection via Groq come fallback quando keyword non matcha
5. **Outbox scheduling**: Implementare `scheduled_send_at` per invio programmato
6. **Performance**: Testare intelligence rebuild con tutti i partner (non solo top 500)
7. **Flag sync testing**: Testare con Gmail IMAP reale prima di abilitare in produzione
