# F9 Report — Inbox Unificata + Fix "Tenuto" + Badge CC + Backfill AI

**Versione**: `casafolino_mail 18.0.9.0.0`
**Branch**: `feat/mail-v3-f9`
**Data**: 2026-04-20

---

## §1 Fix ambiguità "Tenuto"

### Cosa cambia
- **State labels**: "Tenuta (auto)" → "Gestita (auto)", "Tenuta" → "Gestita" nel modello `casafolino.mail.message`
- **UI labels**: filtro "Tenute" → "Gestite", azione/menu "Tenute CRM" → "Gestite CRM"
- **Sender decision**: `('kept', 'Tenuto (valido)')` → `('kept', 'Gestito (valido)')`
- **Triage wizard**: nota triage aggiornata a "gestito"
- **Message-level "Gestito da"**: `triage_user_id` label rinominato in vista form
- **Partner-level "Account owner"**: nuovo campo `account_owner_id` (M2O → res.users) su `res.partner`
- **Filtri search**: "Gestiti da me" (message-level, `triage_user_id = uid`) e "Mia casella" (account-level)

### Migration
- `migrations/18.0.9.0.0/pre-migration.py`: aggiunge colonna `account_owner_id` su `res_partner`, popola da `user_id` (salesperson)

### File modificati
- `models/casafolino_mail_message_staging.py` — state selection labels
- `models/sender_decision.py` — decision label
- `models/triage_wizard.py` — nota triage
- `models/cf_contact.py` — nuovo campo `account_owner_id`
- `views/casafolino_mail_hub_views.xml` — filtri, form label, partner view
- `views/menus.xml` — menu labels

---

## §2 Inbox Unificata + Account Switcher

### Implementazione
- **Nuova action**: `action_casafolino_mail_inbox_unified` — mostra tutti i messaggi gestiti (`keep`/`auto_keep`)
- **Default filter**: `search_default_my_account: 1` → filtra per caselle dove l'utente è `responsible_user_id`
- **Account switcher**: filtro search "Mia casella" + group-by "Casella" esistente. L'utente può rimuovere il filtro per vedere "Tutti"
- **Badge casella**: campo `account_id` in list view con `widget="badge"` e `decoration-info`
- **Menu**: "Inbox Unificata" aggiunto come primo menu (sequence=0)
- **Persistenza**: `mail_v3_default_account_id` già esistente su `res.users` — usato dal client OWL V3

### Nota design
Non implementato dropdown custom JS (fuori scope standard Odoo). Usato approccio standard Odoo: filtri search + context default. Funzionalmente equivalente e più robusto.

---

## §3 Badge "Sei in CC"

### Implementazione
- **Campo computed**: `is_current_user_in_cc` su `casafolino.mail.message`
  - Non stored (depends on context uid) — `@api.depends_context('uid')`
  - Custom `_search` method per supportare domain filters
  - Controlla `cc_emails` vs email utente + email account IMAP di cui è responsabile
- **List view**: colonna "CC" (boolean, optional=show)
- **Form view**: banner `alert-warning` "Sei in CC — non sei il destinatario principale"
- **Filtri search**: "Solo TO (no CC)" e "Sei in CC"

### §3.5 SLA Buyer
Verificato: la vista SQL `casafolino_mail_sla_partner` usa metriche a livello partner (ultimo inbound/outbound, tempi risposta). I messaggi in CC rappresentano attività reale del partner, quindi non gonfiano falsamente gli SLA. Nessuna esclusione necessaria.

---

## §4 Backfill AI Classification

### Cron automatico
- **Metodo**: `_cron_backfill_ai_classification()` su `casafolino.mail.message`
- **Batch**: 50 messaggi per run
- **Frequenza**: ogni 10 minuti
- **Ordine**: `id DESC` (più recenti prima)
- **Filtro**: `ai_classified_at IS NULL AND body_downloaded = True AND (body_html OR body_plain IS NOT NULL)`
- **Rate limit**: 200ms tra chiamate, backoff esponenziale su 429 (2s, 4s, 8s, max 3 retry poi skip)
- **Logging**: `[backfill_ai] processed=X success=Y failed=Z remaining=W`
- **Safety**: `self.env.cr.commit()` dopo ogni messaggio

### Wizard manuale
- **Modello**: `casafolino.mail.backfill.ai.wizard` (transient)
- **Campi**: date range, account filter (M2M), max messaggi
- **Stima costo Groq**: calcola basato su pricing llama-3.3-70b ($0.59/M input, $0.79/M output) con ~600 avg input tokens, ~80 avg output tokens
- **Esecuzione**: inline con rate limit 200ms
- **Menu**: Mail CRM → Configurazione → Backfill AI (solo group `mail_v3_admin`)

### Copertura AI
- **Metodo API**: `get_ai_coverage_stats()` ritorna `{total, classified, unclassified, coverage_pct}`

### Cron XML
- `data/backfill_ai_cron.xml` — usa `eval="env.ref(...).id"` per model_id (safe pattern per Odoo 18 cron)

---

## §5 Versioning

- **Manifest**: `18.0.8.7.0` → `18.0.9.0.0`
- **Nuovi file data**: `data/backfill_ai_cron.xml`
- **Nuovi file view**: `views/backfill_ai_views.xml`
- **Nuovi file wizard**: `wizard/casafolino_mail_backfill_ai.py`
- **Migration**: `migrations/18.0.9.0.0/pre-migration.py`
- **Security**: ACL per `casafolino.mail.backfill.ai.wizard` (group `mail_v3_admin`)

---

## Riepilogo file toccati

| File | Tipo modifica |
|------|--------------|
| `__manifest__.py` | version bump, nuovi data/view files |
| `models/casafolino_mail_message_staging.py` | state labels, is_current_user_in_cc, backfill cron |
| `models/cf_contact.py` | account_owner_id |
| `models/sender_decision.py` | decision label |
| `models/triage_wizard.py` | nota triage |
| `views/casafolino_mail_hub_views.xml` | filtri, badge CC, banner CC, account badge, inbox unificata |
| `views/menus.xml` | menu labels, inbox unificata, backfill AI |
| `views/backfill_ai_views.xml` | **nuovo** wizard form |
| `data/backfill_ai_cron.xml` | **nuovo** cron |
| `wizard/casafolino_mail_backfill_ai.py` | **nuovo** wizard |
| `wizard/__init__.py` | import |
| `security/ir.model.access.csv` | ACL wizard |
| `migrations/18.0.9.0.0/pre-migration.py` | **nuovo** migration |
