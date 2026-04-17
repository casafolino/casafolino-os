# Architecture

**Analysis Date:** 2026-04-17

## Pattern Overview

**Overall:** Odoo 18 Multi-Module Monolith (10 custom modules extending Odoo ERP)

**Key Characteristics:**
- Standard Odoo module architecture: Python models + XML views + OWL JS components
- Modules communicate via Odoo model inheritance (`_inherit`) and relational fields, not APIs
- Two parallel mail systems coexist: legacy `cf.mail.*` and newer `casafolino.mail.*` (Mail Hub)
- OWL client-side dashboards for real-time data visualization (KPI, Treasury, HACCP, Supplier)
- External API integrations (Groq LLM, Serper search, USDA/CIQUAL/CREA nutritional databases)

## Module Dependency Graph

```
base, mail, web (Odoo core)
  |
  +-- casafolino_commercial (sale_management, product, account, purchase)
  |     GDO retailers, Private Label, Treasury, Document footers, Sale discounts
  |
  +-- casafolino_crm_export (crm, sale, mail, contacts)
  |     Export pipeline, samples, fairs, certifications, sequences
  |     |
  |     +-- casafolino_mail (base, mail, web, utm, crm, casafolino_crm_export)
  |           IMAP email client, Agente 007 AI enrichment, email tracking
  |
  +-- casafolino_operations (base, mail, mrp, stock, purchase, sale_management, project)
  |     Production jobs, Mock Recall
  |
  +-- casafolino_product (base, mail, mrp, product)
  |     Allergens (EU 14 + world), Nutrition (USDA/CIQUAL/CREA), BOM analysis
  |
  +-- casafolino_haccp (base, mail, mrp, stock, purchase, product)
  |     HACCP registers, CCP monitoring, NC, quarantine, calibration, reception
  |
  +-- casafolino_kpi (base, mail, sale_management, purchase, account, mrp, stock)
  |     Cross-module KPI dashboard (reads from sale, purchase, account, mrp, stock)
  |
  +-- casafolino_supplier_qual (base, mail, purchase, stock)
  |     Supplier qualification, documents, evaluations (BRC/IFS)
  |
  +-- casafolino_project (project, mail, product)
  |     Project management: samples, labels, fairs, launches, shipments, checklists
  |
  +-- casafolino_labels (base, mail, product)
        Label pipeline management
```

**Cross-module dependency:** `casafolino_mail` depends on `casafolino_crm_export` (the only inter-custom-module dependency). All other modules depend only on Odoo core modules.

## Layers

**Python Model Layer (Business Logic):**
- Purpose: Define data models, business rules, computed fields, state machines, cron jobs
- Location: `casafolino_*/models/*.py`
- Contains: Odoo `Model` and `TransientModel` classes
- Depends on: Odoo ORM, external APIs (Groq, Serper, USDA)
- Used by: XML views, OWL components via RPC

**XML View Layer (Server-Side UI):**
- Purpose: Define form/list/kanban views, actions, menus, view inheritance
- Location: `casafolino_*/views/*.xml`
- Contains: `ir.ui.view`, `ir.actions.act_window`, `ir.actions.client`, `menuitem` records
- Depends on: Model layer (field definitions)
- Used by: Odoo web client for rendering standard CRUD interfaces

**OWL Component Layer (Client-Side UI):**
- Purpose: Rich dashboards and interactive widgets beyond standard Odoo views
- Location: `casafolino_*/static/src/js/*.js` + `casafolino_*/static/src/xml/*.xml`
- Contains: OWL Components registered as `ir.actions.client` or field widgets
- Depends on: `@odoo/owl`, `@web/core/network/rpc`, `@web/core/registry`
- Used by: Menu actions with `tag` pointing to component name

**Controller Layer (HTTP Routes):**
- Purpose: Public HTTP endpoints (email tracking pixel, health check)
- Location: `casafolino_mail/controllers/*.py`
- Contains: `http.Controller` classes with `@http.route` decorators
- Routes:
  - `/cf/track/open/<token>` - email open tracking (returns 1x1 pixel)
  - `/cf/track/click/<token>` - email click tracking (302 redirect)
  - `/cf/track/attachment/<token>/<filename>` - attachment download tracking
  - `/cf/ping` - health check endpoint

**Wizard Layer (Transient Models):**
- Purpose: Multi-step user workflows and data import wizards
- Location: `casafolino_*/wizard/*.py` or `casafolino_*/wizards/*.py`
- Contains: `TransientModel` classes for temporary data processing
- Key wizards:
  - `casafolino_commercial/wizards/cf_treasury_export.py` - Treasury CSV/XLSX export
  - `casafolino_commercial/wizards/sale_discount_wizard.py` - Sale discount application
  - `casafolino_haccp/wizard/cf_haccp_receipt_wizard.py` - HACCP receipt processing
  - `casafolino_mail/wizard/casafolino_mail_assign_lead.py` - Assign email to CRM lead
  - `casafolino_mail/wizard/casafolino_mail_assign_partner.py` - Assign email to partner
  - `casafolino_mail/wizard/casafolino_mail_assign_user.py` - Assign email to user
  - `casafolino_product/models/cf_nutrition_wizard.py` - USDA/CIQUAL/CREA nutritional data import

**Data Layer (Static Configuration):**
- Purpose: Seed data, cron schedules, sequences, configuration parameters
- Location: `casafolino_*/data/*.xml`
- Contains: `ir.cron`, `ir.sequence`, `ir.config_parameter` records, allergen master data

**Report Layer (PDF Generation):**
- Purpose: QWeb PDF reports
- Location: `casafolino_*/report/*.xml`
- Reports: Document footers (commercial), HACCP reports, Nutrition labels

**Security Layer:**
- Purpose: Access control lists and record rules
- Location: `casafolino_*/security/`
- Contains: `ir.model.access.csv` (ACLs), `*_security.xml` (groups + record rules)
- Custom security groups: HACCP (`cf_haccp_security.xml`), Project (`cf_project_security.xml`), Supplier (`cf_supplier_qual_security.xml`)

## Odoo Standard Model Inheritance Map

These modules extend Odoo core models via `_inherit`:

| Odoo Model | Extended By | File |
|---|---|---|
| `res.partner` | casafolino_mail | `casafolino_mail/models/cf_contact.py` |
| `res.partner` | casafolino_commercial | `casafolino_commercial/models/cf_gdo.py` |
| `res.partner` | casafolino_commercial | `casafolino_commercial/models/cf_private_label.py` |
| `res.partner` | casafolino_supplier_qual | `casafolino_supplier_qual/models/cf_supplier_qualification.py` |
| `crm.lead` | casafolino_crm_export | `casafolino_crm_export/models/crm_lead.py` |
| `crm.lead` | casafolino_mail | `casafolino_mail/models/crm_lead_ext.py` |
| `mrp.bom` | casafolino_product | `casafolino_product/models/cf_allergen.py` |
| `mrp.bom` | casafolino_product | `casafolino_product/models/cf_nutrition.py` |
| `mrp.bom.line` | casafolino_product | `casafolino_product/models/cf_allergen.py` |
| `mrp.production` | casafolino_product | `casafolino_product/models/cf_allergen.py` |
| `mrp.production` | casafolino_haccp | `casafolino_haccp/models/cf_haccp_sp.py` |
| `mrp.production` | casafolino_haccp | `casafolino_haccp/models/cf_haccp_ccp_log.py` |
| `mrp.production` | casafolino_haccp | `casafolino_haccp/models/cf_haccp_production_extend.py` |
| `product.template` | casafolino_product | `casafolino_product/models/cf_allergen.py` |
| `product.template` | casafolino_product | `casafolino_product/models/cf_nutrition.py` |
| `product.template` | casafolino_haccp | `casafolino_haccp/models/cf_haccp_raw_material.py` |
| `stock.picking` | casafolino_haccp | `casafolino_haccp/models/cf_haccp_receipt.py` |
| `stock.picking` | casafolino_haccp | `casafolino_haccp/models/cf_haccp_picking_extend.py` |
| `sale.order` | casafolino_commercial | `casafolino_commercial/models/sale_order_ext.py` |
| `account.move` | casafolino_commercial | `casafolino_commercial/models/account_move_ext.py` |
| `account.move.line` | casafolino_commercial | `casafolino_commercial/models/cf_treasury_aml_ext.py` |
| `project.project` | casafolino_project | `casafolino_project/models/cf_project.py` |
| `project.task` | casafolino_project | `casafolino_project/models/cf_project_task.py` |

## Data Flow

**Email Ingestion (Mail Hub):**
1. Cron `_cron_fetch_all_accounts()` runs every 2 hours on `casafolino.mail.account`
2. IMAP connection fetches new emails since `last_fetch_uid` from `casafolino_mail/models/casafolino_mail_account.py`
3. Messages stored as `casafolino.mail.message` records in `casafolino_mail/models/casafolino_mail_message_staging.py`
4. Auto-matching links messages to `res.partner` via sender email
5. Sender rules (`cf.mail.sender.rule`) auto-categorize or discard messages
6. Wizards allow manual assignment to leads/partners/users

**Email Tracking:**
1. Outbound emails embed tracking pixel `<img src="/cf/track/open/<token>">` and rewrite links
2. Controller at `casafolino_mail/controllers/tracking_controller.py` logs opens/clicks
3. Events stored in `casafolino.mail.tracking` model

**Legacy Mail System (cf.mail.*):**
1. `cf.mail.account` defines email accounts with IMAP config
2. `cf.mail.message` stores messages with CRM integration via `casafolino_mail/models/cf_mail_crm.py`
3. `cf.mail.compose` handles outbound email composition

**KPI Dashboard Data Aggregation:**
1. Cron creates `cf.kpi.snapshot` records periodically
2. `casafolino_kpi/models/cf_kpi_dashboard.py` (424 lines) queries across `sale.order`, `purchase.order`, `account.move`, `mrp.production`, `stock.picking`
3. OWL dashboard calls RPC to retrieve snapshot data and renders charts

**Treasury Cash Flow:**
1. `cf.treasury.snapshot` in `casafolino_commercial/models/cf_treasury.py` captures financial state
2. `cf_treasury_analytics.py` extends snapshots with analytics
3. `cf_treasury_cashflow.py` models individual cash flow lines
4. `cf_treasury_aml_ext.py` extends `account.move.line` for treasury categorization
5. Four OWL dashboards: main dashboard, forecast, clients, categories

**HACCP Process:**
1. `stock.picking` (incoming) triggers HACCP reception checks via `cf_haccp_picking_extend.py`
2. `mrp.production` triggers production CCP checks via `cf_haccp_production_extend.py`
3. Non-conformities (`cf.haccp.nc`) can trigger quarantine (`cf.haccp.quarantine`)
4. Reminder cron sends alerts for pending inspections/calibrations

**Nutrition Calculation:**
1. `mrp.bom` extended with nutrition data per ingredient
2. `cf.nutrition.ingredient` holds per-ingredient nutritional values
3. `cf.nutrition.bom` aggregates BOM-level nutrition from ingredients
4. External database wizards (USDA, CIQUAL, CREA) import nutritional data via API
5. Allergen auto-detection scans ingredient names against keyword database

**State Management:**
- Server-side: Odoo ORM fields with `Selection` fields for state machines (e.g., `state = fields.Selection([('draft','Draft'),('confirmed','Confirmed'),...])`)
- Client-side: OWL `useState()` for component-local state in dashboards

## Key Abstractions

**Dual Mail System:**
- Legacy: `cf.mail.account` / `cf.mail.message` / `cf.mail.compose` (in `cf_mail_*.py`)
- Mail Hub: `casafolino.mail.account` / `casafolino.mail.message` (in `casafolino_mail_*.py`)
- Both coexist; Mail Hub is the newer, more feature-rich system with thread grouping

**OWL Dashboard Pattern:**
- All dashboards follow the same structure: `Component` with `static template`, `static props = ["*"]`, `useState`, `onWillStart` calling RPC
- Registered via `registry.category("actions").add("tag_name", Component)`
- Backed by `ir.actions.client` XML records with matching `tag`
- Dashboard components: `cf_kpi_dashboard`, `cf_haccp_dashboard`, `cf_supplier_dashboard`, `cf_treasury_dashboard`, `cf_treasury_forecast`, `cf_treasury_clients`, `cf_treasury_categories`

**Cron-Driven Automation:**
- Most modules use `ir.cron` for periodic processing
- Pattern: model method decorated for cron invocation via `code` field
- Active crons: mail fetch, mail cleanup, treasury sync, export lead scoring, HACCP reminders, nutrition auto-compute, KPI snapshots, fair alerts, supplier qualification

## Entry Points

**Odoo Web Client (Backend):**
- Location: Each module registers root `menuitem` in `views/menus.xml`
- Menu hierarchy: Root menu per module -> sub-menus -> actions
- Root menus: Mail (seq 15), KPI (seq 10), Export CRM (seq 20), Fornitori Qualificati (seq 32), HACCP, Commercial, Product, Operations, Project, Labels

**HTTP Controllers:**
- Location: `casafolino_mail/controllers/`
- Public routes (no auth required): `/cf/track/*`, `/cf/ping`

**Cron Entry Points:**
- Treasury: `casafolino_commercial/data/cf_treasury_cron.xml`
- Export CRM: `casafolino_crm_export/data/cf_export_cron.xml`
- HACCP: `casafolino_haccp/data/cf_haccp_reminder_cron.xml`
- KPI: `casafolino_kpi/data/cf_kpi_cron.xml`
- Mail: `casafolino_mail/data/cf_mail_cron.xml` + post_init_hook crons
- Nutrition: `casafolino_product/data/cf_nutrition_cron.xml`
- Project: `casafolino_project/data/cf_fair_alert_cron.xml`
- Supplier: `casafolino_supplier_qual/data/cf_supplier_qual_cron.xml`

## Error Handling

**Strategy:** Standard Odoo patterns with `UserError` for user-facing errors, `_logger` for background operations.

**Patterns:**
- User actions: `raise UserError(_("message"))` from `odoo.exceptions`
- Cron/background: `try/except` with `_logger.warning()` or `_logger.error()`, continue processing
- IMAP operations: Catch `imaplib` errors, log and skip individual messages
- External API calls: Catch `requests` exceptions, log errors, return gracefully

## Cross-Cutting Concerns

**Logging:** `import logging; _logger = logging.getLogger(__name__)` in every model file
**Validation:** Odoo `@api.constrains` decorators and `_check_*` methods
**Authentication:** Odoo session-based auth for backend; `auth='public'` for tracking endpoints
**Mail Thread:** Most custom models inherit `mail.thread` for chatter/activity support
**Branding:** `#5A6E3A` green accent throughout CSS and OWL templates

---

*Architecture analysis: 2026-04-17*
