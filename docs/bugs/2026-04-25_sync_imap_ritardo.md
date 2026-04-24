# BUG A: Sincronizzazione IMAP in ritardo

**Data analisi**: 2026-04-25
**Modulo**: casafolino_mail (v18.0.12.8.0)
**DB**: folinofood (produzione)

---

## Sintomo

Email arrivano in Mail Hub con ore di ritardo rispetto alla ricezione nella casella Gmail.
L'utente segnala email che appaiono solo dopo diverse ore o non compaiono affatto.

---

## Scope di indagine

### 1. Cron registrati

| ID | Nome | Attivo | Intervallo | Metodo |
|----|------|--------|------------|--------|
| 82 | CasaFolino Mail Sync V2 - Action | **SI** | 15 min | `_cron_fetch_all_accounts()` |
| 83 | CasaFolino Silent Partners - Action | SI | 1 giorno | `_cron_silent_partners_alert()` |
| 84 | CasaFolino AI Classify - Action | SI | 5 min | `_cron_ai_classify_pending()` |
| 85 | CasaFolino Body Fetch Pending - Action | SI | 10 min | `_cron_fetch_pending_bodies()` |
| 98 | CasaFolino: Auto-Attach Email a Lead | **NO** | 15 min | `_cron_auto_attach_leads()` |
| 99 | CasaFolino: Digest Mittenti Fuori-CRM | SI | 1 settimana | `_cron_digest_fuori_crm()` |
| 6 | Mail: Fetchmail Service (Odoo nativo) | **NO** | 5 min | disabilitato |

**Nota**: I cron XML (`cf_mail_cron.xml` e `casafolino_mail_hub_cron.xml`) sono file vuoti (`<odoo></odoo>`).
Tutti i cron vengono creati programmaticamente via `_post_init_hook()` in `__init__.py`.
Questo significa che i cron NON vengono aggiornati/ricreati ad ogni `-u` del modulo.

### 2. Account IMAP

| ID | Nome | Email | Stato | Ultimo fetch | Ultimo fetch OK |
|----|------|-------|-------|-------------|-----------------|
| 1 | Antonio Folino | antonio@casafolino.com | connected | 2026-04-24 02:54:25 | 2026-04-24 02:54:25 |
| 2 | Martina Sinopoli | martina.sinopoli@casafolino.com | connected | 2026-04-24 02:54:27 | 2026-04-24 02:54:27 |
| 3 | Josefina Lazzaro | josefina.lazzaro@casafolino.com | connected | 2026-04-24 02:54:26 | 2026-04-24 02:54:26 |

Tutti connessi e funzionanti all'ultimo check.

### 3. Stato messaggi

- **Totale messaggi**: 1.453
- **Body non scaricati**: 0
- **Body in pending**: 0
- **Body in errore**: 0

Il pipeline body-download funziona correttamente.

---

## Evidenza

### Distribuzione ritardi (email_date vs create_date) — solo email dal 22/04

| Bucket | Count |
|--------|-------|
| 0-15 min | 87 |
| 15-60 min | 46 |
| **1-8 ore** | **46** |
| 8+ ore | 117 (quasi tutti da import iniziale pre-22/04) |

### Gap operativi del cron (analisi create_date)

Il cron e' impostato a 15 minuti, ma ci sono gap significativi nelle esecuzioni:

1. **22 Apr, 06:31 - 15:02 (8.5 ore di gap)**: Nessuna email importata.
   35+ email ricevute tra le 07:36 e le 14:01 sono state tutte importate alle 15:02.
   Causa probabile: modulo aggiornato/riavviato, cron non rieseguito fino al restart.

2. **23 Apr, 03:30 - 10:08 (6.5 ore di gap)**: 8 email delle 06:00-09:05 importate solo alle 10:08.
   Causa probabile: stesso pattern (deploy/update blocca il cron).

3. **23 Apr, 20:30 - 02:20+1 (6 ore di gap)**: Email delle 23:39 importata solo alle 02:20.
   Questo potrebbe essere il periodo notturno con meno email, ma il gap resta.

### Pattern di ritardo recente (23 Apr, ore lavorative normali)

Quando il cron funziona regolarmente (pomeriggio 23 Apr), il ritardo tipico e' **3-15 minuti** — accettabile per un polling ogni 15 minuti.

### Log Odoo (ultimi disponibili)

```
02:54:25 [antonio@casafolino.com] fetched 0, skipped 0, excluded 0
02:54:26 [josefina.lazzaro@casafolino.com] INBOX: fetched 1, skipped-dedup 1, filtered-out 0
02:54:27 [martina.sinopoli@casafolino.com] INBOX: fetched 0, skipped-dedup 1, filtered-out 1
```

Nessun errore IMAP nei log recenti. Il fetch funziona quando il cron gira.

---

## Scenario identificato (Root cause)

### Causa primaria: Gap nel cron dopo deploy/update modulo

Il cron `CasaFolino Mail Sync V2` (ID 82) ha un intervallo di 15 minuti e risulta attivo,
ma **smette di eseguire per ore** quando il container Odoo viene riavviato per aggiornamenti modulo
(`docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http`).

Il meccanismo:
1. Odoo viene fermato per `-u` (update modulo)
2. Il cron ha `nextcall` impostato a 15 min dopo l'ultimo run
3. Se il server resta giu' per il periodo dell'update, il `nextcall` scade
4. Al restart, Odoo NON recupera i run persi (non c'e' `doall=True` -- correttamente rimosso nel commit 5ced424)
5. Il cron riparte al prossimo `nextcall` schedulato, che potrebbe essere ore dopo

### Causa secondaria: Criterio di ricerca IMAP basato su `last_fetch_datetime`

```python
if self.last_fetch_datetime:
    since_date = self.last_fetch_datetime.strftime('%d-%b-%Y')
else:
    since_date = self.sync_start_date.strftime('%d-%b-%Y')
```

Il criterio `SINCE` usa la **data** (senza ora) dell'ultimo fetch.
Questo significa che il fetch recupera tutte le email del giorno corrente,
quindi non perde email. Ma il ritardo resta legato a **quando il cron gira**.

### Causa terziaria: Whitelist CRM filtra email legittime

Il filtro `is_sender_allowed()` in `sender_filter.py` scarta email inbound
il cui mittente non e' nel CRM (ne' per email esatta, ne' per dominio azienda).
Email da contatti nuovi vengono silenziosamente filtrate (`filtered-out` nei log).

Esempio dai log: `martina.sinopoli@casafolino.com` ha 1 email `filtered-out`.

### Non causa: Body download

Tutti i 1.453 messaggi hanno `body_downloaded=true` e `fetch_state='done'`.
Il body viene scaricato inline durante il fetch (riga 360 di `casafolino_mail_account.py`),
non tramite il cron separato. Il cron body-fetch (ID 85) e' solo un fallback per email
con `fetch_state='pending'` e non ha backlog.

---

## Ipotesi di fix (NON implementate)

### Fix 1 — Ridurre intervallo cron a 5 minuti (impatto medio)

```sql
UPDATE ir_cron SET interval_number=5 WHERE id=82;
```

Riduce il ritardo medio da ~7.5 min a ~2.5 min durante il funzionamento normale.
Non risolve i gap post-deploy.

### Fix 2 — Aggiungere catch-up after restart (impatto alto)

Creare un meccanismo che al primo avvio del modulo (o nel `_post_init_hook`)
forzi un fetch immediato:

```python
# In _post_init_hook o in un ir.actions.server post-update
accounts = env['casafolino.mail.account'].search([('state', '=', 'connected')])
for acc in accounts:
    acc._fetch_emails()
```

### Fix 3 — Deploy script con fetch automatico (impatto alto, zero codice)

Aggiungere al `deploy.sh` un comando post-restart che triggera il fetch:

```bash
docker restart odoo-app && sleep 30 && \
docker exec odoo-app python3 -c "
import xmlrpc.client
url = 'http://localhost:8069'
db = 'folinofood'
# ... trigger sync via XML-RPC
"
```

### Fix 4 — Notifica se cron non esegue da > 30 min (monitoring)

Aggiungere un health check che verifica `last_fetch_datetime` di ogni account
e manda alert se > 30 minuti fa.

### Fix 5 — Considerare webhook/push invece di polling (impatto alto, lungo termine)

Gmail API supporta push notifications via Pub/Sub.
Eliminerebbe completamente il polling e i ritardi.
Richiede refactoring significativo del modulo.

---

## File rilevanti

- `casafolino_mail/models/casafolino_mail_account.py` — fetch engine (`_fetch_emails`, `_fetch_folder`, `_cron_fetch_all_accounts`)
- `casafolino_mail/models/sender_filter.py` — whitelist CRM (`is_sender_allowed`)
- `casafolino_mail/models/casafolino_mail_message_staging.py` — `_download_body_imap`, cron secondari
- `casafolino_mail/__init__.py` — `_post_init_hook` (creazione cron programmatica)
- `casafolino_mail/data/cf_mail_cron.xml` — file vuoto (cron non definiti in XML)
