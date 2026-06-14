# Migration Scripts — casafolino_mail

## 20260509_outbound_recipient_match.py

Re-triages existing mail where sender is internal (casafolino.com) but
partner was matched on the sender instead of the external recipient.

### Prerequisites

1. Module `casafolino_mail` must be updated first (`-u casafolino_mail`)
2. Backup PROD before running apply mode

### Dry-run (default — shows what would change, no writes)

```bash
docker exec odoo-app odoo shell -d folinofood --no-http <<'SHELL'
result = env['casafolino.mail.message'].migrate_outbound_match(dry_run=True)
print(result)
SHELL
```

Check logs for per-message detail:
```bash
docker logs odoo-app --tail=200 | grep migrate_outbound
```

### Apply (after reviewing dry-run output)

```bash
docker exec -e PGPASSWORD=odoo odoo-app pg_dump -h odoo-db -U odoo folinofood \
  > /tmp/backup_pre_outbound_migration_$(date +%Y%m%d_%H%M).sql

docker exec odoo-app odoo shell -d folinofood --no-http <<'SHELL'
result = env['casafolino.mail.message'].migrate_outbound_match(dry_run=False)
env.cr.commit()
print(result)
SHELL
```

### Idempotency

Safe to run multiple times. Already-triaged outbound messages (state in
`auto_keep`, `internal`) are skipped automatically.
