# Brief F6 — Pipeline Conversion + Team Productivity

**Formato:** GSD — **MODALITÀ AUTONOMA TOTALE**
**Owner:** Antonio Folino
**Reference spec:** `docs/mail_v3_spec.md` v1.1
**Base:** `feat/mail-v3-f5` (F5 merged, version 18.0.8.4.0)
**Target:** `casafolino_mail` 18.0.8.4.0 → 18.0.8.5.0
**Branch:** `feat/mail-v3-f6` (da `feat/mail-v3-f5`)
**Tempo stimato:** 8-9 ore autonome
**Prev brief:** report_f2, report_f2_1, report_f3, report_merged, report_f4, report_f5

---

## 🚀 COME LANCIARE CODE

**Sul Mac (terminale normale, NON server):**

```bash
cd ~/casafolino-os
git fetch --all
git checkout feat/mail-v3-f5
git pull
claude --dangerously-skip-permissions
```

Poi dentro Code incolla tutto il brief e scrivi "Vai".

---

## ⚠️ 4 REGOLE CRITICHE (come F2/F3/F4/F5)

1. **MAI fermarsi** — 3 eccezioni: data loss prod, credenziali mancanti, spec muta su architettura
2. **11 defaults automatici** per ambiguità (naming `mv3_`/`cf_crm_`, pattern esistenti, UI text IT pro, icone FA5→emoji, colori variabili SCSS, edge case gracefully fail, bug pre-esistenti skip+annota)
3. **Auto-escape 60 min** → commit `wip`, skip, avanti (aumentato da 45 a 60 min su feature complesse come Auto-link lead e Templates)
4. **Commit ogni 30 min + push ogni 3-4 commit**

---

## 1. Obiettivo

**Chiudere il gap pipeline CRM: trasformare Mail V3 da "client email intelligente" a "macchina di conversione conversazioni → pipeline commerciale strutturato".**

Oggi APA Dolci, BILLA Austria, REWE, Dusini, Benedek hanno scambi email attivi ma **zero lead CRM aperti**. Josefina e Martina rispondono ma il CRM non riflette la realtà commerciale. Quando Antonio presenterà pipeline agli investitori del round €4M, forecast non sarà credibile.

**Definition of Done F6:**

Antonio apre CRM alle 9:00 di mattina e vede `crm.lead` aperti su tutti i partner con cui il team ha scambiato 3+ email outbound negli ultimi 30gg. Ciascun lead è linkato al thread Mail V3. Josefina risponde a buyer BILLA con template "Post-Fair Follow-up DE" che si auto-popola con `{{partner_name}}` + `{{last_sample_date}}`. In 1 click dalla sidebar 360 trasforma la richiesta sample in `sale.order` bozza. Domani mattina trova 3 activity Odoo per thread hotness >70 senza reply da 7gg. **Il pipeline si aggiorna da solo mentre il team lavora**.

---

## 2. Contesto dopo F5

Branch `feat/mail-v3-f5` merged, version 18.0.8.4.0 deployata in prod 20/04/2026. Migration F5 pulita su stage + prod:
- Smart Snooze + Undo Send + Scheduled Send live
- Dark Mode + Mobile responsive + Settings 4-tab live
- Calibration feedback hook attivi (NBA dismiss, pin hot/ignore)
- Analytics dashboard live (admin only)
- Composer unificato (wizard transient only)
- Search rispetta record rules
- 25/25 AC passati

**Cron attivi dopo F5:**
82 Mail Sync V2 · 83 Silent Partners · 84 AI Classify · 85 Body Fetch · 86 Draft Autosave Cleanup · 87 Intelligence Rebuild · 90 Outbox Process · 91 Outbox Cleanup · 92 Smart Snooze Checker · 93 Scheduled Send Dispatch

**Cron off by design:** 88/89 IMAP Flag Push/Pull.

**Da F5 report — limitazioni note (non toccare):**
- Hotness pesi fissi (auto-calibrazione = F8 dopo 30gg feedback)
- Analytics su modello transient (no stored metrics) — OK
- IMAP flag bidirezionale disabled by design

---

## 3. Scope IN — 5 deliverable core + 1 bonus

### 3.1 Auto-link email → CRM lead (2h) — **HEART OF F6**

Sistema che popola `crm.lead` automaticamente in base a scambi email significativi con un partner.

**Modello `casafolino.mail.lead.rule`** (new, config table):

```python
class MailLeadRule(models.Model):
    _name = 'casafolino.mail.lead.rule'
    _description = 'Rules for auto-linking email conversations to CRM leads'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    
    # Trigger conditions (AND)
    min_outbound_messages = fields.Integer(default=3, 
        help="Minimum outbound messages in thread")
    min_thread_age_days = fields.Integer(default=0,
        help="Thread must be at least N days old")
    max_thread_age_days = fields.Integer(default=30,
        help="Thread must not be older than N days")
    min_hotness = fields.Integer(default=40,
        help="Partner hotness must be >= this")
    require_subject_keywords = fields.Char(
        help="Comma-separated keywords (any match) in subject or body. Leave empty for no filter.")
    exclude_partners_with_open_lead = fields.Boolean(default=True)
    
    # Output config
    sales_team_id = fields.Many2one('crm.team')
    user_id = fields.Many2one('res.users', string='Assigned to')
    stage_id = fields.Many2one('crm.stage')
    tag_ids = fields.Many2many('crm.tag')
    estimated_revenue = fields.Float(default=0.0)
    
    # Stats
    lead_created_count = fields.Integer(compute='_compute_stats')
```

**Cron 94 (NEW) — Auto-link Leads** (ogni 4 ore):
- Per ciascuna rule attiva:
  - Query thread che soddisfano condizioni trigger
  - Per ogni thread: check se partner ha già `crm.lead` aperto → skip se `exclude_partners_with_open_lead=True`
  - Create `crm.lead`:
    - `partner_id` = thread.partner_id
    - `name` = "[Auto] " + thread.subject (truncated 60 chars)
    - `description` = HTML preview ultimi 3 messaggi thread
    - `source_id` = source "Mail V3 Auto-link" (create if missing)
    - `team_id`, `user_id`, `stage_id`, `tag_ids`, `expected_revenue` dalla rule
    - Campo custom `cf_mail_thread_id` → thread.id
  - Log feedback `auto_lead_created` su `casafolino.partner.intelligence.feedback`

**Regole preconfigurate** (create in migration, 3 regole default):

1. **"Hot buyers active >=3 outbound"**
   - min_outbound=3, max_age=30, min_hotness=60
   - revenue: 5000, stage: Qualificato

2. **"Post-fair follow-up active"**
   - keywords: "fiera,fair,anuga,sial,plma,fancy food,ism,biofach,marca"
   - min_outbound=2, max_age=60, min_hotness=40
   - revenue: 10000, stage: Nuovo

3. **"Sample requests"**
   - keywords: "sample,campione,muestra,sampling"
   - min_outbound=1, min_hotness=30
   - revenue: 3000, stage: Nuovo

**Campo nuovo su `crm.lead`:**
- `cf_mail_thread_id` (M2O → casafolino.mail.thread, indexed)
- `cf_auto_created` (Boolean, computed stored da `source_id` = mail_v3 auto-link)

**View `crm.lead` extension:**
- Smart button "Thread Mail V3" (se `cf_mail_thread_id` set) → apre thread
- Tab nuova "Storico Email" → list messaggi thread (read-only)
- Filter sidebar "Auto-created F6" con counter

**UI admin — menu "Mail CRM → Impostazioni → Regole Auto-link":**
- List regole + form edit
- Bottone "Esegui ora" manuale (trigger cron on-demand)
- Counter lead_created_count per rule

**Endpoint manuale `/cf/mail/v3/leads/auto_create`** (admin only, POST):
- Accetta `rule_id` optional (se omesso, esegue tutte le rule attive)
- Ritorna count lead creati + lista IDs

### 3.2 Quick Convert email → Quote (sale.order) (2h)

Bottone nella sidebar 360 del reading pane: **"Crea offerta"**.

**Wizard `casafolino.mail.quote.wizard` (TransientModel):**

```python
class MailQuoteWizard(models.TransientModel):
    _name = 'casafolino.mail.quote.wizard'
    _description = 'Wizard to quickly create sale.order from email thread'

    thread_id = fields.Many2one('casafolino.mail.thread', required=True)
    partner_id = fields.Many2one('res.partner', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 
        default=lambda self: self.partner_id.property_product_pricelist)
    payment_term_id = fields.Many2one('account.payment.term',
        default=lambda self: self.partner_id.property_payment_term_id)
    incoterm_id = fields.Many2one('account.incoterms')
    warehouse_id = fields.Many2one('stock.warehouse')
    
    line_ids = fields.One2many('casafolino.mail.quote.wizard.line', 'wizard_id')
    
    note = fields.Html(default=lambda self: self._default_note())
    
    def _default_note(self):
        # Estrae ultimi 3 messaggi thread come note contesto
        return "..."
    
    def action_create_sale_order(self):
        # Crea sale.order con:
        #   partner_id, pricelist, payment_term, incoterm, warehouse
        #   order_line da line_ids
        #   cf_mail_thread_id = self.thread_id.id  (nuovo campo)
        #   note = self.note
        # Log feedback 'quote_created_from_thread'
        # Ritorna action apertura sale.order
        pass

class MailQuoteWizardLine(models.TransientModel):
    _name = 'casafolino.mail.quote.wizard.line'
    
    wizard_id = fields.Many2one('casafolino.mail.quote.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True, 
        domain=[('sale_ok', '=', True)])
    product_uom_qty = fields.Float(default=1.0)
    price_unit = fields.Float(related='product_id.lst_price', readonly=False)
    name = fields.Char(related='product_id.name')
```

**Campo nuovo su `sale.order`:**
- `cf_mail_thread_id` (M2O → thread, indexed)
- Smart button "Thread email" → apre thread

**UI — bottone "💰 Crea offerta" nella sidebar 360** del reading pane (solo se partner_id set).
Click → apre wizard modal con:
- Partner prefilled (locked)
- Pricelist/payment/incoterm dal partner
- Campo ricerca prodotti (autocomplete) → aggiunge righe
- Preview totale
- Bottone "Crea offerta" → apre sale.order bozza in nuova tab

**Endpoint `/cf/mail/v3/thread/<int:thread_id>/quote/open_wizard`** — apre wizard via `doAction`.

**View `sale.order`:**
- Smart button "Thread Mail V3" visibile se `cf_mail_thread_id` set
- Tab "Conversazione origine" con iframe Mail V3 thread

### 3.3 Follow-up Automation (1.5h)

Sistema che crea `mail.activity` o task Odoo quando un thread "caldo" non riceve reply per troppo tempo.

**Modello `casafolino.mail.followup.rule`:**

```python
class FollowupRule(models.Model):
    _name = 'casafolino.mail.followup.rule'
    _description = 'Auto follow-up rules for stale hot threads'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Trigger
    min_hotness = fields.Integer(default=70)
    no_reply_days = fields.Integer(default=7,
        help="No inbound reply for N days after last outbound")
    min_outbound_messages = fields.Integer(default=1)
    max_thread_age_days = fields.Integer(default=60)
    
    # Action
    action_type = fields.Selection([
        ('activity', 'Create Activity on Partner'),
        ('lead_activity', 'Create Activity on CRM Lead (if linked)'),
        ('email', 'Send notification email to assigned user'),
    ], default='activity')
    activity_type_id = fields.Many2one('mail.activity.type',
        default=lambda self: self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False))
    activity_summary = fields.Char(default='Follow-up thread caldo')
    activity_note = fields.Text(default='Thread con hotness alta senza reply. Valutare follow-up.')
    activity_user_field = fields.Selection([
        ('thread_user', 'User that last replied in thread'),
        ('partner_user', 'Partner account manager'),
        ('fixed', 'Fixed user'),
    ], default='thread_user')
    activity_user_id = fields.Many2one('res.users', string='Fixed user (if selected)')
    activity_deadline_days = fields.Integer(default=1, string='Deadline in N days from now')

    # Dedup
    skip_if_activity_last_days = fields.Integer(default=3,
        help="Skip thread if activity already created in last N days")
    
    # Stats
    executions_count = fields.Integer(compute='_compute_stats')
    last_run = fields.Datetime(readonly=True)
```

**Cron 95 (NEW) — Follow-up Checker** (ogni 2 ore, daytime only 8-20):
```python
def _cron_followup_check(self):
    for rule in self.search([('active', '=', True)]):
        threads = self._find_stale_threads(rule)
        for thread in threads:
            if self._has_recent_activity(thread, rule.skip_if_activity_last_days):
                continue
            self._create_followup_action(thread, rule)
        rule.last_run = fields.Datetime.now()
```

Query `_find_stale_threads` usa ORM + filtro SQL su:
- `last_message_direction='outbound'`
- `last_message_date < NOW - no_reply_days`
- `partner_id.cf_hotness >= min_hotness`
- `message_count >= min_outbound_messages`
- `create_date > NOW - max_thread_age_days`

**Regole preconfigurate (migration, 2 default):**

1. **"Hot thread no reply 7gg"** — hotness>=70, no_reply=7, activity su thread_user
2. **"Super hot no reply 3gg"** — hotness>=85, no_reply=3, activity su partner_user con deadline 1gg

**UI admin — menu "Mail CRM → Impostazioni → Regole Follow-up":**
- List + form edit
- Bottone "Esegui ora" manuale
- Widget stats: esecuzioni ultimo mese

### 3.4 Email Templates con variabili (1.5h)

Libreria template email con placeholder sostituibili.

**Modello `casafolino.mail.template`** (NON usare `mail.template` Odoo standard per evitare conflitti e per dare UX dedicata Mail V3):

```python
class MailV3Template(models.Model):
    _name = 'casafolino.mail.template'
    _description = 'Mail V3 templates with variables'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Char(help="Short description for selector")
    
    subject = fields.Char(required=True,
        help="Supports {{partner_name}}, {{partner_country}}, {{last_order_date}}, etc.")
    body_html = fields.Html(required=True, sanitize=True)
    
    language = fields.Selection([
        ('it_IT', 'Italiano'),
        ('en_US', 'English'),
        ('de_DE', 'Deutsch'),
        ('es_ES', 'Español'),
        ('fr_FR', 'Français'),
    ], default='it_IT')
    
    category = fields.Selection([
        ('follow_up', 'Follow-up'),
        ('sample_offer', 'Sample/Offer'),
        ('post_fair', 'Post-Fair'),
        ('quote', 'Quote'),
        ('reminder', 'Reminder'),
        ('generic', 'Generic'),
    ], default='generic')
    
    account_ids = fields.Many2many('casafolino.mail.account',
        help="Visible only when composing from these accounts. Empty = all accounts.")
    
    default_signature_id = fields.Many2one('casafolino.mail.signature')
    
    usage_count = fields.Integer(default=0)
    last_used = fields.Datetime()
```

**Variable engine — helper method:**

```python
@api.model
def render_template(self, template_id, partner_id, thread_id=None, context_extra=None):
    """Render template with variable substitution.
    Variables available:
      {{partner_name}} - full name
      {{partner_first_name}} - first word of name
      {{partner_country}}
      {{partner_city}}
      {{partner_language}} - IT/EN/DE etc.
      {{last_order_date}} - last sale.order date, or 'mai'
      {{last_order_number}}
      {{days_since_last_contact}} - int
      {{sender_name}} - current user name
      {{sender_signature}} - user default signature body
      {{today_date}} - formatted today
      {{thread_subject}} - original thread subject
    Returns {subject: rendered, body_html: rendered}.
    """
    template = self.browse(template_id)
    partner = self.env['res.partner'].browse(partner_id)
    
    variables = {
        'partner_name': partner.name or '',
        'partner_first_name': (partner.name or '').split(' ')[0],
        # ... etc
    }
    if context_extra:
        variables.update(context_extra)
    
    rendered_subject = self._render_string(template.subject, variables)
    rendered_body = self._render_string(template.body_html, variables)
    
    # Log usage
    template.sudo().write({
        'usage_count': template.usage_count + 1,
        'last_used': fields.Datetime.now(),
    })
    
    return {'subject': rendered_subject, 'body_html': rendered_body}
```

Sostituzione: regex `{{(\w+)}}` con dict lookup. Unknown vars → sostituiti con stringa vuota + warning in log.

**Templates preconfigurati (migration, 6 default):**

1. IT generic — "Follow-up post incontro"
2. EN generic — "Follow-up after meeting"
3. DE post_fair — "Nachverfolgung nach Messe"
4. IT sample_offer — "Invio campioni CasaFolino"
5. EN sample_offer — "Sample shipment from CasaFolino"
6. IT quote — "Offerta commerciale"

Body HTML con placeholders effettivi: `"Gentile {{partner_first_name}}, grazie per l'interesse mostrato alla fiera..."`

**UI — integrazione nel compose wizard:**
- Nuovo campo `template_id` (M2O → casafolino.mail.template) con domain filter per account corrente
- On select template: chiama `render_template()` → prefill subject + body_html
- Warning inline "Template applicato — puoi modificare prima di inviare"

**Menu "Mail CRM → Impostazioni → Template Email":**
- List con filtro per category/language
- Form edit HTML editor + preview area con variable sample data
- Bottone "Preview con partner..." → modal seleziona partner → mostra preview finale renderizzata

### 3.5 Buyer Brief Enhance (1h)

Estensione del sidebar 360 esistente con pannello **"Commercial Context"**.

**Dati da aggregare (metodo helper `_get_commercial_context`):**

```python
def _get_commercial_context(self, partner_id):
    partner = self.env['res.partner'].browse(partner_id)
    
    # Sale orders last 12 months
    orders = self.env['sale.order'].search([
        ('partner_id', '=', partner_id),
        ('state', 'in', ['sale', 'done']),
        ('create_date', '>=', fields.Datetime.now() - timedelta(days=365)),
    ], order='create_date desc')
    
    # Top 5 SKU per quantity
    top_skus = self.env['sale.report'].read_group(
        domain=[('partner_id', '=', partner_id), ('state', 'in', ['sale', 'done'])],
        fields=['product_id', 'product_uom_qty'],
        groupby=['product_id'],
        orderby='product_uom_qty desc',
        limit=5,
    )
    
    # Open CRM leads
    open_leads = self.env['crm.lead'].search_count([
        ('partner_id', '=', partner_id),
        ('stage_id.is_won', '=', False),
        ('active', '=', True),
    ])
    
    # Open quotes
    open_quotes = self.env['sale.order'].search_count([
        ('partner_id', '=', partner_id),
        ('state', 'in', ['draft', 'sent']),
    ])
    
    return {
        'total_revenue_12m': sum(orders.mapped('amount_total')),
        'order_count_12m': len(orders),
        'last_order_date': orders[0].date_order if orders else None,
        'last_order_number': orders[0].name if orders else None,
        'top_skus': top_skus,
        'open_leads_count': open_leads,
        'open_quotes_count': open_quotes,
        'pricelist': partner.property_product_pricelist.name,
        'payment_term': partner.property_payment_term_id.name or '-',
        'preferred_language': partner.lang or '-',
        'internal_note': partner.comment or '',
    }
```

**UI — pannello nuovo nella sidebar 360** (collapsed by default, expand on click):
- Header: "💼 Commercial Context" + chevron
- Expanded: card con KPI (revenue 12m, #ordini, data ultimo ordine) + top 5 SKU + count lead aperti + count quote aperte + pricelist/payment/lingua
- Bottone "Apri partner completo" → apre form partner

**Cache in-memory** (sessione OWL, invalidata su thread change): evita query ripetute.

### 3.6 BONUS — Undo Send timer customizzabile (0.3h)

**Campo user preference:**
- `mv3_undo_send_seconds` su res.users (Integer, default=10, allowed [0, 5, 10, 30])
- 0 = disabled

**Settings tab "Visualizzazione" — aggiungi:**
- Slider/selection: "Timer annullamento invio": Disattivato / 5s / 10s / 30s

**Backend outbox — leggere da user preference:**
```python
# In mail_compose_wizard send logic
undo_seconds = self.env.user.mv3_undo_send_seconds or 0
if undo_seconds > 0:
    outbox.write({
        'state': 'undoable',
        'undo_until': fields.Datetime.now() + timedelta(seconds=undo_seconds),
    })
else:
    outbox.write({'state': 'queued'})
```

**UI toast:** countdown usa `undo_seconds` del current user (response endpoint lo restituisce).

---

## 4. Scope OUT — NON fare

- ❌ WhatsApp Business integration (F7 dedicated)
- ❌ Google Calendar integration (richiede OAuth setup, F7)
- ❌ Multi-lingua UI switcher (F7)
- ❌ Desktop browser notifications (F7)
- ❌ Hotness pesi auto-calibrati (F8, richiede 30gg feedback data)
- ❌ Smart Labels bidirezionale IMAP (cambio architettura, NO)
- ❌ Modificare intelligence engine o scoring hotness
- ❌ Toccare record rules F2.1 (sono OK)
- ❌ Schema refactor su modelli F2-F5
- ❌ Rifare Analytics dashboard (funziona)

---

## 5. Vincoli Odoo 18

1. ❌ `attrs=` → ✅ `invisible=domain`
2. ❌ `<tree>` → ✅ `<list>`
3. ❌ `_inherit` in `ir.model.access.csv`
4. OWL: `static props = ["*"]`
5. Cron via migration con `_ensure_cron` idempotent (pattern F5)
6. `bleach` per sanitize user HTML in templates
7. Datetime naive UTC
8. Extension di `crm.lead` e `sale.order` via `_inherit` classico (non `_inherits`)
9. Smart button link thread → `type="object"` con action Python che fa `return {'type': 'ir.actions.client', 'tag': 'cf_mail_v3_client', 'params': {'open_thread_id': ...}}`
10. Variable substitution NO uso di `eval()` o Python template engine — regex semplice `{{\w+}}` con dict lookup

---

## 6. Acceptance Criteria (22 AC)

### Install & Migration
- **AC1** Module 18.0.8.4.0 → 18.0.8.5.0 senza ERROR
- **AC2** Migration 18.0.8.5.0 crea: lead_rule, followup_rule, template, quote_wizard tables + campi su crm.lead, sale.order, res.users
- **AC3** Cron 94 (Auto-link) + Cron 95 (Follow-up) creati via ORM `_ensure_cron`
- **AC4** 3 lead_rule default preconfigurate
- **AC5** 2 followup_rule default preconfigurate
- **AC6** 6 template default preconfigurati

### Auto-link Lead
- **AC7** Cron 94 crea crm.lead per thread che soddisfano rule (testato con rule "Hot buyers active")
- **AC8** Lead creato ha `cf_mail_thread_id` + `source_id = Mail V3 Auto-link`
- **AC9** Smart button "Thread Mail V3" su crm.lead apre thread corretto
- **AC10** Partner con lead aperto non riceve duplicati (dedup OK)
- **AC11** Menu admin "Regole Auto-link" + bottone "Esegui ora" funzionante

### Quick Convert Quote
- **AC12** Bottone "💰 Crea offerta" in sidebar 360 apre wizard
- **AC13** Wizard prefilla pricelist/payment/incoterm dal partner
- **AC14** Autocomplete prodotti funziona + add righe
- **AC15** Action "Crea offerta" genera sale.order con `cf_mail_thread_id` set
- **AC16** Smart button da sale.order torna al thread origine

### Follow-up Automation
- **AC17** Cron 95 crea mail.activity su thread stale hotness >= soglia
- **AC18** Dedup funziona: skip thread con activity recente entro `skip_if_activity_last_days`

### Templates
- **AC19** Compose wizard ha selector template → on change prefilla subject + body
- **AC20** Variable substitution `{{partner_name}}`, `{{last_order_date}}`, `{{sender_name}}` OK
- **AC21** Menu "Template Email" + preview con partner sample funzionante

### Commercial Context + Bonus
- **AC22** Sidebar 360 mostra pannello "Commercial Context" expandable con KPI 12m + top 5 SKU + count lead/quote aperti

---

## 7. Deploy path (esegue Antonio)

**Sul server EC2 (ssh ubuntu@51.44.170.55):**

```bash
# 1. Backup preventivo
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo -Fc folinofood > /tmp/folinofood_before_f6_$(date +%Y%m%d_%H%M%S).dump

# 2. Deploy codice
cd /home/ubuntu/casafolino-os && \
git fetch --all && \
git checkout feat/mail-v3-f6 && \
git pull && \
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/

# 3. Upgrade stage prima
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tee /tmp/f6_stage_upgrade.log | tail -80

# 4. Check errori
grep -E "ERROR|CRITICAL|Traceback" /tmp/f6_stage_upgrade.log | head -20

# 5. Se pulito → prod
docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http 2>&1 | tee /tmp/f6_prod_upgrade.log | tail -80 && \
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "DELETE FROM ir_attachment WHERE name LIKE '%web.assets%';" && \
docker restart odoo-app
```

**Query verifica post-deploy:**

```bash
# Nuovi cron
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "
SELECT id, cron_name, active FROM ir_cron WHERE id BETWEEN 94 AND 95 ORDER BY id;
"

# Nuove tabelle
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "
SELECT table_name FROM information_schema.tables 
WHERE table_name IN (
  'casafolino_mail_lead_rule',
  'casafolino_mail_followup_rule',
  'casafolino_mail_template',
  'casafolino_mail_quote_wizard'
) ORDER BY table_name;
"

# Default rules/templates
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "
SELECT 
  (SELECT COUNT(*) FROM casafolino_mail_lead_rule WHERE active=true) AS lead_rules,
  (SELECT COUNT(*) FROM casafolino_mail_followup_rule WHERE active=true) AS followup_rules,
  (SELECT COUNT(*) FROM casafolino_mail_template) AS templates;
"

# Version check
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "
SELECT name, latest_version, state FROM ir_module_module WHERE name='casafolino_mail';
"
```

Expected: `18.0.8.5.0`, `installed`, lead_rules=3, followup_rules=2, templates=6.

---

## 8. Git workflow

Branch: `feat/mail-v3-f6` da `feat/mail-v3-f5`.

Commits atomici:
```
feat(mail-v3): lead auto-link — model + cron 94 + 3 default rules
feat(mail-v3): lead auto-link — crm.lead extension + smart button
feat(mail-v3): quick convert quote — wizard + sale.order extension
feat(mail-v3): quick convert quote — UI sidebar 360 button
feat(mail-v3): followup automation — model + cron 95 + 2 default rules
feat(mail-v3): mail templates — model + variable engine + 6 defaults
feat(mail-v3): mail templates — compose wizard integration
feat(mail-v3): commercial context panel sidebar 360
feat(mail-v3): BONUS undo send customizable timer
chore(mail-v3): migration 18.0.8.5.0 + manifest bump
docs(mail-v3): F6 report
```

Push ogni 3-4 commit.

---

## 9. Report atteso

File: `casafolino_mail/docs/report_f6.md` stesso template F5.

**Raccomandazioni F7 da includere:**
- WhatsApp Business integration
- Google Calendar integration (OAuth setup)
- Multi-lingua UI switcher (IT/EN/DE completo con .po files)
- Desktop browser notifications
- Lead scoring refinement basato su AC del CRM (won/lost feedback loop)

---

## 10. Ordine esecuzione

1. `git checkout -b feat/mail-v3-f6`
2. Leggi brief + report_f5.md
3. Manifest bump 18.0.8.5.0
4. Skeleton migration `migrations/18.0.8.5.0/post-migrate.py` (come F5)
5. **§3.1 Auto-link Lead** — model + campi crm.lead + cron 94 (~2h)
6. **COMMIT + PUSH batch 1**
7. **§3.2 Quick Convert Quote** — wizard + sale.order extension + UI (~2h)
8. **COMMIT + PUSH batch 2**
9. **§3.3 Follow-up Automation** — model + cron 95 (~1.5h)
10. **§3.4 Email Templates** — model + variable engine + 6 defaults (~1.5h)
11. **§3.4 cont.** — integration compose wizard
12. **COMMIT + PUSH batch 3**
13. **§3.5 Commercial Context** panel sidebar 360 (~1h)
14. **§3.6 BONUS** undo customizable timer (~0.3h)
15. Default rules + templates in migration
16. docs/report_f6.md
17. **COMMIT + PUSH finale**

**Totale: ~8-9h autonome.**

---

## 11. Una cosa sola

> F6 chiude il gap vero di CasaFolino: il pipeline commerciale invisibile.
>
> Oggi il team risponde a email ma CRM è muto. Dopo F6 il pipeline si aggiorna da solo mentre si lavora. BILLA, REWE, APA Dolci diventano lead visibili con storico, contesto e prossimi passi automatici.
>
> È la feature che quando Antonio presenterà il round €4M, farà la differenza tra "dimmi cosa hai in pipeline" e "ecco il pipeline, aggiornato in tempo reale dal lavoro del team".
>
> **MAI fermarti. 4 regole. Vai.**
