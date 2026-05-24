# Brief #6.4 — F8 AI Assist Scoping

Status 2026-05-24: superseded. The first implementation was removed because it did not provide enough operational value in the composer. Use this brief only as historical context; a new AI composer spec is required before rebuilding the feature.

**Data:** 2026-05-07

## F8 Composer Files
- JS: static/src/js/mail_v3/mail_v3_compose.js (721 lines, ComposeWizard)
- JS: static/src/js/mail_v3/compose_wizard_dialog.js (ComposeWizardDialog wraps ComposeWizard)
- XML: static/src/xml/mail_v3/mail_v3_compose.xml (373 lines)
- XML: static/src/xml/mail_v3/compose_wizard_dialog.xml

## OWL18 Pattern Check: COMPLIANT
- useService("user"): 0 matches
- this.user.: 0 matches
- t-on-*="this.: 0 matches
- Uses rpc import, useState, useRef, onMounted — all modern

## Snippet Model
- Name: casafolino.mail.snippet (models/snippet.py)
- Fields: name, code, category, language, subject, body, active

## AI Panel Injection Point
- After .mv3-compose__editor-wrap (line ~261 in XML)
- ComposeWizard.static.components needs CFComposeAIPanel added
- Callback integration: applyAIBody + appendAIBody on ComposeWizard

## Files to create
- models/cf_mail_compose_ai.py (AbstractModel, 6 endpoints)
- static/src/compose_ai_panel/compose_ai_panel.js
- static/src/compose_ai_panel/compose_ai_panel.xml
- static/src/compose_ai_panel/compose_ai_panel.scss

## Files to modify
- static/src/js/mail_v3/mail_v3_compose.js (import + components + callbacks)
- static/src/xml/mail_v3/mail_v3_compose.xml (inject panel)
- models/__init__.py (import new model)
- security/ir.model.access.csv (ACL)
- __manifest__.py (assets)

## Blockers
None. F8 is OWL18 compliant.
