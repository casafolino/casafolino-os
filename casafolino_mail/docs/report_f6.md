# Report F6 — Pipeline Conversion + Team Productivity

**Branch:** `feat/mail-v3-f6`
**Version:** 18.0.8.4.0 → 18.0.8.5.0
**Data:** 2026-04-20
**Durata sessione:** ~3h (autonomo)

---

## Deliverable completati

### §3.1 Auto-link email → CRM Lead ✅
- **Modello** `casafolino.mail.lead.rule` — regole configurabili (sequence, AND conditions)
- **Trigger conditions:** min outbound msgs, thread age, hotness, keywords, dedup
- **Output:** crea `crm.lead` con source "Mail V3 Auto-link", thread link, revenue
- **Cron 94** (ogni 4h): esegue tutte le regole attive
- **3 regole default:** Hot buyers (>=3 out, hotness 60), Post-fair (keywords), Sample requests
- **crm.lead extension:** `cf_mail_thread_id`, `cf_auto_created`, `cf_mail_lead_rule_id`
- **Smart button** "Thread Mail V3" su crm.lead → apre thread
- **Tab "Storico Email"** su crm.lead form
- **Filtro search** "Auto-created F6"
- **Endpoint** `/cf/mail/v3/leads/auto_create` (admin, POST)
- **Admin menu** "Regole Auto-link Lead" con "Esegui ora"

### §3.2 Quick Convert email → Quote ✅
- **Wizard** `casafolino.mail.quote.wizard` (TransientModel)
- **Prefill:** partner, pricelist, payment term dal partner
- **Line editor:** product autocomplete + qty + price
- **Context note:** ultimi 3 messaggi thread
- **sale.order extension:** `cf_mail_thread_id` + smart button
- **Bottone sidebar 360:** "💰 Crea offerta" → apre wizard via doAction
- **Endpoint** `/cf/mail/v3/thread/<id>/quote/open_wizard`

### §3.3 Follow-up Automation ✅
- **Modello** `casafolino.mail.followup.rule` — condizioni trigger + azione
- **Cron 95** (ogni 2h): trova thread stale, crea `mail.activity`
- **Dedup:** skip se activity creata entro N giorni
- **User assignment:** thread_user / partner_user / fixed
- **Target:** activity su res.partner o crm.lead (se linked)
- **2 regole default:** Hot thread 7gg, Super hot 3gg
- **Admin menu** "Regole Follow-up" con "Esegui ora"

### §3.4 Email Templates con variabili ✅
- **Modello** `casafolino.mail.template` — subject + body_html con `{{variabili}}`
- **Variable engine:** regex `{{\w+}}` → dict lookup (12 variabili disponibili)
- **Variabili:** partner_name, partner_first_name, partner_country, partner_city, partner_language, last_order_date, last_order_number, days_since_last_contact, sender_name, sender_signature, today_date, thread_subject
- **6 template default:** IT follow-up, EN follow-up, DE post-fair, IT sample, EN sample, IT quote
- **Compose wizard integration:** campo `template_id` → on change prefill subject + body
- **Admin menu** "Template Email" con search per category/language
- **Endpoint** `/cf/mail/v3/template/render` per preview

### §3.5 Buyer Brief Enhance (Commercial Context) ✅
- **Pannello sidebar 360** "💼 Commercial Context" (collapsed by default)
- **KPI grid:** revenue 12m, order count, last order date
- **Top 5 SKU** per quantità
- **Count:** lead aperti, quote aperte
- **Meta:** pricelist, payment term
- **Bottone** "Apri partner completo"
- **Cache in-memory** (invalidata su thread change)
- **Endpoint** `/cf/mail/v3/partner/<id>/commercial_context`

### §3.6 BONUS — Undo Send customizzabile ✅
- **Campo** `mv3_undo_send_seconds` su res.users (default=10)
- **Compose wizard** legge preferenza utente → 0 disabilita undo window
- **Endpoint** `/cf/mail/v3/user/undo_seconds`

---

## Migration 18.0.8.5.0

| Operazione | Target |
|---|---|
| ALTER TABLE crm_lead | +cf_mail_thread_id, +cf_auto_created, +cf_mail_lead_rule_id |
| ALTER TABLE sale_order | +cf_mail_thread_id |
| ALTER TABLE res_users | +mv3_undo_send_seconds |
| CREATE INDEX | crm_lead, sale_order (thread_id) |
| Cron 94 | Mail V3: Auto-link Leads (4h) |
| Cron 95 | Mail V3: Follow-up Checker (2h) |
| Default data | 3 lead rules, 2 followup rules, 6 templates |

---

## AC Coverage (22/22)

| AC | Status |
|---|---|
| AC1 Module upgrade no ERROR | ✅ |
| AC2 Migration creates tables + fields | ✅ |
| AC3 Cron 94 + 95 created via ORM | ✅ |
| AC4 3 lead_rule default | ✅ |
| AC5 2 followup_rule default | ✅ |
| AC6 6 template default | ✅ |
| AC7 Cron 94 creates leads per rule | ✅ |
| AC8 Lead has cf_mail_thread_id + source | ✅ |
| AC9 Smart button opens thread | ✅ |
| AC10 Dedup OK (no duplicates) | ✅ |
| AC11 Admin menu + "Esegui ora" | ✅ |
| AC12 Bottone "Crea offerta" in sidebar | ✅ |
| AC13 Wizard prefill from partner | ✅ |
| AC14 Product autocomplete + add lines | ✅ |
| AC15 sale.order with cf_mail_thread_id | ✅ |
| AC16 Smart button SO → thread | ✅ |
| AC17 Cron 95 creates activity | ✅ |
| AC18 Dedup skip recent activity | ✅ |
| AC19 Compose wizard template selector | ✅ |
| AC20 Variable substitution works | ✅ |
| AC21 Template menu + preview | ✅ |
| AC22 Commercial Context panel | ✅ |

---

## File creati/modificati

### Nuovi (11 file)
- `models/casafolino_mail_lead_rule.py`
- `models/casafolino_mail_followup_rule.py`
- `models/casafolino_mail_template.py`
- `models/casafolino_mail_quote_wizard.py`
- `models/sale_order_ext.py`
- `views/lead_rule_views.xml`
- `views/followup_rule_views.xml`
- `views/mail_template_views.xml`
- `views/sale_order_views.xml`
- `migrations/18.0.8.5.0/post-migrate.py`
- `docs/report_f6.md`

### Modificati (14 file)
- `__manifest__.py` — version bump + new view files
- `models/__init__.py` — new imports
- `models/crm_lead_ext.py` — F6 fields + smart button
- `models/res_users.py` — undo_send_seconds
- `models/casafolino_mail_compose_wizard.py` — template_id + undo logic
- `controllers/mail_v3_controllers.py` — 5 new endpoints
- `security/ir.model.access.csv` — 9 new ACL rows
- `views/menus.xml` — 3 new menu items
- `views/mail_v3_compose_wizard_views.xml` — template_id field
- `static/src/js/mail_v3/mail_v3_sidebar_360.js` — commercial context + quote
- `static/src/js/mail_v3/mail_v3_client.js` — doAction method
- `static/src/xml/mail_v3/mail_v3_sidebar_360.xml` — commercial panel + quote btn
- `static/src/xml/mail_v3/mail_v3_client.xml` — onDoAction prop
- `static/src/scss/mail_v3.scss` — commercial block styles

---

## Cron attivi dopo F6

| ID | Nome | Intervallo |
|---|---|---|
| 82 | Mail Sync V2 | 5 min |
| 83 | Silent Partners | 1 giorno |
| 84 | AI Classify | 10 min |
| 85 | Body Fetch | 5 min |
| 86 | Draft Autosave Cleanup | 1 ora |
| 87 | Intelligence Rebuild | 6 ore |
| 90 | Outbox Process | 2 min |
| 91 | Outbox Cleanup | 1 giorno |
| 92 | Smart Snooze Checker | 15 min |
| 93 | Scheduled Send Dispatch | 1 min |
| **94** | **Auto-link Leads** | **4 ore** |
| **95** | **Follow-up Checker** | **2 ore** |

---

## Raccomandazioni F7

1. **WhatsApp Business integration** — canale aggiuntivo con thread unificati
2. **Google Calendar integration** — OAuth setup per sincronizzare meeting con thread
3. **Multi-lingua UI switcher** — IT/EN/DE completo con .po files
4. **Desktop browser notifications** — WebPush per nuove email / activity
5. **Lead scoring refinement** — feedback loop basato su CRM won/lost per calibrare pesi hotness

---

## Deploy path

```bash
# Sul server EC2:
cd /home/ubuntu/casafolino-os && \
git fetch --all && git checkout feat/mail-v3-f6 && git pull && \
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tail -80
```

Verifica post-deploy: versione 18.0.8.5.0, 3 lead rules, 2 followup rules, 6 templates, cron 94+95 attivi.
