# Codebase Concerns

**Analysis Date:** 2026-04-17

## Critical Issues

### Duplicate Model Architecture in casafolino_mail

- Issue: The mail module contains **two parallel model systems** that serve overlapping purposes. `cf.mail.account` + `cf.mail.message` (original) coexist alongside `casafolino.mail.account` + `casafolino.mail.message` (newer "staging/hub" version). Both are loaded, both have security entries, and both manage email accounts and messages with different field sets and different logic.
- Files:
  - `casafolino_mail/models/cf_mail_account.py` (`cf.mail.account` -- 617 lines)
  - `casafolino_mail/models/cf_mail_message.py` (`cf.mail.message` -- 969 lines)
  - `casafolino_mail/models/casafolino_mail_account.py` (`casafolino.mail.account` -- 519 lines)
  - `casafolino_mail/models/casafolino_mail_message_staging.py` (`casafolino.mail.message` -- 1656 lines)
  - `casafolino_mail/models/__init__.py` (imports both sets)
- Impact: Data fragmentation between two model systems, double maintenance burden, confusion about which model to use for new features, potential data sync issues. The JS client (`cf_mail_client.js`) must know which model to call for which operation.
- Fix approach: Audit which model system is actively used by the UI (likely the `casafolino.*` set based on the staging views). Migrate any remaining functionality from `cf.*` models into `casafolino.*` models, then deprecate and remove the old set. This is the single largest source of tech debt.

### Open Redirect Vulnerability in Tracking Controller

- Issue: The click tracking endpoint accepts an arbitrary URL parameter and redirects to it without validation. An attacker can craft a tracking link that redirects to a phishing page.
- Files: `casafolino_mail/controllers/tracking_controller.py` (lines 32-41)
- Trigger: `GET /cf/track/click/<token>?url=https://evil.com` -- the controller does `unquote(url)` then `request.redirect(target, code=302)` with no domain whitelist.
- Fix approach: Validate the `url` parameter against an allowlist of domains, or at minimum reject `javascript:` schemes and ensure the URL starts with `http://` or `https://`. Example:
  ```python
  if not target.startswith(('http://', 'https://')) or any(d in target for d in BLOCKED_DOMAINS):
      target = '/'
  ```

### Hardcoded Admin Bypass by Email Login

- Issue: Access control checks use `self.env.user.login == 'antonio@casafolino.com'` as a hardcoded admin bypass in three separate methods. This circumvents Odoo's group-based security model, is not auditable, and breaks if the user email changes.
- Files:
  - `casafolino_mail/models/cf_mail_message.py` (lines 153, 200, 238)
  - `casafolino_supplier_qual/models/cf_supplier_document.py` (lines 80-84)
- Impact: Security bypass that cannot be managed through Odoo's standard access control. Any method checking `is_admin` grants full access to all mail accounts based on a string comparison.
- Fix approach: Replace with proper group membership check only: `self.env.user.has_group('base.group_system')`. If a custom admin role is needed, create a dedicated security group `group_cf_mail_admin`.

### IMAP Passwords Stored as Plaintext Char Fields

- Issue: Both mail account models store IMAP/SMTP passwords as plain `fields.Char`. These values are readable via RPC by any user with read access to the model, and visible in database dumps.
- Files:
  - `casafolino_mail/models/casafolino_mail_account.py` (line 24): `imap_password = fields.Char('App Password')`
  - `casafolino_mail/models/cf_mail_account.py` (line 54): `imap_password = fields.Char('Password / App Password')`
- Impact: Credential exposure to any authenticated Odoo user with model read access, and in database backups.
- Fix approach: Use Odoo's `ir.config_parameter` with restricted access, or implement field-level access control. At minimum, exclude the password field from `fields_get` and `read` results for non-admin users. Consider using `groups="base.group_system"` on the field definition.

## Moderate Issues

### Hardcoded SMTP Server in Email Sending

- Issue: The `_build_and_send_email` method hardcodes `smtp.gmail.com:587` instead of reading from the account's SMTP configuration fields (`smtp_host`, `smtp_port`).
- Files: `casafolino_mail/models/casafolino_mail_message_staging.py` (line 1321)
- Impact: Emails can only be sent via Gmail SMTP regardless of account configuration. The account model has `smtp_host` and `smtp_port` fields that are ignored.
- Fix approach: Replace `smtplib.SMTP('smtp.gmail.com', 587, timeout=30)` with `smtplib.SMTP(account.smtp_host or 'smtp.gmail.com', account.smtp_port or 587, timeout=30)`.

### Hardcoded URLs and Fallback to erp.casafolino.com

- Issue: Multiple places hardcode `erp.casafolino.com:4589` as fallback URL instead of relying solely on `web.base.url` system parameter.
- Files:
  - `casafolino_mail/models/casafolino_mail_message_staging.py` (lines 1264-1267): Hardcoded fallback URL for tracking links
  - `casafolino_mail/models/casafolino_mail_message_staging.py` (line 1217): Skip tracking for `erp.casafolino.com` links
  - `casafolino_mail/models/casafolino_mail_message_staging.py` (line 1247): Hardcoded `@casafolino.com` in generated Message-ID
- Impact: Breaks if the server URL changes. Tracking links would point to wrong server.
- Fix approach: Always use `self.env['ir.config_parameter'].sudo().get_param('web.base.url')` and remove hardcoded fallbacks.

### Misleading Error Messages (Anthropic vs Groq)

- Issue: The `action_enrich_007` method (Agente 007) references "Anthropic API key" in its error message and docstring, but actually uses the Groq API with `casafolino.groq_api_key`.
- Files: `casafolino_mail/models/cf_contact.py` (lines 395, 399)
- Impact: Confusing for developers and end users. Error message directs users to set a non-existent `casafolino.anthropic_api_key` parameter.
- Fix approach: Update the docstring to "Multi-source enrichment via Groq LLM + Serper web search" and the error message to reference `casafolino.groq_api_key`.

### Stale deploy.sh References Old Module Names

- Issue: The `deploy.sh` script lists pre-merge module names (`casafolino_gdo`, `casafolino_allergen`, `casafolino_nutrition`, `casafolino_private_label`, `casafolino_production`, `casafolino_recall`, `casafolino_treasury`) that no longer exist as separate modules.
- Files: `deploy.sh` (lines 11-23)
- Impact: Running `./deploy.sh` without arguments will fail or skip actual modules. The script does not include `casafolino_commercial`, `casafolino_operations`, `casafolino_product`, `casafolino_project`, or `casafolino_labels`.
- Fix approach: Update the MODULES array to match current module names.

### Excessive sudo() Usage in Mail Module

- Issue: The `casafolino_mail_message_staging.py` file uses `sudo()` liberally (20+ occurrences), including for partner creation, message writes, and search operations. Many of these bypass access control unnecessarily.
- Files:
  - `casafolino_mail/models/casafolino_mail_message_staging.py` (lines 182, 342, 348, 394, 559, 966, 1050, 1054, 1126, 1127, 1263, 1396, 1467)
  - `casafolino_mail/controllers/tracking_controller.py` (lines 46, 63, 64, 122)
- Impact: Bypasses Odoo record rules and access controls. Any bug in these methods could allow unauthorized data access or modification.
- Fix approach: Audit each `sudo()` call. Keep only those strictly necessary (e.g., cron jobs, system parameter reads, cross-user operations). For the tracking controller, `sudo()` is justified since `auth='public'`, but validate inputs more strictly.

### Broad Exception Handling Silencing Errors

- Issue: Multiple `except Exception` blocks silently swallow errors with just a log warning, or worse, with bare `pass`. This makes debugging production issues extremely difficult.
- Files:
  - `casafolino_mail/models/casafolino_mail_message_staging.py` (lines 925, 1495, 1502, 1514 -- bare `except Exception: pass`)
  - `casafolino_mail/models/casafolino_mail_message_staging.py` (lines 176, 217, 581, 627, 867, 1161, 1202, 1405, 1477)
  - `casafolino_product/models/cf_nutrition_wizard.py` (lines 58, 580)
  - `casafolino_product/models/cf_nutrition.py` (lines 479, 494)
- Impact: Failed email syncs, broken enrichment calls, and data corruption can go unnoticed.
- Fix approach: Replace broad `except Exception` with specific exception types (`ConnectionError`, `ValueError`, `smtplib.SMTPException`, etc.). Remove bare `pass` blocks and add at minimum `_logger.warning()` with `exc_info=True`.

### Timezone-Naive datetime.now() Usage

- Issue: Several modules use `datetime.now()` which returns a timezone-naive datetime, instead of Odoo's timezone-aware `fields.Datetime.now()` or `fields.Date.context_today(self)`.
- Files:
  - `casafolino_mail/models/cf_mail_account.py` (lines 441, 490)
  - `casafolino_operations/models/cf_recall_session.py` (lines 47, 55)
  - `casafolino_haccp/models/cf_haccp_reminder.py` (lines 38, 74)
- Impact: Date comparisons may be off by hours depending on server timezone vs user timezone. HACCP reminders could fire at wrong times.
- Fix approach: Replace `datetime.now()` with `fields.Datetime.now()` for datetime fields, and `fields.Date.context_today(self)` for date-only comparisons.

### PII Storage in Tracking Model (GDPR Risk)

- Issue: The email tracking system stores IP addresses and user agents for every open, click, and download event. For EU customers, this constitutes personal data under GDPR.
- Files:
  - `casafolino_mail/models/casafolino_mail_tracking.py` (lines 23-24)
  - `casafolino_mail/controllers/tracking_controller.py` (lines 71-72, 96-106)
- Impact: GDPR compliance risk. No retention policy, no consent mechanism, no anonymization.
- Fix approach: Add a data retention cron that anonymizes/deletes tracking records older than N days. Consider whether IP storage is necessary at all for business purposes. Add tracking opt-out capability.

## Minor Issues

### Oversized Files Need Splitting

- Issue: Several files exceed 500 lines, making them difficult to navigate and maintain.
- Files:
  - `casafolino_mail/models/casafolino_mail_message_staging.py` -- 1656 lines (email triage, sync, send, CRM integration, tracking, search all in one file)
  - `casafolino_product/models/cf_nutrition.py` -- 1234 lines
  - `casafolino_mail/models/cf_mail_message.py` -- 969 lines
  - `casafolino_mail/models/cf_contact.py` -- 803 lines (partner extension + Agente 007 + email history sync)
  - `casafolino_mail/static/src/js/cf_mail_client.js` -- 1725 lines (entire OWL client in one file)
  - `casafolino_mail/models/cf_mail_account.py` -- 617 lines
- Fix approach: Split `casafolino_mail_message_staging.py` into: message model, sync logic, send logic, CRM integration, search. Split `cf_mail_client.js` into separate OWL components (composer, message list, detail view, sidebar).

### Hardcoded User Lookup by Email Substring

- Issue: Supplier document expiry notification searches for a user by partial email match `('email', 'ilike', 'mirabelli')` then falls back to hardcoded `antonio@casafolino.com`.
- Files: `casafolino_supplier_qual/models/cf_supplier_document.py` (lines 79-84)
- Impact: Breaks if the user changes name/email. Not maintainable.
- Fix approach: Use a system parameter `casafolino.quality_manager_user_id` or a dedicated security group to identify the quality manager.

### Hardcoded Internal Domain Filter

- Issue: Multiple places hardcode `@casafolino.com` as the internal email domain to filter out internal messages.
- Files:
  - `casafolino_mail/models/casafolino_mail_message_staging.py` (lines 534-538, 744)
  - `casafolino_mail/models/cf_mail_message.py` (line 288)
- Impact: Breaks if the company adds additional email domains.
- Fix approach: Store internal domains in `ir.config_parameter` (e.g., `casafolino.internal_domains`) and read dynamically.

### Build/Fix Scripts Committed to Repository Root

- Issue: Development-only scripts are committed at repo root alongside production module code.
- Files:
  - `build_all.py` (3764 lines)
  - `build_complete.py` (0 lines -- empty)
  - `fix_crm_v31.py` (1164 lines)
  - `crm_export_mockup.html`
  - `mockup_ui_modules_v1.html`
  - `QONTO_pre2025_mancanti.csv`
  - `REVOLUT_post_mar2026_mancanti.csv`
- Impact: Clutters the repository, risk of accidental execution on server, the CSV files may contain financial data.
- Fix approach: Move to a `_dev/` or `_archive/` directory excluded from deployment. Add to `.gitignore` if no longer needed. Verify CSV files do not contain sensitive financial details before keeping them in git.

### Undocumented Modules Not in Architecture List

- Issue: Two modules (`casafolino_labels`, `casafolino_project`) exist in the codebase but are not mentioned in the CLAUDE.md architecture table of 8 modules.
- Files:
  - `casafolino_labels/__manifest__.py` -- Label pipeline management
  - `casafolino_project/__manifest__.py` -- Project management (samples, fairs, launches)
- Impact: New developers (and Claude instances) may not know these modules exist or their purpose.
- Fix approach: Update CLAUDE.md to document all 10 active modules.

### Missing Serper API Key Re-fetch Inside Loop

- Issue: In `action_enrich_007`, the `serper_key` is fetched once before the loop (line 397) and then **re-fetched inside the loop** on every partner iteration (line 410).
- Files: `casafolino_mail/models/cf_contact.py` (lines 397, 410)
- Impact: Unnecessary database reads on every loop iteration.
- Fix approach: Remove the redundant `get_param` call inside the loop (line 410).

## Test Coverage Gaps

### No Automated Tests

- What's not tested: The entire codebase has zero test files. No unit tests, no integration tests, no test directories in any module.
- Files: No `tests/` directory in any of the 10 modules.
- Risk: Any code change can introduce regressions undetected. Critical business logic (HACCP compliance, treasury calculations, email sending, Agente 007 enrichment) has no safety net.
- Priority: **High** -- Start with tests for the most critical paths: email send/receive, treasury snapshot calculations, HACCP temperature logging, and Agente 007 JSON parsing.

## Dependencies at Risk

### External API Dependencies Without Circuit Breakers

- Risk: Three external APIs (Groq, Serper, USDA, Telegram) are called synchronously in user-facing actions with no retry logic, no circuit breaker, and no graceful degradation.
- Files:
  - `casafolino_mail/models/cf_contact.py` (Groq + Serper -- 120s timeout)
  - `casafolino_product/models/cf_nutrition.py` (USDA + OpenFoodFacts)
  - `casafolino_haccp/models/cf_haccp_reminder.py` (Telegram)
- Impact: A 120-second timeout on Groq means the user stares at a spinner for 2 minutes if the API is slow. If Serper is down, the enrichment partially fails silently.
- Fix approach: Consider running enrichment as a background job (Odoo queue_job or cron). Add retry with exponential backoff. Set reasonable max timeouts (30s for user-facing, 120s for background).

---

*Concerns audit: 2026-04-17*
