# BRIEF TECNICO — CasaFolino Mail Hub v2
## Refactoring `casafolino_mail` con IMAP, Triage UI e Sync Contatti

**Data:** Aprile 2026  
**Modulo target:** `casafolino_mail` (già esistente nel repo `casafolino-os`)  
**Obiettivo:** Trasformare il modulo mail in un vero CRM email hub — tipo HubSpot — dove ogni email viene scaricata, valutata, e se tenuta viene collegata al contatto Odoo con tutto lo storico.

---

## CONTESTO TECNICO

### Infrastruttura
- Server EC2: `51.44.170.55`, porta Odoo `4589`
- Container: `odoo-app` + `odoo-db` (postgres:15)
- Addons host: `/docker/enterprise18/addons/custom/`
- Repo GitHub: `github.com/casafolino/casafolino-os`
- DB stage: `folinofood_stage` | DB prod: `folinofood`
- Python disponibile nel container: Python 3.10+ con librerie standard (`imaplib`, `email` già incluse)

### Cosa esiste già in `casafolino_mail`
- Agente 007: arricchimento contatti via Groq (llama-3.3-70b-versatile) + Serper.dev
- API keys in `ir.config_parameter`: `casafolino.groq_api_key`, `casafolino.serper_api_key`
- Estensioni `res.partner` per campi custom (007)
- **NON TOCCARE** la logica Agente 007 esistente — si integra, non si riscrive

### Regole Odoo 18 da rispettare SEMPRE
1. NO `attrs=` → usare `invisible=`, `readonly=`, `required=` direttamente
2. NO `tree` → usare `list`
3. Cron XML: NON usare `model_id ref=` → causa ParseError. Definire cron con `model` come stringa
4. Actions (`ir.actions.act_window`) PRIMA delle view nel file XML
5. Menuitem DOPO l'`act_window` a cui fanno riferimento
6. Kanban: `t-name="card"` non `t-name="kanban-box"`
7. Bottoni dentro page: `<div class="o_row">` non `<header>`
8. Notebook: `<xpath expr="//notebook" position="inside">` con `priority` 99
9. Root menuitem: richiede `web_icon="casafolino_mail,static/description/icon.png"`

---

## ARCHITETTURA — PANORAMICA

```
Gmail Account 1 (antonio@)  ─┐
Gmail Account 2 (josefina@) ─┤──→ IMAP SSL ──→ casafolino.mail.message (staging)
Gmail Account 3 (info@)     ─┘       │
                                      ├──→ Auto-match con res.partner
                                      ├──→ Blacklist check (globale)
                                      └──→ TRIAGE UI
                                            │
                                  ┌─────────┴─────────┐
                                  ▼                   ▼
                                KEEP               DISCARD
                                  │                   │
                            Download body        Elimina dopo 30gg
                            + allegati
                                  │
                            Collega a partner
                            (chatter mail.message)
                                  │
                            Se partner "tracked":
                            scarica TUTTO lo storico
```

---

## CONNESSIONE: IMAP con Gmail App Password

**Nessuna dipendenza esterna.** Si usa `imaplib` + `email` della libreria standard Python.

Ogni account Gmail necessita di:
- 2FA attivo sull'account Google (già fatto)
- Password app generata da: Google Account → Sicurezza → Password per le app
- Host: `imap.gmail.com`, Porta: `993`, SSL: Sì

Cartelle Gmail IMAP:
- Email ricevute: `INBOX`
- Email inviate: `[Gmail]/Posta inviata` (in italiano) o `[Gmail]/Sent Mail` (in inglese)
- Per determinare il nome corretto: il codice deve fare `imap.list()` e cercare la cartella con attributo `\Sent`

---

## STEP 1 — Modelli Dati

### File: `models/mail_account.py`

**Modello: `casafolino.mail.account`**

| Campo | Tipo | Note |
|---|---|---|
| `name` | Char | Nome descrittivo (es. "Antonio - Gmail") |
| `email_address` | Char | required, es. antonio@casafolino.com |
| `responsible_user_id` | Many2one → res.users | Chi fa il triage per questa casella |
| `imap_host` | Char | Default: `imap.gmail.com` |
| `imap_port` | Integer | Default: `993` |
| `imap_password` | Char | Password app Gmail (campo con widget password) |
| `imap_use_ssl` | Boolean | Default: True |
| `sent_folder` | Char | Auto-detected o manuale. Es. `[Gmail]/Posta inviata` |
| `sync_start_date` | Date | Default: 2025-01-01 |
| `last_fetch_datetime` | Datetime | Ultimo fetch completato |
| `last_fetch_uid` | Char | Ultimo UID processato (per fetch incrementale) |
| `state` | Selection | `draft`, `connected`, `error` |
| `error_message` | Text | Ultimo errore di connessione |
| `active` | Boolean | Default True |
| `fetch_inbox` | Boolean | Default True — scarica email ricevute |
| `fetch_sent` | Boolean | Default True — scarica email inviate |

**Metodi:**
- `action_test_connection()` — Connessione IMAP, login, lista cartelle. Se OK → state='connected', rileva automaticamente sent_folder
- `action_fetch_now()` — Fetch manuale (chiama il fetch engine)
- `_get_imap_connection()` — Costruisce connessione IMAP SSL, fa login, ritorna oggetto

```python
import imaplib

def _get_imap_connection(self):
    """Apre connessione IMAP SSL a Gmail."""
    self.ensure_one()
    try:
        if self.imap_use_ssl:
            imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        else:
            imap = imaplib.IMAP4(self.imap_host, self.imap_port)
        imap.login(self.email_address, self.imap_password)
        return imap
    except Exception as e:
        self.write({'state': 'error', 'error_message': str(e)})
        raise UserError(f"Connessione IMAP fallita: {e}")

def action_test_connection(self):
    """Testa la connessione e rileva la cartella Sent."""
    self.ensure_one()
    imap = self._get_imap_connection()
    
    # Rileva cartella sent
    status, folders = imap.list()
    sent_folder = None
    for folder in folders:
        decoded = folder.decode()
        if '\\Sent' in decoded:
            # Estrai il nome della cartella tra virgolette
            parts = decoded.split('"')
            if len(parts) >= 3:
                sent_folder = parts[-2]
            break
    
    imap.logout()
    
    vals = {'state': 'connected', 'error_message': False}
    if sent_folder:
        vals['sent_folder'] = sent_folder
    self.write(vals)
    
    return {'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'OK', 'message': f'Connessione riuscita. Sent: {sent_folder}', 'type': 'success'}}
```

**Vista form per mail_account:**
```xml
<record id="casafolino_mail_account_form" model="ir.ui.view">
    <field name="name">casafolino.mail.account.form</field>
    <field name="model">casafolino.mail.account</field>
    <field name="arch" type="xml">
        <form string="Account Email">
            <div class="o_row mb-3">
                <button name="action_test_connection" string="🔌 Test Connessione" type="object" class="btn btn-primary"/>
                <button name="action_fetch_now" string="📥 Fetch Now" type="object" class="btn btn-success" invisible="state != 'connected'"/>
            </div>
            <group>
                <group string="Account">
                    <field name="name"/>
                    <field name="email_address"/>
                    <field name="responsible_user_id"/>
                    <field name="state" widget="badge" decoration-info="state=='draft'" decoration-success="state=='connected'" decoration-danger="state=='error'"/>
                </group>
                <group string="IMAP">
                    <field name="imap_host"/>
                    <field name="imap_port"/>
                    <field name="imap_password" password="True"/>
                    <field name="imap_use_ssl"/>
                    <field name="sent_folder"/>
                </group>
                <group string="Sync">
                    <field name="sync_start_date"/>
                    <field name="last_fetch_datetime"/>
                    <field name="fetch_inbox"/>
                    <field name="fetch_sent"/>
                </group>
            </group>
            <field name="error_message" invisible="state != 'error'" readonly="1"/>
        </form>
    </field>
</record>
```

---

### File: `models/mail_message_staging.py`

**Modello: `casafolino.mail.message` (STAGING — NON confondere con `mail.message` nativo Odoo)**

| Campo | Tipo | Note |
|---|---|---|
| `account_id` | Many2one → casafolino.mail.account | required |
| `message_id_rfc` | Char | Header Message-ID RFC 2822, UNIQUE per deduplicazione |
| `imap_uid` | Char | UID IMAP per riscaricare il body dopo |
| `imap_folder` | Char | Cartella di origine (INBOX, Sent) |
| `direction` | Selection | `inbound` / `outbound` |
| `sender_email` | Char | Indirizzo mittente |
| `sender_name` | Char | Nome mittente (estratto da header) |
| `sender_domain` | Char | Dominio estratto automaticamente, stored, index=True |
| `recipient_emails` | Char | Destinatari (comma separated) |
| `cc_emails` | Char | CC (comma separated) |
| `subject` | Char | Oggetto |
| `email_date` | Datetime | Data originale dell'email |
| `snippet` | Text | Prime 200 chars del body text (estratto dall'header fetch se possibile) |
| `state` | Selection | `new`, `keep`, `discard` — default `new` |
| `partner_id` | Many2one → res.partner | Contatto matchato |
| `match_type` | Selection | `exact`, `domain`, `manual`, `none` |
| `body_html` | Html | Body completo — vuoto finché state != keep |
| `body_downloaded` | Boolean | default False |
| `attachment_ids` | One2many → ir.attachment | Allegati scaricati |
| `triage_user_id` | Many2one → res.users | Chi ha fatto la decisione |
| `triage_date` | Datetime | Quando è stata fatta la decisione |

**Constraint SQL:**
```python
_sql_constraints = [
    ('message_id_unique', 'unique(message_id_rfc)', 
     'Email già presente (Message-ID duplicato).'),
]
```

**NOTA IMPORTANTE:** La deduplicazione è su `message_id_rfc` (globale, cross-account), non su account+UID. Se antonio@ e josefina@ sono entrambi in CC su un'email, quell'email appare una sola volta nel triage. Il primo account che la scarica la crea, il secondo la skippa.

**Campi computed:**
```python
@api.depends('sender_email')
def _compute_sender_domain(self):
    for rec in self:
        if rec.sender_email and '@' in rec.sender_email:
            rec.sender_domain = rec.sender_email.split('@')[1].lower().strip()
        else:
            rec.sender_domain = ''
```

---

### File: `models/mail_blacklist.py`

**Modello: `casafolino.mail.blacklist`**

| Campo | Tipo | Note |
|---|---|---|
| `type` | Selection | `domain` / `email` |
| `value` | Char | required, lowercase, es. "linkedin.com" o "noreply@amazon.it" |
| `notes` | Text | Opzionale |

**Constraint + normalizzazione:**
```python
_sql_constraints = [
    ('value_unique', 'unique(type, value)', 'Questo valore è già in blacklist.'),
]

@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if vals.get('value'):
            vals['value'] = vals['value'].lower().strip()
    return super().create(vals_list)
```

**La blacklist è GLOBALE.** Nessun campo account_id. Se blacklisti `linkedin.com`, vale per tutte le caselle.

**Metodo helper per check rapido:**
```python
@api.model
def is_blacklisted(self, email_address):
    """Controlla se un indirizzo o il suo dominio è in blacklist."""
    email_lower = email_address.lower().strip()
    domain = email_lower.split('@')[1] if '@' in email_lower else ''
    
    return bool(self.search([
        '|',
        '&', ('type', '=', 'email'), ('value', '=', email_lower),
        '&', ('type', '=', 'domain'), ('value', '=', domain),
    ], limit=1))
```

---

### File: `models/res_partner.py` (estensione — AGGIUNGERE ai campi esistenti)

Aggiungere questi campi al `res.partner` SENZA toccare i campi Agente 007 già esistenti:

| Campo | Tipo | Note |
|---|---|---|
| `mail_tracked` | Boolean | Default False — se True, le nuove email vanno direttamente in chatter |
| `mail_first_sync_done` | Boolean | Default False — lo storico completo è stato scaricato? |
| `mail_last_sync` | Datetime | Ultimo sync email per questo contatto |
| `mail_message_count` | Integer | Compute: conta mail.message tipo email nel chatter |

```python
def _compute_mail_message_count(self):
    for partner in self:
        partner.mail_message_count = self.env['mail.message'].search_count([
            ('res_id', '=', partner.id),
            ('model', '=', 'res.partner'),
            ('message_type', '=', 'email'),
        ])
```

---

## STEP 2 — IMAP Fetch Engine

### File: `models/mail_fetch.py`

Questo è il cuore del sistema. Metodi da aggiungere a `casafolino.mail.account`.

```python
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import logging
import re

_logger = logging.getLogger(__name__)


class CasafolinoMailAccount(models.Model):
    # ... (campi definiti in Step 1)

    def action_fetch_now(self):
        """Fetch manuale per questo account."""
        self.ensure_one()
        self._fetch_emails()

    def _fetch_emails(self):
        """Fetch principale: scarica header da INBOX e/o Sent."""
        self.ensure_one()
        imap = self._get_imap_connection()
        total_new = 0
        total_skip = 0
        total_blacklist = 0

        try:
            folders_to_fetch = []
            if self.fetch_inbox:
                folders_to_fetch.append(('INBOX', 'inbound'))
            if self.fetch_sent and self.sent_folder:
                folders_to_fetch.append((self.sent_folder, 'outbound'))

            for folder_name, direction in folders_to_fetch:
                new, skip, bl = self._fetch_folder(imap, folder_name, direction)
                total_new += new
                total_skip += skip
                total_blacklist += bl

            self.write({
                'last_fetch_datetime': fields.Datetime.now(),
                'state': 'connected',
                'error_message': False,
            })

            _logger.info(
                f"Mail fetch {self.email_address}: "
                f"{total_new} nuove, {total_skip} duplicate, {total_blacklist} blacklisted"
            )

        except Exception as e:
            self.write({'state': 'error', 'error_message': str(e)})
            _logger.error(f"Mail fetch error {self.email_address}: {e}")
            raise
        finally:
            try:
                imap.logout()
            except:
                pass

    def _fetch_folder(self, imap, folder_name, direction):
        """Fetch di una singola cartella IMAP."""
        Blacklist = self.env['casafolino.mail.blacklist']
        Message = self.env['casafolino.mail.message']

        new_count = 0
        skip_count = 0
        blacklist_count = 0

        # Seleziona la cartella (readonly)
        status, data = imap.select(f'"{folder_name}"', readonly=True)
        if status != 'OK':
            _logger.warning(f"Cannot select folder {folder_name}: {data}")
            return 0, 0, 0

        # Costruisci criterio di ricerca
        # Formato data IMAP: 01-Jan-2025
        if self.last_fetch_datetime:
            since_date = self.last_fetch_datetime.strftime('%d-%b-%Y')
        else:
            since_date = self.sync_start_date.strftime('%d-%b-%Y')

        search_criteria = f'(SINCE {since_date})'
        status, msg_ids = imap.search(None, search_criteria)

        if status != 'OK' or not msg_ids[0]:
            return 0, 0, 0

        uid_list = msg_ids[0].split()
        _logger.info(f"Folder {folder_name}: {len(uid_list)} email trovate dal {since_date}")

        # Processa in batch da 50
        batch_size = 50
        for i in range(0, len(uid_list), batch_size):
            batch = uid_list[i:i + batch_size]

            for uid in batch:
                uid_str = uid.decode()

                # Scarica solo header
                status, header_data = imap.fetch(uid, '(BODY.PEEK[HEADER] BODY.PEEK[TEXT]<0.200>)')
                if status != 'OK':
                    continue

                # Parsa gli header
                raw_header = None
                snippet_raw = b''
                for part in header_data:
                    if isinstance(part, tuple):
                        if b'HEADER' in part[0]:
                            raw_header = part[1]
                        elif b'TEXT' in part[0]:
                            snippet_raw = part[1]

                if not raw_header:
                    continue

                msg = email.message_from_bytes(raw_header)

                # Estrai Message-ID
                message_id = msg.get('Message-ID', '').strip()
                if not message_id:
                    # Genera un fallback unico
                    message_id = f"<{self.email_address}-{uid_str}-{folder_name}@generated>"

                # Deduplicazione: skip se Message-ID già esiste
                existing = Message.search([('message_id_rfc', '=', message_id)], limit=1)
                if existing:
                    skip_count += 1
                    continue

                # Estrai mittente
                sender_name, sender_email = parseaddr(msg.get('From', ''))
                sender_name = self._decode_header_value(sender_name)
                sender_email = sender_email.lower().strip() if sender_email else ''

                # Check blacklist
                if sender_email and Blacklist.is_blacklisted(sender_email):
                    blacklist_count += 1
                    continue

                # Estrai destinatari
                to_raw = msg.get('To', '')
                cc_raw = msg.get('Cc', '')
                recipient_emails = self._extract_emails(to_raw)
                cc_emails = self._extract_emails(cc_raw)

                # Estrai oggetto
                subject = self._decode_header_value(msg.get('Subject', '(nessun oggetto)'))

                # Estrai data
                date_str = msg.get('Date', '')
                try:
                    email_date = parsedate_to_datetime(date_str)
                except:
                    email_date = fields.Datetime.now()

                # Snippet (prime 200 chars del body text)
                snippet = ''
                if snippet_raw:
                    try:
                        snippet = snippet_raw.decode('utf-8', errors='ignore')[:200].strip()
                    except:
                        snippet = ''

                # Determina direction effettiva
                actual_direction = direction
                if direction == 'inbound' and sender_email == self.email_address.lower():
                    actual_direction = 'outbound'

                # Matching con res.partner
                partner_id, match_type = self._match_partner(
                    sender_email if actual_direction == 'inbound' else recipient_emails,
                    actual_direction
                )

                # Crea record staging
                vals = {
                    'account_id': self.id,
                    'message_id_rfc': message_id,
                    'imap_uid': uid_str,
                    'imap_folder': folder_name,
                    'direction': actual_direction,
                    'sender_email': sender_email,
                    'sender_name': sender_name,
                    'recipient_emails': recipient_emails,
                    'cc_emails': cc_emails,
                    'subject': subject,
                    'email_date': email_date,
                    'snippet': snippet,
                    'state': 'new',
                    'partner_id': partner_id,
                    'match_type': match_type,
                }

                # Se il partner è tracked, scarica subito body e metti in keep
                if partner_id:
                    partner = self.env['res.partner'].browse(partner_id)
                    if partner.mail_tracked:
                        vals['state'] = 'keep'
                        # Body verrà scaricato dopo la creazione

                try:
                    new_msg = Message.create(vals)
                    new_count += 1

                    # Se stato keep (partner tracked), scarica body
                    if new_msg.state == 'keep':
                        new_msg._download_body_imap(imap, folder_name, uid_str)
                        if new_msg.partner_id:
                            new_msg._create_partner_mail_message()

                except Exception as e:
                    _logger.warning(f"Error creating mail message: {e}")
                    continue

            # Commit ogni batch
            self.env.cr.commit()
            _logger.info(f"Batch {i//batch_size + 1}: {new_count} nuove fin qui")

        return new_count, skip_count, blacklist_count

    def _decode_header_value(self, value):
        """Decodifica header MIME (=?UTF-8?Q?...?= etc)."""
        if not value:
            return ''
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or 'utf-8', errors='ignore'))
            else:
                result.append(part)
        return ' '.join(result).strip()

    def _extract_emails(self, header_value):
        """Estrae lista email da header To/Cc."""
        if not header_value:
            return ''
        # Parsa tutti gli indirizzi
        addresses = []
        # Split su virgola per gestire più indirizzi
        for part in header_value.split(','):
            name, addr = parseaddr(part.strip())
            if addr:
                addresses.append(addr.lower().strip())
        return ', '.join(addresses)

    def _match_partner(self, email_or_emails, direction):
        """Cerca partner corrispondente. Ritorna (partner_id, match_type) o (False, 'none')."""
        Partner = self.env['res.partner']

        # Determina l'email da cercare
        if direction == 'inbound':
            email_to_match = email_or_emails  # è una stringa singola (sender_email)
        else:
            # Per outbound, prendi il primo destinatario
            if isinstance(email_or_emails, str) and email_or_emails:
                email_to_match = email_or_emails.split(',')[0].strip()
            else:
                return False, 'none'

        if not email_to_match:
            return False, 'none'

        # 1. Match esatto per email
        partner = Partner.search([('email', '=ilike', email_to_match)], limit=1)
        if partner:
            return partner.id, 'exact'

        # 2. Match per dominio (company website)
        domain = email_to_match.split('@')[1] if '@' in email_to_match else ''
        if domain:
            partner = Partner.search([
                ('is_company', '=', True),
                ('website', 'ilike', domain),
            ], limit=1)
            if partner:
                return partner.id, 'domain'

        return False, 'none'
```

---

## STEP 3 — Download Body + Allegati (action_keep)

### Metodi in `casafolino.mail.message`:

```python
def action_keep(self):
    """Marca come keep, scarica body, collega a partner."""
    for record in self:
        record.write({
            'state': 'keep',
            'triage_user_id': self.env.user.id,
            'triage_date': fields.Datetime.now(),
        })

        # Scarica body se non ancora fatto
        if not record.body_downloaded:
            try:
                imap = record.account_id._get_imap_connection()
                record._download_body_imap(imap, record.imap_folder, record.imap_uid)
                imap.logout()
            except Exception as e:
                _logger.error(f"Error downloading body for {record.message_id_rfc}: {e}")

        # Se ha un partner, crea nel chatter
        if record.partner_id:
            record._create_partner_mail_message()

def action_discard(self):
    """Marca come discard."""
    self.write({
        'state': 'discard',
        'triage_user_id': self.env.user.id,
        'triage_date': fields.Datetime.now(),
    })

def _download_body_imap(self, imap, folder_name, uid):
    """Scarica body completo e allegati via IMAP."""
    self.ensure_one()

    status, _ = imap.select(f'"{folder_name}"', readonly=True)
    if status != 'OK':
        return

    # Scarica messaggio completo
    status, msg_data = imap.fetch(uid.encode() if isinstance(uid, str) else uid, '(RFC822)')
    if status != 'OK':
        return

    raw_email = None
    for part in msg_data:
        if isinstance(part, tuple):
            raw_email = part[1]
            break

    if not raw_email:
        return

    msg = email.message_from_bytes(raw_email)

    # Estrai body
    body_html = ''
    body_text = ''
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))

            # Allegati
            if 'attachment' in content_disposition or part.get_filename():
                filename = part.get_filename()
                if filename:
                    filename = self.env['casafolino.mail.account']._decode_header_value(filename)
                    file_data = part.get_payload(decode=True)
                    if file_data:
                        attachments.append({
                            'name': filename,
                            'datas': base64.b64encode(file_data),
                            'mimetype': content_type,
                        })
            # Body
            elif content_type == 'text/html':
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body_html = payload.decode(charset, errors='ignore')
            elif content_type == 'text/plain' and not body_html:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body_text = payload.decode(charset, errors='ignore')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            if msg.get_content_type() == 'text/html':
                body_html = payload.decode(charset, errors='ignore')
            else:
                body_text = payload.decode(charset, errors='ignore')

    # Salva
    self.write({
        'body_html': body_html or f'<pre>{body_text}</pre>',
        'body_downloaded': True,
    })

    # Crea allegati
    for att in attachments:
        self.env['ir.attachment'].create({
            'name': att['name'],
            'datas': att['datas'],
            'mimetype': att['mimetype'],
            'res_model': 'casafolino.mail.message',
            'res_id': self.id,
        })
```

---

## STEP 4 — Integrazione Chatter Partner

```python
def _create_partner_mail_message(self):
    """Crea mail.message nativo nel chatter del partner."""
    self.ensure_one()
    if not self.partner_id or not self.body_html:
        return

    # Evita duplicati
    existing = self.env['mail.message'].search([
        ('message_id', '=', self.message_id_rfc),
        ('res_id', '=', self.partner_id.id),
        ('model', '=', 'res.partner'),
    ], limit=1)
    if existing:
        return

    # Crea mail.message nel chatter
    msg_vals = {
        'model': 'res.partner',
        'res_id': self.partner_id.id,
        'message_type': 'email',
        'subtype_id': self.env.ref('mail.mt_note').id,
        'body': self.body_html,
        'subject': self.subject,
        'email_from': self.sender_email,
        'date': self.email_date,  # DATA ORIGINALE — cruciale per ordinamento corretto
        'message_id': self.message_id_rfc,
    }
    self.env['mail.message'].sudo().create(msg_vals)
```

**PUNTO CRITICO:** Il campo `date` DEVE essere la data originale dell'email, non `fields.Datetime.now()`. Altrimenti le email del 2023 appaiono come messaggi di oggi nel chatter.

---

## STEP 5 — Triage UI (Viste)

### File: `views/mail_message_views.xml`

```xml
<!-- ACTION — deve venire PRIMA delle viste -->
<record id="action_mail_message_triage" model="ir.actions.act_window">
    <field name="name">Email Triage</field>
    <field name="res_model">casafolino.mail.message</field>
    <field name="view_mode">list,form</field>
    <field name="search_view_id" ref="casafolino_mail_message_search"/>
    <field name="context">{'search_default_state_new': 1}</field>
</record>

<record id="action_mail_account" model="ir.actions.act_window">
    <field name="name">Account Email</field>
    <field name="res_model">casafolino.mail.account</field>
    <field name="view_mode">list,form</field>
</record>

<record id="action_mail_blacklist" model="ir.actions.act_window">
    <field name="name">Blacklist</field>
    <field name="res_model">casafolino.mail.blacklist</field>
    <field name="view_mode">list,form</field>
</record>

<!-- VISTA LISTA TRIAGE -->
<record id="casafolino_mail_message_list" model="ir.ui.view">
    <field name="name">casafolino.mail.message.list</field>
    <field name="model">casafolino.mail.message</field>
    <field name="arch" type="xml">
        <list string="Email Triage" decoration-muted="state=='discard'" decoration-success="state=='keep'" decoration-info="state=='new'" multi_edit="1">
            <field name="email_date" string="Data"/>
            <field name="direction" string="Dir"/>
            <field name="sender_name" string="Da"/>
            <field name="sender_email" string="Email"/>
            <field name="sender_domain" string="Dominio"/>
            <field name="subject" string="Oggetto"/>
            <field name="snippet" string="Preview" optional="show"/>
            <field name="partner_id" string="Contatto"/>
            <field name="match_type" string="Match" optional="hide"/>
            <field name="account_id" string="Casella"/>
            <field name="state" string="Stato" widget="badge"
                   decoration-info="state=='new'"
                   decoration-success="state=='keep'"
                   decoration-danger="state=='discard'"/>
        </list>
    </field>
</record>

<!-- VISTA SEARCH -->
<record id="casafolino_mail_message_search" model="ir.ui.view">
    <field name="name">casafolino.mail.message.search</field>
    <field name="model">casafolino.mail.message</field>
    <field name="arch" type="xml">
        <search string="Cerca Email">
            <field name="subject"/>
            <field name="sender_email"/>
            <field name="sender_name"/>
            <field name="sender_domain"/>
            <field name="partner_id"/>
            <filter name="state_new" string="Da valutare" domain="[('state','=','new')]"/>
            <filter name="state_keep" string="Tenute" domain="[('state','=','keep')]"/>
            <filter name="state_discard" string="Scartate" domain="[('state','=','discard')]"/>
            <separator/>
            <filter name="no_partner" string="Senza contatto" domain="[('partner_id','=',False)]"/>
            <filter name="inbound" string="Ricevute" domain="[('direction','=','inbound')]"/>
            <filter name="outbound" string="Inviate" domain="[('direction','=','outbound')]"/>
            <separator/>
            <group expand="0" string="Raggruppa per">
                <filter name="group_domain" string="Dominio" context="{'group_by':'sender_domain'}"/>
                <filter name="group_partner" string="Contatto" context="{'group_by':'partner_id'}"/>
                <filter name="group_account" string="Casella" context="{'group_by':'account_id'}"/>
                <filter name="group_state" string="Stato" context="{'group_by':'state'}"/>
                <filter name="group_date" string="Data" context="{'group_by':'email_date:day'}"/>
            </group>
        </search>
    </field>
</record>

<!-- VISTA FORM -->
<record id="casafolino_mail_message_form" model="ir.ui.view">
    <field name="name">casafolino.mail.message.form</field>
    <field name="model">casafolino.mail.message</field>
    <field name="arch" type="xml">
        <form string="Email">
            <div class="o_row mb-3">
                <button name="action_keep" string="✅ Tieni" type="object" class="btn btn-success" invisible="state != 'new'"/>
                <button name="action_discard" string="❌ Scarta" type="object" class="btn btn-danger" invisible="state != 'new'"/>
                <button name="action_blacklist_domain" string="🚫 Blacklist Dominio" type="object" class="btn btn-warning"/>
                <button name="action_create_partner" string="👤 Crea Contatto" type="object" class="btn btn-secondary" invisible="partner_id != False"/>
                <button name="action_launch_007" string="🔍 Agente 007" type="object" class="btn btn-info" invisible="partner_id == False"/>
            </div>
            <group>
                <group string="Email">
                    <field name="email_date"/>
                    <field name="direction"/>
                    <field name="sender_name"/>
                    <field name="sender_email"/>
                    <field name="recipient_emails"/>
                    <field name="cc_emails"/>
                    <field name="subject"/>
                    <field name="snippet" invisible="body_downloaded"/>
                </group>
                <group string="CRM">
                    <field name="partner_id"/>
                    <field name="match_type"/>
                    <field name="account_id"/>
                    <field name="state" widget="badge"/>
                    <field name="triage_user_id"/>
                    <field name="triage_date"/>
                </group>
            </group>
            <notebook>
                <page string="Contenuto" name="content" invisible="not body_downloaded">
                    <field name="body_html" widget="html" readonly="1"/>
                </page>
                <page string="Allegati" name="attachments" invisible="not body_downloaded">
                    <field name="attachment_ids"/>
                </page>
                <page string="Tecnico" name="technical">
                    <group>
                        <field name="message_id_rfc"/>
                        <field name="imap_uid"/>
                        <field name="imap_folder"/>
                        <field name="sender_domain"/>
                        <field name="body_downloaded"/>
                    </group>
                </page>
            </notebook>
        </form>
    </field>
</record>
```

---

## STEP 6 — Blacklist + Azioni Bulk

### Metodi in `casafolino.mail.message`:

```python
def action_blacklist_domain(self):
    """Aggiunge il dominio alla blacklist e scarta tutte le email da quel dominio."""
    Blacklist = self.env['casafolino.mail.blacklist']
    domains_done = set()

    for record in self:
        domain = record.sender_domain
        if domain and domain not in domains_done:
            existing = Blacklist.search([('type', '=', 'domain'), ('value', '=', domain)], limit=1)
            if not existing:
                Blacklist.create({'type': 'domain', 'value': domain})
            domains_done.add(domain)

    # Scarta TUTTE le email new da questi domini
    if domains_done:
        all_from_domains = self.search([
            ('sender_domain', 'in', list(domains_done)),
            ('state', '=', 'new'),
        ])
        all_from_domains.write({
            'state': 'discard',
            'triage_user_id': self.env.user.id,
            'triage_date': fields.Datetime.now(),
        })

def action_create_partner(self):
    """Crea un nuovo res.partner dall'email."""
    self.ensure_one()
    email_addr = self.sender_email if self.direction == 'inbound' else (self.recipient_emails.split(',')[0].strip() if self.recipient_emails else '')
    name = self.sender_name if self.direction == 'inbound' else email_addr

    partner = self.env['res.partner'].create({
        'name': name or email_addr,
        'email': email_addr,
    })
    self.write({'partner_id': partner.id, 'match_type': 'manual'})

    return {
        'type': 'ir.actions.act_window',
        'res_model': 'res.partner',
        'res_id': partner.id,
        'view_mode': 'form',
        'target': 'current',
    }

def action_launch_007(self):
    """Lancia Agente 007 sul partner collegato."""
    self.ensure_one()
    if self.partner_id:
        return self.partner_id.action_enrich_007()  # Riusa metodo esistente di Agente 007
```

### File: `data/server_actions.xml`

```xml
<odoo>
    <record id="action_bulk_keep" model="ir.actions.server">
        <field name="name">✅ Tieni selezionati</field>
        <field name="model_id" ref="model_casafolino_mail_message"/>
        <field name="binding_model_id" ref="model_casafolino_mail_message"/>
        <field name="binding_view_types">list</field>
        <field name="state">code</field>
        <field name="code">records.action_keep()</field>
    </record>

    <record id="action_bulk_discard" model="ir.actions.server">
        <field name="name">❌ Scarta selezionati</field>
        <field name="model_id" ref="model_casafolino_mail_message"/>
        <field name="binding_model_id" ref="model_casafolino_mail_message"/>
        <field name="binding_view_types">list</field>
        <field name="state">code</field>
        <field name="code">records.action_discard()</field>
    </record>

    <record id="action_bulk_blacklist" model="ir.actions.server">
        <field name="name">🚫 Blacklist dominio selezionati</field>
        <field name="model_id" ref="model_casafolino_mail_message"/>
        <field name="binding_model_id" ref="model_casafolino_mail_message"/>
        <field name="binding_view_types">list</field>
        <field name="state">code</field>
        <field name="code">records.action_blacklist_domain()</field>
    </record>
</odoo>
```

---

## STEP 7 — Fetch Storico per Contatto

### Aggiungere in `res.partner`:

```python
def action_sync_full_email_history(self):
    """Scarica tutto lo storico email per questo contatto da tutte le caselle."""
    self.ensure_one()
    if not self.email:
        raise UserError("Il contatto non ha un indirizzo email.")

    accounts = self.env['casafolino.mail.account'].search([('state', '=', 'connected')])
    email_lower = self.email.lower().strip()
    Message = self.env['casafolino.mail.message']

    for account in accounts:
        imap = account._get_imap_connection()
        try:
            folders = []
            if account.fetch_inbox:
                folders.append(('INBOX', 'inbound'))
            if account.fetch_sent and account.sent_folder:
                folders.append((account.sent_folder, 'outbound'))

            for folder_name, direction in folders:
                status, _ = imap.select(f'"{folder_name}"', readonly=True)
                if status != 'OK':
                    continue

                # Cerca TUTTE le email da/a questo indirizzo, SENZA limite di data
                # IMAP OR: (OR FROM "email" TO "email")
                search_criteria = f'(OR FROM "{email_lower}" TO "{email_lower}")'
                status, msg_ids = imap.search(None, search_criteria)

                if status != 'OK' or not msg_ids[0]:
                    continue

                uid_list = msg_ids[0].split()
                _logger.info(f"Storico {email_lower} in {folder_name}: {len(uid_list)} email")

                for uid in uid_list:
                    uid_str = uid.decode()

                    # Scarica completo (header + body)
                    status, msg_data = imap.fetch(uid, '(RFC822)')
                    if status != 'OK':
                        continue

                    raw_email = None
                    for part in msg_data:
                        if isinstance(part, tuple):
                            raw_email = part[1]
                            break
                    if not raw_email:
                        continue

                    msg = email.message_from_bytes(raw_email)
                    message_id = msg.get('Message-ID', '').strip()

                    if not message_id:
                        message_id = f"<{account.email_address}-{uid_str}-{folder_name}@generated>"

                    # Skip se già esiste
                    if Message.search([('message_id_rfc', '=', message_id)], limit=1):
                        continue

                    # Parsa e crea (logica simile al fetch engine)
                    sender_name, sender_email_addr = parseaddr(msg.get('From', ''))
                    sender_name = account._decode_header_value(sender_name)
                    sender_email_addr = sender_email_addr.lower().strip()

                    subject = account._decode_header_value(msg.get('Subject', ''))
                    try:
                        email_date = parsedate_to_datetime(msg.get('Date', ''))
                    except:
                        email_date = fields.Datetime.now()

                    actual_direction = 'outbound' if sender_email_addr == account.email_address.lower() else 'inbound'

                    # Crea record staging con state=keep e body
                    new_msg = Message.create({
                        'account_id': account.id,
                        'message_id_rfc': message_id,
                        'imap_uid': uid_str,
                        'imap_folder': folder_name,
                        'direction': actual_direction,
                        'sender_email': sender_email_addr,
                        'sender_name': sender_name,
                        'recipient_emails': account._extract_emails(msg.get('To', '')),
                        'cc_emails': account._extract_emails(msg.get('Cc', '')),
                        'subject': subject,
                        'email_date': email_date,
                        'state': 'keep',
                        'partner_id': self.id,
                        'match_type': 'exact',
                        'triage_user_id': self.env.user.id,
                        'triage_date': fields.Datetime.now(),
                    })

                    # Scarica body direttamente dal raw già disponibile
                    new_msg._parse_and_save_body(msg)
                    new_msg._create_partner_mail_message()

                    self.env.cr.commit()  # Commit ogni email

        finally:
            try:
                imap.logout()
            except:
                pass

    self.write({
        'mail_tracked': True,
        'mail_first_sync_done': True,
        'mail_last_sync': fields.Datetime.now(),
    })
```

**Metodo helper `_parse_and_save_body` in `casafolino.mail.message`:**
```python
def _parse_and_save_body(self, msg_obj):
    """Parsa body e allegati da un oggetto email.message già scaricato."""
    self.ensure_one()
    body_html = ''
    body_text = ''
    attachments = []

    if msg_obj.is_multipart():
        for part in msg_obj.walk():
            content_type = part.get_content_type()
            disposition = str(part.get('Content-Disposition', ''))

            if 'attachment' in disposition or part.get_filename():
                filename = part.get_filename()
                if filename:
                    filename = self.env['casafolino.mail.account']._decode_header_value(filename)
                    file_data = part.get_payload(decode=True)
                    if file_data:
                        attachments.append({
                            'name': filename,
                            'datas': base64.b64encode(file_data),
                            'mimetype': content_type,
                        })
            elif content_type == 'text/html':
                payload = part.get_payload(decode=True)
                if payload:
                    body_html = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
            elif content_type == 'text/plain' and not body_html:
                payload = part.get_payload(decode=True)
                if payload:
                    body_text = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
    else:
        payload = msg_obj.get_payload(decode=True)
        if payload:
            charset = msg_obj.get_content_charset() or 'utf-8'
            if msg_obj.get_content_type() == 'text/html':
                body_html = payload.decode(charset, errors='ignore')
            else:
                body_text = payload.decode(charset, errors='ignore')

    self.write({
        'body_html': body_html or f'<pre>{body_text}</pre>',
        'body_downloaded': True,
    })

    for att in attachments:
        self.env['ir.attachment'].create({
            'name': att['name'],
            'datas': att['datas'],
            'mimetype': att['mimetype'],
            'res_model': 'casafolino.mail.message',
            'res_id': self.id,
        })
```

### Bottone nella vista partner:

```xml
<record id="view_partner_form_mail_hub" model="ir.ui.view">
    <field name="name">res.partner.form.mail.hub</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="priority">99</field>
    <field name="arch" type="xml">
        <xpath expr="//div[@name='button_box']" position="inside">
            <button name="action_sync_full_email_history" string="📧 Sync Email"
                    type="object" class="oe_stat_button" icon="fa-envelope">
                <field name="mail_message_count" string="Email" widget="statinfo"/>
            </button>
        </xpath>
    </field>
</record>
```

---

## STEP 8 — Cron Sync Continuo

### File: `data/cron.xml`

```xml
<odoo>
    <record id="cron_fetch_new_emails" model="ir.cron">
        <field name="name">CasaFolino: Fetch nuove email</field>
        <field name="model_id" eval="ref('casafolino_mail.model_casafolino_mail_account')"/>
        <field name="state">code</field>
        <field name="code">model._cron_fetch_all_accounts()</field>
        <field name="interval_number">2</field>
        <field name="interval_type">hours</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>

    <record id="cron_cleanup_discarded" model="ir.cron">
        <field name="name">CasaFolino: Cleanup email scartate</field>
        <field name="model_id" eval="ref('casafolino_mail.model_casafolino_mail_message')"/>
        <field name="state">code</field>
        <field name="code">model._cron_cleanup_discarded()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">days</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>
</odoo>
```

**NOTA CRITICA SUI CRON Odoo 18:** Se `model_id eval="ref()"` causa ParseError, sostituire con file cron vuoto `<odoo></odoo>` e creare i cron manualmente via Python:

```python
# In __init__.py del modulo, aggiungere post_init_hook
def _post_init_hook(env):
    """Crea cron se non esistono."""
    Cron = env['ir.cron'].sudo()
    
    if not Cron.search([('name', '=', 'CasaFolino: Fetch nuove email')]):
        Cron.create({
            'name': 'CasaFolino: Fetch nuove email',
            'model_id': env.ref('casafolino_mail.model_casafolino_mail_account').id,
            'state': 'code',
            'code': 'model._cron_fetch_all_accounts()',
            'interval_number': 2,
            'interval_type': 'hours',
            'numbercall': -1,
            'active': True,
        })
    
    if not Cron.search([('name', '=', 'CasaFolino: Cleanup email scartate')]):
        Cron.create({
            'name': 'CasaFolino: Cleanup email scartate',
            'model_id': env.ref('casafolino_mail.model_casafolino_mail_message').id,
            'state': 'code',
            'code': 'model._cron_cleanup_discarded()',
            'interval_number': 1,
            'interval_type': 'days',
            'numbercall': -1,
            'active': True,
        })
```

### Metodi cron:

```python
# In casafolino.mail.account:
@api.model
def _cron_fetch_all_accounts(self):
    """Fetch incrementale per tutti gli account connessi."""
    accounts = self.search([('state', '=', 'connected'), ('active', '=', True)])
    for account in accounts:
        try:
            account._fetch_emails()
        except Exception as e:
            account.write({'state': 'error', 'error_message': str(e)})
            _logger.error(f"Cron fetch error {account.email_address}: {e}")

# In casafolino.mail.message:
@api.model
def _cron_cleanup_discarded(self):
    """Elimina email scartate più vecchie di 30 giorni."""
    from datetime import timedelta
    cutoff = fields.Datetime.now() - timedelta(days=30)
    old = self.search([('state', '=', 'discard'), ('triage_date', '<', cutoff)])
    count = len(old)
    old.unlink()
    _logger.info(f"Mail cleanup: {count} email scartate eliminate.")
```

---

## STEP 9 — Access Rules e Security

### File: `security/ir_rules.xml`

```xml
<odoo>
    <record id="rule_mail_message_user" model="ir.rule">
        <field name="name">CasaFolino Mail: solo proprie caselle</field>
        <field name="model_id" ref="model_casafolino_mail_message"/>
        <field name="domain_force">[('account_id.responsible_user_id', '=', user.id)]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <record id="rule_mail_message_admin" model="ir.rule">
        <field name="name">CasaFolino Mail: admin vede tutto</field>
        <field name="model_id" ref="model_casafolino_mail_message"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[(4, ref('base.group_system'))]"/>
    </record>
</odoo>
```

### File: `security/ir.model.access.csv`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_mail_account_user,casafolino.mail.account.user,model_casafolino_mail_account,base.group_user,1,0,0,0
access_mail_account_admin,casafolino.mail.account.admin,model_casafolino_mail_account,base.group_system,1,1,1,1
access_mail_message_user,casafolino.mail.message.user,model_casafolino_mail_message,base.group_user,1,1,1,0
access_mail_message_admin,casafolino.mail.message.admin,model_casafolino_mail_message,base.group_system,1,1,1,1
access_mail_blacklist_user,casafolino.mail.blacklist.user,model_casafolino_mail_blacklist,base.group_user,1,1,1,0
access_mail_blacklist_admin,casafolino.mail.blacklist.admin,model_casafolino_mail_blacklist,base.group_system,1,1,1,1
```

---

## STEP 10 — Menu

### File: `views/menus.xml`

```xml
<odoo>
    <!-- Menu items sotto il menu root casafolino_mail già esistente -->
    <!-- NOTA: sostituire MENU_ROOT_ESISTENTE con l'xml_id reale del root menu di casafolino_mail -->
    <menuitem id="menu_mail_triage" name="Email Triage" parent="MENU_ROOT_ESISTENTE" action="action_mail_message_triage" sequence="5"/>
    <menuitem id="menu_mail_accounts" name="Account Email" parent="MENU_ROOT_ESISTENTE" action="action_mail_account" sequence="10"/>
    <menuitem id="menu_mail_blacklist" name="Blacklist" parent="MENU_ROOT_ESISTENTE" action="action_mail_blacklist" sequence="15"/>
</odoo>
```

**NOTA:** Claude Code deve verificare nel codice esistente qual è l'xml_id del root menu di casafolino_mail e sostituire `MENU_ROOT_ESISTENTE`.

---

## STRUTTURA FILE FINALE DEL MODULO

```
casafolino_mail/
├── __init__.py                    ← aggiungere import nuovi file + post_init_hook se serve
├── __manifest__.py                ← aggiungere nuovi file data/views/security
├── models/
│   ├── __init__.py                ← aggiungere import nuovi modelli
│   ├── mail_account.py            ← NUOVO (Step 1+2)
│   ├── mail_message_staging.py    ← NUOVO (Step 1+3+4)
│   ├── mail_blacklist.py          ← NUOVO (Step 1)
│   ├── res_partner.py             ← ESTESO (Step 1+7) — aggiungere campi, NON sovrascrivere 007
│   ├── [file esistenti 007]       ← NON TOCCARE
├── views/
│   ├── mail_message_views.xml     ← NUOVO (Step 5)
│   ├── mail_account_views.xml     ← NUOVO (in Step 1, vista form account)
│   ├── mail_blacklist_views.xml   ← NUOVO (vista semplice lista+form)
│   ├── res_partner_views.xml      ← ESTESO (Step 7) — bottone Sync Email
│   ├── menus.xml                  ← NUOVO (Step 10)
│   ├── [file esistenti 007]       ← NON TOCCARE
├── security/
│   ├── ir.model.access.csv        ← ESTESO (Step 9)
│   ├── ir_rules.xml               ← NUOVO (Step 9)
├── data/
│   ├── cron.xml                   ← NUOVO (Step 8)
│   ├── server_actions.xml         ← NUOVO (Step 6)
├── static/
│   └── description/
│       └── icon.png               ← GIÀ ESISTENTE
```

---

## ORDINE DI SVILUPPO (rigoroso — un step alla volta)

| Step | Cosa | Test prima di proseguire |
|---|---|---|
| 1 | Modelli dati (account, message, blacklist, ext partner) | `--update` senza errori, tabelle nel DB |
| 2 | IMAP fetch engine + bottone "Fetch Now" | Fetch da una casella, email in staging |
| 3 | Download body + allegati (action_keep) | Keep → body visibile, allegati scaricati |
| 4 | Integrazione chatter partner | Email nel chatter con data corretta |
| 5 | Vista triage lista + form + search | UI funzionante, filtri ok |
| 6 | Blacklist + azioni bulk + server actions | Blacklist dominio → tutte scartate |
| 7 | Fetch storico per contatto | Bottone su partner → storico completo |
| 8 | Cron sync continuo | Cron attivo, fetch automatico |
| 9 | Access rules + permessi | Josefina vede solo le sue |
| 10 | Menu | Navigazione completa |

**REGOLA ASSOLUTA:** Testare OGNI step su `folinofood_stage` prima di proseguire. Mai 2 step insieme.

---

## PREREQUISITO: Password App Gmail

Per ogni casella email da collegare, servono le password app Gmail:

1. Vai su https://myaccount.google.com/security
2. Verifica che la "Verifica in due passaggi" sia attiva
3. Cerca "Password per le app" (o vai su https://myaccount.google.com/apppasswords)
4. Crea una nuova password app per "Posta" / "Altro" → nomina "Odoo Mail Hub"
5. Google genera una password di 16 caratteri (tipo `abcd efgh ijkl mnop`) — copiala
6. Inseriscila nel campo `imap_password` dell'account Odoo (senza spazi)

Ripetere per ogni casella: antonio@, josefina@, info@, ecc.

---

## NOTE FINALI

- **Performance fetch iniziale:** ~46.000 email per casella con IMAP richiederà 30-60 minuti. Il fetch scarica solo header (veloce). Il download body avviene solo per le email marcate "keep" (on demand). Non è un problema di performance, solo di tempo.
- **Connessione IMAP:** Gmail limita a 15 connessioni simultanee per account. Il codice usa una connessione alla volta, quindi nessun problema. Gestire sempre `try/finally` con `imap.logout()`.
- **Commit intermedi:** ogni 50 email processate, fare `self.env.cr.commit()` per non perdere tutto in caso di errore.
- **Logging:** ogni operazione logga con `_logger` — INFO per operazioni normali, WARNING per skip/blacklist, ERROR per errori.
- **Import necessari in testa ai file Python:** `import imaplib`, `import email`, `from email.header import decode_header`, `from email.utils import parseaddr, parsedate_to_datetime`, `import base64`, `import logging`.
