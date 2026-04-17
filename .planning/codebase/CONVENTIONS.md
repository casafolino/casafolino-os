# Coding Conventions

**Analysis Date:** 2026-04-17

## Naming Patterns

**Odoo Model Names (Python `_name`):**
- Prefix `cf.` for most models: `cf.gdo.retailer`, `cf.haccp.nc`, `cf.treasury.snapshot`
- Full prefix `casafolino.` for some newer models: `casafolino.supplier.qualification`, `casafolino.mail.message`, `casafolino.mail.account`
- Mixed convention exists -- use `cf.` prefix for new models unless the sub-module already uses `casafolino.`

**Python Files:**
- Snake_case with `cf_` prefix: `cf_gdo.py`, `cf_haccp_nc.py`, `cf_treasury.py`
- Newer mail module uses `casafolino_mail_*.py` for some files alongside `cf_mail_*.py`
- Inheritance extension files: `{original_model}_ext.py` (e.g., `sale_order_ext.py`, `account_move_ext.py`, `crm_lead_ext.py`)

**Python Fields:**
- Custom fields use `cf_` prefix on inherited models: `cf_market`, `cf_lead_score`, `cf_rotting_days`, `cf_job_title`
- Agente 007 fields use `cf_007_` prefix: `cf_007_enriched`, `cf_007_fatturato`, `cf_007_mercati`
- Native model fields (non-inherited) do NOT use `cf_` prefix: `state`, `name`, `partner_id`, `notes`

**Selection field keys:**
- Lowercase snake_case: `('supermarket', 'Supermercato')`, `('ok', 'OK')`, `('warning', 'Attenzione')`
- Italian labels for user-facing strings, English keys

**XML Record IDs:**
- Views: `view_cf_{model_short}_{view_type}` (e.g., `view_cf_gdo_retailer_kanban`, `view_cf_gdo_retailer_form`)
- Actions: `action_cf_{area}_{name}` (e.g., `action_cf_gdo_retailers`, `action_cf_crm_all`)
- Menus: `menu_cf_{area}_{name}` (e.g., `menu_cf_gdo_root`, `menu_cf_gdo_retailers`)

**JS Components:**
- PascalCase class names: `CfMailClient`, `CfKpiDashboard`, `CfHaccpDashboard`, `CfTreasuryDashboard`
- Static template assigned as string: `static template = "cf_mail_client.App"` or `static template = "casafolino_kpi.CfKpiDashboard"`
- Registry tag matches manifest action tag: `registry.category("actions").add("cf_kpi_dashboard", CfKpiDashboard)`

**CSS Files:**
- Prefix `cf_`: `cf_mail_client.css`, `cf_haccp.css`, `cf_crm.css`

## Code Style

**Formatting:**
- No linter or formatter configured (no `.eslintrc`, `.prettierrc`, `pyproject.toml`, etc.)
- Follow existing style by convention
- Python: 4-space indentation, ~100-120 char line length observed
- JS: 4-space indentation

**Linting:**
- None configured. Rely on Odoo's own validation during `--update`.

**Python File Headers:**
- Some files use `# -*- coding: utf-8 -*-` encoding header (older modules: `casafolino_haccp`, `casafolino_kpi`, `casafolino_supplier_qual`)
- Newer files (mail, crm_export, commercial) omit it
- Convention: include it for consistency, but not enforced

## Import Organization

**Python:**
1. Standard library imports (`datetime`, `json`, `logging`, `re`, `base64`)
2. Odoo framework imports (`from odoo import models, fields, api`)
3. Odoo exceptions (`from odoo.exceptions import UserError`)

**Typical import block:**
```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)
```

**JS (OWL Components):**
1. OWL framework: `import { Component, useState, onMounted } from "@odoo/owl";`
2. Odoo registry: `import { registry } from "@web/core/registry";`
3. Odoo services: `import { useService } from "@web/core/utils/hooks";`
4. RPC: `import { rpc } from "@web/core/network/rpc";`

**Path Aliases:**
- Use `@odoo/owl` for OWL imports
- Use `@web/core/...` for Odoo web framework
- NEVER use `import rpc from 'web.rpc'` (old API)

## Error Handling

**Python Patterns:**

User-facing validation errors use `UserError`:
```python
from odoo.exceptions import UserError
raise UserError("Il contatto non ha un indirizzo email.")
```

Constraint violations use `ValidationError`:
```python
from odoo.exceptions import ValidationError
raise ValidationError("La data di fine deve essere successiva alla data di inizio.")
```

Access control uses `AccessError`:
```python
from odoo.exceptions import AccessError
raise AccessError("Solo gli amministratori possono eliminare.")
```

Background/cron operations use try/except with logging -- never raise to avoid killing the cron:
```python
try:
    # operation
except Exception as e:
    _logger.error('Cron sync error for %s: %s', account.email, e)
```

**JS Patterns:**

Dashboard components wrap RPC in try/catch with state error:
```javascript
async _load() {
    try {
        this.state.data = await rpc("/web/dataset/call_kw", { ... });
    } catch (e) {
        this.state.error = "Errore caricamento KPI: " + (e.message || e);
    } finally {
        this.state.loading = false;
    }
}
```

## Logging

**Framework:** Python `logging` module

**Setup pattern (every file that logs):**
```python
import logging
_logger = logging.getLogger(__name__)
```

**When to log:**
- `_logger.info(...)` for significant operations (sync counts, cron progress)
- `_logger.warning(...)` for recoverable errors (API failures, bad data)
- `_logger.error(...)` for failures that need attention (send errors, sync failures)
- Use `%s` formatting, NOT f-strings: `_logger.warning('Error: %s', e)` (lazy evaluation)

**Error messages** are in English (for log parsing); user-facing strings are in Italian.

## Comments

**When to Comment:**
- Section headers using `# ── Section Name ──` or `# ==== Section ====` for visual grouping
- Brief inline comments in Italian for domain-specific logic
- Docstrings on complex public methods (not consistently applied)

**JSDoc/TSDoc:**
- Not used. JS comments are minimal inline explanations.

## Function Design

**State machine actions** follow a simple pattern:
```python
def action_to_analysis(self):
    self.write({"state": "analysis"})

def action_close(self):
    self.write({"state": "closed"})
```

**Computed fields** always iterate with `for rec in self:`:
```python
@api.depends("field1", "field2")
def _compute_something(self):
    for rec in self:
        rec.computed_field = some_logic(rec.field1, rec.field2)
```

**Dashboard data methods** use `@api.model` and return dicts:
```python
@api.model
def get_dashboard_data(self):
    return {"key": value, ...}
```

## Module Design

**Manifest (`__manifest__.py`):**
- Version format: `18.0.X.Y.Z` (most modules) or simple `X.0` (casafolino_mail)
- Category: `'CasaFolino'` for proprietary modules, standard Odoo categories for domain modules
- License: `'LGPL-3'` (most modules) or `'OPL-1'` (casafolino_mail)
- `'installable': True` always present
- `'application': True` for root-menu modules
- Assets always under `'web.assets_backend'` (NEVER `web.assets_web`)

**Data file order in manifest:**
1. `security/*.xml` (security rules first)
2. `security/ir.model.access.csv`
3. `data/*.xml` (sequences, crons, config data)
4. `views/*.xml` (view definitions)
5. `views/menus.xml` (menu items last)
6. `report/*.xml` (reports)

**Security CSV pattern:**
```
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_cf_model_user,cf.model user,model_cf_model,base.group_user,1,1,1,0
access_cf_model_mgr,cf.model manager,model_cf_model,base.group_system,1,1,1,1
```
Two rows per model: user (no delete) and manager (full access).

**XML file ordering rules (CRITICAL):**
1. Actions (`ir.actions.act_window`, `ir.actions.client`) BEFORE views that reference them
2. Views BEFORE menu items
3. Menu items: root menus first, then child menus

**OWL Component registration:**
```javascript
class CfMyComponent extends Component {
    static template = "module.TemplateName";
    static props = ["*"];
    // ...
}
registry.category("actions").add("tag_name", CfMyComponent);
```
Always include `static props = ["*"]` to avoid OWL prop validation errors.

## Brand Colors (CSS)

- Primary accent: `#5A6E3A` (CasaFolino green)
- Dark accent: `#3d4d28`
- Light accent: `rgba(90,110,58,0.1)`
- Use system sans-serif fonts only -- never import external fonts via CSS `@import url()`

## OWL Template Rules (XML)

- Use `t-name="card"` for kanban templates (NOT `t-name="kanban-box"`)
- Use `<list>` instead of `<tree>` for list views
- Use direct `invisible="condition"` instead of `attrs="{...}"`
- No parentheses in invisible expressions: `invisible="state == 'draft'"` not `invisible="(state == 'draft')"`
- Event handlers must reference method names, never inline arrow functions

---

*Convention analysis: 2026-04-17*
