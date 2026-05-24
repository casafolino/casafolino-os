# CasaFolino Mail Module — v6 Architecture

**Last updated:** 2026-05-07
**Roadmap:** Brief #6.0 → #6.6
**Status:** Production-ready, structurally complete.

## Philosophy

- Gmail stays the home for reading/writing mail (web/mobile)
- Only mail from CRM partners with `mail_tracked=True` enters Odoo
- In Odoo: positioner + project chatter + F8 composer with AI
- Multi-user: each sees own mail. Antonio has "view as Josefina/Martina"

## Ingestion flow

1. Cron IMAP fetch (5 min): `FETCH BODY.PEEK[HEADER]` on new UIDs
2. Extract From/To, normalize, search `res.partner` with `mail_tracked=True`
3. No match → skip (mail stays in Gmail)
4. Match → create `casafolino.mail.raw` with `triage_state='pending'`
5. Cron triage RAW (5 min): deterministic rules + AI classify
6. Promote to `casafolino.mail.message` with `body_downloaded=False`
7. Cron body fetch (10 min): download body + attachments async
8. Cron AI suggestion (5 min): Groq generates top-3 dossier suggestions
9. User opens Posizionatore: sees mail with confidence badges (green/orange/gray)
10. HIGH (>threshold): click "Confirm" → instant positioning
11. MEDIUM/LOW: dialog with AI candidates or manual selector
12. Positioning creates `mail.message` in project chatter (original email_date!)
13. Hook records `cf.mail.position.feedback` (match/mismatch)
14. Cron daily: recalculates `partner.cf_ai_accuracy_score`
15. Score adjusts HIGH threshold per partner: 0.7 (reliable AI) → 0.9 (unreliable)

## Models

| Model | File | Purpose |
|-------|------|---------|
| casafolino.mail.account | casafolino_mail_account.py | IMAP accounts, fetch engine |
| casafolino.mail.message | casafolino_mail_message_staging.py | Messages, AI classifier, positioner |
| casafolino.mail.raw | casafolino_mail_raw.py | RAW staging pre-triage |
| casafolino.mail.thread | casafolino_mail_thread.py | Conversation threads |
| casafolino.mail.draft | casafolino_mail_draft.py | Draft emails |
| casafolino.mail.outbox | casafolino_mail_outbox.py | Outbox queue |
| casafolino.mail.folder | casafolino_mail_folder.py | Mail folders |
| casafolino.mail.folder.rule | casafolino_mail_folder_rule.py | Auto-sort rules |
| casafolino.mail.snippet | snippet.py | Reply snippets |
| cf.mail.position.feedback | cf_mail_position_feedback.py | AI match/mismatch history |
| casafolino.mail.sla.partner | sla_partner.py | SLA dashboard |
| casafolino.mail.orphan.partner | orphan_partner.py | Orphan dashboard |
| casafolino.mail.lead.score | lead_score.py | Lead scoring |

## OWL Components

| Component | Path | Purpose |
|-----------|------|---------|
| F8 ComposeWizard | js/mail_v3/mail_v3_compose.js | Outlook-style composer |
| CFInboxSelector | inbox_selector/ | "View as" pill for supervisor |
| Posizionatore list | posizionatore_views.xml | Mail positioning with AI confidence |

## Crons

| Name | Interval | Method |
|------|----------|--------|
| Mail Sync V2 | 5 min | _cron_fetch_all_accounts |
| Body Fetch Pending | 10 min | (body download) |
| Triage RAW | 5 min | _cron_triage_raw |
| AI Suggestion* | 5 min | _cron_run_ai_suggestion |
| Accuracy Refresh* | 24h | _cron_refresh_ai_accuracy |

*Create via UI: Settings → Technical → Scheduled Actions

## Composer AI

The F8 AI Assist panel was removed on 2026-05-24. The composer currently has no active AI panel or `cf.mail.compose.ai` endpoints.

AI should be reintroduced only after a new spec defines concrete CRM actions and a useful review flow.

## Permission model

- Default: each user sees own mail (record rules on account.responsible_user_id)
- Antonio (uid=2, `cf_can_see_all_inboxes=True`): can call `cf_get_inbox_messages_as_user(N)` with controlled sudo
- Josefina/Martina: AccessError if they call impersonation endpoints

## OWL18 mandatory patterns

| Wrong | Right |
|-------|-------|
| `useService("user")` | `import { user } from "@web/core/user"` |
| `this.user.uid` | `user.userId` |
| `t-on-click="this.X"` | `t-on-click="X"` |
| `<tree>` | `<list>` |
| `attrs="{...}"` | `invisible="..."`, `readonly="..."` |
| `class="x" ... class="y"` | `class="x y"` |
| CSS var no fallback | `var(--x, #fallback)` |

## Brief history

| # | What | Status |
|---|------|--------|
| #6.0 | Demolition (sender_policy + triage + fetch_totale) | Done |
| #6.1 | Ingestion rerouting (mail_tracked, fetch+match, body lazy) | Done |
| #6.2 | Posizionatore UI (3 AI confidence dynamics) | Done |
| #6.3 | AI feedback loop (accuracy score, dynamic threshold) | Done |
| #6.4 | F8 AI assist panel (tone/lang/sig/replies) | Removed 2026-05-24 |
| #6.5 | Inbox selector ("view as" for supervisor) | Done |
| #6.6 | Test prod + migration (backfill, cleanup, perf, E2E) | Done |

## Remaining backlog

- Brief #B6: Tab Mail in dashboard 360° (populate with mail timeline per project)
- Brief #5.1/#5.2: Dashboard 360° additional tabs (Commerciale, Campionature, Documenti)
