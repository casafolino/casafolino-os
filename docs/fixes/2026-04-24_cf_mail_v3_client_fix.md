# Fix: KeyNotFoundError cf_mail_v3_client

**Date:** 2026-04-24
**Module:** casafolino_mail v18.0.12.8.0
**Severity:** P1 — menu navigation completely broken

## Diagnosis

**Scenario:** Missing files on server (not orphan DB, not tag rename)

The entire `casafolino_mail/` directory was absent from `/docker/enterprise18/addons/custom/` on the EC2 server. The DB (both stage and prod) had correct records:
- `ir_act_client` id=1631 (prod) / 1661 (stage), tag=`cf_mail_v3_client`
- `ir_ui_menu` pointing to the action
- `ir_model_data` linking module `casafolino_mail` to the action

The git repo on the server had the code on branch `feat/mail-delete-template-v12` (V12.8.0), but the `sudo cp -rf` step was never executed after `git pull`. This is the known gap documented in CLAUDE.md: "Git pull says 'Already up to date' but server runs old code — these are different directories."

## Root Cause

After pushing V12.8.0 commits and running `git pull` on the server, the `sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/` step was skipped. Odoo's asset bundler could not find the JS file that registers `cf_mail_v3_client` in the OWL actions registry, causing a `KeyNotFoundError` when any menu tried to load the mail client.

## Commands Executed

```bash
# Stage
docker exec -e PGPASSWORD=odoo odoo-db psql -U odoo -d folinofood_stage \
  -c "UPDATE ir_cron SET active=false WHERE id IN (82,83,84);"
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo folinofood_stage | gzip > /tmp/backup_stage_pre_fix_*.sql.gz
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http
docker exec -e PGPASSWORD=odoo odoo-db psql -U odoo -d folinofood_stage \
  -c "DELETE FROM ir_attachment WHERE name LIKE 'web.assets_%';"
docker restart odoo-app
# Verified: action exists, JS registered, no errors

# Prod
docker exec -e PGPASSWORD=odoo odoo-db psql -U odoo -d folinofood \
  -c "UPDATE ir_cron SET active=false WHERE id IN (82,83,84);"
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo folinofood | gzip > /tmp/backup_prod_pre_fix_*.sql.gz
docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http
docker exec -e PGPASSWORD=odoo odoo-db psql -U odoo -d folinofood \
  -c "DELETE FROM ir_attachment WHERE name LIKE 'web.assets_%';"
docker restart odoo-app
docker exec -e PGPASSWORD=odoo odoo-db psql -U odoo -d folinofood \
  -c "UPDATE ir_cron SET active=true WHERE id IN (82,83,84);"
docker exec -e PGPASSWORD=odoo odoo-db psql -U odoo -d folinofood_stage \
  -c "UPDATE ir_cron SET active=true WHERE id IN (82,83,84);"
```

## Verification

| Check | Result |
|-------|--------|
| `ir_act_client` tag=cf_mail_v3_client exists prod | id=1631 |
| Menu "La Mia Casella" points to action 1631 | OK |
| JS file in container | registry.category("actions").add("cf_mail_v3_client", ...) |
| Module update — no errors | "Modules loaded" |
| Crons 82/83/84 re-enabled | active=true, nextcall scheduled |
| Docker logs — no errors post-restart | Clean |

## Prevention

Always run the full deploy sequence after `git pull`:
```bash
cd /home/ubuntu/casafolino-os && git pull && \
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d DB_NAME -u casafolino_mail --stop-after-init --no-http
```

No code changes required. Fix was operational (file copy), not code.
