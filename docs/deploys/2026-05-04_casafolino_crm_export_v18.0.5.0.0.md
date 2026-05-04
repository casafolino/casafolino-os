# Deploy Report ��� casafolino_crm_export v18.0.5.0.0

**Data:** 2026-05-04
**Branch:** feat/crm-pipeline-restructure → main (commit 65fc814)
**Target:** folinofood (PROD)
**Esito:** DEPLOY OK + post-deploy fix completati

## Obiettivo

Trasformazione CRM da geo-centrico a operatore-centrico:
- 6 pipeline mercato → tag crm.tag (7 mercato + 6 canale = 13 tag)
- 6 stage → 9 stage uniformi (Primo Contatto, Interesse, Trattativa, Preventivo, Campionatura, Negoziazione, Vinta, Persa, Standby)
- Pipeline operatore: Antonio + Josefina con bordo card colorato
- Cron Standby auto-entry a 30gg dal cf_date_last_contact

## File modificati

| File | Scopo |
|------|-------|
| `CHANGELOG.md` | Changelog v18.0.5.0.0 |
| `__init__.py` | Import nuovi modelli |
| `__manifest__.py` | Versione + nuovi data file |
| `data/cf_crm_stages_data.xml` | Definizione 9 stage con sequence/fold/is_won |
| `data/cf_crm_tags_market_channel.xml` | 13 tag mercato+canale con colori |
| `migrations/18.0.5.0.0/post-migrate.py` | Remap stage, assegna tag da cf_market/cf_channel, drop colonne, crea cron |
| `models/__init__.py` | Import cf_crm_stage + cf_mail_activity |
| `models/cf_crm_stage.py` | Estensione crm.stage (campi custom) |
| `models/cf_export_sample.py` | Rimozione campi cf_market/cf_channel |
| `models/cf_mail_activity.py` | Mail activity custom per CRM |
| `models/crm_lead.py` | Nuovi computed, logica pipeline operatore, cron method |
| `static/src/css/cf_crm.css` | Stile card kanban bordo colorato per operatore |
| `views/cf_sample_views.xml` | Rimozione viste campi obsoleti |
| `views/crm_lead_views.xml` | Vista kanban/form/list riscritta per 9 stage |
| `views/menus.xml` | Menu semplificato (no sub-pipeline) |

## Backup

- Stage: `/tmp/backup_stage_crm_20260502_144150.sql` (371M)
- Prod: `/tmp/backup_prod_crm_20260504_063002.sql` (409M)

## Timeline esecuzione

| Ora (UTC) | Evento |
|-----------|--------|
| 06:29 | Merge feat/crm-pipeline-restructure → main, push |
| 06:30:02 | Backup prod creato (409M) |
| 06:31:10 | Git pull + copy addons su EC2 |
| 06:31:20 | Update modulo avviato |
| 06:33:24 | Update completato (124s, no ERROR) — migration eseguita |
| 06:33:40 | Restart odoo-app |
| 06:33:55 | HTTP 200 OK verificato |
| 06:41:23 | Cron dry-run OK (CRON_OK result=None) |
| 06:44:18 | Fix orfani: 42 lead riassegnati a Primo Contatto |
| 06:48:51 | Audit Standby: 115 lead analizzati, CSV salvato |
| 06:50:xx | Fix Standby: 4 lead con attivita aperte riportati a Primo Contatto |

## Risultati acceptance criteria

| # | Criterio | Esito | Dettaglio |
|---|----------|-------|-----------|
| 1 | Stage 9 nuovi | OK | 9 righe in crm_stage |
| 2 | Tag 13 nuovi | OK | 7 mercato (color=1) + 6 canale (color=2) |
| 3 | Stage vecchi eliminati | OK | Contatto/Qualificazione: 0 righe |
| 4 | Colonne droppate | OK | cf_market, cf_channel rimossi da information_schema |
| 5 | Cron Standby attivo | OK | Daily, next: 2026-05-05 |
| 6 | View duplicate | OK | 0 duplicati |
| 7 | Total opps conservate | OK | 213 pre = 213 post |
| 8 | Lead orfani stage | Risolto | 42 riassegnati (erano pre-esistenti con NULL) |
| 9 | Errori runtime log | OK | Nessun ERROR nel log post-restart |

## Distribuzione finale pipeline (post-fix completi)

| Stage | Lead | Note |
|-------|------|------|
| Primo Contatto | 54 | 50 da migration + 4 da Standby fix |
| Interesse | 29 | ex-Qualificazione |
| Trattativa | 0 | nuovo, nessun lead mappato |
| Preventivo | 9 | mantenuto |
| Campionatura | 0 | nuovo, nessun lead mappato |
| Negoziazione | 7 | mantenuto |
| Vinta | 3 | mantenuto |
| Persa | 0 | nuovo, nessun lead mappato |
| Standby | 111 | 115 da migration - 4 riportati |
| **Totale** | **213** | |

## Distribuzione tag mercato

| Tag | Lead |
|-----|------|
| Europa | 44 |
| Italia | 3 |
| America | 1 |

## Distribuzione tag canale

| Tag | Lead |
|-----|------|
| E-commerce | 2 |
| Foodservice | 1 |
| Distributore | 1 |

## Anomalie risolte

### 1. 42 lead orfani senza stage

Lead pre-esistenti con `stage_id IS NULL` (importati da Bigin CRM senza mapping stage). Non toccati dalla migration perche non avevano stage di partenza. Riassegnati manualmente a "Primo Contatto" con `probability=5` e messaggio chatter.

File pre-check: `/tmp/orfani_pre_assign_20260504_064418.txt`

### 2. 115 lead in Standby da migration

La post-migrate ha applicato logica retroattiva: lead senza contatto da 60+ giorni spostati a Standby. Audit completo:

- **4 lead con attivita aperte** → riportati a Primo Contatto (id: 2, 3, 5, 8)
- **12 lead con revenue (totale 1.28M EUR)** → analizzati, confermati dormienti (12+ mesi senza attivita), lasciati in Standby in attesa di decisione Antonio
- **99 restanti** → confermati legittimamente dormienti, lasciati in Standby

File audit: `/tmp/standby_audit_20260504_064851.csv`

### 3. cf_date_last_contact universalmente NULL

Il campo non era mai stato popolato prima della migration. Il criterio "60gg senza contatto" della post-migrate ha quindi catturato TUTTI i lead che non erano in stage Vinta/Persa e che non avevano attivita recente. Questo spiega il volume alto (115) in Standby.

## Lezioni apprese

1. **I brief di migration devono dichiarare esplicitamente cosa NON fare.** La logica retroattiva (60gg → Standby) non era nel brief originale e ha richiesto audit post-deploy per recuperare lead validi.

2. **Suggerimento per CLAUDE.md:** aggiungere clausola "Le migration applicano SOLO quanto specificato nel brief. Nessuna logica retroattiva (Standby, archiviazione, default su record esistenti) senza esplicita richiesta nel brief."

3. **Pre-populare cf_date_last_contact** prima di attivare logiche cron basate su quel campo. Senza dati storici, il cron Standby considererebbe nuovamente tutti i lead come "senza contatto".

## Rollback procedure

Backup disponibile fino al 2026-05-11 in `/tmp/backup_prod_crm_20260504_063002.sql`.

```bash
# Stop app
docker stop odoo-app

# Restore
docker exec -i -e PGPASSWORD=odoo odoo-db psql -U odoo -d postgres -c "DROP DATABASE folinofood;"
docker exec -i -e PGPASSWORD=odoo odoo-db psql -U odoo -d postgres -c "CREATE DATABASE folinofood OWNER odoo;"
cat /tmp/backup_prod_crm_20260504_063002.sql | docker exec -i -e PGPASSWORD=odoo odoo-db psql -U odoo -d folinofood

# Ripristina codice
cd /home/ubuntu/casafolino-os && git checkout HEAD~1 -- casafolino_crm_export
sudo cp -rf casafolino_crm_export /docker/enterprise18/addons/custom/

# Restart
docker start odoo-app
```

## Prossimi step rinviati

- Fine-tuning form view premium (HubSpot-style card layout)
- Dashboard CRM con KPI per Josefina
- Integrazione email IMAP <-> trattative (overlap con casafolino_mail F8)
- Drop tabelle vecchie cf_export_lead, cf_export_stage
- Popolare cf_date_last_contact da storico mail_message per tutti i lead attivi
