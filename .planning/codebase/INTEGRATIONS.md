# External Integrations

**Analysis Date:** 2026-04-17

## APIs & External Services

**AI / LLM:**
- Groq API (LLaMA 3.3 70B) - AI contact enrichment (Agente 007) + email AI actions (translate, summarize, suggest reply, analyze, draft)
  - SDK/Client: `requests` + `urllib.request` (direct HTTP)
  - Endpoint: `https://api.groq.com/openai/v1/chat/completions`
  - Model: `llama-3.3-70b-versatile`
  - Auth: `casafolino.groq_api_key` in `ir.config_parameter`
  - Used in: `casafolino_mail/models/cf_contact.py` (Agente 007 enrichment), `casafolino_mail/models/cf_mail_message.py` (email AI actions)

**Web Search:**
- Serper.dev - Web search for contact/company enrichment
  - SDK/Client: `requests` (direct HTTP POST to `https://google.serper.dev/search`)
  - Auth: `casafolino.serper_api_key` in `ir.config_parameter`
  - Used in: `casafolino_mail/models/cf_contact.py`
  - Features: Country-specific search queries (IT, DE, AT, CH, GB, US, CA, FR, ES) targeting business registries (fatturatoitalia.it, northdata.de, companieshouse.gov.uk, societe.com, etc.)

**Nutrition Data:**
- USDA FoodData Central - Nutritional data lookup for food products
  - Endpoint: `https://api.nal.usda.gov/fdc/v1/foods/search`
  - Auth: `casafolino.usda_api_key` in `ir.config_parameter` (defaults to `DEMO_KEY`)
  - Used in: `casafolino_product/models/cf_nutrition.py`, `casafolino_product/models/cf_nutrition_wizard.py`
  - Data types: SR Legacy, Foundation, Branded

- Open Food Facts - Free nutritional data lookup
  - Endpoint: `https://world.openfoodfacts.org/cgi/search.pl`
  - Auth: None required (public API)
  - Used in: `casafolino_product/models/cf_nutrition.py`

**Messaging:**
- Telegram Bot API - HACCP reminders and alerts
  - Endpoint: `https://api.telegram.org/bot{token}/sendMessage`
  - Auth: `cf_haccp.telegram_bot_token` + `cf_haccp.telegram_chat_id` in `ir.config_parameter`
  - Used in: `casafolino_haccp/models/cf_haccp_reminder.py`
  - Sends HTML-formatted temperature check reminders to HACCP operators

## Email (IMAP/SMTP)

**Mail Hub - Primary email system:**
- IMAP (inbound) - Gmail and other providers
  - Client: Python `imaplib` (standard library)
  - Default host: `imap.gmail.com:993` (SSL)
  - Config model: `casafolino.mail.account` in `casafolino_mail/models/casafolino_mail_account.py`
  - Features: Inbox + Sent folder sync, UID-based incremental fetch, auto-detect sent folder, since-date filtering, company domain filtering (internal vs external)

- SMTP (outbound) - Gmail and other providers
  - Client: Python `smtplib` (standard library)
  - Default host: `smtp.gmail.com:587` (TLS)
  - Config model: `cf.mail.account` in `casafolino_mail/models/cf_mail_account.py`
  - Features: HTML email composition, attachment compression, tracking pixel injection

**Legacy email system (cf.mail.account):**
- Parallel model in `casafolino_mail/models/cf_mail_account.py` with IMAP + SMTP config
- Coexists with newer `casafolino.mail.account` (Mail Hub)

## Email Tracking

**Custom tracking system:**
- Open tracking: 1x1 transparent PNG pixel at `/cf/track/open/<token>`
- Click tracking: Link rewriting to `/cf/track/click/<token>?url=<target>` with 302 redirect
- Download tracking: Attachment downloads via `/cf/track/download/<token>/<attachment_id>`
- Controller: `casafolino_mail/controllers/tracking_controller.py`
- Tracking model: `casafolino_mail/models/casafolino_mail_tracking.py`
- Base URL: `web.base.url` parameter, falls back to `http://erp.casafolino.com:4589`

## Data Storage

**Database:**
- PostgreSQL 15
  - Docker container: `odoo-db`
  - Connection: Managed by Odoo ORM, no direct connection strings in code
  - Staging: `folinofood_stage`
  - Production: `folinofood`

**File Storage:**
- Odoo `ir.attachment` system (files stored in DB or filestore)
- No external file storage (S3, etc.)

**Caching:**
- Odoo built-in ORM cache only
- No Redis/Memcached

## Authentication & Identity

**Auth Provider:**
- Odoo built-in authentication (username/password)
- No external SSO/OAuth for users
- IMAP auth: App Passwords stored per-account in model fields

**Security:**
- Odoo record rules and access control lists (`ir.model.access.csv`)
- Security groups defined in: `casafolino_haccp/security/cf_haccp_security.xml`, `casafolino_supplier_qual/security/cf_supplier_qual_security.xml`, `casafolino_project/security/cf_project_security.xml`
- Mail account access: `casafolino_mail/security/ir_rules.xml`

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, etc.)

**Logs:**
- Python `logging` module throughout all models (`_logger = logging.getLogger(__name__)`)
- Docker container logs: `docker logs odoo-app`
- No centralized log aggregation

## CI/CD & Deployment

**Hosting:**
- AWS EC2 t3.large (`51.44.170.55`)
- Docker Compose (containers: `odoo-app` + `odoo-db`)
- Domain: `erp.casafolino.com` (port 4589)

**CI Pipeline:**
- None - No automated CI/CD
- Manual deploy flow: local git push -> SSH to EC2 -> git pull -> sudo cp to Docker addons -> module update -> restart

**Deploy script:** `deploy.sh`
- Clears Odoo asset cache from DB
- Runs `odoo -u MODULE --stop-after-init --no-http`
- Restarts `odoo-app` container

## Odoo XML-RPC API

**Internal scripting:**
- `scripts/import_bank_statements.py` - Imports bank statement lines via Odoo XML-RPC
  - Endpoint: `http://erp.casafolino.com:4589/xmlrpc/2/`
  - Used for Qonto and Revolut bank statement imports
- `scripts/reconcile_step2_auto.py` - Auto-reconciliation via XML-RPC

## Webhooks & Callbacks

**Incoming:**
- `/cf/track/open/<token>` - Email open tracking (public, no auth)
- `/cf/track/click/<token>` - Email click tracking (public, no auth)
- `/cf/track/download/<token>/<attachment_id>` - Attachment download tracking (public, no auth)

**Outgoing:**
- None detected

## Scheduled Jobs (Crons)

| Module | Cron File | Purpose |
|--------|-----------|---------|
| `casafolino_commercial` | `data/cf_treasury_cron.xml` | Treasury data sync |
| `casafolino_crm_export` | `data/cf_export_cron.xml` | Export pipeline automation |
| `casafolino_haccp` | `data/cf_haccp_reminder_cron.xml` | HACCP temperature reminders (Telegram) |
| `casafolino_kpi` | `data/cf_kpi_cron.xml` | KPI dashboard refresh |
| `casafolino_mail` | `data/cf_mail_cron.xml` | Email sync (IMAP fetch) |
| `casafolino_mail` | `data/casafolino_mail_hub_cron.xml` | Mail Hub sync |
| `casafolino_product` | `data/cf_nutrition_cron.xml` | Nutrition data sync |
| `casafolino_project` | `data/cf_fair_alert_cron.xml` | Fair deadline alerts |
| `casafolino_supplier_qual` | `data/cf_supplier_qual_cron.xml` | Supplier qualification checks |

## Related External Systems (Not in This Repo)

| System | URL | Stack |
|--------|-----|-------|
| HACCP App | `casafolino-haccp-rouge.vercel.app` | Next.js + Supabase |
| Treasury App | `casafolino-treasury.vercel.app` | React + Vite + Railway |
| Shopify Store | `casafolino.com` | Shopify (Mochi/Koto theme) |
| n8n Automation | Not specified | Shopify-Odoo sync, inventory, KPIs |

## Environment Configuration

**Required system parameters (ir.config_parameter):**
- `casafolino.groq_api_key` - Groq LLM API key (Agente 007 + email AI)
- `casafolino.serper_api_key` - Serper.dev web search key (Agente 007)
- `casafolino.usda_api_key` - USDA FoodData Central key (nutrition sync)
- `cf_haccp.telegram_bot_token` - Telegram bot token (HACCP reminders)
- `cf_haccp.telegram_chat_id` - Telegram chat ID (HACCP reminders)
- `web.base.url` - Base URL for tracking links

**Secrets location:**
- All API keys stored in Odoo `ir.config_parameter` table (database)
- IMAP passwords stored in `casafolino.mail.account` model fields (database)
- No `.env` files used

---

*Integration audit: 2026-04-17*
