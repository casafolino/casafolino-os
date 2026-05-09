# CasaFolino CRM Export — Scripts

## Inbound Lead Workflow

Script generico per creare partner + contatto + lead CRM + inviare mail template.
Idempotente: rilanciare con stessa email non duplica record.

### Prerequisiti

1. Modulo `casafolino_crm_export` aggiornato sul server (`-u casafolino_crm_export`)
2. Template mail registrato (es. `mail_template_inbound_it_dettaglio_gourmet`)
3. SSH key configurata (`~/.ssh/chieve_odoo_mac.pem`)

### Uso rapido (da Mac)

```bash
cd ~/casafolino-os/casafolino_crm_export/scripts
chmod +x inbound_lead.sh

# Preview (default: TEST_MODE=true)
./inbound_lead.sh \
  --partner "Nome Negozio SRL" \
  --contact "Nome Persona" \
  --email "info@negozio.it" \
  --phone "+39 333 1234567" \
  --street "Via Esempio 10" \
  --city "Reggio Emilia" \
  --zip "42100" \
  --state "Reggio Emilia" \
  --notes "Inbound dal modulo contatti Shopify 12/05/2026" \
  --tags "Inbound Shopify,Dettaglio gourmet,Gift / ceste regalo,Emilia-Romagna,IT" \
  --template "casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet"

# Invio reale (dopo verifica preview)
./inbound_lead.sh \
  --partner "Nome Negozio SRL" \
  --email "info@negozio.it" \
  --test-mode false
```

### Uso diretto sul server (via docker exec)

```bash
docker exec \
  -e PARTNER_NAME="Bottega del Gusto" \
  -e EMAIL="mario@bottegadelgusto.it" \
  -e CONTACT_NAME="Mario" \
  -e CITY="Bologna" \
  -e STATE_NAME="Bologna" \
  -e EXTRA_TAGS="Inbound Shopify,Dettaglio gourmet,Emilia-Romagna,IT" \
  -e TEMPLATE_XMLID="casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet" \
  -e TEST_MODE="true" \
  odoo-app bash -c "odoo shell -d folinofood --no-http < /docker/enterprise18/addons/custom/casafolino_crm_export/scripts/seed_inbound_lead.py"
```

### Parametri

| Parametro | Env var | Obbligatorio | Default |
|---|---|---|---|
| `--partner` | `PARTNER_NAME` | Si | — |
| `--email` | `EMAIL` | Si | — |
| `--template` | `TEMPLATE_XMLID` | Si* | inbound_it_dettaglio_gourmet |
| `--contact` | `CONTACT_NAME` | No | — |
| `--phone` | `PHONE` | No | — |
| `--street` | `STREET` | No | — |
| `--city` | `CITY` | No | — |
| `--zip` | `ZIP` | No | — |
| `--state` | `STATE_NAME` | No | — |
| `--country` | `COUNTRY_CODE` | No | IT |
| `--notes` | `NOTES` | No | — |
| `--tags` | `EXTRA_TAGS` | No | — |
| `--stage` | `STAGE_NAME` | No | Qualifica |
| `--owner` | `OWNER_LOGIN` | No | martina.sinopoli@casafolino.com |
| `--source` | `SOURCE_NAME` | No | Shopify Contact Form |
| `--medium` | `MEDIUM_NAME` | No | Website |
| `--description` | `LEAD_DESCRIPTION` | No | — |
| `--test-mode` | `TEST_MODE` | No | true |
| `--force-new-lead` | `FORCE_NEW_LEAD` | No | false |

*Il template ha un default nel bash helper ma e' obbligatorio nello script Python.

### Tag consigliati per profilo

| Profilo | Tags |
|---|---|
| Dettaglio gourmet IT | `Inbound Shopify,Dettaglio gourmet,Gift / ceste regalo,IT,<regione>` |
| HoReCa IT (futuro) | `Inbound,HoReCa,Ristoranti,IT,<regione>` |
| Distributore EU (futuro) | `Inbound,Distributore,Export,<paese>` |
| Private Label (futuro) | `Inbound,Private Label,<canale>,<paese>` |

### Output

Lo script produce output JSON strutturato con:
- `status`: `ok` | `blocker` | `error`
- `partner_id`, `lead_id`, `lead_url`
- `tags_applied`, `tags_created`
- `preview_path`: path HTML preview sul server
- `mail_sent`: dettagli invio (null se TEST_MODE)
- `warnings`: lista warning non bloccanti

### Script archivio

`seed_lead_angolo_via_canalino.py` — primo caso reale (Debora, Modena). Mantenuto come documentazione.
