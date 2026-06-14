# Brief #6.5 — Inbox Selector Scoping

**Data:** 2026-05-07

## Account per user
- Antonio (uid=2): 1 account (responsible_user_id)
- Josefina (uid=6): 1 account
- Martina (uid=8): 1 account
- FK field: casafolino_mail_account.responsible_user_id

## res_users.py already exists
- Already has mail_v3_* preferences fields
- Will add cf_can_see_all_inboxes here

## Strategy: Approach B
- Server-side sudo() with manual filter on account_id.responsible_user_id
- Permission gate: cf_can_see_all_inboxes=True required
- No record rule modification

## Files to create
- static/src/inbox_selector/inbox_selector.{js,xml,scss}

## Files to modify
- models/res_users.py (add cf_can_see_all_inboxes)
- models/casafolino_mail_message_staging.py (add server endpoints)
- views/posizionatore_views.xml (add js_class)
- __manifest__.py (assets)

## Blockers
None.
