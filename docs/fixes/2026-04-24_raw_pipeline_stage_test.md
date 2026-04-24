# RAW Pipeline — Stage Test Report

**Data**: 2026-04-24
**Branch**: `feat/mail-raw-pipeline` (4 commit: ddef59f → 1478aef)
**Stato**: testato su stage, NON deployato in prod

---

## Cosa e stato fatto

1. **Cron 82 fix** (timeout IMAP + body deferred) deployato in prod — funzionante
2. **Pipeline RAW → Triage → MESSAGE** sviluppata e testata su stage:
   - Nuovo modello `casafolino.mail.raw` con staging pre-triage
   - Fetch "stupido" scarica solo header + preview in RAW (nessun filtro)
   - Cron triage applica regole deterministiche + AI Groq, promuove a MESSAGE
   - Cron cleanup elimina RAW processati dopo 48h
   - Migration DELETE CASCADE messaggi esistenti + backfill da 2026-04-01

## Numeri stage

| Metrica | Valore |
|---------|--------|
| RAW creati (backfill 24gg, 2 account) | 1,069 |
| Promoted → MESSAGE | 290 |
| Discarded | 10 |
| Errori triage | 0 |
| Triage deterministico | 97% (sender_kept 78, crm_exact 18) |
| Triage AI (Groq) | 3% (3 record) |
| Tempo fetch backfill | 196s |
| Tempo triage per 100 record | ~100-105s |

## Stato prod attuale

- **Versione**: 18.0.12.11.0 (pre-RAW, codice timeout fix)
- **Cron 82**: attivo, funzionante (0.005-0.080s per run)
- **Cron 85**: attivo
- **Container**: pulito, zero file RAW residui
- **Branch server**: `feat/mail-delete-template-v12`

## Lezioni apprese per prossimo deploy

1. **Feature flag obbligatorio**: non deployare codice che cambia modelli nel container
   condiviso prod/stage senza aver prima aggiornato il DB target con `-u`. Il codice
   Python viene caricato per TUTTI i database, ma i modelli ORM esistono solo nei DB
   aggiornati.

2. **No swap multipli di codice**: alternare `cp -rf` tra branch diversi lascia file
   orfani (es. `casafolino_mail_raw.py` resta dopo restore perche `cp` non cancella
   file assenti nella source). Usare `rm -rf` + `cp -rf` oppure `rsync --delete`.

3. **Migration deve registrare cron indipendentemente dall'idempotency check**:
   `_post_init_hook` esegue solo su install, non su update. La registrazione cron
   nel migration file deve avvenire PRIMA del check idempotente, non dopo.

4. **Cron scheduler Odoo gira sul DB attivo** (prod), non su stage. I cron creati
   su stage non si auto-eseguono — vanno testati via `odoo shell`.

## Prossimi passi

- Deploy prod del branch `feat/mail-raw-pipeline` — richiede conferma esplicita
- Pre-requisiti: `rsync --delete` invece di `cp -rf`, disabilitare cron 82 prima
  del deploy, backup DB prod, `-u casafolino_mail -d folinofood`
- Backfill stimato: ~3000-5000 RAW per 3 account, ~50 min di triage
