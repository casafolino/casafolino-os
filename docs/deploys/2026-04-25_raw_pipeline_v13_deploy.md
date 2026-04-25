# RAW Pipeline V13 — Deploy Prod

**Data**: 2026-04-25 00:00 UTC
**Branch**: `feat/mail-raw-pipeline`
**Versione**: 18.0.13.0.0
**Feature flag**: `casafolino.use_raw_pipeline = true`

---

## Cosa e stato deployato

Pipeline a 3 stadi per fetch email IMAP:

1. **Cron 82 (Mail Sync V2)**: scarica header + preview in `casafolino.mail.raw` (nessun filtro)
2. **Cron 110 (Triage RAW)**: regole deterministiche (97%) + AI Groq (3%), promuove a `casafolino.mail.message` o scarta
3. **Cron 111 (Cleanup RAW)**: elimina RAW processati dopo 48h (notturno 03:00 UTC)

Feature flag `casafolino.use_raw_pipeline` controlla il dispatcher in `_fetch_folder`:
- `false` → path legacy (scrive direttamente in MESSAGE, whitelist CRM)
- `true` → path RAW (scrive in RAW, triage separato)

## Deploy graduale

| Fase | Azione | Risultato |
|------|--------|-----------|
| Flag OFF | Deploy codice + `-u` su prod | Zero regressioni, cron 82 legacy path |
| Verifica | 2 cicli cron 82 con flag OFF | 1,591 messages preservati, 0 RAW |
| Flip | SQL atomico: DELETE CASCADE + reset dates + flag ON | 1,591 messages cancellati |
| Backfill | Cron 82 scarica da 2026-04-01 | 1,763 RAW in 10 min |
| Triage | Cron 110 processa 100/run | 157 promoted, 43 discarded, 0 errori |
| TEST OK | Utente verifica Mail Hub | Email coerenti, pipeline stabile |

## Numeri post-flip (10 min)

| Metrica | Valore |
|---------|--------|
| RAW totali | 1,763 |
| RAW promoted | 157 |
| RAW discarded | 43 |
| RAW error | 0 |
| RAW pending | 1,563 |
| Messages creati | 157 |
| Messages con body | 62 |

Backfill in corso. Completamento stimato: ~02:00 ora italiana (80 min residui a 100/run ogni 5 min).

## Hotfix durante deploy

**Commit 4ee9ad2**: `_fetch_folder_raw` usava `self.env['casafolino.mail.raw']` senza `.sudo()`. Il cron gira come admin ma il contesto account non ha permessi create su RAW. Fix: `.sudo()` sul modello RAW.

Causa: ir.model.access.csv da `perm_create=0` per `base.group_user`. Il cron eredita il contesto dell'account, non del sistema.

## Commits branch

```
4ee9ad2 fix(mail): sudo() on RAW model in _fetch_folder_raw
6c30151 feat(mail): add use_raw_pipeline feature flag (default OFF)
1478aef fix(mail): register triage+cleanup crons in migration
20148af feat(mail): register triage + cleanup crons, bump to v18.0.13.0.0
b8c2056 feat(mail): rewrite _fetch_folder to populate RAW instead of MESSAGE
ddef59f feat(mail): add casafolino.mail.raw model + views + security
```

## Crons attivi in prod

| ID | Nome | Intervallo | Stato |
|----|------|-----------|-------|
| 82 | Mail Sync V2 | 5 min | attivo |
| 83 | Silent Partners | 1 giorno | attivo |
| 84 | AI Classify | 5 min | attivo |
| 85 | Body Fetch Pending | 10 min | attivo |
| 99 | Digest Mittenti | 1 settimana | attivo |
| 110 | Triage RAW | 5 min | attivo |
| 111 | Cleanup RAW | 1 giorno (03:00) | attivo |

## Rollback

### Scenario B — Rollback completo (post-flip, richiede DB restore)

```bash
# 1. Disable nuovi crons
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c \
  "UPDATE ir_cron SET active=false WHERE id IN (110, 111);"

# 2. Disable cron 82
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c \
  "UPDATE ir_cron SET active=false WHERE id=82;"

# 3. Restore DB da backup
gunzip -c /tmp/backup_prod_pre_flip_1777074924.sql.gz | \
  docker exec -i -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood

# 4. Restore codice
cd /home/ubuntu/casafolino-os && git checkout feat/mail-delete-template-v12
sudo rm -rf /docker/enterprise18/addons/custom/casafolino_mail
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/
docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http
docker restart odoo-app

# 5. Riattiva cron 82
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c \
  "UPDATE ir_cron SET active=true WHERE id=82;"
```

### Scenario C — Rollback parziale (torna a legacy senza restore DB)

```bash
# 1. Flip flag a false
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c \
  "UPDATE ir_config_parameter SET value='false' WHERE key='casafolino.use_raw_pipeline';"

# Effetti:
# - Cron 82 al prossimo run torna a scrivere in MESSAGE (legacy)
# - RAW esistenti restano, cron 111 li pulisce dopo 48h
# - Messages gia promossi restano dove sono
# - Mail Hub continua a funzionare
# - Triage RAW no-op (nessun nuovo pending)
```

## Backup disponibili

| File | Contenuto |
|------|-----------|
| `/tmp/backup_prod_pre_raw_deploy_1777073818.sql.gz` (76MB) | Pre-deploy codice V13 |
| `/tmp/backup_prod_pre_flip_1777074924.sql.gz` (76MB) | Pre-flip flag (1,591 messages) |
