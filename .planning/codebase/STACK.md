# Technology Stack

**Analysis Date:** 2026-04-17

## Languages

**Primary:**
- Python 3.10+ - All backend logic, Odoo models, controllers, wizards, cron jobs
- JavaScript (ES6+) - OWL frontend components for Odoo 18 backend views
- XML - Odoo view definitions, data records, menus, security rules, report templates

**Secondary:**
- CSS - Custom styling for OWL components and Odoo views
- SQL - Ad-hoc database maintenance scripts (referenced in `CLAUDE.md`)
- Bash - Deploy script `deploy.sh`

## Runtime

**Environment:**
- Odoo 18 Enterprise (Python framework + web server)
- Docker container `odoo-app` on AWS EC2 t3.large
- PostgreSQL 15 in Docker container `odoo-db`

**Package Manager:**
- pip (managed inside Docker image, no `requirements.txt` in repo)
- No lockfile in repo - dependencies come from the Odoo 18 Docker image

## Frameworks

**Core:**
- Odoo 18 Enterprise - Full ERP framework (ORM, web server, views, security, cron, mail)
- OWL (Odoo Web Library) - Reactive frontend framework bundled with Odoo 18

**Frontend Libraries:**
- Chart.js 4.4.0 - Loaded via CDN prepend in `casafolino_commercial/__manifest__.py` for treasury dashboards

**Build/Dev:**
- Odoo asset bundling system - All JS/CSS/XML registered via `__manifest__.py` `assets` key under `web.assets_backend`
- No separate webpack/vite/rollup - Odoo handles all asset compilation

## Key Dependencies

**Odoo Core Modules (depends in manifests):**
- `base` - Used by all 10 modules
- `mail` - Used by 9 modules (activity tracking, chatter)
- `product` - Used by 5 modules (casafolino_commercial, casafolino_product, casafolino_operations, casafolino_labels, casafolino_project)
- `sale_management` - Used by casafolino_commercial, casafolino_operations, casafolino_kpi
- `purchase` - Used by casafolino_commercial, casafolino_haccp, casafolino_operations, casafolino_supplier_qual, casafolino_kpi
- `account` - Used by casafolino_commercial, casafolino_kpi
- `mrp` - Used by casafolino_haccp, casafolino_operations, casafolino_product, casafolino_kpi
- `stock` - Used by casafolino_haccp, casafolino_operations, casafolino_supplier_qual, casafolino_kpi
- `crm` - Used by casafolino_mail, casafolino_crm_export
- `web` - Used by casafolino_mail (OWL client components)
- `utm` - Used by casafolino_mail (UTM source tracking)
- `project` - Used by casafolino_operations, casafolino_project
- `contacts` - Used by casafolino_crm_export

**Inter-module dependency:**
- `casafolino_mail` depends on `casafolino_crm_export` (CRM lead integration)

**Python Standard Library (heavily used):**
- `imaplib` / `smtplib` - IMAP/SMTP email sync in `casafolino_mail/models/casafolino_mail_account.py`
- `email` - Email parsing (headers, MIME) in multiple mail models
- `requests` - HTTP calls to external APIs (Groq, Serper, USDA, Open Food Facts, Telegram)
- `json` - API request/response handling
- `csv` - Data import scripts
- `xmlrpc.client` - Used in `scripts/import_bank_statements.py` for Odoo XML-RPC API
- `base64` - Attachment handling, tracking pixel
- `uuid` - Token generation for email tracking
- `re` - Pattern matching throughout

## Modules Overview

| Module | Version | Purpose |
|--------|---------|---------|
| `casafolino_commercial` | 18.0.2.1.0 | GDO retail, Private Label, Treasury (cash flow), Doc Footers |
| `casafolino_crm_export` | 18.0.2.0.0 | B2B export CRM pipeline with scoring, samples, fairs |
| `casafolino_haccp` | 18.0.2.0.0 | HACCP/BRC/IFS food safety management |
| `casafolino_kpi` | 18.0.1.0.0 | Unified KPI dashboard |
| `casafolino_labels` | 18.0.1.0.0 | Product label management pipeline |
| `casafolino_mail` | 5.0 | IMAP email client, AI enrichment (Agente 007), tracking |
| `casafolino_operations` | 18.0.1.0.0 | Production calendar, mock recall |
| `casafolino_product` | 18.0.1.1.0 | Allergens (EU+US), nutritional values |
| `casafolino_project` | 18.0.1.1.0 | Project management: samples, labels, fairs, launches |
| `casafolino_supplier_qual` | 18.0.1.0.0 | Supplier qualification workflows (BRC/IFS) |

## Configuration

**Environment:**
- API keys stored in `ir.config_parameter` (Odoo system parameters), not `.env` files
- Key parameters: `casafolino.groq_api_key`, `casafolino.serper_api_key`, `casafolino.usda_api_key`, `cf_haccp.telegram_bot_token`, `cf_haccp.telegram_chat_id`
- Database config: `web.base.url` defaults to `http://erp.casafolino.com:4589`
- IMAP credentials stored in `casafolino.mail.account` model fields

**Build:**
- No build step outside Odoo - assets compiled by Odoo's asset pipeline
- `__manifest__.py` in each module declares all assets under `web.assets_backend`
- Chart.js loaded via CDN prepend: `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js`

## Platform Requirements

**Development:**
- macOS (local repo at `/Users/antoniofolino/casafolino-os`)
- Git + SSH key for EC2 access (`~/.ssh/chieve_odoo_mac.pem`)
- No local Odoo instance needed - develop and push to EC2

**Production:**
- AWS EC2 t3.large (IP: `51.44.170.55`)
- Docker containers: `odoo-app` (Odoo 18) + `odoo-db` (PostgreSQL 15)
- Addons path inside container: `/mnt/extra-addons/custom/`
- Addons path on host: `/docker/enterprise18/addons/custom/`
- Git repo on server: `/home/ubuntu/casafolino-os/` (must `sudo cp -rf` to addons path after pull)
- Deploy script: `deploy.sh` (handles asset cache clear, module update, container restart)
- Staging DB: `folinofood_stage`
- Production DB: `folinofood`

---

*Stack analysis: 2026-04-17*
