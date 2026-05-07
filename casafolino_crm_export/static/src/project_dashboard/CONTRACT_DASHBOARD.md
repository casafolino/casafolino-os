# CFProjectDashboard — Contract

**Last updated:** 2026-05-07 — Brief #5.0
**JS:** `casafolino_crm_export/static/src/project_dashboard/project_dashboard.js`
**Template:** `casafolino_crm_export/static/src/project_dashboard/project_dashboard.xml`
**SCSS:** `casafolino_crm_export/static/src/project_dashboard/project_dashboard.scss`
**Python:** `casafolino_crm_export/models/project_project.py` → `cf_get_dashboard_data()`

## Purpose

OWL client action — 360° dashboard for a CRM export project (dossier).
Registered as `casafolino_crm_export.project_dashboard` in action registry.
Opened via:
- Button `action_open_project_360` on `crm.lead` form (premium + inherited)
- Stat button "360°" in button_box of inherited lead form
- Menu "Progetti 360°" → list view → click project record (future)

## State (useState)

| Field | Type | Initial | Description |
|---|---|---|---|
| isLoading | bool | true | Data loading in progress |
| data | object/null | null | Full dashboard payload from `cf_get_dashboard_data()` |
| activeTab | string | "timeline" | Currently selected tab ID |
| timelineFilter | string | "all" | Timeline event type filter |
| error | string/null | null | Error message if load failed |

## Data shape (from Python)

`state.data` is the return value of `project.project.cf_get_dashboard_data()`:

```
{
  project: { id, name, status_dossier, dossier_priority, create_date },
  lead: { id, name, stage_name, stage_sequence, stage_position, expected_revenue,
          probability, priority, score, rotting_state, days_in_stage, forecast_value } | null,
  partner: { id, name, city, country_name, country_code, phone, mobile, email, website, lang } | null,
  kpi: { revenue, forecast, sample_count, email_count, next_activity, lead_count },
  timeline: [{ type, color, type_label, title, subtitle, date, date_label, author, model }],
  contacts: [{ id, name, email, phone, function, is_primary }],
  owner: { id, name, initials, color_class, login },
}
```

## Props

| Prop | Type | Required | Description |
|---|---|---|---|
| action | Object | yes (via registry) | Odoo action with `context.active_id` or `context.default_project_id` |
| * | any | no | Accepts all props (static props = ["*"]) |

## Service dependencies

| Service | Variable | Usage |
|---|---|---|
| orm | this.orm | call `cf_get_dashboard_data` on project.project |
| action | this.action | doAction for navigation (lead form, partner form, sample, offer, activity) |
| user | this.user | Available for user context — ⚠️ OWL18 uses `this.user.userId` NOT `.uid` |
| notification | this.notification | Toast messages for disabled tabs and errors |

## Public methods

| Method | Args | Returns | Description | Status |
|---|---|---|---|---|
| _loadData | — | Promise | Fetches `cf_get_dashboard_data` via ORM call, sets state | OK |
| onTabChange | tabId:string | void | Switches tab or shows notification for disabled tabs | OK |
| onTimelineFilter | filter:string | void | Filters timeline by event type | OK |
| onQuickActionMail | — | void | Notification placeholder (Brief #8) | OK |
| onQuickActionSample | — | Promise | Opens cf.export.sample form for linked lead | OK |
| onQuickActionOffer | — | Promise | Opens sale.order form with partner pre-filled | OK |
| onQuickActionActivity | — | Promise | Opens mail.activity form for project | OK |
| onOpenLead | — | Promise | Navigates to lead form view | OK |
| onOpenPartner | — | Promise | Navigates to partner form view | OK |
| onGoBack | — | void | Navigates back to CRM pipeline kanban | OK |
| onRefresh | — | Promise | Reloads dashboard data | OK |
| onContactClick | contactId:int | void | Opens partner form for clicked contact | OK |

## Getters (computed)

| Getter | Returns | Description |
|---|---|---|
| statusLabel | string | Human label for status_dossier |
| statusColor | string | CSS color class name |
| partnerFlag | string | Emoji flag from country code |
| partnerLocation | string | "city, country" string |
| stageSegments | array | 9 objects with index/active/current for stage bar |
| kpiRevenue | string | Formatted revenue (e.g. "45k") |
| kpiForecast | string | Formatted forecast |
| filteredTimeline | array | Timeline filtered by timelineFilter |
| tabs | array | Tab definitions with enabled/disabled + brief ref |
| timelineFilters | array | Filter pill definitions |

## Template handler mapping (project_dashboard.xml)

| Template binding | Element | Class method |
|---|---|---|
| t-on-click | "Riprova" button (error state) | onRefresh |
| t-on-click | Back arrow button | onGoBack |
| t-on-click | Refresh button (topbar) | onRefresh |
| t-on-click | Partner name | onOpenPartner |
| t-on-click | Lead name | onOpenLead |
| t-on-click (arrow fn) | Tab pill | onTabChange(tab.id) |
| t-on-click (arrow fn) | Timeline filter pill | onTimelineFilter(f.id) |
| t-on-click | Quick action "Email" | onQuickActionMail |
| t-on-click | Quick action "Campione" | onQuickActionSample |
| t-on-click | Quick action "Offerta" | onQuickActionOffer |
| t-on-click | Quick action "Attività" | onQuickActionActivity |
| t-on-click (arrow fn) | Contact row | onContactClick(contact.id) |

## Sub-templates

| Template name | Purpose |
|---|---|
| casafolino_crm_export.CFProjectDashboard | Root template |
| casafolino_crm_export.CFProjectDashboard.CustomerPanel | Reusable customer panel (partner + contacts + lead summary) |

## Backlog

| Brief | Tab | Status |
|---|---|---|
| #5.1 | Commerciale | Notification placeholder |
| #5.1 | Campionature | Notification placeholder |
| #5.2 | Documenti | Notification placeholder |
| B6 | Mail | Notification placeholder |
| #8 | Quick action mail | Notification placeholder |

## Maintenance

**Golden rule:** no one modifies the template XML without first reading this file
AND confirming the modification is consistent with the class. No one modifies
the class without updating this file in the same commit.

When this file updates:
- Add/modify a public method → update "Public methods" section
- Add/modify a template binding → update "Template handler mapping" section
- Add/modify a state field → update "State" section
- Add/modify a service → update "Service dependencies" section
