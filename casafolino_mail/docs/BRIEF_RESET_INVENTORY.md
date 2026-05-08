# Brief #RESET — Inventario pre-reset

**Data:** 2026-05-08
**Backup:** `/tmp/backup_pre_reset_20260508_124134.sql.gz` (87MB)

## Volume pre-reset

| Tabella | Record |
|---|---|
| casafolino_mail_message | 2995 |
| cf_mail_position_feedback | 0 |
| crm_lead | 561 |
| project_project (dossier) | 60 |
| cf_export_sample | 1 |
| res_partner (totale) | 16399 |
| mail_message on project | 144 |
| mail_message on lead | 1458 |

## Duplicati partner

| Tipo | Count |
|---|---|
| Duplicati per email (case-insensitive) | 2325 |
| Empty records (no name/email/phone/mobile) | 9 |

## Caselle IMAP

| ID | Nome | Email | last_fetch_uid | sync_start_date | last_fetch_datetime |
|---|---|---|---|---|---|
| 1 | Antonio Folino | antonio@casafolino.com | 18727 | 2026-04-01 | 2026-05-08 12:41:34 |
| 2 | Martina Sinopoli | martina.sinopoli@casafolino.com | 18707 | 2026-04-01 | 2026-05-01 15:21:40 |
| 3 | Josefina Lazzaro | josefina.lazzaro@casafolino.com | 18711 | 2026-04-01 | 2026-05-06 14:37:29 |

Nota: `sync_start_date` gia' impostato a 2026-04-01 su tutte le caselle.

## Cron CasaFolino attivi

| ID | Nome | Active | Intervallo |
|---|---|---|---|
| 82 | Mail Sync V2 | true | 5 min |
| 83 | Silent Partners | true | 1 day |
| 84 | AI Classify | true | 5 min |
| 85 | Body Fetch Pending | true | 10 min |
| 98 | Auto-Attach Email a Lead | false | 15 min |
| 99 | Digest Mittenti Fuori-CRM | true | 1 week |
| 110 | Triage RAW | true | 5 min |
| 111 | Cleanup RAW | true | 1 day |
| 117 | Cleanup Trash | true | 1 day |
| 118 | Cleanup Mass Action Logs | true | 30 min |
| 119 | Send Scheduled Drafts | true | 5 min |
| 125 | Auto-Standby Lead inattivi | true | 1 day |
| 138 | AI suggestion mail | true | 5 min |
| 139 | Accuracy refresh mail AI | true | 1 day |

## Post-wipe (Phase 1)

13 cron CasaFolino disattivati.

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
| res_partner | 16399 | 16399 |

FK cleanup: 970 threads, 1044 thread_partner_rel, 505 crm_tag_rel, 85 ir_attachment, 29 project_update, 87 project_tags_rel.
VACUUM ANALYZE eseguito.

## Dedup partner (Phase 2)

- Empty records: skip (referenziati da sale_order, non cancellabili)
- Duplicati per email marcati `active=FALSE`: 2325
- Partner attivi finali: 14052 (85.7% del pre-reset)
- Partner con email attivi: 11316
- Partner mail_tracked attivi: 38
- Duplicati rimanenti: 0

## IMAP reconfig (Phase 3)

- 3 caselle resettate: last_fetch_uid=NULL, last_fetch_datetime=NULL
- sync_start_date=2026-04-01 su tutte
- IMAP SINCE supportato: SI (riga 226 casafolino_mail_account.py)
- Logica: se last_fetch_datetime NULL, usa sync_start_date come SINCE
- Nessun fallback necessario
