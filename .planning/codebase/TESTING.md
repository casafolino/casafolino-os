# Testing Patterns

**Analysis Date:** 2026-04-17

## Test Framework

**Runner:**
- No automated test framework configured
- No `pytest`, `unittest`, `jest`, or `vitest` configuration files exist
- No test directories (`tests/`, `test/`) exist in any module

**Assertion Library:**
- Not applicable

**Run Commands:**
```bash
# No automated test suite exists. Testing is manual.
# Module update on staging is the primary validation:
docker exec odoo-app odoo -d folinofood_stage -u MODULE_NAME --stop-after-init --no-http 2>&1 | tail -15
```

## Test File Organization

**Location:**
- No test files exist. The only test-related file is a ping controller:
  `casafolino_mail/controllers/test_controller.py` -- a simple HTTP endpoint (`/cf/ping` returns `pong`) used to verify the Odoo HTTP stack is running

**Pattern for future tests:**
- Odoo convention: create `tests/` directory inside each module
- Test files named `test_*.py`
- Import in `tests/__init__.py`

## Current Validation Strategy

**Manual staging workflow (the only "testing" in place):**

1. Push code to GitHub (`git push`)
2. SSH to EC2, pull and copy to Docker addons path
3. Run `--update` on staging DB (`folinofood_stage`)
4. Check logs for `ERROR`, `WARNING`, `ParseError`, `ImportError`
5. Manually verify UI: open module menu, check forms, test buttons
6. If touching views: check `ir_ui_view` for duplicates
7. If touching security: check `ir.model.access.csv` loaded correctly
8. Backup prod DB before every production deploy
9. After prod deploy: verify at `erp.casafolino.com`

**Log checking:**
```bash
docker logs odoo-app --tail=50 | grep -E "ERROR|WARNING|ImportError|ParseError"
```

## Mocking

**Framework:** None

**Current approach:**
- No mocks exist. External API calls (Groq, Serper, IMAP) are called directly.
- Errors in external calls are caught via try/except and logged.

## Fixtures and Factories

**Test Data:**
- No test fixtures exist
- Some modules include seed data in `data/` XML files:
  - `casafolino_crm_export/data/cf_sample_stages.xml` -- CRM sample stages
  - `casafolino_crm_export/data/cf_sequence_data.xml` -- sequence definitions
  - `casafolino_product/data/cf_allergen_14eu.xml` -- EU allergen master data
  - `casafolino_product/data/cf_nutrition_regulations.xml` -- nutrition regulations
  - `casafolino_haccp/data/cf_haccp_sequences.xml` -- HACCP sequence numbers

## Coverage

**Requirements:** None enforced
**Tools:** None configured

## Test Types

**Unit Tests:**
- Do not exist. If implementing, use Odoo's `TransactionCase`:
```python
# tests/test_cf_gdo.py
from odoo.tests.common import TransactionCase

class TestCfGdoRetailer(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test'})

    def test_create_retailer(self):
        retailer = self.env['cf.gdo.retailer'].create({
            'partner_id': self.partner.id,
            'retailer_type': 'supermarket',
        })
        self.assertEqual(retailer.retailer_type, 'supermarket')
```

**Integration Tests:**
- Do not exist. If implementing, use Odoo's `HttpCase` for controller tests:
```python
# tests/test_tracking.py
from odoo.tests.common import HttpCase

class TestTracking(HttpCase):
    def test_ping(self):
        response = self.url_open('/cf/ping')
        self.assertEqual(response.text, 'pong')
```

**E2E Tests:**
- Not used

## Recommended Testing Priorities

If adding tests, prioritize these high-value areas:

**Critical business logic (computed fields):**
- `casafolino_crm_export/models/crm_lead.py` -- `_compute_cf_lead_score`, `_compute_cf_rotting` (scoring + rotting state machine)
- `casafolino_commercial/models/cf_treasury.py` -- `_compute_forecast`, `_compute_live_data` (financial calculations)
- `casafolino_haccp/models/cf_haccp_ccp.py` -- `_compute_state` (CCP pass/fail logic)

**State machine transitions:**
- `casafolino_haccp/models/cf_haccp_nc.py` -- NC workflow (open -> analysis -> action -> verified -> closed)
- `casafolino_haccp/models/cf_haccp_sp.py` -- SP release validation (blocks if NC open)

**External API integrations:**
- `casafolino_mail/models/cf_contact.py` -- Agente 007 enrichment (Groq + Serper)
- `casafolino_product/models/cf_nutrition.py` -- Open Food Facts + USDA API calls
- `casafolino_mail/models/casafolino_mail_account.py` -- IMAP sync

**Security boundaries:**
- `casafolino_mail/models/casafolino_mail_message_staging.py` -- `AccessError` on delete (admin-only)

## Running Odoo Tests (if implemented)

```bash
# Run tests for a specific module on staging:
docker exec odoo-app odoo -d folinofood_stage \
    -u casafolino_haccp --test-enable --stop-after-init --no-http \
    2>&1 | tail -30

# Run tests with specific test class:
docker exec odoo-app odoo -d folinofood_stage \
    -u casafolino_haccp --test-tags /casafolino_haccp \
    --stop-after-init --no-http 2>&1 | tail -30
```

## Validation via Module Update

The primary quality gate is the Odoo module update process. Errors caught include:
- **ParseError**: Invalid XML in views (wrong attributes, missing fields)
- **ImportError**: Missing Python imports in `__init__.py`
- **ValueError**: Invalid field definitions, broken computed dependencies
- **IntegrityError**: Duplicate XML IDs, security CSV format errors

```bash
# Check for common errors after update:
docker logs odoo-app --tail=100 | grep -E "ERROR|ParseError|ImportError|ValueError"

# Check for duplicate views:
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood_stage -c \
    "SELECT name, count(*) FROM ir_ui_view WHERE name LIKE 'cf.%' GROUP BY name HAVING count(*) > 1;"

# Check installed module state:
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood_stage -c \
    "SELECT name, state FROM ir_module_module WHERE name LIKE 'casafolino%' ORDER BY name;"
```

---

*Testing analysis: 2026-04-17*
