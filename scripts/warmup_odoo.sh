#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${CF_WARMUP_BASE_URL:-http://127.0.0.1:4589}"
DB="${CF_DB:-folinofood}"
ROUNDS="${CF_WARMUP_ROUNDS:-3}"
TIMEOUT="${CF_WARMUP_TIMEOUT:-60}"
READY_TIMEOUT="${CF_WARMUP_READY_TIMEOUT:-${TIMEOUT}}"

URLS=(
  "erp.casafolino.com|/web/login"
  "erp.casafolino.com|/it/"
  "company.casafolino.com|/it/"
  "b2b.casafolino.com|/b2b"
)

echo "==> Attendo Odoo su ${BASE_URL}..."
for attempt in $(seq 1 20); do
  if curl -fsS -o /dev/null --connect-timeout 3 --max-time "$READY_TIMEOUT" -H "Host: erp.casafolino.com" "${BASE_URL}/web/login"; then
    break
  fi
  if [ "$attempt" -eq 20 ]; then
    echo "Odoo non pronto dopo 20 tentativi" >&2
    exit 1
  fi
  sleep 5
done

for round in $(seq 1 "$ROUNDS"); do
  echo "==> Warmup round ${round}/${ROUNDS}"
  for entry in "${URLS[@]}"; do
    host="${entry%%|*}"
    path="${entry#*|}"
    code=$(curl -ksS -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time "$TIMEOUT" -H "Host: ${host}" "${BASE_URL}${path}" || true)
    echo "  ${host}${path} -> ${code}"
  done
done
