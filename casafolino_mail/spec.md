# CasaFolino Mail V2 — Spec Tecnica

**Versione spec:** 1.0 — 17/04/2026
**Owner:** Antonio Folino
**Stato:** Draft — da implementare in 2 brief sessioni Claude Code

---

## 1. Problema

Il modulo `casafolino_mail` attuale contiene **due implementazioni parallele** dello stesso layer mail:
- Stack vecchio `cf.mail.*` (UI Gmail-style, 1700 LOC, 1.200 messaggi in DB, 2 cron orfani che scaricano ogni 20 min)
- Stack nuovo `casafolino.mail.*` (staging triage, 2330 LOC, 14.500 messaggi in DB, cron post_init_hook probabilmente mai eseguito)

Conseguenze:
- Due sync IMAP paralleli saturano Gmail → errori auth frequenti
- Bug ricorrenti: quando ne fixi uno, si rompe l'altro
- Menu puntano al vecchio, dati reali nel nuovo → incoerenza UX
- 3 mesi di patch senza convergenza

## 2. Decisione strategica

**Il modulo non è un client email. È un ponte selettivo Gmail → CRM.**

Gmail resta il client primario (lettura, ricerca, mobile, archivio). In Odoo finisce solo ciò che serve al business, arricchito e collegato a partner/lead.

## 3. Architettura target

### 3 livelli indipendenti

```
┌───────────────────────────────────────────────────────────┐
│ Gmail (client primario, NON modificato)                   │
└────────────────────┬──────────────────────────────────────┘
                     │ IMAP selettivo (label + allowlist)
                     ▼
┌───────────────────────────────────────────────────────────┐
│ [1] INGESTION                                             │
│  - casafolino.mail.account (configurazione IMAP)          │
│  - Cron "CasaFolino: Mail Sync" (ogni 15 min)             │
│  - Fetch selettivo: label "Odoo" + allowlist domini       │
│  - Dedup via UNIQUE constraint DB                         │
└────────────────────┬──────────────────────────────────────┘
                     ▼
┌───────────────────────────────────────────────────────────┐
│ [2] TRIAGE                                                │
│  - casafolino.mail.message (staging con state machine)    │
│  - casafolino.mail.sender_policy (regole configurabili)   │
│  - State: new → auto_keep | auto_discard | review         │
│  - Review → keep | discard (manuale)                      │
└────────────────────┬──────────────────────────────────────┘
                     ▼
┌───────────────────────────────────────────────────────────┐
│ [3] CRM ENRICHMENT                                        │
│  - Timeline su res.partner (One2many messages)            │
│  - Quick convert: message → crm.lead (action button)      │
│  - Silent partners: cron → mail.activity automatica       │
└───────────────────────────────────────────────────────────┘
```

### Modelli

**`casafolino.mail.account`** — Configurazione casella (esistente, da mantenere con modifiche)

Campi essenziali:
- `name`, `email_address`, `app_password`, `imap_host`, `imap_port`
- `gmail_label` (nuovo, default "Odoo")
- `use_allowlist` (nuovo, boolean, default True)
- `responsible_user_id`
- `last_fetch_datetime`, `last_successful_fetch_datetime` (separati!)
- `last_imap_uid` (per resume sync)
- `state` (draft/connected/error), `last_error`

**`casafolino.mail.message`** — Staging messaggi (esistente, da semplificare)

Campi essenziali:
- `account_id`, `message_id_rfc`, `imap_uid`, `imap_folder`
- `direction` (inbound/outbound)
- `subject`, `sender_email`, `sender_domain`, `sender_name`, `recipient_emails`
- `body_html`, `body_plain`, `snippet` (200 char per list view)
- `email_date`
- `partner_id`, `lead_id`
- `state` (new/auto_keep/keep/auto_discard/discard/review)
- `classification` (commerciale/admin/fornitore/newsletter/interno/personale — opzionale in V2, reservato per ciclo AI successivo)
- `language` (IT/EN/DE/FR/ES)
- `is_read`, `is_important`
- `attachments_count`
- `policy_applied_id` (tracking: quale regola ha deciso)

**Constraints:**
- UNIQUE (account_id, message_id_rfc)
- Index su partner_id, email_date, state, sender_domain

**`casafolino.mail.sender_policy`** — Regole triage (NUOVO, sostituisce blacklist + sender_rule)

Campi:
- `name`, `active`, `priority` (10-100)
- `pattern_type` (email_exact/domain/regex_subject)
- `pattern_value` (es. `*@rewe-group.at`)
- `action` (auto_keep/auto_discard/escalate/review)
- `default_owner_id` (Many2one res.users)
- `default_tag_ids` (Many2many cf.contact.tag)
- `auto_create_partner` (boolean)
- `notes`

**`casafolino.mail.tracking`** — Pixel tracking (esistente, mantenere com'è)

### Estensioni

**`res.partner`** (inherit):
- `casafolino_mail_ids` (One2many casafolino.mail.message, compute o domain filter)
- `casafolino_last_email_date` (Datetime computed)
- `casafolino_email_count` (Integer computed)
- Tab nuova "Email CRM" nella form

**`crm.lead`** (inherit):
- `source_email_id` (Many2one casafolino.mail.message)

## 4. Flow funzionali

### 4.1 Ingestion flow

```
Cron ogni 15 min:
 FOR EACH account in casafolino.mail.account (active=True):
   try:
     connect IMAP (host, port, user, app_password)
     if account.use_allowlist:
       domains = read allowlist from sender_policy where action='auto_keep'
     fetch from label "Odoo" OR FROM/TO in allowlist domains
     from UID > account.last_imap_uid
     batch 100 per volta
     FOR EACH message:
       if exists (account_id, message_id_rfc): skip
       parse MIME, extract partner_match
       apply sender_policy → set state
       create casafolino.mail.message
     update account.last_imap_uid, last_successful_fetch_datetime
     set state='connected', last_error=''
   except IMAPAuth:
     set state='error', last_error=...
     create mail.activity to responsible_user_id
   except:
     log error, next account
```

### 4.2 Triage flow

```
Message creato con state='new' da ingestion:
  find matching sender_policy (by priority desc):
    pattern_type='email_exact' AND pattern_value==sender_email → match
    pattern_type='domain' AND sender_domain matches wildcard → match
    pattern_type='regex_subject' AND subject regex match → match
  if policy found:
    apply action:
      auto_keep → state='auto_keep', apply tags, owner, partner
      auto_discard → state='auto_discard'
      escalate → state='review', is_important=True
      review → state='review'
    policy_applied_id = policy.id
  else:
    state stays 'new' (will appear in review queue)
```

### 4.3 CRM enrichment flow

**Quick convert email → lead** (azione su form message):
```
button "Crea Lead CRM":
  partner_id = message.partner_id or create new partner
  lead = crm.lead.create({
    'name': message.subject,
    'partner_id': partner_id.id,
    'email_from': message.sender_email,
    'description': message.body_plain[:2000],
    'user_id': message.policy_applied_id.default_owner_id or env.user,
    'source_id': ref('utm.utm_source_email'),
    'tag_ids': message.policy_applied_id.default_tag_ids,
    'source_email_id': message.id,
  })
  open lead in new view
```

**Timeline su partner** (tab xpath):
```xml
<xpath expr="//notebook" position="inside">
  <page string="Email CRM" name="casafolino_emails">
    <field name="casafolino_mail_ids" readonly="1">
      <list>
        <field name="email_date"/>
        <field name="direction"/>
        <field name="sender_email"/>
        <field name="subject"/>
        <field name="state"/>
        <button name="action_view_message" type="object" string="Apri"/>
      </list>
    </field>
  </page>
</xpath>
```

**Silent partners alert** (cron giornaliero):
```
cron daily 07:00:
  threshold_days = config_param('casafolino_mail.silent_days_threshold', 21)
  SELECT partner_id FROM res_partner
  WHERE active AND id IN (SELECT partner_id FROM crm_lead WHERE stage_id.is_won=False AND active)
    AND (SELECT MAX(email_date) FROM casafolino_mail_message
         WHERE partner_id=res_partner.id AND state IN ('keep','auto_keep'))
        < NOW() - INTERVAL 'threshold_days'
  FOR EACH silent_partner:
    create mail.activity:
      activity_type='todo'
      summary='Riattivare conversazione'
      note=f'Partner silente da oltre {threshold_days} giorni'
      user_id=partner.user_id or salesperson
      res_id=partner.id, res_model='res.partner'
```

## 5. Menu finali (solo 5 voci)

```
Mail CasaFolino (root, icon casafolino_mail/static/description/icon.png)
  ├── Inbox Triage (state='review' OR state='new', default filter last 7 days)
  ├── Tenute CRM (state IN 'keep','auto_keep')
  ├── Archivio Scarto (state IN 'discard','auto_discard') — admin only
  └── Configurazione (group_system)
       ├── Account IMAP
       └── Regole Mittenti (sender_policy)
```

Nessun menu per: blacklist (sostituita da policy), tracking (è automatico), compose (si usa Gmail).

## 6. Security

**Gruppi nuovi:**
- `casafolino_mail.group_user` — vede solo le sue email (secondo responsible_user_id)
- `casafolino_mail.group_manager` — vede tutto, configura policy

**Record rules:**
- message: user vede se `account_id.responsible_user_id = env.user` o `env.user in assigned_user_ids` (se esiste)
- manager: accesso totale

## 7. Acceptance criteria (globali)

Alla fine di TUTTO il lavoro, il modulo deve soddisfare:

1. ✅ Zero modelli `cf.mail.*` in `ir_model`
2. ✅ Un solo cron attivo: "CasaFolino: Mail Sync" ogni 15 min
3. ✅ Cron 80 e 81 eliminati da `ir_cron`
4. ✅ UNIQUE constraint `(account_id, message_id_rfc)` attivo
5. ✅ `last_fetch_datetime` si aggiorna a ogni esecuzione cron
6. ✅ Almeno 3 sender_policy di esempio create via post_init_hook (esempio: `*@rewe-group.at` → auto_keep, `*newsletter*` → auto_discard)
7. ✅ Tab "Email CRM" visibile nella form di `res.partner`
8. ✅ Bottone "Crea Lead CRM" funziona da form message
9. ✅ Cron silent partner crea mail.activity correttamente
10. ✅ Sync Gmail parte senza errori auth (dopo reset app password)
11. ✅ Nessun errore in `docker logs odoo-app` relativo a casafolino_mail per almeno 1h post-deploy

## 8. Fuori scope V2 (ciclo successivo)

- AI classifier (Groq) automatico su category + sentiment + language
- SLA dashboard buyer
- Lead scoring 0-100
- Compose/reply da Odoo con template
- Snippet library multilingua
- Auto-merge contatti duplicati
- Redaction IBAN/card

## 9. Rischi e mitigazioni

| Rischio | Probabilità | Mitigazione |
|---|---|---|
| Demolizione vecchio stack rompe res.partner (cf_contact) | Media | Verificare pre-demolizione che cf_contact.py NON usi modelli cf.mail.*. Audit query: `grep "cf\.mail\." models/cf_contact.py` |
| Perdita dati unici in cf_mail_message (1200 record) | Bassa | Query pre-demolizione: quanti hanno message_id_rfc NON presente in casafolino_mail_message. Se <50 → ignora. Se >50 → INSERT SELECT migration |
| App password Josefina/Martina bloccano sync | Alta | Fase 0: rigenerare app password Google, aggiornare record. Obbligatorio prima di brief 1 |
| Cron silent partner scatena troppe mail.activity | Bassa | Filtro: solo partner con crm.lead attivo. Non su TUTTI i partner |
| View xpath su res.partner confligge con altri moduli (cf_contact) | Media | Usare priority=99 su view inherit + testare su stage |
