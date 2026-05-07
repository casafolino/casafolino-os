# Brief #5.0 — Scoping Vista Progetto 360° MVP

**Data:** 2026-05-07

## Modelli rilevanti (già in DB)

### project.project (casafolino_crm_export/models/project_project.py)
- `cf_status_dossier` — Selection (exploration/active/on_hold/won/closed)
- `cf_dossier_priority` — Selection (low/medium/high)
- `cf_dossier_value_estimate` — Float
- `cf_managed_by_id` — Many2one → res.partner (agent)
- `cf_open_issues_count` — Integer (computed)
- `cf_last_activity_date` — Datetime (computed)
- `cf_lead_count` — Integer (computed)

### crm.lead (casafolino_crm_export/models/crm_lead.py)
- `cf_project_id` — Many2one → project.project (line 178)
- `cf_lead_score`, `cf_rotting_days`, `cf_rotting_state`
- `cf_sample_ids`, `cf_sample_count`
- `cf_date_last_contact`, `cf_date_next_followup`
- `cf_email_count`, `cf_partner_email_ids`
- `cf_forecast_value`, `cf_days_in_stage`
- `cf_next_activity_summary`, `cf_next_activity_date`
- Owner color: `USER_COLOR_MAP` dict (login → hex)
- `OWNER_LOGIN_TO_CLASS` dict (login → CSS class)

## Confirmed fields exist in DB
- `cf_status_dossier` on project.project
- `cf_project_id` on crm.lead
- `cf_managed_by_id` on project.project (note: Brief says cf_managed_by_ids m2m but actual is cf_managed_by_id m2o)

## Files to create (Phase 1-5)

### Phase 1 — Data layer
- `casafolino_crm_export/models/project_project.py` (extend existing)

### Phase 2 — OWL Component
- `casafolino_crm_export/static/src/project_dashboard/project_dashboard.js`
- `casafolino_crm_export/static/src/project_dashboard/project_dashboard.xml`

### Phase 3 — Views + Action
- `casafolino_crm_export/views/project_project_views.xml` (extend existing)
- `casafolino_crm_export/views/crm_lead_views.xml` (extend existing — add button)
- `casafolino_crm_export/models/crm_lead.py` (add action_open_project_360 method)

### Phase 4 — SCSS
- `casafolino_crm_export/static/src/project_dashboard/project_dashboard.scss`
- `casafolino_crm_export/__manifest__.py` (add assets)

### Phase 5 — Docs
- `casafolino_crm_export/static/src/project_dashboard/CONTRACT_DASHBOARD.md`
- `casafolino_crm_export/static/src/project_dashboard/SMOKE_TEST.md`
- `casafolino_crm_export/TODO.md` (update)

## Assumptions
- Brief says `cf_managed_by_ids` (m2m) but DB has `cf_managed_by_id` (m2o). Using existing m2o.
- No new `cf_*` fields needed — all data aggregated from existing models.
- `cf.sample.request` model referenced in Brief does NOT exist. Module has `cf.export.sample`. Will use that.
- Timeline will aggregate: mail.message + mail.activity on project + lead. No cf.sample.request timeline (model name mismatch).
- Premium form view (`cf_crm_lead_view_form_premium`) is standalone, not inherited from crm.crm_lead_view_form. The button "Apri progetto 360°" will be added to BOTH the premium form AND the inherited form.

## Blockers
None identified.
