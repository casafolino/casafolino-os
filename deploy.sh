#!/bin/bash
# deploy.sh — CasaFolino OS deploy su AWS EC2
# Uso: ./deploy.sh [modulo]   (senza argomenti = aggiorna tutti i moduli)

set -e

DB="${CF_DB:-folinofood_stage}"
CONTAINER="odoo-app"

MODULES=(
    casafolino_mail
    casafolino_mail_stats
    casafolino_mail_templates
    casafolino_followup_tuttofood
    casafolino_project
    casafolino_initiative
    casafolino_initiative_dashboard
    casafolino_crm_export
    casafolino_commercial
    casafolino_product
    casafolino_operations
    casafolino_haccp
    casafolino_kpi
    casafolino_supplier_qual
    casafolino_home
    casafolino_workspace
    casafolino_fair_report
    casafolino_labels
)

if [ -n "$1" ]; then
    MOD_LIST="$1"
else
    MOD_LIST=$(IFS=,; echo "${MODULES[*]}")
fi

echo "==> Deploy su DB: $DB"
echo "==> Moduli: $MOD_LIST"

# Pulisci asset cache
echo "==> Pulizia asset cache..."
docker exec odoo-db psql -U odoo -d "$DB" \
    -c "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';" 2>/dev/null || true

# Update moduli
echo "==> Aggiornamento moduli..."
docker exec "$CONTAINER" odoo \
    -d "$DB" \
    -u "$MOD_LIST" \
    --stop-after-init \
    --no-http

# Restart
echo "==> Restart container..."
docker restart "$CONTAINER"

echo "==> Deploy completato."
