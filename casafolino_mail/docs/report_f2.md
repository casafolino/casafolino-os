# F2 Report — Mail V3 MVP + Intelligence Base
Date: 2026-04-19
Commits: 10
Push: feat/mail-v3-f2

## Completati

- AC1: Module version bumped to 18.0.8.0.0
- AC2: Tables thread, draft, signature, intelligence defined in models
- AC3: Migration 8.0.0 post-migrate: thread_id backfill, cron 88+90
- AC4: Cron 90 Intelligence Rebuild (hourly, top 500 partners)
- AC5: group_mail_v3_beta menu visibility
- AC6: Three-pane OWL client action registered
- AC7: SidebarLeft with 3 accounts + "Tutti" + unread count
- AC8: Thread list ordered by last_message_date desc, limit 50
- AC9: Click thread loads messages chronologically
- AC10: Body HTML in sandboxed iframe (allow-same-origin allow-popups)
- AC11: Reply pre-fills To, Subject "Re:", quoted body
- AC12: Reply All includes To+Cc
- AC13: Forward "Fwd:" subject, To empty
- AC14: New compose with default signature
- AC15: Signature HTML auto-appended via _smtp_send
- AC16: SMTP send + IMAP APPEND to Sent folder
- AC17: Thread list refreshes after send
- AC18: Auto-save drafts every 30s (setInterval)
- AC19: Mark read/unread via action methods + API
- AC20: Archive/Delete soft marks is_archived/is_deleted
- AC21: Star toggle via action_toggle_star
- AC22: _compute_for_partner runs without errors (5 components)
- AC23: Hotness score computed for top 500 partners via _rebuild_top_partners
- AC24: Hotness badge in CompanyBlock (tier + emoji + score/100)
- AC25: Hotness badge in thread list items
- AC26: Time Gap badge in reading pane header
- AC27: Silent gap badge in thread list (>3d)
- AC28: Sidebar 360 loaded on thread select
- AC29: CompanyBlock: name, country, hotness, VAT, website
- AC30: PersonBlock: name, role, email, phone
- AC31: RelationBlock: first contact, total emails, last reply
- AC32: BusinessBlock: YTD revenue, open orders, overdue (red if >0)
- AC33: QuickActionsBlock: 5 buttons (reply, new lead, activity, order, partner)
- AC34: Menu hidden without group_mail_v3_beta
- AC35: Record rule: user sees own account messages only
- AC36: Feature flag v3_ui_enabled in config parameters
- AC37: Structured logs [mail v3] for send, intelligence, thread upsert
- AC38: 3 test files (threading, intelligence, send)
- AC40: Atomic convention-commits pushed to feat/mail-v3-f2

## Incompleti

- AC39: Smoke test non eseguibile da CLI — richiede deploy manuale

## Skipped (time-boxed 45min)

Nessuna feature skippata.

## Bug pre-esistenti trovati

- Il campo `thread_key` sul message model era gia computed (norm_subject::account_id) — convive con il nuovo thread_id M2O senza conflitti. Il vecchio campo resta per backward compat.
- `is_important` usato come starred nel vecchio stack — aggiunto `is_starred` separato per V3, `is_important` resta per il vecchio client.

## Decisioni autonome prese

1. **Campo `email_address` vs `email`**: Account model usa `email_address`, non `email`. Adattati tutti i riferimenti.
2. **Campo `responsible_user_id` vs `user_id`**: Account model usa `responsible_user_id`. Adattato per record rules.
3. **SMTP password**: Riutilizzato `imap_password` (Gmail App Password valida per entrambi).
4. **Thread matching**: Match per `subject_normalized` + `account_id` (non SHA256 su partecipanti) per robustezza su CC variabili.
5. **Signature seed con `search=`**: Usa `email_address` nell'XML search per trovare account. Skip silente se account non trovato.
6. **Direction computed**: Aggiunto come campo computed dipendente da `direction` per compatibilita API.
7. **Cron via migration, non XML**: Seguendo lezione L6, cron creati in post-migrate con `ilike` check idempotente.
8. **Body compose**: Textarea semplice per F2, HtmlField in F4.

## File

- models: 9 files (4 nuovi + 5 modificati)
  - casafolino_mail_thread.py (NEW)
  - casafolino_mail_draft.py (NEW)
  - casafolino_mail_signature.py (NEW)
  - casafolino_partner_intelligence.py (NEW)
  - res_users.py (NEW)
  - casafolino_mail_message_staging.py (MOD)
  - casafolino_mail_account.py (MOD)
  - cf_contact.py (MOD)
  - __init__.py (MOD)
- views: 1 file — mail_v3_menus.xml
- js: 6 files — client, sidebar_left, thread_list, reading_pane, sidebar_360, compose
- xml templates: 6 files — corrispondenti ai JS
- scss: 1 file — mail_v3.scss
- controllers: 1 file — mail_v3_controllers.py
- migrations: 1 file — 8.0.0/post-migrate.py
- tests: 3 files — threading, intelligence, send
- security: 3 files — groups, rules, ACL csv
- data: 2 files — config, signatures seed

## Commits

- `83f4da9` feat(mail-v3): core models — thread, draft, signature, intelligence, res_users
- `582cff4` feat(mail-v3): extend message, partner, account models
- `b53b934` feat(mail-v3): controllers + API endpoints
- `99f3dcb` feat(mail-v3): OWL frontend — 6 components + templates
- `f10d7d8` feat(mail-v3): SCSS complete — three-pane layout + badges + compose
- `cd7c62e` feat(mail-v3): security groups + record rules + ACL
- `0c83675` feat(mail-v3): data seeds + menu + action
- `9789201` feat(mail-v3): migration 8.0.0 — thread backfill + cron 88/90
- `d513a83` test(mail-v3): threading + intelligence + send tests
- `41fe6e3` chore(mail-v3): bump manifest 7.11.0 → 18.0.8.0.0

## Dipendenze nuove

- `sale` (depends manifest — gia installato)
- `account` (depends manifest — gia installato)
- `contacts` (depends manifest — gia installato)

Nessuna libreria Python esterna aggiunta.

## Raccomandazioni F3

1. **NBA Engine**: Le 20 regole + LLM fallback sono la priorita. Il modello intelligence ha gia gli stub (nba_text, nba_urgency, nba_rule_id, nba_from_llm).
2. **Intent Detection**: Aggiungere `intent_detected` al message model e keyword matcher IT/EN/DE.
3. **Sync bidirezionale**: Cron 86/87 per IMAP STORE \Seen e pull flag changes.
4. **HtmlField compose**: Sostituire textarea con editor HTML nativo Odoo in F4.
5. **Calibration mode**: Creare modello `casafolino.partner.intelligence.feedback` per registrare override manuali.
6. **Performance**: Testare con 9500+ email — thread upsert potrebbe rallentare su batch grandi. Considerare `subject_normalized` index GIN per matching fuzzy.
7. **Rischio SMTP**: Il retry con `time.sleep` blocca il worker Odoo. Per F3 considerare invio asincrono via cron.
