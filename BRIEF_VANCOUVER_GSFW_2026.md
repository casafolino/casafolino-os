# BRIEF — Vancouver GSFW 2026: import contatti + follow-up automatico

## Obiettivo

Importare 117 contatti dalla fiera **Grocery & Specialty Foods West 2026 (Vancouver)** in Odoo prod (`folinofood`), creando per ciascuno:
- `res.partner` (dedup su email)
- `crm.lead` con tag `FAIR:VANCOUVER-2026`
- Invio mail follow-up EN con template dedicato e CC su `martina.sinopoli@casafolino.com`

Stesso pattern operativo di SIAL Canada Montreal 2026, adattato per Vancouver.

---

## Contesto

- File CSV pulito da Claude (chat): 117 contatti validi, dedup su email già fatto, 1 scarto (nome incompleto).
- Distribuzione: 115 Canada + 2 USA. **Tutti EN**, nessun contatto QC francofono nel file.
- Templates SIAL Montreal EN/FR (Partner) sono già in produzione e funzionanti — vanno **duplicati**, non modificati.
- CC Martina: **solo su Vancouver**, fissato a livello di template Vancouver (così resta valido anche per ri-invii futuri).

---

## Scope IN

1. Crea `crm.tag` `FAIR:VANCOUVER-2026` (color 5).
2. Duplica template `SIAL Montreal EN (Partner)` → `Vancouver Grocery EN (Partner)` con subject/body adattati e CC Martina.
3. Duplica template `SIAL Montreal FR (Partner)` → `Vancouver Grocery FR (Partner)` (per simmetria, non sarà usato in questa campagna ma resta pronto).
4. Carica CSV sul server EC2 e nel container Odoo.
5. Per ogni riga del CSV: trova-o-crea `res.partner` (dedup su `email_normalized`), applica tag, crea `crm.lead` con tag e `user_id = Antonio`.
6. Test pilota su 3 contatti (i primi 3 lead Vancouver creati): invio mail e verifica rendering + CC Martina.
7. **STOP** per conferma Antonio.
8. Solo dopo OK: invio batch sui restanti 114 lead.

## Scope OUT

- Wizard import generico riusabile (rinviato a prossima settimana — brief separato).
- Import sezione FR (non ci sono contatti QC).
- Modifica dei template SIAL Montreal originali.
- Cancellazione contatti pre-esistenti che potrebbero matchare per email (li riusiamo + aggiungiamo solo il tag).

---

## Vincoli Odoo 18

- No `attrs=`, no `<tree>` (non si tocca XML in questo brief comunque).
- Datetime naive UTC.
- `mail.template`: campo `email_cc` accetta più indirizzi separati da virgola.
- `crm.lead.user_id` deve essere `res.users` valido — usa `antonio@casafolino.com`.
- `res.partner` dedup: cerca su `email_normalized` (lowercase + strip). Se non esiste, crea.
- Tag su lead: `tag_ids = [(4, tag_id)]`.
- Tag su partner: `category_id = [(4, partner_category_id)]` (se vuoi anche sul partner — opzionale, decisione tua se aggiungerlo).

---

## Acceptance criteria

- [ ] `crm.tag` `FAIR:VANCOUVER-2026` esiste con `color=5`.
- [ ] `mail.template` `Vancouver Grocery EN (Partner)` esiste con subject contenente "Grocery & Specialty Foods West 2026" e `email_cc = "martina.sinopoli@casafolino.com"`.
- [ ] `mail.template` `Vancouver Grocery FR (Partner)` esiste con CC Martina.
- [ ] 117 partner trovati o creati (somma matched + new = 117).
- [ ] 117 `crm.lead` creati con tag `FAIR:VANCOUVER-2026` e `user_id = Antonio`.
- [ ] Pilot test: 3 mail inviate, log mostra `mail.message` con `email_cc` contenente martina.
- [ ] Batch finale: 114 mail inviate, 0 errori SMTP.
- [ ] Report finale: matched / created / lead_new / mail_sent / mail_failed.

---

## Deploy path

### Sul Mac (Antonio, prima di lanciare Claude Code)

```bash
# 1. Salva il CSV scaricato dalla chat in tmp/
mkdir -p ~/casafolino-os/tmp
mv ~/Downloads/vancouver_contacts_for_odoo.csv ~/casafolino-os/tmp/

# 2. Lancia Claude Code
cd ~/casafolino-os && claude --dangerously-skip-permissions
```

### Dentro Claude Code (autonomo)

```bash
# === FASE 0: backup pre-modifica ===
ssh -i ~/.ssh/chieve_odoo_mac.pem ubuntu@51.44.170.55 \
  "docker exec -e PGPASSWORD=odoo odoo-app pg_dump -h odoo-db -U odoo folinofood > /tmp/backup_pre_vancouver_$(date +%Y%m%d_%H%M%S).sql"

# === FASE 1: upload CSV sul server e nel container ===
scp -i ~/.ssh/chieve_odoo_mac.pem tmp/vancouver_contacts_for_odoo.csv \
  ubuntu@51.44.170.55:/tmp/
ssh -i ~/.ssh/chieve_odoo_mac.pem ubuntu@51.44.170.55 \
  "docker cp /tmp/vancouver_contacts_for_odoo.csv odoo-app:/tmp/"
```

### Sul server EC2 — dentro container Odoo

Creazione tag + duplicazione template + import + lead. Lancia tutto con `odoo shell`:

```bash
ssh -i ~/.ssh/chieve_odoo_mac.pem ubuntu@51.44.170.55
docker exec -i odoo-app odoo shell -d folinofood --no-http << 'PYEOF'
import csv
from odoo.api import Environment

# === STEP 1: tag ===
Tag = env['crm.tag']
tag = Tag.search([('name', '=', 'FAIR:VANCOUVER-2026')], limit=1)
if not tag:
    tag = Tag.create({'name': 'FAIR:VANCOUVER-2026', 'color': 5})
    print(f"✓ Tag creato id={tag.id}")
else:
    print(f"= Tag esiste id={tag.id}")

# === STEP 2: duplica template EN ===
T = env['mail.template']
src_en = T.search([('name', '=', 'SIAL Montreal EN (Partner)')], limit=1)
assert src_en, "Template SIAL Montreal EN (Partner) non trovato"

dst_en = T.search([('name', '=', 'Vancouver Grocery EN (Partner)')], limit=1)
if not dst_en:
    dst_en = src_en.copy({'name': 'Vancouver Grocery EN (Partner)'})
    new_subject = 'Great meeting you at Grocery & Specialty Foods West 2026, Vancouver'
    new_body = (src_en.body_html or '')
    # Sostituzioni testuali: aggiorna riferimenti SIAL Montreal → Vancouver
    new_body = new_body.replace('SIAL Canada in Montreal', 'Grocery & Specialty Foods West 2026 in Vancouver')
    new_body = new_body.replace('SIAL Canada Montreal', 'Grocery & Specialty Foods West 2026 (Vancouver)')
    new_body = new_body.replace('SIAL Canada', 'Grocery & Specialty Foods West (Vancouver)')
    new_body = new_body.replace('SIAL Montreal', 'Grocery & Specialty Foods West (Vancouver)')
    new_body = new_body.replace('SIAL', 'GSFW')
    dst_en.write({
        'subject': new_subject,
        'body_html': new_body,
        'email_cc': 'martina.sinopoli@casafolino.com',
    })
    print(f"✓ Template EN creato id={dst_en.id} CC={dst_en.email_cc}")
else:
    print(f"= Template EN esiste id={dst_en.id}")

# === STEP 3: duplica template FR (per simmetria) ===
src_fr = T.search([('name', '=', 'SIAL Montreal FR (Partner)')], limit=1)
if src_fr:
    dst_fr = T.search([('name', '=', 'Vancouver Grocery FR (Partner)')], limit=1)
    if not dst_fr:
        dst_fr = src_fr.copy({'name': 'Vancouver Grocery FR (Partner)'})
        new_subject_fr = 'Ravis de notre rencontre au Grocery & Specialty Foods West 2026, Vancouver'
        new_body_fr = (src_fr.body_html or '')
        new_body_fr = new_body_fr.replace('SIAL Canada à Montréal', 'Grocery & Specialty Foods West 2026 à Vancouver')
        new_body_fr = new_body_fr.replace('SIAL Canada Montréal', 'Grocery & Specialty Foods West (Vancouver)')
        new_body_fr = new_body_fr.replace('SIAL Canada', 'Grocery & Specialty Foods West (Vancouver)')
        new_body_fr = new_body_fr.replace('SIAL Montreal', 'Grocery & Specialty Foods West (Vancouver)')
        new_body_fr = new_body_fr.replace('SIAL', 'GSFW')
        dst_fr.write({
            'subject': new_subject_fr,
            'body_html': new_body_fr,
            'email_cc': 'martina.sinopoli@casafolino.com',
        })
        print(f"✓ Template FR creato id={dst_fr.id}")
    else:
        print(f"= Template FR esiste id={dst_fr.id}")

env.cr.commit()

# === STEP 4: import partner + lead ===
Partner = env['res.partner']
Lead = env['crm.lead']
antonio = env['res.users'].search([('login', '=', 'antonio@casafolino.com')], limit=1)
assert antonio, "Utente Antonio non trovato"

stats = {'matched_partner': 0, 'new_partner': 0, 'new_lead': 0, 'lead_skipped': 0}
created_lead_ids = []

with open('/tmp/vancouver_contacts_for_odoo.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        email = (row.get('email') or '').strip().lower()
        if not email:
            continue
        # find or create partner
        p = Partner.search([('email_normalized', '=', email)], limit=1)
        if not p:
            p = Partner.search([('email', '=ilike', email)], limit=1)
        if p:
            stats['matched_partner'] += 1
        else:
            country = env['res.country'].search([('name', '=', row.get('country') or 'Canada')], limit=1)
            p = Partner.create({
                'name': row.get('name') or row.get('company') or email,
                'email': email,
                'phone': row.get('phone') or False,
                'function': row.get('job_title') or False,
                'city': row.get('city') or False,
                'state_id': False,  # mapping provincia opzionale, lasciamo vuoto
                'zip': row.get('zip') or False,
                'country_id': country.id if country else False,
                'lang': 'en_US',
                'is_company': False,
                'company_name': row.get('company') or False,
            })
            stats['new_partner'] += 1
        # check se esiste già un lead Vancouver per questo partner
        existing_lead = Lead.search([
            ('partner_id', '=', p.id),
            ('tag_ids', 'in', [tag.id]),
        ], limit=1)
        if existing_lead:
            stats['lead_skipped'] += 1
            continue
        lead = Lead.create({
            'name': f"Vancouver 2026 — {row.get('company') or row.get('name')}",
            'partner_id': p.id,
            'email_from': email,
            'phone': row.get('phone') or False,
            'contact_name': row.get('name') or False,
            'partner_name': row.get('company') or False,
            'function': row.get('job_title') or False,
            'user_id': antonio.id,
            'tag_ids': [(4, tag.id)],
            'type': 'lead',
            'description': f"Imported from GSFW 2026 Vancouver contact list — {row.get('city') or ''} {row.get('state') or ''}".strip(),
        })
        created_lead_ids.append(lead.id)
        stats['new_lead'] += 1

env.cr.commit()
print(f"\n=== IMPORT REPORT ===")
print(f"  Partner matched (esistenti): {stats['matched_partner']}")
print(f"  Partner nuovi creati: {stats['new_partner']}")
print(f"  Lead nuovi creati: {stats['new_lead']}")
print(f"  Lead skippati (già presenti con tag Vancouver): {stats['lead_skipped']}")
print(f"  Primi 3 lead ID per pilot: {created_lead_ids[:3]}")
PYEOF
```

### STOP ESPLICITO PRE-PILOT

Antonio deve confermare di vedere in Odoo i lead Vancouver creati con tag corretto **prima** di procedere all'invio mail. Apri:

```
https://erp.casafolino.com/odoo/crm  (filtra tag = FAIR:VANCOUVER-2026)
```

Verifica:
- Numero lead = 117 (o leggermente meno se alcuni partner avevano già un lead Vancouver duplicato).
- Tutti assegnati ad Antonio.
- Tag `FAIR:VANCOUVER-2026` presente.

### FASE 5 — Pilot test (3 mail)

```bash
docker exec -i odoo-app odoo shell -d folinofood --no-http << 'PYEOF'
T = env['mail.template']
Lead = env['crm.lead']
tpl = T.search([('name', '=', 'Vancouver Grocery EN (Partner)')], limit=1)
tag = env['crm.tag'].search([('name', '=', 'FAIR:VANCOUVER-2026')], limit=1)

# Prendi i primi 3 lead Vancouver senza ancora mail inviata
pilot_leads = Lead.search([
    ('tag_ids', 'in', [tag.id]),
    ('description', 'not ilike', '__VANCOUVER_MAIL_SENT__'),
], order='id asc', limit=3)

print(f"Pilot leads: {pilot_leads.ids}")
for lead in pilot_leads:
    if not lead.partner_id:
        continue
    # Invia mail al partner usando il template
    tpl.send_mail(lead.partner_id.id, force_send=True, email_layout_xmlid='mail.mail_notification_light')
    # Marca lead come "mail inviata" nella description
    lead.description = (lead.description or '') + '\n__VANCOUVER_MAIL_SENT__'
    print(f"  ✓ Mail inviata a {lead.partner_id.email}")

env.cr.commit()
print("Pilot completato. Controlla la mail di Martina per CC.")
PYEOF
```

### STOP ESPLICITO PRE-BATCH

Antonio deve verificare:
1. Le 3 mail pilot sono arrivate ai destinatari (chiedi conferma a Josefina/team).
2. Martina ha ricevuto la copia in CC su tutte e 3.
3. Rendering OK (no testo rotto, link funzionanti).

Solo dopo "✅ OK batch Vancouver" da Antonio → procedi.

### FASE 6 — Batch finale (114 mail rimanenti)

```bash
docker exec -i odoo-app odoo shell -d folinofood --no-http << 'PYEOF'
T = env['mail.template']
Lead = env['crm.lead']
tpl = T.search([('name', '=', 'Vancouver Grocery EN (Partner)')], limit=1)
tag = env['crm.tag'].search([('name', '=', 'FAIR:VANCOUVER-2026')], limit=1)

remaining = Lead.search([
    ('tag_ids', 'in', [tag.id]),
    ('description', 'not ilike', '__VANCOUVER_MAIL_SENT__'),
], order='id asc')

sent, failed = 0, 0
for lead in remaining:
    if not lead.partner_id or not lead.partner_id.email:
        failed += 1
        continue
    try:
        tpl.send_mail(lead.partner_id.id, force_send=False)  # accodato
        lead.description = (lead.description or '') + '\n__VANCOUVER_MAIL_SENT__'
        sent += 1
    except Exception as e:
        print(f"  ✗ {lead.partner_id.email}: {e}")
        failed += 1

env.cr.commit()
print(f"\n=== BATCH REPORT ===")
print(f"  Mail accodate: {sent}")
print(f"  Errori: {failed}")
print(f"  Le mail partono via cron mail.mail entro pochi minuti.")
PYEOF
```

---

## Note finali

- **Cron Odoo invio mail**: `Mail: Email Queue Manager` gira ogni 60s, quindi le mail accodate partono in ~1 minuto.
- **Verifica deliverability**: dopo 30 minuti, controlla in Odoo `Discuss → Tracking` per bounce rate Vancouver.
- **Tag in CRM**: filtra `FAIR:VANCOUVER-2026` per dashboard follow-up dedicato.
- **Backup**: già fatto in FASE 0. Se qualcosa va storto: `psql ... < /tmp/backup_pre_vancouver_*.sql`.

---

## Riepilogo numeri attesi

| Metrica | Valore atteso |
|---|---|
| Partner trovati esistenti | ~5–10 (clienti/contatti già in DB) |
| Partner nuovi creati | ~107–112 |
| Lead nuovi creati | 117 |
| Mail pilot | 3 |
| Mail batch finale | 114 |
| CC Martina | 117 (su tutte) |
