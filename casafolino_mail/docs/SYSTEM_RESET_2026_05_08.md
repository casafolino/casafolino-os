# Reset CasaFolino OS — 2026-05-08

## Scopo
Reset controllato post-deploy completo del progetto restyling SW.
Sistema azzerato sui dati operativi per ripartire pulito con flusso nuovo.

## Decisioni Antonio
- Mantieni partner, deduplica
- Wipe totale mail, ricarica IMAP dal 1 aprile 2026
- Wipe totale lead/project/sample
- Conserva configurazioni (caselle, utenti, tag, listini, view)

## Operazioni eseguite

### Wipe (Phase 1)
| Tabella | Pre | Post |
|---|---|---|
| casafolino_mail_message | 2995 | 0 |
| casafolino_mail_raw | 418 | 0 |
| cf_mail_position_feedback | 0 | 0 |
| crm_lead | 561 | 0 |
| project_project (dossier) | 60 | 0 |
| cf_export_sample | 1 | 0 |
| mail_message on project | 144 | 0 |
| mail_message on lead | 1458 | 0 |

FK cleanup: threads, tags, attachments, project_update, project_milestone, project_collaborator.

### Dedup partner (Phase 2)
- Duplicati per email marcati `active=FALSE`: 2325
- Partner attivi finali: 14052 (85.7% del pre-reset)
- Partner con email attivi: 11316
- Partner mail_tracked attivi: 38
- Duplicati rimanenti: 0

### IMAP reset (Phase 3)
- 3 caselle resettate
- last_fetch_uid=NULL, last_fetch_datetime=NULL
- sync_start_date=2026-04-01
- IMAP SINCE filtro attivo nel codice

### Cron (Phase 4)
- Disattivati durante reset: 13
- Riattivati post-reset: 13
- Cron 98 (Auto-Attach Email a Lead) rimane off (era gia' off pre-reset)

## Backup
- Pre-reset: `/tmp/backup_pre_reset_20260508_124134.sql.gz` (87MB)
- Recommendazione: archiviare il backup off-server entro 7 giorni

## Rollback
Se serve recovery (entro 7 giorni):
```bash
gunzip -k /tmp/backup_pre_reset_20260508_124134.sql.gz
docker exec -i -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood < /tmp/backup_pre_reset_20260508_124134.sql
docker restart odoo-app
```

## Cosa aspettarsi nelle prossime ore

1. Cron IMAP fetch parte ogni 5 min
2. Le mail ricevute nelle caselle Gmail dal 1 aprile 2026 entrano nel sistema
3. SOLO mail di partner con `mail_tracked=True` vengono processate nel Posizionatore
4. AI suggestion processa le mail entrate (cron 5 min)
5. Apri Posizionatore -> vedi mail con badge confidence

## Cosa fare ora (Antonio)

1. Verifica nel browser che il Posizionatore non dia errori
2. Spunta `mail_tracked=True` su 10-20 partner reali (clienti attivi, buyer SIAL Canada, distributori)
3. Aspetta 30 minuti
4. Apri Posizionatore -> smista le prime mail con AI suggestion
