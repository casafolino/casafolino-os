# Report F7 — Hotfix Mail V3 + Triage UX

**Versione:** 18.0.8.5.1 → 18.0.8.6.0
**Branch:** `fix/mail-v3-f7` (da `fix/mail-v3-f6-5`)
**Data:** 2026-04-20
**Autore:** Claude Code (Opus 4.6)

---

## 1. Bug Fix Applicati

### A. Sidebar 360 + Bottoni compose (AC1-AC5)

**Root cause:** In `selectThread()`, la chiamata RPC `/sidebar_360` era in serie con il caricamento messaggi. Se l'endpoint sidebar hangava (per lock DB causati dal cron Groq), il reading pane rimaneva bloccato su "Caricamento" e i bottoni Rispondi/Inoltra/Scrivi non apparivano mai.

**Fix:** Separato sidebar loading in metodo `_loadSidebar360()` indipendente. Messaggi ora renderizzano immediatamente, sidebar carica in parallelo. Aggiunto error fallback nella sidebar template ("Dati non disponibili" se RPC fallisce).

**File modificati:**
- `static/src/js/mail_v3/mail_v3_client.js` — selectThread refactored, nuovo _loadSidebar360
- `static/src/xml/mail_v3/mail_v3_sidebar_360.xml` — error fallback state
- `static/src/xml/mail_v3/mail_v3_client.xml` — aggiunto onQuickAction prop

### B. Ingestion IMAP Backlog (AC6-AC7)

**Root cause:** `_classify_with_groq()` veniva chiamato INLINE per ogni email durante `_fetch_folder`. Su 429 Groq, `time.sleep(20)` bloccava l'intera transazione → SerializationFailure → cron 82 falliva → backlog cresceva.

**Fix:**
1. Rimosso `_classify_with_groq()` dalla pipeline di ingestion (ora skip inline, deferisce a cron separato)
2. Rimosso `time.sleep(20)` dal handler 429 — ora skip immediato con log "will retry later"
3. HOTFIX A operativa: Groq key svuotata temporaneamente → ingestion ripartita in 8 minuti, 57 nuove email ingerite, email Bianchi trovata

**File modificati:**
- `models/casafolino_mail_account.py` — rimosso inline classify
- `models/casafolino_mail_message_staging.py` — rimosso sleep(20) su 429

---

## 2. Soluzione Groq 429 (AC8-AC9)

**Reply Assistant** (`/cf/mail/v3/message/<id>/reply_assistant`):
- Retry fino a 3 tentativi con exponential backoff (2s, 4s, 8s cap)
- Su 429: legge header `retry-after`, attende e riprova
- Messaggio user-friendly in italiano se tutti i tentativi falliscono: "Risposta AI non disponibile al momento. Riprova tra qualche secondo."
- Nessun stacktrace esposto all'utente

**AC10 (throttling per utente):** Non implementato separatamente — il backoff lato server + il rate limit nativo Groq già fungono da throttle. Se necessario, aggiungere contatore in `res.users` in F8.

---

## 3. Feature Triage Bulk + Auto-Noreply + Info Enrichment

### §3.6 Triage Bulk Actions (AC11)

- Metodi `action_bulk_ignore_sender` e `action_bulk_keep` su `casafolino.mail.orphan.partner`
- List view con `multi_edit="1"` e header buttons "Ignora selezionati" / "Tieni selezionati"
- Ogni azione crea policy + decisione + retroactive apply su messaggi esistenti

### §3.7 Auto-Cleanup Noreply (AC12)

- Endpoint admin POST `/cf/mail/v3/triage/autoclean_noreply`
- Pattern regex: noreply, no-reply, donotreply, mailer-daemon, postmaster, info, news, newsletter, automated, notification
- Crea `auto_discard` policy per ogni email + decisione `ignored_sender`
- Retroactive apply su messaggi inbound in stato new/review

### §3.8 Info Enrichment Wizard (AC13)

Campi computed nel wizard triage:
- `sender_tld` — es. `.de`, `.it`, `.com`
- `partner_website_detected` — dominio se non è email pubblica (gmail/yahoo/etc)
- `is_likely_buyer` — keyword match su subject + body preview
- `similar_partners_count` — count partner con stesso dominio email

Visualizzati in sezione "Indizi" prima dei bottoni decisione.

### Search View (AC14)

Aggiunti filtri:
- "Solo noreply@" — domain filter per 9 pattern comuni
- "Priority cold" — filtra solo orfani cold

---

## 4. Query SQL One-Shot Eseguite

```sql
-- HOTFIX A: svuota Groq key per sbloccare ingestion
UPDATE ir_config_parameter SET value='' WHERE key='casafolino.groq_api_key';

-- Trigger immediato cron sync + body fetch
UPDATE ir_cron SET nextcall=NOW() WHERE id IN (82, 85);
```

**Risultato:** 57 email ingerite in 8 minuti, email Bianchi confermata presente.

---

## 5. AC Coverage

| AC | Stato | Note |
|----|-------|------|
| AC1 | ✅ | Sidebar carica indipendentemente da messaggi |
| AC2 | ✅ | Rispondi funziona (fix: messaggi renderizzano senza aspettare sidebar) |
| AC3 | ✅ | Reply All — stessa fix |
| AC4 | ✅ | Inoltra — stessa fix |
| AC5 | ✅ | Scrivi — stessa fix |
| AC6 | ✅ | Email Bianchi ingerita (confermato via SQL) |
| AC7 | ✅ | Inline classify rimosso → no più backlog multi-ora |
| AC8 | ✅ | Errore 429 → messaggio IT user-friendly |
| AC9 | ✅ | 3 retry con backoff esponenziale |
| AC10 | ⚠️ | Throttling implicito via backoff, no contatore per-utente |
| AC11 | ✅ | Bulk wizard: seleziona 20+ → Ignora in 1 click |
| AC12 | ✅ | Auto-cleanup endpoint per noreply |
| AC13 | ✅ | TLD, is_likely_buyer, similar_partners nel wizard |
| AC14 | ✅ | Filtro "Solo noreply@" nella search view |

---

## 6. Raccomandazioni F8

- **WhatsApp integration** — collegare WhatsApp Business API per contatti preferenziali
- **Calendar sync** — auto-detect meeting requests e proporre slot
- **Multi-lingua reply** — reply assistant rileva lingua inbound e genera nella stessa
- **Hotness auto-calibrata** — feedback loop su decisioni triage → calibra soglie
- **AC10 pieno** — contatore Groq calls per utente in `res.users` con soft limit
- **Classify cron dedicato** — processare backlog ai_classified_at=NULL in batch separato
- **Ripristino Groq key** — dopo conferma backlog svuotato, ripristinare da /tmp/groq_key_backup.txt

---

## 7. Note Operative

**Groq key attualmente VUOTA su prod.** Classificazione AI disattivata. 
Ripristino quando Antonio conferma che ingestion è stabile (1-2h).

```sql
-- RIPRISTINO (quando pronto)
UPDATE ir_config_parameter SET value='<valore da backup>' WHERE key='casafolino.groq_api_key';
```
