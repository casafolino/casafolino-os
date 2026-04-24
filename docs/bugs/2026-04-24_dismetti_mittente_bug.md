# Bug: "Dismetti mittente" non persiste

**Date:** 2026-04-24
**Module:** casafolino_mail
**Severity:** P2 — sender dismissal ineffective, requires repeated user action
**Reported sender:** `sanafood@bolognafiere.it`

## Scenario identificato

**Scenario C + account mismatch:** Il dismiss scrive correttamente in DB e il cron IMAP filtra le nuove email, ma ci sono **3 bug concorrenti** che causano la riapparizione:

### Bug 1: Account mismatch (CRITICO)

La tabella `casafolino_mail_sender_preference` ha una constraint `UNIQUE(email, account_id)`. Il sender `sanafood@bolognafiere.it` ha **due record su due account diversi**:

| id  | email                      | status    | account_id |
|-----|----------------------------|-----------|------------|
| 87  | sanafood@bolognafiere.it   | **kept**  | 2          |
| 518 | sanafood@bolognafiere.it   | dismissed | 1          |

Il messaggio (id=16618) appartiene ad **account 2**, dove lo status è `kept`. Il dismiss è stato eseguito su **account 1**. Il thread list filter (controller lines 79-201) filtra per gli account dell'utente corrente, quindi il messaggio su account 2 con status `kept` passa il filtro e il thread resta visibile.

**Root cause:** L'endpoint `/cf/mail/v3/sender_decision/dismiss` (line 1496) cerca la preference con:
```python
pref = request.env['casafolino.mail.sender_preference'].search([
    ('email', '=ilike', email),
    ('account_id', 'in', user_accounts),
], limit=1)
```
Con `limit=1` e `account_id IN user_accounts`, se l'utente ha 2 account (ids [1, 2]), il search restituisce il **primo** record trovato (id=87, account 2? o id=518, account 1?). L'ordine non è determinato. Il dismiss potrebbe colpire l'account sbagliato o solo uno dei due.

### Bug 2: Thread filter è troppo permissivo (CONTRIBUENTE)

Il filtro threads (controller lines 200-202):
```python
# Skip threads where ALL senders are dismissed
if thread_has_dismissed and not has_pending_sender and not has_keep_message:
    continue
```

Questo skippa il thread **solo se**:
1. `thread_has_dismissed` = True (almeno un sender è dismissed)
2. `not has_pending_sender` (nessun sender è pending)
3. `not has_keep_message` (nessun messaggio in stato keep/auto_keep)

Il messaggio 16618 ha `state = 'keep'`, quindi `has_keep_message = True` → il thread passa anche se il sender fosse dismissed su entrambi gli account.

### Bug 3: Cascade delete non elimina le email esistenti dell'account sbagliato

`_cascade_delete_emails()` (sender_preference.py line 103-118) esegue:
```python
DELETE FROM casafolino_mail_message
WHERE sender_email = %s AND account_id = %s
```

Questo cancella solo i messaggi dell'account associato alla preference dismissata (account 1), non quelli dell'account 2 dove il messaggio effettivamente risiede.

## Evidenza DB (prod folinofood)

```sql
-- Preference: 2 record, account mismatch
SELECT id, email, status, account_id FROM casafolino_mail_sender_preference
WHERE email ILIKE '%sanafood%bolognafiere%';
--  87 | sanafood@bolognafiere.it | kept      | 2
-- 518 | sanafood@bolognafiere.it | dismissed | 1

-- Messaggio sopravvive su account 2
SELECT id, sender_email, account_id, state, thread_id FROM casafolino_mail_message
WHERE sender_email ILIKE '%sanafood%bolognafiere%';
-- 16618 | sanafood@bolognafiere.it | 2 | keep | 699

-- Thread ancora visibile
SELECT id, subject, is_archived FROM casafolino_mail_thread WHERE id = 699;
-- 699 | Aperte le iscrizioni a SANA Food 2027 | f

-- Cron 109: nextcall troppo lontano (bug separato, Odoo default per ir.cron senza numbercall)
SELECT id, cron_name, active, nextcall FROM ir_cron WHERE id = 109;
-- 109 | Dismiss cascade: sanafood@bolognafiere.it | t | 2026-05-24 02:26:00
```

## Flusso IMAP (funziona)

Il cron IMAP (`_fetch_folder`, account.py lines 285-294) **filtra correttamente**:
```python
# ── V12.6: Skip dismissed senders ──
pref = Preference.search([
    ('email', '=ilike', sender_email_addr),
    ('account_id', '=', resolved_account_id),
], limit=1)
if pref and pref.status == 'dismissed':
    filtered_out += 1
    continue
```

Ma anche qui, cerca per `account_id = resolved_account_id`. Se la email entra su account 2 dove il status è `kept`, il filtro non la blocca.

## Ipotesi di fix (non implementate)

1. **Dismiss cross-account:** Quando si dismette un sender, il dismiss deve propagarsi a **tutti** gli account dell'utente, non solo al primo trovato. L'endpoint `/sender_decision/dismiss` deve cercare tutte le preference per quell'email e dismissarle tutte, o crearne di nuove per account mancanti.

2. **Cascade delete cross-account:** `_cascade_delete_emails()` deve eliminare i messaggi su **tutti** gli account dove il sender è dismissed, non solo sull'account della preference corrente.

3. **Thread filter rafforzato:** Cambiare la logica per skippare il thread anche se `has_keep_message = True` quando **il sender di quei messaggi keep è dismissed** (non solo quando il thread ha messaggi dismissed generici).

4. **Cron nextcall fix:** I cron cascade creati senza `numbercall` (fix V12.8) ereditano Odoo default di 1 mese. Il `nextcall` dovrebbe essere `now() + 12 seconds` (com'è nel codice). Verificare che il campo `nextcall` sia effettivamente settato correttamente all'atto della create.
