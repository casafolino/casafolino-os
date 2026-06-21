#!/usr/bin/env bash
# Housekeeping disco EC2 — prune immagini console (preserva running + :stage + :pre-s5 + 2 recenti),
# rotazione pg_dump (ultimi 3), df log + ALERT se >80%. System cron, nessun Odoo ir.cron, no downtime prod.
#
# Deploy: copia in /home/ubuntu/ops/disk_housekeeping.sh, chmod +x, cron giornaliero:
#   0 3 * * * /home/ubuntu/ops/disk_housekeeping.sh >> /home/ubuntu/ops/housekeeping.log 2>&1
# Consigliato: richiamarlo anche in coda al runbook di deploy console.
set -u
TS() { date '+%Y-%m-%d %H:%M:%S'; }
echo "[$(TS)] === housekeeping start ==="

# 1) IMAGE PRUNE — preserva immagine in esecuzione, :stage, :pre-s5 (rollback), 2 più recenti.
RUNNING=$(docker inspect -f '{{.Image}}' casafolino-console-prod 2>/dev/null || true)
PROTECTED=$(
  { echo "$RUNNING"
    docker images --no-trunc --format '{{.ID}} {{.Repository}}:{{.Tag}}' casafolino-console \
      | awk '$2 ~ /:(stage|pre-s5)$/ {print $1}'
    docker images --no-trunc --format '{{.ID}}' casafolino-console | awk '!s[$0]++' | head -2
  } | sort -u | grep -v '^$' )
docker images --format '{{.Repository}}:{{.Tag}}|{{.ID}}' casafolino-console | while IFS='|' read -r name id; do
  full=$(docker inspect -f '{{.Id}}' "$id" 2>/dev/null)
  if ! grep -qx "$full" <<< "$PROTECTED"; then
    docker rmi "$name" >/dev/null 2>&1 && echo "[$(TS)] rmi $name"
  fi
done
docker image prune -f >/dev/null 2>&1 && echo "[$(TS)] dangling pruned"
docker builder prune -f --keep-storage 2GB >/dev/null 2>&1 && echo "[$(TS)] build cache capped 2GB"

# 2) BACKUP ROTATION — tiene gli ultimi 3 pg_dump, cancella i più vecchi.
mapfile -t OLD < <(ls -1t /tmp/backup*.sql 2>/dev/null | tail -n +4)
for f in "${OLD[@]}"; do rm -f "$f" && echo "[$(TS)] rm backup $f"; done

# 3) DISK CHECK — df log + ALERT >80%.
USE=$(df --output=pcent / | tail -1 | tr -dc '0-9')
echo "[$(TS)] disk / = ${USE}%"
[ "${USE:-0}" -gt 80 ] && echo "[$(TS)] ALERT: disco / oltre 80% (${USE}%)"
echo "[$(TS)] === housekeeping done ==="
