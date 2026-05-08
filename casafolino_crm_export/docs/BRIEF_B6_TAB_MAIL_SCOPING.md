# Brief #B6 — Tab Mail Dashboard Scoping

**Data:** 2026-05-08

## Dependencies
- casafolino_mail NOT in depends → must add in Phase 1
- F8 composer: ComposeWizard component (not client action)
- Quick reply: will navigate to partner form (chatter) instead

## Volume
- Positioned mail: 0 (system fresh, no positioning done yet)
- Projects with mail: 0

## Tab Mail current state
- Tab "Mail" shows notification "disponibile in Brief #5.2 / B6"
- Need to: remove 'mail' from placeholder block, add real content

## Files to modify
- models/project_project.py (_cf_get_mail_timeline, _cf_get_mail_count, extend cf_get_dashboard_data)
- __manifest__.py (add casafolino_mail to depends)
- static/src/project_dashboard/project_dashboard.js (handlers + tab logic)
- static/src/project_dashboard/project_dashboard.xml (tab Mail content)
- static/src/project_dashboard/project_dashboard.scss (mail cards styling)

## Blockers
None.
