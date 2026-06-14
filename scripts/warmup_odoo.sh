#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${CF_WARMUP_BASE_URL:-http://127.0.0.1:4589}"
DB="${CF_DB:-folinofood}"
ROUNDS="${CF_WARMUP_ROUNDS:-3}"
TIMEOUT="${CF_WARMUP_TIMEOUT:-60}"

URLS=(
  "erp.casafolino.com|/web/login"
  "erp.casafolino.com|/it/"
  "company.casafolino.com|/it/"
  "b2b.casafolino.com|/b2b"
  "erp.casafolino.com|/voice_ai/config?db=${DB}"
  "erp.casafolino.com|/voice_ai/outbound/next?db=${DB}"
)

echo "==> Attendo Odoo su ${BASE_URL}..."
for attempt in $(seq 1 60); do
  if curl -fsS -o /dev/null --max-time 5 -H "Host: erp.casafolino.com" "${BASE_URL}/web/login"; then
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    echo "Odoo non pronto dopo 60 tentativi" >&2
    exit 1
  fi
  sleep 2
done

for round in $(seq 1 "$ROUNDS"); do
  echo "==> Warmup round ${round}/${ROUNDS}"
  for entry in "${URLS[@]}"; do
    host="${entry%%|*}"
    path="${entry#*|}"
    code=$(curl -ksS -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" -H "Host: ${host}" "${BASE_URL}${path}" || true)
    echo "  ${host}${path} -> ${code}"
  done
done
