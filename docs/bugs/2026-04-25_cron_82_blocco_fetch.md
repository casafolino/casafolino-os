# Cron 82 — Blocco Fetch IMAP: Diagnosi

**Data**: 2026-04-25
**Modulo**: casafolino_mail v18.0.12.8.0
**Cron**: #82 "CasaFolino Mail Sync V2 - Action" (ogni 5 min)
**Stato attuale**: active=false (disabilitato manualmente)

---

## 1. Sintesi esecutiva

La causa root del blocco e il **combinato di due fattori**: (1) nessun socket timeout sulle connessioni IMAP (`imaplib.IMAP4_SSL` senza parametro `timeout`), e (2) Odoo configurato senza workers (`#workers = 4` commentato in odoo.conf), il che **disabilita i time limit** `limit_time_cpu` e `limit_time_real`. Se Gmail smette di rispondere mid-FETCH (rate limit, network glitch, connessione RST), Python attende all'infinito su `socket.recv()`, il thread principale non ritorna mai, e il cron dispatcher si blocca.

L'account Antonio (id=1, 736 messaggi, INBOX da ~18.000 email Gmail) e il fatto che il body download avviene **inline** nel loop (non deferred) amplificano la finestra di esposizione al rischio: ~80 comandi IMAP FETCH per ogni run con nuove email.

---

## 2. Stato account IMAP

Tabella `casafolino_mail_account` (NON `cf_mail_account` — quest'ultima e legacy):

| id | name | email | state | last_fetch | last_ok_fetch | sync_start | active |
|----|------|-------|-------|------------|---------------|------------|--------|
| 1 | Antonio Folino | antonio@casafolino.com | connected | 2026-04-24 21:30:50 | 2026-04-24 21:30:50 | 2026-04-01 | t |
| 2 | Martina Sinopoli | martina.sinopoli@casafolino.com | connected | 2026-04-24 21:31:03 | 2026-04-24 21:31:03 | 2026-04-01 | t |
| 3 | Josefina Lazzaro | josefina.lazzaro@casafolino.com | connected | 2026-04-24 21:30:58 | 2026-04-24 21:30:58 | 2026-04-01 | t |

**Nota**: tutti 3 account in stato `connected`. La tabella legacy `cf_mail_account` mostra Josefina e Martina con AUTHENTICATIONFAILED, ma il cron usa `casafolino_mail_account`.

**Messaggi per account**: Antonio=736, Martina=489, Josefina=363 (totale 1.588).

---

## 3. Analisi codice fetch — Punti di blocco

### 3.1 Nessun IMAP socket timeout
**File**: `casafolino_mail_account.py:57-58`
```python
imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
```
`IMAP4_SSL` accetta un parametro `timeout` (aggiunto in Python 3.9) che qui non viene passato. Default: `None` = **attesa infinita**.

**Impatto**: qualsiasi `imap.search()`, `imap.fetch()`, `imap.select()` puo bloccare il processo per sempre se il server smette di rispondere.

### 3.2 Body download inline nel loop di fetch
**File**: `casafolino_mail_account.py:360`
```python
new_msg._download_body_imap(imap, folder_name, uid_str)
```
Chiamato per ogni email nuova DENTRO il loop principale. Ogni call fa:
1. `imap.select()` (ri-selezione cartella — ridondante, gia selezionata a riga 216)
2. `imap.fetch(uid, '(RFC822)')` — scarica email COMPLETA (body + allegati)
3. Parse MIME, write body_html, crea ir.attachment

Per 40 email nuove = **80 comandi IMAP FETCH** (40 header + 40 body) + 40 SELECT ridondanti.

**File**: `casafolino_mail_message_staging.py:578`
```python
status, _ = imap.select('"%s"' % folder_name, readonly=True)  # RIDONDANTE
```

### 3.3 Dedup query per-email (OK, ma costoso)
**File**: `casafolino_mail_account.py:280`
```python
existing = Message.search([('message_id_rfc', '=', message_id)], limit=1)
```
Indice btree presente su `message_id_rfc` — veloce. Ma 52 query DB per run (40 dedup + 12 filtered). Accettabile.

### 3.4 Sender preference query per-email
**File**: `casafolino_mail_account.py:287-290`
```python
pref = Preference.search([
    ('email', '=ilike', sender_email_addr),
    ('account_id', '=', resolved_account_id),
], limit=1)
```
Una query aggiuntiva per email. Non ha indice dedicato (da verificare). Con 52 email = 52 query extra.

### 3.5 `is_sender_allowed` — 3 query DB per email inbound non-esatto
**File**: `sender_filter.py:99-147`
Per ogni email inbound il cui mittente non ha match esatto:
1. `Partner.search(email =ilike)` — match esatto
2. `Partner.search(is_company, email ilike @domain)` — match dominio
3. `Partner.search(email_domains_extra != False)` — carica TUTTI i partner con extra domains

Step 3 attualmente restituisce 0 record (nessun partner ha `email_domains_extra`), quindi e un no-op. Ma se crescesse, diventerebbe O(N) per email.

### 3.6 Nessun limite sul numero di email per run
La SEARCH IMAP usa `SINCE last_fetch_datetime` senza cap. Se `last_fetch_datetime` e vecchio (o NULL → fallback a `sync_start_date = 2026-04-01`), una SEARCH su Gmail INBOX con 18.000 email potrebbe restituire migliaia di UID, generando migliaia di FETCH + query.

---

## 4. Analisi volume IMAP — Stima SEARCH

Con `last_fetch_datetime = 2026-04-24 21:30:50` e `sync_start_date = 2026-04-01`:

| Account | Se last_fetch recente (24h) | Se fallback a sync_start (24 gg) |
|---------|----------------------------|----------------------------------|
| Antonio (18k email Gmail) | ~50-100 email | ~2.000-5.000 email |
| Martina | ~10-30 | ~200-500 |
| Josefina | ~10-30 | ~200-500 |

**Scenario critico**: se un deploy/rollback resetta `last_fetch_datetime` a NULL, il sistema tenta di fetchare l'intero storico dal 2026-04-01 per tutti e 3 gli account. Per Antonio, questo significa potenzialmente migliaia di FETCH header + body, con ~9 secondi per email (misurato dal run da 473s / 52 email).

Tempo stimato per 3.000 email senza errori: **~7.5 ore**. Con un hang IMAP: **infinito**.

---

## 5. Storico blocchi

### Log disponibili (post-restart 21:35 UTC)
Solo 2 run di cron 82 visibili:

| Orario | Durata | Risultato |
|--------|--------|-----------|
| 21:21:44 → 21:29:38 | **473s** (7m 53s) | 40 fetched, 0 skip, 12 filtered |
| 21:30:38 → 21:31:03 | **24.6s** | 0 fetched, 40 skip, 12 filtered |

Entrambi completati. La prima run e lenta ma non bloccata.

**Log pre-restart**: persi. Il container restartato alle 21:35 ha cancellato i log del ciclo precedente. Il blocco riportato dall'utente (solo "starting" senza "done") si e verificato in un ciclo precedente i cui log non sono piu disponibili.

### Correlazione temporale
- Nessun cron 82 visibile tra 10:28 e 21:21 (~11 ore di gap) → il cron era probabilmente disabilitato o il container era stato restartato prima
- Gli altri cron (84, 85, 24) girano normalmente nel periodo visibile

---

## 6. Ambiente

### odoo.conf — CRITICO
```
#workers = 4          ← COMMENTATO: single-thread mode
limit_time_cpu = 600  ← IGNORATO senza workers
limit_time_real = 1200 ← IGNORATO senza workers
```

**Workers commentati** = Odoo gira in single-thread mode. In questa modalita:
- I limiti `limit_time_cpu` e `limit_time_real` **non vengono applicati**
- Il cron runner gira nel thread principale
- Un cron bloccato blocca TUTTO: altri cron, richieste web, websocket

### Docker
- Nessun resource limit (memory, CPU, PID)
- Container `odoo-app` connesso a `odoo-db` via rete Docker

---

## 7. Causa root

**Causa primaria**: connessione IMAP senza timeout + Odoo senza workers (nessun time limit).

**Meccanismo del blocco**:
1. Cron 82 parte, connette a Gmail IMAP (no timeout)
2. Per ogni email nuova, esegue `imap.fetch(uid, '(RFC822)')` per scaricare body completo
3. Se Gmail smette di rispondere mid-transfer (rate limit, network issue, connection stale):
   - `socket.recv()` blocca indefinitamente
   - Python non ha timeout → attesa infinita
   - Odoo senza workers → nessun watchdog per killare il processo
4. Il thread principale resta appeso → cron dispatcher fermo → tutti i cron bloccati
5. Solo un restart del container sblocca la situazione

**Account piu esposto**: Antonio (id=1) — unico con INBOX ad alto volume (18k email Gmail). Martina e Josefina hanno volumi minori.

**Fattore amplificante**: body download inline. Ogni run con N email nuove genera 2N+1 comandi IMAP (1 SEARCH + N HEADER FETCH + N BODY FETCH), ognuno potenzialmente bloccante.

---

## 8. Ipotesi di fix

### FIX IMMEDIATO — Timeout IMAP (1 riga, basso rischio)
**File**: `casafolino_mail_account.py:57-58`
```python
# PRIMA:
imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
# DOPO:
imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, timeout=60)
```
E per IMAP4 (riga 60):
```python
imap = imaplib.IMAP4(self.imap_host, self.imap_port, timeout=60)
```
**Effetto**: se Gmail non risponde entro 60s, Python lancia `socket.timeout`, il try/except in `_fetch_emails` lo cattura, l'account viene messo in stato `error`, e il cron prosegue con gli altri account.

### FIX STRUTTURALE — Deferire body download (refactor medio)
Separare header fetch e body download:
1. `_fetch_folder` scarica solo HEADER e crea record con `fetch_state='pending'`
2. Un cron separato (cron 85 esiste gia: "Body Fetch Pending") scarica i body in batch

Questo dimezza i comandi IMAP per run e riduce la finestra di esposizione.

**Nota**: il cron 85 esiste gia ma gira a vuoto ("processed 0 records, 0 records remaining") perche attualmente tutti i body vengono scaricati inline. Basta rimuovere la riga 360 (`new_msg._download_body_imap(...)`) per attivarlo.

### FIX STRUTTURALE 2 — Abilitare workers in odoo.conf
```
workers = 4
```
Riabilita i time limit (`limit_time_real=1200`). Un cron che supera 20 minuti viene killato dal watchdog. Richiede test completo perche impatta tutto il sistema (websocket, long-polling, ecc.).

### FIX STRUTTURALE 3 — Cap per run
Aggiungere `MAX_EMAILS_PER_RUN = 200` in `_fetch_folder`:
```python
uid_list = msg_ids[0].split()[:MAX_EMAILS_PER_RUN]
```
Evita run da ore quando `last_fetch_datetime` e vecchio.

### FIX DI PROCESSO — Monitoring
1. Aggiungere log con timestamp all'inizio e fine di ogni folder fetch
2. Aggiungere campo `last_fetch_duration` sull'account per tracking
3. Alert se un fetch supera 5 minuti (anomalia)

---

## 9. Raccomandazione

**Applicare PRIMA**: Fix immediato (timeout IMAP) — 1 riga, rischio zero, risolve il blocco infinito.

**Applicare SUBITO DOPO**: Rimuovere body download inline (riga 360) per attivare il cron 85 gia esistente. Questo dimezza i comandi IMAP per run e separa la responsabilita.

**Valutare**: Abilitare `workers=4` in odoo.conf per riattivare i time limit di Odoo. Test completo necessario.

| Fix | Complessita | Rischio | Impatto |
|-----|-------------|---------|---------|
| Timeout IMAP | 1 riga | Nullo | Elimina hang infinito |
| Defer body download | Rimuovere 1 riga | Basso (cron 85 esiste) | Dimezza finestra rischio |
| Cap per run | 1 riga | Nullo | Evita run da ore |
| Workers | 1 riga config | Medio (test) | Time limit attivi |
