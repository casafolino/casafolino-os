# Diagnostica Sender Policy — Inbox Triage Bug

**Data:** 2026-04-20
**Segnalazione:** Giorgia Negro (contactlbb.com) appare ancora in Inbox Triage dopo "scarto". Martina Sinopoli (casafolino.com) email interne appaiono in triage.

---

## STEP 1 — Schema sender_policy

```
 column_name     | data_type
-----------------+-----------------------------
 id              | integer
 priority        | integer
 default_owner_id| integer
 name            | character varying
 pattern_type    | character varying (email_exact|domain|regex_subject)
 pattern_value   | character varying
 action          | character varying (auto_keep|auto_discard|escalate|review)
 active          | boolean
 auto_create_partner | boolean
 match_ai_category   | character varying
 notes           | text
```

## STEP 2 — Conta policy

| total | active |
|-------|--------|
| 4     | 4      |

**Solo 4 policy totali.** Nessuna creata da triage per Giorgia o casafolino.com.

## STEP 3 — Policy specifiche

```
0 rows — NESSUNA policy per giorgia.negro, contactlbb.com, martina.sinopoli, casafolino.com
```

**Le 4 policy esistenti:**

| id | name | pattern_type | pattern_value | action | priority |
|---|---|---|---|---|---|
| 1 | Newsletter domain → discard | domain | *mailup* | auto_discard | — |
| 2 | REWE group → keep auto | domain | *rewe-group* | auto_keep | — |
| 3 | Default: review | domain | * | review | — |
| 4 | Newsletter AI-detected → discard | domain | * | auto_discard | — |

**Policy 3 (wildcard `*` → review)** cattura TUTTO. Policy 4 ha `match_ai_category='newsletter'` presumibilmente.

## STEP 4 — Messaggi Giorgia Negro ultimi 30gg

| id | state | policy_applied_id | email_date |
|---|---|---|---|
| 14970 | **review** | 3 | 2026-04-20 14:07 |
| 14932 | **review** | 3 | 2026-04-20 13:29 |
| 14930 | **review** | 3 | 2026-04-20 13:10 |
| 14652 | discard | 3 | 2026-04-17 17:48 |
| 14645 | **review** | 3 | 2026-04-17 15:53 |

**428 in discard, 8 in review.** I messaggi vecchi sono stati scartati manualmente (stato cambiato a mano) ma le NUOVE email entrano come `review` perché nessuna policy `auto_discard` esiste per questo sender.

## STEP 5 — Messaggi Martina Sinopoli ultimi 7gg

| id | state | direction | policy_applied_id | email_date |
|---|---|---|---|---|
| 14933 | **review** | inbound | 3 | 2026-04-20 13:41 |
| 14931 | **review** | inbound | 3 | 2026-04-20 13:13 |
| 14928 | **review** | inbound | 3 | 2026-04-20 12:46 |
| 14923 | **review** | inbound | 3 | 2026-04-20 10:04 |
| 14919 | **review** | inbound | 3 | 2026-04-20 07:51 |

**Email interne casafolino.com appaiono tutte come `review`** — nessuna policy per il dominio interno.

## STEP 6 — Policy application coverage

| no_policy | with_policy | total |
|---|---|---|
| 14660 | 221 | 14881 |

**Solo 1.5% dei messaggi ha policy applicata.** Il 98.5% arriva senza match significativo (la policy 3 wildcard matcha tutto come "review" ma non viene settata come policy_applied_id su tutti i messaggi — solo quelli processati dal cron AI Classify o dall'IMAP sync recente).

## STEP 7 — Action "Inbox Triage"

```sql
domain: [('state', 'in', ['new', 'review'])]
```

**Mostra TUTTI i messaggi in state `new` o `review`** — senza filtrare per direction (mostra anche inbound interni), senza escludere sender con decisione precedente.

## STEP 8 — Nessun cron retroattivo

```
0 rows — no cron for policy/retroactive/apply
```

## STEP 9 — Codice `action_triage_ignore_sender`

```python
# triage_wizard.py:170
def action_triage_ignore_sender(self):
    Policy.create({
        'pattern_value': '*%s*' % email,  # es: *giorgia.negro@contactlbb.com*
        'action': 'auto_discard',
        'priority': 15,
    })
    self._create_decision('ignored_sender', sender_policy_id=policy.id)
    return self._open_next_orphan()
```

**Crea policy MA:**
1. NON applica retroattivamente ai messaggi esistenti
2. NON cambia `state` dei messaggi già in DB
3. Funziona solo per il wizard "Triage Orfano" (orphan.partner), NON per l'Inbox Triage (list di messaggi)

**Flow `_apply_sender_policy`** — chiamato SOLO su:
- IMAP sync nuovi messaggi (`casafolino_mail_account.py:368`)
- Cron AI Classify su messaggi `state='new'` (`casafolino_mail_message_staging.py:1174`)

## STEP 10 — Conferma: nessun cron retroattivo

0 rows. Non esiste meccanismo per ri-applicare policy ai messaggi già processati.

## STEP 11 — Controller Mail V3

Il controller Mail V3 non ha endpoint "scarta" per sender. L'utente nella UI tradizionale (Inbox Triage list) probabilmente fa **cambio stato manuale** via button o write diretto, che NON crea sender_policy.

---

## CONCLUSIONE

### Diagnosi: **COMBINAZIONE di A + C**

**Bug principale (A):** Quando Antonio "scarta" messaggi dall'Inbox Triage (list view), usa l'azione bulk che cambia `state='discard'` sul singolo messaggio, ma **NON crea sender_policy**. L'azione "Ignora mittente" dal Triage Orfano creerebbe la policy, ma è un wizard diverso che Antonio non ha usato per Giorgia (evidenza: 0 policy per giorgia.negro).

**Bug secondario (C):** Anche se creasse la policy dal Triage Orfano, il sistema NON applica retroattivamente. I messaggi già in `state='review'` restano visibili. La policy agisce solo su nuove email in arrivo (IMAP sync) o su messaggi ancora in `state='new'` (cron AI classify).

**Bug Martina (manca design):** Nessuna policy esclude email interne @casafolino.com. Servirebbero due cose:
1. Policy `*@casafolino.com` → `auto_discard` (o meglio `auto_keep` per thread interni)
2. Oppure filtro direction nel domain della view Inbox Triage

### Evidenza

| Fatto | Conseguenza |
|---|---|
| 0 policy per giorgia/contactlbb/casafolino | Policy non fu mai creata |
| 428 Giorgia in `discard` | Stato cambiato a mano, non via policy |
| 8 Giorgia in `review` (recenti) | Nuove email entrano come review |
| Martina tutta in `review` | Nessuna esclusione interni |
| Only 221/14881 con policy_applied_id | Sistema policy sotto-utilizzato |
| No cron retroattivo | Policy nuove non toccano storico |

---

## FIX RACCOMANDATO

### Fix minimale (2 commit, <1h)

**Commit 1:** `fix(mail-v3): inbox triage exclude internal + add retroactive apply`

```python
# In triage_wizard.py — dopo create policy, aggiungere:
# Retroactive: mark existing messages from this sender as auto_discard
msgs = self.env['casafolino.mail.message'].search([
    ('sender_email', '=ilike', email),
    ('state', 'in', ['new', 'review']),
])
if msgs:
    msgs.write({'state': 'auto_discard', 'policy_applied_id': policy.id})
```

**Commit 2:** `fix(mail-v3): add casafolino.com internal domain policy + seed`

```python
# In migration or data XML:
# Policy: *@casafolino.com → auto_keep (priority 20)
# This prevents internal emails from appearing in triage
```

**Anche:** aggiornare domain della view Inbox Triage:
```xml
<field name="domain">[('state', 'in', ['new', 'review']), ('direction', '=', 'inbound')]</field>
```
Questo filtra outbound (che non serve triagare).

### Fix completo (F6.5 dedicato)

1. Retroactive apply cron periodico (ogni 1h, scansiona messaggi `state='review'` e ri-applica policy)
2. Bottone "Ignora sender" direttamente nella list view Inbox Triage (non solo Triage Orfano)
3. Bottone "Ignora dominio" nella list view
4. Dashboard policy con contatore messaggi affetti
5. "Inbox Triage" filtro default esclude outbound + interni

### Risk level

**MEDIO** — Non causa data loss. Impatto: Antonio vede rumore nell'Inbox Triage (email che aveva deciso di ignorare riappaiono, email interne del team occupano spazio mentale). Non bloccante per operations ma degradato per produttività quotidiana.

### Azione immediata (senza deploy)

```sql
-- Crea policy per contactlbb.com
INSERT INTO casafolino_mail_sender_policy (name, pattern_type, pattern_value, action, priority, active, create_uid, write_uid, create_date, write_date)
VALUES ('Ignora contactlbb.com', 'domain', '*contactlbb*', 'auto_discard', 15, true, 1, 1, NOW(), NOW());

-- Crea policy per interni casafolino.com  
INSERT INTO casafolino_mail_sender_policy (name, pattern_type, pattern_value, action, priority, active, create_uid, write_uid, create_date, write_date)
VALUES ('Interni casafolino.com → keep auto', 'domain', '*@casafolino.com*', 'auto_keep', 20, true, 1, 1, NOW(), NOW());

-- Retroattivo: marca messaggi contactlbb come discard
UPDATE casafolino_mail_message SET state = 'discard' 
WHERE sender_email ILIKE '%@contactlbb.com' AND state IN ('new', 'review');

-- Retroattivo: marca messaggi interni come keep
UPDATE casafolino_mail_message SET state = 'keep' 
WHERE sender_email ILIKE '%@casafolino.com' AND state IN ('new', 'review');
```
