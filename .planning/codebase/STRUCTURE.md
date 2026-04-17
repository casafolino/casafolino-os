# Codebase Structure

**Analysis Date:** 2026-04-17

## Directory Layout

```
casafolino-os/
├── casafolino_commercial/      # GDO, Private Label, Treasury, Doc footers
├── casafolino_crm_export/      # Export CRM pipeline, samples, fairs
├── casafolino_haccp/           # HACCP registers, CCP, NC, quarantine, calibration
├── casafolino_kpi/             # KPI dashboard and snapshots
├── casafolino_labels/          # Label pipeline management
├── casafolino_mail/            # Email client, Agente 007, tracking
├── casafolino_operations/      # Production jobs, Mock Recall
├── casafolino_product/         # Allergens, Nutrition
├── casafolino_project/         # Project management (fairs, samples, launches)
├── casafolino_supplier_qual/   # Supplier qualification (BRC/IFS)
├── scripts/                    # Bank import/reconciliation scripts
├── docs/                       # Mockup HTML files
├── deploy.sh                   # Deploy script (references old module names)
├── build_all.py                # Legacy monolithic build file (not used in production)
├── fix_crm_v31.py              # One-time migration script
├── CLAUDE.md                   # Project instructions for Claude Code
└── .claude/CLAUDE.md           # Extended project instructions
```

## Standard Module Structure

Every `casafolino_*` module follows this Odoo 18 convention:

```
casafolino_<name>/
├── __init__.py              # Imports models/, wizard(s)/, controllers/
├── __manifest__.py          # Module metadata, depends, data files, assets
├── models/
│   ├── __init__.py          # Imports all model files
│   └── *.py                 # Model definitions
├── views/
│   ├── *_views.xml          # Form, list, kanban view definitions
│   └── menus.xml            # Actions + menu items (menus.xml or *_menus.xml)
├── security/
│   ├── ir.model.access.csv  # Access control lists
│   └── *_security.xml       # Security groups + record rules (optional)
├── data/
│   └── *.xml                # Cron jobs, sequences, seed data
├── report/
│   └── *.xml                # QWeb PDF report templates (optional)
├── static/
│   ├── description/
│   │   └── icon.png         # Module icon (required for root menuitem)
│   └── src/
│       ├── js/*.js          # OWL components
│       ├── xml/*.xml        # OWL templates
│       └── css/*.css        # Component stylesheets
├── wizard/ or wizards/
│   ├── __init__.py
│   └── *.py                 # TransientModel wizards
└── controllers/             # HTTP controllers (only casafolino_mail has this)
    ├── __init__.py
    └── *.py
```

## Directory Purposes

**`casafolino_commercial/`:**
- Purpose: GDO retail management, Private Label clients, Treasury/cash flow, document footers, sale discounts
- Models (9): `cf_gdo.py`, `cf_private_label.py`, `cf_treasury.py`, `cf_treasury_cashflow.py`, `cf_treasury_aml_ext.py`, `cf_treasury_analytics.py`, `sale_order_ext.py`, `cf_doc_footer.py`, `account_move_ext.py`
- OWL dashboards (4): Treasury dashboard, forecast, clients, categories
- Wizards (2): Treasury export, sale discount
- Key: Depends on Chart.js via CDN (prepended in manifest assets)

**`casafolino_crm_export/`:**
- Purpose: B2B export CRM pipeline with scoring, rotting, samples, fairs, certifications
- Models (4): `crm_lead.py` (extends `crm.lead`), `cf_export_sample.py`, `cf_export_fair.py`, `cf_export_sequence.py`
- No OWL components, CSS-only frontend

**`casafolino_haccp/`:**
- Purpose: Full HACCP management system: reception, production checks, CCP, NC, quarantine, calibration, documents, traceability
- Models (20): Largest model count of any module. Includes v2 registers (temperature, sanification, CCP log, labeling, traceability, pest control, training, hygiene)
- Extends: `stock.picking`, `mrp.production`, `product.template`
- OWL: HACCP dashboard
- Custom security groups in `cf_haccp_security.xml`

**`casafolino_kpi/`:**
- Purpose: Unified KPI dashboard aggregating data from sales, purchases, accounting, manufacturing, inventory
- Models (1): `cf_kpi_dashboard.py` (424 lines) - snapshot creation + RPC methods
- OWL: KPI dashboard with collapsible sections

**`casafolino_labels/`:**
- Purpose: Product label pipeline management
- Models (1): `cf_label.py`
- Simplest module, no OWL components

**`casafolino_mail/`:**
- Purpose: Gmail-style email client, dual IMAP system, AI contact enrichment (Agente 007), email tracking
- Models (13): Largest module. Two parallel systems - legacy (`cf_mail_*.py`) and Hub (`casafolino_mail_*.py`)
- Controllers (2): Tracking pixel + health check
- Wizards (3): Assign to lead/partner/user
- OWL (2): Mail client, lead mail widget
- Has `post_init_hook` for cron creation
- Only module with HTTP controllers
- Only module depending on another custom module (`casafolino_crm_export`)

**`casafolino_operations/`:**
- Purpose: Production calendar (job scheduling) and Mock Recall exercises
- Models (3): `cf_production_job.py`, `cf_recall_session.py`, `cf_recall_wizard.py`
- No OWL components

**`casafolino_product/`:**
- Purpose: EU+world allergen matrix with keyword auto-detection, nutritional values with external database import
- Models (4 files, many classes): `cf_allergen.py` (6 models), `cf_nutrition.py` (4 models), `cf_nutrition_regulation.py`, `cf_nutrition_wizard.py` (7 wizard models)
- OWL: Nutrition chart field widget
- Extends: `mrp.bom`, `mrp.bom.line`, `mrp.production`, `product.template`
- Has `post_init_hook` for cleaning up duplicate views from module merger

**`casafolino_project/`:**
- Purpose: Project management for samples, labels, fairs, product launches with templates and checklists
- Models (5): `cf_project.py` (extends `project.project`), `cf_project_task.py` (extends `project.task`), `cf_project_template.py`, `cf_project_shipment.py`, `cf_project_checklist.py`
- Custom security groups in `cf_project_security.xml`
- Has `post_init_hook` for fair alert cron creation

**`casafolino_supplier_qual/`:**
- Purpose: BRC/IFS supplier qualification with document tracking and periodic evaluations
- Models (3): `cf_supplier_qualification.py`, `cf_supplier_document.py`, `cf_supplier_evaluation.py`
- Extends: `res.partner` (adds qualification fields)
- OWL: Supplier dashboard
- Custom security groups in `cf_supplier_qual_security.xml`

## Key File Locations

**Entry Points:**
- `casafolino_*/views/menus.xml`: Root menu registration + action definitions per module
- `casafolino_project/views/cf_project_menus.xml`: Uses different naming convention
- `casafolino_labels/views/cf_label_menus.xml`: Uses different naming convention

**Configuration:**
- `casafolino_*/__manifest__.py`: Module metadata, dependencies, data file order, asset registration
- `casafolino_mail/data/cf_mail_config.xml`: Mail system configuration parameters
- `casafolino_mail/data/cf_utm_sources.xml`: UTM source definitions

**Core Logic (largest files):**
- `casafolino_mail/models/casafolino_mail_message_staging.py` (1656 lines): Mail Hub message model - IMAP fetch, thread grouping, auto-matching
- `casafolino_product/models/cf_nutrition.py` (1234 lines): Nutrition calculation engine, BOM aggregation
- `casafolino_mail/models/cf_mail_message.py` (969 lines): Legacy mail message model
- `casafolino_mail/models/cf_contact.py` (803 lines): res.partner extension with Agente 007 AI enrichment
- `casafolino_product/models/cf_allergen.py` (630 lines): Allergen detection, BOM scanning, keyword matching
- `casafolino_mail/models/cf_mail_account.py` (617 lines): Legacy IMAP account
- `casafolino_product/models/cf_nutrition_wizard.py` (602 lines): USDA/CIQUAL/CREA import wizards
- `casafolino_mail/models/casafolino_mail_account.py` (519 lines): Mail Hub IMAP account
- `casafolino_kpi/models/cf_kpi_dashboard.py` (424 lines): KPI aggregation across all modules
- `casafolino_commercial/models/cf_treasury.py` (399 lines): Treasury snapshot management
- `casafolino_crm_export/models/crm_lead.py` (375 lines): Export CRM lead extensions

**Security:**
- `casafolino_haccp/security/cf_haccp_security.xml`: HACCP user/manager groups
- `casafolino_project/security/cf_project_security.xml`: Project user/manager groups
- `casafolino_supplier_qual/security/cf_supplier_qual_security.xml`: Supplier qual groups
- `casafolino_mail/security/ir_rules.xml`: Record rules for mail access control

**Reports:**
- `casafolino_commercial/report/cf_doc_footer_report.xml`: Document footer template
- `casafolino_haccp/report/cf_haccp_report.xml`: HACCP inspection reports
- `casafolino_product/report/cf_nutrition_label_report.xml`: Nutritional label generation

**Scripts (non-module):**
- `scripts/fast_import.py`: Fast bank statement import
- `scripts/import_bank_statements.py`: Bank statement importer
- `scripts/reconcile_step1_map_partners.sql`: SQL for partner mapping
- `scripts/reconcile_step2_auto.py`: Auto-reconciliation
- `scripts/reconcile_step3_verify.sql`: Reconciliation verification

## Naming Conventions

**Files:**
- Model files: `cf_<domain>.py` or `casafolino_<domain>.py` (newer convention)
- View files: `cf_<domain>_views.xml`
- Menu files: `menus.xml` (standard) or `cf_<domain>_menus.xml` (variant)
- OWL JS: `cf_<domain>_<component>.js`
- OWL XML: `cf_<domain>_<component>.xml`
- CSS: `cf_<domain>.css`

**Directories:**
- Modules: `casafolino_<domain>/` (lowercase with underscores)
- Wizard directory: `wizard/` (singular, most modules) or `wizards/` (plural, casafolino_commercial)

**Models:**
- Custom models: `cf.<domain>.<entity>` (e.g., `cf.haccp.receipt`) or `casafolino.<domain>.<entity>` (newer, e.g., `casafolino.mail.account`)
- Inherited models: Use `_inherit` without `_name` to extend existing models

## Where to Add New Code

**New Feature in Existing Module:**
- Add model in `casafolino_<module>/models/<new_model>.py`
- Import in `casafolino_<module>/models/__init__.py`
- Add views in `casafolino_<module>/views/<new_model>_views.xml`
- Register in `__manifest__.py` `data` list (views AFTER security)
- Add security in `casafolino_<module>/security/ir.model.access.csv`
- Add menu items in existing `menus.xml` (actions BEFORE menuitems that reference them)

**New OWL Dashboard:**
- JS component: `casafolino_<module>/static/src/js/cf_<name>.js`
- XML template: `casafolino_<module>/static/src/xml/cf_<name>.xml`
- Register in `__manifest__.py` under `assets.web.assets_backend`
- Create `ir.actions.client` record with `tag` matching component registration
- Follow pattern: `static props = ["*"]`, `useState`, `onWillStart`, RPC calls

**New Module:**
- Create `casafolino_<name>/` at repository root
- Follow standard module structure (see template above)
- Add `static/description/icon.png` for root menu icon
- Use `web_icon` attribute on root `menuitem`
- Prefer `cf.<domain>.<entity>` naming for new models

**New Wizard:**
- Add in `casafolino_<module>/wizard/` (singular preferred)
- Create `TransientModel` class
- Add wizard view XML
- Register in `__init__.py` and `__manifest__.py`

**New HTTP Controller:**
- Currently only `casafolino_mail` has controllers
- Add in `casafolino_<module>/controllers/`
- Import in module `__init__.py`
- Use `auth='public'` for unauthenticated endpoints, `auth='user'` for backend

**New Cron Job:**
- Add XML in `casafolino_<module>/data/cf_<name>_cron.xml`
- Define method on the target model
- Register XML in `__manifest__.py` `data` list
- Alternative: create cron in `post_init_hook` (see casafolino_mail pattern)

## Special Directories

**`scripts/`:**
- Purpose: One-off bank import and reconciliation scripts
- Generated: No
- Committed: Yes
- Not an Odoo module; run manually via Python

**`docs/`:**
- Purpose: HTML mockup files
- Contains: `mockup_crm.html`
- Reference only, not deployed

**`.planning/`:**
- Purpose: GSD planning and codebase analysis documents
- Generated: Yes (by Claude Code)
- Committed: Yes

**`.claude/`:**
- Purpose: Claude Code configuration, commands, hooks
- Contains: `CLAUDE.md`, agents, commands, hooks
- Committed: Yes

**Root-level legacy files:**
- `build_all.py`, `build_complete.py`: Legacy monolithic build scripts (not used in production)
- `fix_crm_v31.py`: One-time CRM migration script
- `fix_icons.sql`: One-time SQL fix
- `deploy.sh`: Deploy script (references old module names, needs update)
- `*.html`, `*.md` (non-CLAUDE): Mockups and briefs

## Module Size Summary

| Module | Models (files) | Views | OWL Components | Wizards | Lines (largest file) |
|---|---|---|---|---|---|
| casafolino_mail | 13 | 7 | 2 | 3 | 1656 |
| casafolino_haccp | 20 | 13 | 1 | 1 | 165 |
| casafolino_product | 4 (many classes) | 5 | 1 | 4 files (7 classes) | 1234 |
| casafolino_commercial | 9 | 10 | 4 | 2 | 399 |
| casafolino_crm_export | 4 | 4 | 0 | 0 | 375 |
| casafolino_project | 5 | 7 | 0 | 0 | 331 |
| casafolino_kpi | 1 | 2 | 1 | 0 | 424 |
| casafolino_supplier_qual | 3 | 2 | 1 | 0 | 100 |
| casafolino_operations | 3 | 4 | 0 | 0 | (small) |
| casafolino_labels | 1 | 2 | 0 | 0 | (small) |

---

*Structure analysis: 2026-04-17*
