# Brief #DEPLOY — Report

**Data:** 2026-05-08

## Phase 0 — Pre-flight

- **Backup PROD:** `/tmp/backup_pre_deploy_20260508_065259.sql` (431 MB)
- **Server repo:** synced to `573de8e` (Brief #FINAL Phase 8)
- **Cron AI suggestion:** non esistente (da creare)
- **Cron Accuracy refresh:** non esistente (da creare)
- **Backup files /tmp pre-cleanup:** 14 file, ~5.9 GB totali

## Phase 1 — Deploy + smoke

- **git pull:** `573de8e` synced (10 files, 931 insertions)
- **cp modules:** casafolino_crm_export + casafolino_mail -> /docker/enterprise18/addons/custom/
- **-u update:** SUCCESS ("Modules loaded" in 52.7s, no ERROR/CRITICAL)
  - WARNING: `action_open_project_360 is not a valid action on crm.lead` (Studio validation noise, button type="object" not action — harmless)
  - WARNING: `action_open_dashboard is not a valid action on project.project` (same — harmless)
- **Module states:** both `installed`
- **Cache invalidate:** 5 asset attachments deleted
- **Container:** UP
- **HTTP:** 200 (erp.casafolino.com/web/login)
- **Logs post-restart:** clean (no ERROR/CRITICAL/Traceback)
- **ORM smoke via shell:** NOT POSSIBLE — circular dependency casafolino_crm_export <-> casafolino_mail prevents shell from loading custom modules. Web app works fine (modules loaded by -u).
- **Pattern check on server:** 0/4 (useService(user), this.user., `<tree>`, attrs=)

## Phase 2 — Cron + cleanup

- **Cron AI suggestion mail** (id=138): every 5 minutes, active=True
- **Cron Accuracy refresh mail AI** (id=139): every 1 day, active=True
- **Backup cleanup:** 13 file eliminati (~5.5 GB liberati)
- **Backup conservato:** `/tmp/backup_pre_deploy_20260508_065259.sql` (431 MB)

## Stato finale

PROGETTO RESTYLING SW CASAFOLINO LIVE IN PROD

- Pipeline + List + Wizard nuovo lead
- Dashboard 360 con 7 tab (Timeline, Cliente, Commerciale, Campionature, Documenti, Note, Mail)
- Modulo mail end-to-end (ingestion, posizionatore, AI feedback, F8 + AI assist, multi-casella)
- 2 cron attivi in background
- Pattern check: 0/4 anti-pattern OWL18
