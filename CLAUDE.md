# CasaFolino OS — Guida Tecnica per Claude Code

## Progetto
Modulo Odoo 18 custom per CasaFolino Srls (azienda food italiana).
Stack: Odoo 18 Enterprise, Docker, PostgreSQL 15, AWS EC2.

---

## REGOLE CRITICHE OWL ODOO 18 — MAI VIOLARE

### 1. Event handlers nel template XML
**VIETATO** — arrow function con blocco `{}`:
```xml
<!-- SBAGLIATO: genera "Unexpected identifier" in OWL -->
<select t-on-change="(e) => { if(e.target.value) this.doSomething(e.target.value); }"/>
<input t-on-change="(e) => { this.state.val = e.target.value; }"/>
```
**CORRETTO** — usa sempre un metodo dedicato nel componente:
```xml
<!-- GIUSTO -->
<select t-on-change="onSelectChange"/>
<input t-on-change="onInputChange"/>
```
```javascript
// Nel componente JS:
onSelectChange(ev) {
    if (ev.target.value) this.doSomething(ev.target.value);
}
onInputChange(ev) {
    this.state.val = ev.target.value;
}
```

### 2. CSS — niente import esterni
**VIETATO**:
```css
/* SBAGLIATO: rompe la compilazione del bundle */
@import url('https://fonts.googleapis.com/css2?family=Inter');
```
**CORRETTO**: usa font di sistema o font già in Odoo.

### 3. RPC calls nel JS
**VIETATO**:
```javascript
// SBAGLIATO in Odoo 18
const rpc = useService('rpc');
import rpc from 'web.rpc';
```
**CORRETTO**:
```javascript
// GIUSTO in Odoo 18
import { rpc } from "@web/core/network/rpc";
// Poi usalo direttamente:
const result = await rpc("/web/dataset/call_kw", { ... });
```

### 4. Views XML — attributi condizionali
**VIETATO**:
```xml
<!-- SBAGLIATO: attrs= non esiste in Odoo 18 -->
<field name="x" attrs="{'invisible': [('state', '=', 'draft')]}"/>
```
**CORRETTO**:
```xml
<!-- GIUSTO -->
<field name="x" invisible="state == 'draft'"/>
```

### 5. Views XML — invisible/readonly expressions
**VIETATO**:
```xml
<!-- SBAGLIATO: parentesi tonde negli invisible -->
<field name="x" invisible="(state == 'draft')"/>
```
**CORRETTO**:
```xml
<!-- GIUSTO: niente parentesi tonde -->
<field name="x" invisible="state == 'draft'"/>
```

### 6. Assets nel manifest
**VIETATO**:
```python
# SBAGLIATO: web.assets_web non esiste per backend
'assets': {'web.assets_web': [...]}
```
**CORRETTO**:
```python
# GIUSTO
'assets': {'web.assets_backend': [...]}
```

### 7. Menus XML — ordine dichiarazione
**REGOLA**: le `record` action devono venire PRIMA dei `menuitem` che le referenziano.
```xml
<!-- PRIMA l'action -->
<record id="action_cf_mail" model="ir.actions.client">...</record>
<!-- POI il menu che usa l'action -->
<menuitem id="menu_cf_mail" action="action_cf_mail"/>
```

### 8. Conflitti ir_model_data
Se appare: `found record of different model ir.actions.client (ID)`:
```sql
DELETE FROM ir_model_data WHERE name='action_cf_mail_client' AND module='casafolino_mail';
```

---

## STRUTTURA MODULI CASAFOLINO
```
casafolino_mail/
├── __manifest__.py          # version, depends, assets
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── cf_contact.py        # res.partner extension
│   ├── cf_mail_message.py   # cf.mail.message model
│   └── cf_mail_account.py   # cf.mail.account model
├── security/
│   └── ir.model.access.csv
├── static/
│   └── src/
│       ├── css/cf_mail_client.css
│       ├── js/cf_mail_client.js
│       └── xml/cf_mail_client.xml
└── views/
    ├── cf_mail_views.xml
    └── menus.xml
```

## Brand CasaFolino
- **Accent primario**: `#5A6E3A` (verde)
- **Accent dark**: `#3d4d28`
- **Accent light**: `rgba(90,110,58,0.1)`
- **Font**: sistema sans-serif (no Google Fonts)

## Deploy
```bash
# Sul server AWS EC2 51.44.170.55
~/deploy.sh
```

## Database
- **Stage**: `folinofood_stage` (per sviluppo)
- **Prod**: `folinofood` (non toccare mai senza autorizzazione esplicita)

## Comandi utili
```bash
# Update modulo specifico
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http

# Pulisci asset cache
docker exec odoo-db psql -U odoo -d folinofood_stage -c "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';"

# Restart
docker restart odoo-app
```

## Colonne res_partner custom (già esistenti nel DB)
cf_job_title, cf_department, cf_linkedin, cf_instagram, cf_whatsapp,
cf_language, cf_country_origin, cf_birthday, cf_fairs, cf_notes,
cf_last_contact, cf_email_count, cf_opt_out, cf_gdpr_consent,
cf_gdpr_date, cf_source, cf_rating
