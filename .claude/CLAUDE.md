# CasaFolino OS — Odoo 18 Enterprise Custom Modules

## Project Overview

Custom Odoo 18 Enterprise module suite for CasaFolino Srls Società Benefit, an artisan gourmet food producer based in Pianopoli, Calabria. The system manages commercial operations, production, quality (HACCP/BRC/IFS), CRM export pipeline, KPIs, and AI-powered contact enrichment (Agente 007).

## Architecture — 8 Modules (post April 2025 merge)

| Module | Scope |
|---|---|
| `casafolino_commercial` | GDO retail management + Private Label + Tesoreria (cash flow) |
| `casafolino_operations` | Produzione CF (production calendar) + Mock Recall |
| `casafolino_product` | Allergeni (EU+US matrix) + Nutrizione (nutritional values) |
| `casafolino_supplier_qual` | Supplier qualification workflows |
| `casafolino_crm_export` | Export pipeline, lead management, country tracking |
| `casafolino_haccp` | HACCP, CCP monitoring, NC, calibration, quarantine |
| `casafolino_kpi` | Dashboard KPI, automated reports |
| `casafolino_mail` | Extended contacts, Agente 007 AI enrichment, IMAP email |

External IDs were migrated from old module names (12 → 8 merge). If you encounter `ir.model.data` references to old names like `casafolino_allergen`, `casafolino_nutrition`, `casafolino_gdo`, `casafolino_private_label`, `casafolino_treasury`, `casafolino_production`, `casafolino_recall`, check whether they map to the new merged modules above.

## Infrastructure

| Component | Value |
|---|---|
| Server | EC2 t3.large `51.44.170.55` |
| Odoo port | `4589` (URL: `erp.casafolino.com`) |
| Docker app container | `odoo-app` |
| Docker DB container | `odoo-db` (postgres:15) |
| Addons path (inside container) | `/mnt/extra-addons/custom/` |
| Addons path (host) | `/docker/enterprise18/addons/custom/` |
| Git repo on server | `/home/ubuntu/casafolino-os/` |
| GitHub | `github.com/casafolino/casafolino-os` (branch: `main`) |
| Mac local repo | `/Users/antoniofolino/casafolino-os` |
| Production DB | `folinofood` |
| Staging DB | `folinofood_stage` |
| SSH | `ubuntu@51.44.170.55` with key `~/.ssh/chieve_odoo_mac.pem` |

## Deploy Flow — CRITICAL

The server does NOT read from `/home/ubuntu/casafolino-os/`. Odoo reads from `/docker/enterprise18/addons/custom/`. You MUST copy after every git pull.

### Standard deploy (staging first, then prod):

```bash
# 1. Push from Mac
cd /Users/antoniofolino/casafolino-os
git add -A && git commit -m "description" && git push

# 2. On EC2 — pull + copy + update staging
cd /home/ubuntu/casafolino-os && git pull && \
sudo cp -rf MODULE_NAME /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d folinofood_stage -u MODULE_NAME --stop-after-init --no-http 2>&1 | tail -15 && \
docker restart odoo-app

# 3. On EC2 — deploy to production (after staging verification)
docker exec -e PGPASSWORD=odoo odoo-app pg_dump -h odoo-db -U odoo folinofood > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql && \
docker exec odoo-app odoo -d folinofood -u MODULE_NAME --stop-after-init --no-http 2>&1 | tail -20 && \
docker restart odoo-app
```

### Deploy multiple modules at once:

```bash
sudo cp -rf casafolino_commercial casafolino_operations casafolino_product casafolino_mail /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d folinofood_stage -u casafolino_commercial,casafolino_operations,casafolino_product,casafolino_mail --stop-after-init --no-http 2>&1 | tail -30
```

## Odoo 18 XML Rules — MANDATORY

These are hard-learned rules. Violating them causes ParseError, invisible elements, or broken views.

1. **No `attrs=` attribute** → Use `invisible=`, `readonly=`, `required=` directly on the element
2. **No `<tree>`** → Use `<list>` instead
3. **Cron XML**: Never use `model_id ref=` in `<record model="ir.cron">` — causes ParseError. Use empty `<odoo></odoo>` files or define crons without model_id ref
4. **Root menuitems require icon**: `web_icon="module_name,static/description/icon.png"` — without this, the menu icon won't display
5. **Kanban templates**: Use `t-name="card"` not `t-name="kanban-box"`
6. **Actions before views**: `ir.actions.act_window` records must precede view records in XML files
7. **Menuitems after actions**: `menuitem` records must follow the `act_window` they reference
8. **Buttons inside notebook pages**: Use `<div class="o_row mb-3">` wrapper, NOT `<header>` (not supported inside `<page>` in Odoo 18)
9. **Inheriting notebook**: Use `<xpath expr="//notebook" position="inside">` with `<field name="priority">99</field>` for reliable override
10. **OWL JS components**: All components must have `static props = ["*"]` to avoid prop validation errors

### View inheritance template:

```xml
<record id="view_unique_id" model="ir.ui.view">
    <field name="name">description.view</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="priority">99</field>
    <field name="arch" type="xml">
        <xpath expr="//notebook" position="inside">
            <page string="Tab Name" name="tab_name">
                <div class="o_row mb-3">
                    <button name="method_name" string="Button Text" type="object" class="btn btn-primary"/>
                </div>
                <group>
                    <field name="field_name"/>
                </group>
            </page>
        </xpath>
    </field>
</record>
```

### Stat button in button_box:

```xml
<xpath expr="//div[@name='button_box']" position="inside">
    <button name="method_name" string="Label" type="object" class="oe_stat_button" icon="fa-icon-name"/>
</xpath>
```

## Common Errors & Certified Fixes

### ImportError: cannot import name 'X'
**Cause**: `models/__init__.py` imports a `.py` file that doesn't exist.
**Fix**: Remove the orphan import line. Scan all init files:
```bash
for INIT in $(find . -name "__init__.py" | grep -v __pycache__); do
    DIR=$(dirname $INIT)
    python3 -c "
import re, os
content = open('$INIT').read()
imports = re.findall(r'from \. import (\w+)', content)
missing = [i for i in imports if not os.path.exists('$DIR/'+i+'.py') and not os.path.exists('$DIR/'+i+'/__init__.py')]
if missing: print('ORPHAN: $INIT ->', missing)
" 2>/dev/null
done
```

### Duplicate views after repeated updates
**Cause**: Multiple `-u` runs create duplicate `ir_ui_view` rows.
**Fix**:
```bash
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo DB_NAME -c "
DELETE FROM ir_ui_view WHERE name='VIEW_NAME' AND id = (
  SELECT MIN(id) FROM ir_ui_view WHERE name='VIEW_NAME'
);"
docker restart odoo-app
```

### SerializationFailure (concurrent update)
**Cause**: Odoo still running during `--update`.
**Fix**: Always use `--stop-after-init --no-http` which handles clean shutdown.

### Git pull says "Already up to date" but server runs old code
**Cause**: Git repo updated but `/docker/enterprise18/addons/custom/` was not.
**Fix**: Always `sudo cp -rf` after `git pull`. These are different directories.

### Permission denied on addons copy
**Fix**: Always use `sudo cp`.

## Agente 007 — AI Contact Enrichment

Located in `casafolino_mail`. Uses Groq API (not Anthropic).

| Config | Value |
|---|---|
| LLM | `llama-3.3-70b-versatile` via Groq |
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| API key param | `casafolino.groq_api_key` in `ir.config_parameter` |
| Web search | Serper.dev (`casafolino.serper_api_key` in `ir.config_parameter`) |

Serper integration includes country-specific source maps and page scraping for contact enrichment.

### Retrieving API keys in Python:

```python
api_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.groq_api_key', '')
serper_key = self.env['ir.config_parameter'].sudo().get_param('casafolino.serper_api_key', '')
```

## Python Coding Conventions

- Python 3.10+ (Odoo 18 requirement)
- Use `self.env['model.name']` not `self.pool`
- Use `fields.Date.context_today(self)` for dates, not `datetime.now()`
- Translations: `_("translatable string")` with `from odoo import _`
- Logging: `import logging; _logger = logging.getLogger(__name__)`
- Security: Always `sudo()` only when necessary, prefer record rules
- API methods: Decorate public API methods with `@api.model` or appropriate decorator
- Computed fields: Always define `depends` correctly to avoid cache issues

## Database Commands

### psql direct query:
```bash
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "SQL_QUERY"
```

### Check Odoo logs:
```bash
docker logs odoo-app --tail=50 | grep -E "ERROR|WARNING|ImportError|ParseError"
```

### Clear asset cache:
```bash
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c \
"DELETE FROM ir_attachment WHERE name LIKE '%web.assets%';"
docker restart odoo-app
```

### Check active crons:
```bash
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c \
"SELECT id, cron_name, active, nextcall FROM ir_cron WHERE active=true ORDER BY nextcall LIMIT 20;"
```

### Check installed modules:
```bash
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c \
"SELECT name, state FROM ir_module_module WHERE name LIKE 'casafolino%' ORDER BY name;"
```

## File Structure Convention

Each module follows this structure:
```
casafolino_module/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── model_file.py
├── views/
│   └── view_file.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── data_file.xml
├── static/
│   └── description/
│       └── icon.png          # REQUIRED for root menuitem
└── wizard/                    # optional
    ├── __init__.py
    └── wizard_file.py
```

## Testing Checklist Before Deploy

1. Run `--update` on staging first — never directly on prod
2. Check logs for ERROR/WARNING after update
3. Verify the UI: open the module menu, check forms, test buttons
4. If touching views: check `ir_ui_view` for duplicates
5. If touching security: check `ir.model.access.csv` loaded correctly
6. Backup prod DB before every production deploy
7. After prod deploy: verify at `erp.casafolino.com` (port 4589)

## Git Workflow

- Branch: `main` (single branch workflow)
- Commit messages: descriptive, module name prefix when touching single module
- If merge conflicts on server:
```bash
git stash && git pull && git stash pop
# If conflicts remain:
git checkout --theirs CONFLICTED_FILE
git add -A && git commit -m "merge: resolve conflicts" && git push
```

## Related External Systems

| System | Purpose |
|---|---|
| HACCP App | `casafolino-haccp-rouge.vercel.app` (Supabase + Next.js) |
| Treasury App | `casafolino-treasury.vercel.app` (React + Vite + Railway backend) |
| B2B Website | Planned: Next.js + Sanity CMS + Vercel |
| Shopify | `casafolino.com` (Mochi/Koto theme) |
| n8n | Shopify→Odoo sync, inventory sync, KPI extraction |
