#!/usr/bin/env bash
#
# inbound_lead.sh — Helper CLI per il workflow Inbound Lead CasaFolino
#
# Wrapper che lancia seed_inbound_lead.py sul server EC2 via SSH + docker exec.
# Tutti i parametri vengono passati come env vars al container Odoo.
#
# Requisiti:
#   - SSH key: ~/.ssh/chieve_odoo_mac.pem
#   - Server: ubuntu@51.44.170.55
#   - Script copiato in: /docker/enterprise18/addons/custom/casafolino_crm_export/scripts/
#
set -euo pipefail

SSH_KEY="${SSH_KEY:-$HOME/.ssh/chieve_odoo_mac.pem}"
SSH_HOST="${SSH_HOST:-ubuntu@51.44.170.55}"
DB="${DB:-folinofood}"
SCRIPT_PATH="/docker/enterprise18/addons/custom/casafolino_crm_export/scripts/seed_inbound_lead.py"

# Defaults
PARTNER_NAME=""
EMAIL=""
CONTACT_NAME=""
PHONE=""
STREET=""
CITY=""
ZIP=""
STATE_NAME=""
COUNTRY_CODE="IT"
NOTES=""
EXTRA_TAGS=""
TEMPLATE_XMLID="casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet"
STAGE_NAME="Qualifica"
OWNER_LOGIN="martina.sinopoli@casafolino.com"
SOURCE_NAME="Shopify Contact Form"
MEDIUM_NAME="Website"
LEAD_DESCRIPTION=""
TEST_MODE="true"
FORCE_NEW_LEAD="false"

usage() {
    cat <<'USAGE'
Usage: inbound_lead.sh [OPTIONS]

Required:
  --partner NAME         Nome attivita/azienda
  --email EMAIL          Email contatto

Optional:
  --contact NAME         Nome persona di contatto
  --phone PHONE          Telefono
  --street STREET        Indirizzo
  --city CITY            Citta
  --zip ZIP              CAP
  --state STATE          Provincia (es. "Bologna", "Modena")
  --country CODE         Codice paese (default: IT)
  --notes TEXT           Note interne
  --tags CSV             Tag separati da virgola (es. "Inbound,Dettaglio gourmet,IT")
  --template XMLID       XML ID template mail (default: inbound_it_dettaglio_gourmet)
  --stage NAME           Stage CRM (default: Qualifica)
  --owner LOGIN          Login owner Odoo (default: martina.sinopoli@casafolino.com)
  --source NAME          UTM source (default: Shopify Contact Form)
  --medium NAME          UTM medium (default: Website)
  --description TEXT     Messaggio originale del contatto
  --test-mode true|false Preview only o invio reale (default: true)
  --force-new-lead       Forza creazione nuovo lead anche se esiste
  --db DATABASE          Database Odoo (default: folinofood)
  --help                 Mostra questo help

Examples:
  # Preview mode (default)
  ./inbound_lead.sh \
    --partner "Bottega del Gusto" \
    --email "mario@bottegadelgusto.it" \
    --contact "Mario" \
    --city "Bologna" \
    --state "Bologna" \
    --tags "Inbound Shopify,Dettaglio gourmet,Emilia-Romagna,IT"

  # Invio reale
  ./inbound_lead.sh \
    --partner "Bottega del Gusto" \
    --email "mario@bottegadelgusto.it" \
    --test-mode false
USAGE
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --partner)      PARTNER_NAME="$2"; shift 2;;
        --email)        EMAIL="$2"; shift 2;;
        --contact)      CONTACT_NAME="$2"; shift 2;;
        --phone)        PHONE="$2"; shift 2;;
        --street)       STREET="$2"; shift 2;;
        --city)         CITY="$2"; shift 2;;
        --zip)          ZIP="$2"; shift 2;;
        --state)        STATE_NAME="$2"; shift 2;;
        --country)      COUNTRY_CODE="$2"; shift 2;;
        --notes)        NOTES="$2"; shift 2;;
        --tags)         EXTRA_TAGS="$2"; shift 2;;
        --template)     TEMPLATE_XMLID="$2"; shift 2;;
        --stage)        STAGE_NAME="$2"; shift 2;;
        --owner)        OWNER_LOGIN="$2"; shift 2;;
        --source)       SOURCE_NAME="$2"; shift 2;;
        --medium)       MEDIUM_NAME="$2"; shift 2;;
        --description)  LEAD_DESCRIPTION="$2"; shift 2;;
        --test-mode)    TEST_MODE="$2"; shift 2;;
        --force-new-lead) FORCE_NEW_LEAD="true"; shift;;
        --db)           DB="$2"; shift 2;;
        --help|-h)      usage;;
        *)              echo "Unknown option: $1"; usage;;
    esac
done

# Validate required
if [[ -z "$PARTNER_NAME" ]]; then
    echo "ERROR: --partner is required"
    exit 1
fi
if [[ -z "$EMAIL" ]]; then
    echo "ERROR: --email is required"
    exit 1
fi

echo "========================================"
echo "INBOUND LEAD — $PARTNER_NAME"
echo "Email: $EMAIL"
echo "Template: $TEMPLATE_XMLID"
echo "Test mode: $TEST_MODE"
echo "DB: $DB"
echo "========================================"
echo ""

# Build docker exec env flags
ENV_FLAGS=""
ENV_FLAGS="$ENV_FLAGS -e PARTNER_NAME=$(printf '%q' "$PARTNER_NAME")"
ENV_FLAGS="$ENV_FLAGS -e EMAIL=$(printf '%q' "$EMAIL")"
ENV_FLAGS="$ENV_FLAGS -e TEMPLATE_XMLID=$(printf '%q' "$TEMPLATE_XMLID")"
ENV_FLAGS="$ENV_FLAGS -e TEST_MODE=$(printf '%q' "$TEST_MODE")"
ENV_FLAGS="$ENV_FLAGS -e STAGE_NAME=$(printf '%q' "$STAGE_NAME")"
ENV_FLAGS="$ENV_FLAGS -e OWNER_LOGIN=$(printf '%q' "$OWNER_LOGIN")"
ENV_FLAGS="$ENV_FLAGS -e SOURCE_NAME=$(printf '%q' "$SOURCE_NAME")"
ENV_FLAGS="$ENV_FLAGS -e MEDIUM_NAME=$(printf '%q' "$MEDIUM_NAME")"
ENV_FLAGS="$ENV_FLAGS -e COUNTRY_CODE=$(printf '%q' "$COUNTRY_CODE")"
ENV_FLAGS="$ENV_FLAGS -e FORCE_NEW_LEAD=$(printf '%q' "$FORCE_NEW_LEAD")"

[[ -n "$CONTACT_NAME" ]]    && ENV_FLAGS="$ENV_FLAGS -e CONTACT_NAME=$(printf '%q' "$CONTACT_NAME")"
[[ -n "$PHONE" ]]           && ENV_FLAGS="$ENV_FLAGS -e PHONE=$(printf '%q' "$PHONE")"
[[ -n "$STREET" ]]          && ENV_FLAGS="$ENV_FLAGS -e STREET=$(printf '%q' "$STREET")"
[[ -n "$CITY" ]]            && ENV_FLAGS="$ENV_FLAGS -e CITY=$(printf '%q' "$CITY")"
[[ -n "$ZIP" ]]             && ENV_FLAGS="$ENV_FLAGS -e ZIP=$(printf '%q' "$ZIP")"
[[ -n "$STATE_NAME" ]]      && ENV_FLAGS="$ENV_FLAGS -e STATE_NAME=$(printf '%q' "$STATE_NAME")"
[[ -n "$NOTES" ]]           && ENV_FLAGS="$ENV_FLAGS -e NOTES=$(printf '%q' "$NOTES")"
[[ -n "$EXTRA_TAGS" ]]      && ENV_FLAGS="$ENV_FLAGS -e EXTRA_TAGS=$(printf '%q' "$EXTRA_TAGS")"
[[ -n "$LEAD_DESCRIPTION" ]] && ENV_FLAGS="$ENV_FLAGS -e LEAD_DESCRIPTION=$(printf '%q' "$LEAD_DESCRIPTION")"

# Build SSH command
CMD="docker exec $ENV_FLAGS odoo-app bash -c 'odoo shell -d $DB --no-http < $SCRIPT_PATH'"

echo "Connecting to $SSH_HOST..."
echo ""

ssh -i "$SSH_KEY" "$SSH_HOST" "$CMD"

echo ""
echo "Done."
