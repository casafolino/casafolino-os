# casafolino_mail — Code Review Report

_Eseguita il: 2026-05-05_
_Versione modulo analizzata: 18.0.17.1.1 (manifest) — versione dichiarata 18.0.18.0.0 nel brief_
_Codebase: 126 file, 21.445 righe_

## TL;DR (5 righe max)

Modulo funzionante in produzione con architettura solida per il volume attuale (3 utenti, ~800 msg). **Sicurezza multi-utente buona** grazie a record rules pervasive. Principali rischi: (1) password IMAP in chiaro nel DB, (2) SQL DELETE diretto che bypassa ORM e record rules in `sender_preference`, (3) 5.965 thread orfani su stage, (4) body_html con `sanitize=False` combinato con `innerHTML` lato OWL = vettore XSS potenziale, (5) N+1 e `time.sleep()` nei cron che non scalano. Nulla di bloccante per il volume attuale, ma 3-4 fix sono urgenti prima di crescere.

## SCORE PER AREA (1–10)

- Sicurezza: **6/10** — record rules solide, ma password plaintext e SQL DELETE bypassano il modello
- Performance: **5/10** — OK a 800 msg, non scala a 50K senza fix indici + N+1 + sleep cron
- Robustezza: **6/10** — SAVEPOINT + partial unique index buoni, ma `cr.commit()` in loop e error swallowing
- Data model: **7/10** — ben strutturato, state machine chiara, qualche ridondanza
- Manutenibilità: **6/10** — file message_staging da 2.429 righe, buona naming, scarsa doc interna
- **Score globale: 6/10**

---

## INVENTARIO

### Modelli (31 file Python in models/)

| # | Modello | File | Tipo | Righe |
|---|---------|------|------|-------|
| 1 | `casafolino.mail.account` | casafolino_mail_account.py | Model | ~795 |
| 2 | `casafolino.mail.message` | casafolino_mail_message_staging.py | Model | ~2429 |
| 3 | `casafolino.mail.raw` | casafolino_mail_raw.py | Model | ~530 |
| 4 | `casafolino.mail.thread` | casafolino_mail_thread.py | Model | ~200 |
| 5 | `casafolino.mail.sender_policy` | casafolino_mail_sender_policy.py | Model | ~100 |
| 6 | `casafolino.mail.sender_preference` | casafolino_mail_sender_preference.py | Model | ~143 |
| 7 | `casafolino.mail.tracking` | casafolino_mail_tracking.py | Model | ~50 |
| 8 | `casafolino.mail.draft` | casafolino_mail_draft.py | Model | ~150 |
| 9 | `casafolino.mail.outbox` | casafolino_mail_outbox.py | Model | ~258 |
| 10 | `casafolino.mail.folder` | casafolino_mail_folder.py | Model | ~120 |
| 11 | `casafolino.mail.folder.rule` | casafolino_mail_folder_rule.py | Model | ~60 |
| 12 | `casafolino.mail.snippet` | snippet.py | Model | ~50 |
| 13 | `casafolino.mail.snippet.picker` | snippet_picker.py | TransientModel | ~30 |
| 14 | `casafolino.mail.signature` | casafolino_mail_signature.py | Model | ~40 |
| 15 | `casafolino.mail.template` | casafolino_mail_template.py | Model | ~30 |
| 16 | `casafolino.mail.snooze` | casafolino_mail_snooze.py | Model | ~50 |
| 17 | `casafolino.mail.lead.rule` | casafolino_mail_lead_rule.py | Model | ~60 |
| 18 | `casafolino.mail.sender.filter` | sender_filter.py | AbstractModel (mixin) | ~150 |
| 19 | `casafolino.mail.sender.decision` | sender_decision.py | Model | ~80 |
| 20 | `casafolino.mail.triage.wizard` | triage_wizard.py | TransientModel | ~50 |
| 21 | `casafolino.mail.sla.partner` | sla_partner.py | SQL View (`_auto=False`) | ~140 |
| 22 | `casafolino.mail.orphan.partner` | orphan_partner.py | SQL View (`_auto=False`) | ~80 |
| 23 | `casafolino.mail.lead.score` | lead_score.py | SQL View (`_auto=False`) | ~100 |
| 24 | `casafolino.partner.intelligence` | casafolino_partner_intelligence.py | Model | ~720 |
| 25 | `casafolino.partner.intelligence.feedback` | casafolino_partner_intelligence_feedback.py | Model | ~30 |
| 26 | `casafolino.mail.response.metric` | casafolino_mail_response_metric.py | TransientModel | ~150 |
| 27 | `casafolino.mail.mass.action.log` | casafolino_mail_mass_action_log.py | Model | ~30 |
| 28 | `res.partner` (extend) | cf_contact.py | _inherit | ~830 |
| 29 | `crm.lead` (extend) | crm_lead_ext.py | _inherit | ~50 |
| 30 | `res.users` (extend) | res_users.py | _inherit | ~30 |

### Wizards (4)
- `casafolino.mail.assign.partner.wizard`
- `casafolino.mail.assign.lead.wizard`
- `casafolino.mail.assign.user.wizard`
- `casafolino.mail.create.lead.wizard`

### Controllers (3)
- `mail_v3_controllers.py` — ~1100 righe, 25+ endpoints JSON
- `tracking_controller.py` — 125 righe, 3 endpoints HTTP public
- `test_controller.py` — 10 righe, ping endpoint

### OWL Components (16 JS + 19 XML templates)
| Componente | File | Righe |
|------------|------|-------|
| MailV3Client | mail_v3_client.js | ~1313 |
| ComposeWizard | mail_v3_compose.js | ~721 |
| ThreadList | mail_v3_thread_list.js | ~64 |
| ReadingPane | mail_v3_reading_pane.js | ~115 |
| SidebarLeft | mail_v3_sidebar_left.js | ~63 |
| Sidebar360 | mail_v3_sidebar_360.js | ~153 |
| ReplyAssistant | mail_v3_reply_assistant.js | ~55 |
| MailV3Analytics | mail_v3_analytics.js | ~39 |
| SenderDecisionPopup | mail_v3_sender_decision_popup.js | ~88 |
| DismissedSenders | mail_v3_dismissed_senders.js | ~78 |
| FolderSidebar | mail_v3_folder_sidebar.js | ~199 |
| Notifications | mail_v3_notifications.js | ~144 |
| SyncBadge | mail_v3_sync_badge.js | ~93 |
| Insight360TabBar | mail_v3_insight_360_tabbar.js | ~197 |
| ComposeWizardDialog | compose_wizard_dialog.js | ~77 |
| SnippetClipboard | snippet_clipboard.js | ~29 |
| TriageShortcuts | triage_shortcuts.js | ~42 |

### Cron (creati via post_init_hook)
1. **CasaFolino Mail Sync V2** — ogni 5 min — `_cron_fetch_all_accounts`
2. **CasaFolino Silent Partners** — giornaliero 7:00 — `_cron_silent_partners_alert`
3. **CasaFolino Triage RAW** — ogni 5 min — `_cron_triage_raw`
4. **CasaFolino Cleanup RAW** — giornaliero 3:00 — `_cron_cleanup_raw`
5. _(One-shot)_ **Dismiss cascade** — creato per ogni dismiss, 12s delay

**Nota**: su stage, solo 1 cron attivo (`Auto-Standby Lead inattivi`). I cron mail non risultano attivi — possibile che l'account Antonio sia in stato `error` e i cron non girino.

### Record Rules (ir_rules.xml)
Coperte: account, message, tracking, thread, raw, folder, folder_rule, sender_preference, draft, outbox, mass_action_log. Pattern: `(account_id.responsible_user_id, '=', user.id)` per user, `(1, '=', 1)` per admin.

### Sicurezza ACL (ir.model.access.csv)
47 righe. Copertura completa per tutti i 31 modelli.

---

## TRACES

### Trace 1 — Email entrante "ordinaria"

**Percorso**: Cron `_cron_fetch_all_accounts` → `_fetch_emails()` → `_fetch_folder()` → dispatcher `_fetch_folder_legacy` o `_fetch_folder_raw` (flag `casafolino.use_raw_pipeline`).

**Legacy path** (`_fetch_folder_legacy`):
1. Connessione IMAP con timeout 60s
2. `imap.select()` su INBOX/Sent
3. `imap.search(SINCE last_fetch_datetime)` — cerca per data, non UID
4. Per ogni UID nel batch (50):
   a. Fetch `BODY.PEEK[HEADER]` — solo header, body scaricato dopo
   b. Parse Message-ID, From, To, CC
   c. `_resolve_account_id()` — mappa a quale account assegnare
   d. Dedup: `Message.search([('message_id_rfc', '=', message_id)])` — **una query per email!**
   e. Check `sender_preference` dismissed — **una query per email!**
   f. `is_sender_allowed()` dal mixin `sender_filter` — **1-2 query per email!**
   g. `Message.create(vals)` con SAVEPOINT implicito
   h. `Preference.sudo().create()` per nuovo mittente — silente su errore
5. `self.env.cr.commit()` ogni 50 messaggi

**Findings**:
- 🟠 **N+1 nella dedup** (riga 285): per ogni email, fa `search([message_id_rfc = X])`. Con 500 email/giorno = 500 query. Fix: pre-caricare set di message_id_rfc esistenti.
- 🟠 **N+1 nel sender_preference check** (riga 291-296): per ogni email, cerca preference. Fix: pre-caricare mappa `{email: pref}`.
- 🟡 **IMAP SEARCH per data, non UID** (riga 239): se `last_fetch_datetime` è ieri, ri-scansiona tutte le email da ieri. Su account con 200 mail/giorno il lunedì dopo weekend = 600+ email riscansionate. La dedup le blocca, ma lo spreco IMAP c'è.
- 🟡 **Nessun lock anti-concorrenza** (riga 614-622): se due worker cron partono, entrambi leggono `last_fetch_datetime` uguale, fetchano le stesse email, la dedup (partial unique index) previene duplicati ma c'è spreco.

### Trace 2 — Race condition cron

**Scenario**: Due esecuzioni `_cron_fetch_all_accounts` ravvicinate.

1. Cron A legge `last_fetch_datetime = 10:00`
2. Cron B legge `last_fetch_datetime = 10:00` (stesso valore, A non ha ancora finito)
3. Entrambi fetchano email SINCE 10:00
4. Cron A fa `Message.create()` per email X → OK, inserita
5. Cron B fa `Message.create()` per email X → partial unique index `casafolino_mail_message_rfc_account_uniq` → violazione UNIQUE
6. Nel path RAW: SAVEPOINT cattura l'errore (riga 510-516) e continua
7. Nel path legacy: `except Exception as e: continue` (riga 363-364) cattura e continua

**Findings**:
- 🟢 **SAVEPOINT nel path RAW è strutturale** — la combinazione partial unique index + SAVEPOINT + continue è corretta per idempotenza.
- 🟡 **Path legacy senza SAVEPOINT** (riga 349-364): usa bare `try/except continue` che è meno strutturale ma funziona perché ogni insert è atomica nel contesto ORM.
- 🟡 **`last_fetch_datetime` aggiornato nel finally** (riga 164): il timestamp viene aggiornato anche su errore, quindi se il cron fallisce a metà batch (50/100), le 50 rimanenti vengono ri-fetchate al giro successivo — **buon design resiliente**.
- 🟢 **`cr.commit()` ogni 50** (riga 367): limita blast radius su crash — le prime 50 sono salve.
- ✅ **Query stage conferma zero duplicati**: `message_id_rfc` duplicati = 0 righe.

### Trace 3 — User isolation breach

**Scenario**: Martina (Back Office) prova ad accedere alle mail di Antonio (CEO).

**(a) `search()` diretta su `casafolino.mail.message`**:
Record rule `rule_mail_message_user` filtra `('account_id.responsible_user_id', '=', user.id)`. Martina vede solo email dei propri account. ✅ **Bloccato**.

**(b) `browse()` per ID specifico**:
Se Martina fa `self.env['casafolino.mail.message'].browse(42).read()`, Odoo applica la record rule in lettura. Se msg 42 appartiene ad Antonio → AccessError. ✅ **Bloccato**.

**(c) RPC dal browser via DevTools**:
I controller `/cf/mail/v3/` usano `_get_user_account_ids()` (riga 38-43 controller) che filtra per `responsible_user_id = request.env.uid`. Anche se Martina forgia una richiesta con `account_ids` di Antonio, l'intersezione (riga 66) limita ai suoi account. ✅ **Bloccato**.

**(d) Partner timeline su partner condiviso**:
I partner (`res.partner`) non hanno record rules di isolamento per casafolino_mail. Martina PUÒ vedere i partner, ma la timeline (chatter) è gestita da `mail.message` nativo Odoo. Le email sincronizzate nel chatter via `_create_partner_mail_message` (riga 768-795) sono visibili a tutti perché usano `mail.message.sudo().create()`. 🟠 **BUCO**: Martina può vedere i contenuti delle email di Antonio nel chatter del partner.

**(e) `mail.activity` assegnata cross-user**:
Il cron `_cron_silent_partners_alert` (riga 627-687) crea activity assegnate all'`user_id` del lead. Queste activity sono visibili nel calendar/activity view solo all'utente target. Ma il partner form mostra TUTTE le activity. 🟡 **Parziale**: visibilità dipende dalla vista, non dal modello.

**Vettori d'attacco concreti**:
1. 🟠 `_create_partner_mail_message` (message_staging.py:795) — email body copiato nel chatter partner con `sudo()`, visibile a tutti
2. 🟡 `action_keep_for_all` (message_staging.py:1897-1899) — `self.sudo()` cerca email su TUTTI gli account per "keep for all", cross-isolation by design ma permette a un utente di marcare come keep email di altri
3. 🟡 `do_assign` (message_staging.py:1822) — `msg.sudo().write({'assigned_user_ids': ...})` permette di assegnare qualsiasi messaggio con sudo, ma il `browse` iniziale è soggetto a record rules

### Trace 4 — F8 OWL ComposeWizardDialog

**Percorso**: `ComposeWizardDialog.js` → `/cf/mail/v3/compose/prepare` → crea `casafolino.mail.draft` → autosave ogni 15s → `/cf/mail/v3/draft/{id}/send` → `draft.action_send()`.

**Da `draft.action_send()`** (casafolino_mail_draft.py):
1. Crea `casafolino.mail.outbox` con `state='undoable'`, `undo_until = now + 10s`
2. Client mostra countdown 10s con "Undo"
3. Se undo: `outbox.action_undo()` → elimina outbox
4. Se timeout: cron `_cron_process_outbox` (ogni 2 min) trova `undoable` con `undo_until <= now` → transiziona a `queued` → `_send_smtp()`

**SMTP Send** (`outbox._send_smtp`, riga 137):
1. `smtplib.SMTP('smtp.gmail.com', 587)` — hardcoded
2. `server.login(account.email_address, account.imap_password)` — password plaintext dal DB
3. `server.sendmail()`
4. `_imap_append_sent()` — copia nella cartella Sent via IMAP
5. `_create_outbound_message()` — crea record in `casafolino.mail.message`

**Punti deboli**:
- 🟡 **Gap tra undo window e cron**: undo window = 10s, cron outbox gira ogni ~2 min. Email rimane in `undoable` per 10s, poi diventa `queued`, ma il cron potrebbe non girare per altri 110s. **Delay effettivo invio: 10s-130s dopo click send**.
- 🟡 **Se SMTP fallisce**: retry con `max_retries=3`, poi `state='error'`. L'utente non ha feedback immediato — deve tornare e controllare.
- 🟢 **Browser chiuso prima del commit**: il draft è già salvato (autosave ogni 15s). L'outbox è creato atomicamente. Se l'utente chiude dopo aver premuto Send, l'outbox esiste e verrà processato dal cron.
- 🟡 **IMAP append failure** (riga 184-185): errore silente, l'email è inviata ma non appare nella cartella Sent di Gmail.

---

## RISPOSTE DOMANDE 1–8

### 1. SICUREZZA E ISOLAMENTO MULTI-UTENTE

**Risultato**: L'isolamento multi-utente è **solido per il path standard** (OWL client → controller → record rules). I buchi sono nei percorsi laterali:

| # | Vettore | File:Riga | Severity | Impatto |
|---|---------|-----------|----------|---------|
| 1 | Chatter leaks: email body copiato in `mail.message` su partner condiviso con `sudo()` | message_staging.py:795 | 🟠 MAJOR | Martina vede corpo email inviate da/a Antonio nel chatter del partner |
| 2 | `action_keep_for_all` usa `self.sudo()` per cercare email di TUTTI gli account | message_staging.py:1898 | 🟠 MAJOR | Un utente può forzare keep su email di account altrui |
| 3 | `_cascade_delete_emails` usa SQL DELETE diretto, bypassa record rules | sender_preference.py:116-121 | 🟠 MAJOR | Dismiss di un mittente cancella email cross-account senza check ownership |
| 4 | Password IMAP in chiaro come `fields.Char` senza `groups=` restriction | casafolino_mail_account.py:27 | 🟠 MAJOR | Qualsiasi utente con accesso al modulo può leggere le app password |
| 5 | `is_admin()` hardcoda `antonio@casafolino.com` | casafolino_mail_account.py:696 | 🟡 MINOR | Non scalabile, ma basso rischio con 3 utenti |
| 6 | Tracking endpoints `auth='public'` senza rate limiting | tracking_controller.py:23-57 | 🟡 MINOR | Chiunque con un token valido può registrare eventi tracking illimitati |
| 7 | `body_html = fields.Html(sanitize=False)` + `innerHTML` in OWL | message_staging.py:93, mail_v3_compose.js:144/495 | 🟠 MAJOR | Email malevola con XSS nel body → eseguita nel browser dell'utente |
| 8 | `prompt('URL:')` per link senza validazione — `javascript:` URI possibile | mail_v3_compose.js:241 | 🟡 MINOR | Self-XSS: l'utente stesso dovrebbe incollare un URI malevolo |

### 2. PERFORMANCE E SCALABILITÀ

**Volume target**: 50.000 messaggi a 12 mesi, ~500 mail/giorno.

**Top 3 bottleneck**:

| # | Bottleneck | File:Riga | Severity | Impatto a 50K msg |
|---|-----------|-----------|----------|--------------------|
| 1 | **N+1 in fetch legacy**: dedup per email (search per message_id), preference check per email, is_sender_allowed per email | account.py:285,291,314 | 🟠 MAJOR | 500 msg/giorno × 3 query = 1500 query/fetch. A 50K totali la search diventa lenta senza indice composito |
| 2 | **`time.sleep()` nei cron AI**: 2.5s tra chiamate × 25 msg = 62.5s blocco cron thread | message_staging.py:1213 | 🟠 MAJOR | Con 500 msg/giorno, classify backlog cresce più veloce di 25 msg/5min. Sleep blocks Odoo worker |
| 3 | **Thread list N+1 nel controller**: per ogni thread, query last_msg, query lead, query attachment_count, iterate message_ids | mail_v3_controllers.py:184-277 | 🟠 MAJOR | 50 thread × 5 query = 250 query per page load. Con 6K thread diventa visibilmente lento |

**Indici mancanti (verificato su stage)**:
- 🟡 **Composito `(account_id, state, email_date DESC)`**: il dominio più frequente è `[account_id IN X, state='keep', is_deleted=false]` + ORDER BY email_date DESC. Esiste `idx_msg_read` ma copre solo `(is_read, account_id) WHERE state='keep'`.
- 🟡 **`(sender_email, account_id)`** per dedup sender_preference: usato in ogni fetch, manca indice composito.
- 🟢 **Indici duplicati**: `direction_computed` ha 3 indici identici (confermato su stage). Stessa cosa per `is_deleted`, `is_archived`, `thread_id`. Spreco di spazio e write amplification.

**Stato attuale su stage**: 837 messaggi, 669 raw, 6.258 thread (5.965 orfani!), 2.596 sender_pref. Il volume è bassissimo — i problemi di performance non sono ancora visibili.

### 3. COERENZA TRANSAZIONALE E IDEMPOTENZA

**SAVEPOINT per duplicate UID** (RAW path, account.py:510-516):
```python
with self.env.cr.savepoint():
    Raw.create(vals)
```
Combinato con il partial unique index `casafolino_mail_message_rfc_account_uniq`, è una **soluzione strutturale corretta**. Non è un cerotto — è il pattern PostgreSQL raccomandato per "INSERT IF NOT EXISTS" con race condition.

**Verifica su stage**: Zero duplicati confermati (`message_id_rfc` HAVING COUNT > 1 = 0 righe).

**`cr.commit()` in loop** — il vero rischio:

| Posizione | Pattern | Rischio |
|-----------|---------|---------|
| account.py:367 | Commit ogni 50 msg | Se crash a msg 75, le prime 50 sono committate ma `last_fetch_datetime` NON è aggiornato (è nel `finally`). Il refetch li ri-scarica e la dedup li blocca. ✅ OK |
| message_staging.py:1210 | Commit per ogni classify | Se crash dopo 10/25, le 10 sono classificate e committate. Le altre restano pending. ✅ OK |
| message_staging.py:1264 | Commit per ogni body download | Stesso pattern. ✅ OK |
| outbox.py:253 | Commit per ogni send | Se crash dopo 5/20 invii, le 5 sono inviate. Le altre restano queued. ✅ OK |

Il pattern `cr.commit()` è coerente e resiliente, anche se viola la best practice Odoo di non committare dentro transazioni ORM.

**🔴 Unica eccezione critica**: `_cascade_delete_emails` (sender_preference.py:116-121) fa `DELETE FROM casafolino_mail_message WHERE ...` con SQL diretto. Questo:
- Bypassa `unlink()` hooks (thread cleanup, attachment cleanup)
- Bypassa record rules (cancella email di qualsiasi account)
- Non aggiorna computed fields sui thread
- **Causa**: i 5.965 thread orfani su stage sono probabilmente causati da questo — le email vengono cancellate ma i thread restano.

### 4. DATA MODEL E STATE MACHINE

#### casafolino.mail.account

- **Campo mancante**: `last_error_datetime` — sapere QUANDO l'ultimo errore è avvenuto aiuterebbe a distinguere errori transienti da persistenti. Attualmente c'è `error_message` ma non il timestamp dell'errore.
- **Campo ridondante**: `email_address` duplica l'informazione che potrebbe stare in `res.users.email` tramite `responsible_user_id`. Ma è corretto tenerlo separato perché l'indirizzo IMAP può differire.
- **Indice mancante**: composito `(responsible_user_id, active, state)` — usato da `_get_user_account_ids()` in ogni request controller.

#### casafolino.mail.message

- **Campo mancante**: `raw_id` (link a `casafolino.mail.raw`) — quando un RAW viene promosso a message, il link si perde. Utile per debug e tracciabilità pipeline.
- **Campo ridondante**: `direction_computed` (riga 164-207) — ha un doppio `@api.depends` bug (solo l'ultimo decorator ha effetto) e il valore è sempre uguale a `direction`. Il campo esiste solo per avere un indice separato, ma `direction` potrebbe essere indicizzato direttamente.
- **Indice mancante** (verificato): composito `(account_id, state, is_deleted, email_date DESC)` — il dominio standard del thread list.

#### casafolino.mail.sender_policy

- **Campo mancante**: `account_id` — le policy sono globali (cross-account). Potrebbe servire una policy per-account per gestire casi dove un dominio è keep per Antonio ma discard per Martina.
- **Campo ridondante**: nessuno — modello snello.
- **Indice mancante**: composito `(active, priority)` per l'ordinamento `match_sender`.

**State machine buchi**:

La macchina a stati `new → auto_keep|auto_discard|review → keep|discard` ha queste proprietà:

- 🟡 **Transizione `review → keep|discard`**: OK, pilotata da triage manuale.
- 🟡 **Transizione `discard → keep`**: NON esiste nel codice. `action_discard` fa `unlink()` (riga 671), quindi il record sparisce — non c'è rollback. Se un utente scarta per errore, l'email è persa (a meno di re-fetch IMAP).
- 🟡 **Ri-classificazione policy**: se un messaggio in `review` viene riclassificato da una policy nuova, la ri-classificazione avviene solo nel cron `_cron_ai_classify_pending` che guarda `state='new'` (riga 1200). Un messaggio in `review` NON viene riclassificato — è corretto perché l'utente ha già deciso.
- 🟡 **Stato `auto_attached`**: non ha exit path verso `keep` o `discard`. I messaggi restano in questo stato indefinitamente.

### 5. ERROR HANDLING — comportamento sotto failure reale

**(a) Groq HTTP 429 per 30 minuti (rate limit)**

- **Cron classify** (message_staging.py:369-386): retry 1 volta con `time.sleep(20)`, poi scrive `ai_error='Rate limit 429 dopo retry'` e passa al prossimo. Con 25 msg e 429 persistente: i primi 2 consumano 40s in sleep, i restanti 23 vengono marcati con `ai_error`. Il cron gira ogni 5 min, quindi ogni giro tenta 25 msg.
- **RAW triage** (casafolino_mail_raw.py:345-346): `time.sleep(20)` su 429, poi retry. Stessa logica.
- **Reply assistant** (controller, riga 864-898): retry con backoff esponenziale (2s, 4s, 8s), max 3 tentativi. L'utente vede "Risposta AI non disponibile" dopo ~14s.
- 🟡 **Impatto**: durante un rate limit di 30 min, ~6 cron run × 25 msg × 20s sleep = worker thread bloccato per ~30 min. Non catastrofico con 3 utenti, ma blocca 1 worker.

**(b) IMAP TimeoutError dopo aver salvato 50 di 100 messaggi del batch**

- `_fetch_folder_legacy` (account.py:159-162): eccezione propagata al caller `_fetch_emails`, che la catcha, scrive `state='error'`, e il `finally` aggiorna `last_fetch_datetime`.
- Le 50 salvate sono committate (riga 367).
- Al prossimo giro, `last_fetch_datetime` è aggiornato → IMAP search da quel punto → le 50 rimanenti vengono ri-fetchate.
- 🟢 **Resiliente**: nessuna perdita dati.

**(c) AI classification ritorna JSON malformato per 50 messaggi su 100**

- `json.JSONDecodeError` catturato (riga 440-446): scrive `ai_error='JSON parse error: ...'` e `ai_classified_at=now()`. Il messaggio è marcato come "tentato" e NON verrà ri-tentato (il cron filtra per `ai_classified_at = False`).
- 🟡 **Nessun retry automatico** per JSON malformato. I messaggi restano con `ai_error` per sempre. Servirebbero un meccanismo di retry per errori transienti o un cron di "retry ai errors".

**(d) Race condition su constraint UNIQUE durante insert concorrenti**

- Path RAW: SAVEPOINT cattura → `continue` → OK.
- Path legacy: `except Exception: continue` → OK ma meno pulito.
- 🟢 **Gestito correttamente**.

**(e) Gmail revoca l'app password durante un fetch**

- `imaplib.IMAP4.login()` solleva `imaplib.IMAP4.error`.
- Catturato in `_get_imap_connection` (riga 73-75): scrive `state='error', error_message=str(e)`.
- Il cron cerca solo `state='connected'` (riga 616), quindi l'account non viene più fetchato fino a fix manuale.
- 🟡 **Nessun alert attivo**: l'utente deve accorgersi che le email non arrivano più. Sarebbe utile una notifica bus.bus o activity.

**(f) Disco pieno durante salvataggio attachment**

- `ir.attachment.create()` solleva eccezione.
- Catturato in `_download_body_imap` (riga 760-764): `except Exception as e: _logger.warning(...)`. Il body_html è già salvato (riga 743-748), solo l'allegato manca.
- 🟡 **Parzialmente resiliente**: body salvato, allegato perso silenziosamente. L'utente non sa che manca un allegato.

### 6. TEST COVERAGE

**Stato attuale**: 1 file test (`test_multi_user_isolation.py`, 123 righe).

**🟠 Il test non funziona**: usa campi inesistenti `imap_user`, `smtp_host`, `smtp_user`, `smtp_password` (righe 39-55) che non esistono sul modello `casafolino.mail.account`. Il test fallirebbe con `ValueError: Invalid field 'imap_user'`.

**5 test critici mancanti**:

| # | Test | Oggetto | Comportamento atteso | Rischio senza |
|---|------|---------|---------------------|---------------|
| 1 | `test_dedup_message_id_rfc` | Inserimento email con stesso message_id_rfc + account_id | Secondo insert non crea duplicato (SAVEPOINT o unique index violation) | Duplicati in produzione |
| 2 | `test_cascade_delete_cross_account` | `_cascade_delete_emails` non cancella email di account non-dismissed | Solo email dell'account dismissed vengono cancellate | Data loss cross-utente |
| 3 | `test_xss_body_html` | Email con `<script>alert(1)</script>` nel body_html | Script non eseguito nel rendering OWL | XSS in produzione |
| 4 | `test_groq_429_resilience` | Mock Groq che ritorna 429 per 5 chiamate consecutive | Cron non crasha, messaggi marcati con ai_error, retry al giro successivo | Cron bloccato indefinitamente |
| 5 | `test_imap_fetch_partial_failure` | IMAP timeout dopo 25 messaggi su 50 | I primi 25 committati, last_fetch_datetime aggiornato, nessun duplicato al refetch | Perdita o duplicazione email |

### 7. INTEGRAZIONI ESTERNE — punti fragili

#### IMAP Gmail (auth via app password)

- **Fallimento silenzioso**: account con `state='error'` smette di essere fetchato. Nessuna notifica all'utente.
- **Fallimento rumoroso**: `UserError("Connessione IMAP fallita: %s")` in action manuale. Nel cron: logged e `state='error'`.
- **Health check**: campo `state` e `last_successful_fetch_datetime`. Nessun allarme proattivo.
- 🟡 **Gap**: se Gmail cambia formato risposta IMAP o limita connessioni, il modulo fallisce silenziosamente.

#### Groq API (HTTP)

- **Fallimento silenzioso**: messaggi marcati con `ai_error` — nessun alert. L'utente vede email non classificate nell'inbox.
- **Fallimento rumoroso**: 403 Cloudflare (già gestito con retry), 500 server error → logged.
- **Health check**: nessuno. Il controller `/cf/mail/v3/settings/test_groq` è manuale.
- 🟡 **Gap**: se Groq cambia il modello `llama-3.3-70b-versatile` o lo depreca, tutte le classificazioni si fermano silenziosamente.

#### Odoo mail.thread / mail.activity

- **Fallimento silenzioso**: `_create_partner_mail_message` (riga 768-795) crea `mail.message` con `sudo()`. Se il modello `mail.message` cambia schema in un aggiornamento Odoo, l'errore è catturato a livello superiore.
- **Health check**: nessuno.

#### CRM Lead (crm.lead)

- **Fallimento silenzioso**: `_maybe_auto_create_lead` (riga 459-550) fa `try/except` con log warning. Se il modello CRM non è installato o i campi custom mancano, l'errore è ignorato.
- **Health check**: nessuno.
- 🟡 **Dipendenza hardcoded**: campi `cf_auto_created`, `cf_mail_thread_id` dal modulo `casafolino_crm_export` — se quel modulo cambia, questo si rompe.

### 8. BUS FACTOR E LEGGIBILITÀ

**Cosa manda in confusione un junior**:
1. Il file `casafolino_mail_message_staging.py` (2429 righe) mischia model fields, AI classification, email sending, CRM integration, OWL API, cron methods, e utility methods. Un junior non sa da dove iniziare.
2. Il naming `message_staging` suggerisce un modello di staging, ma è il modello principale `casafolino.mail.message`.
3. Due pipeline parallele (legacy vs RAW) controllate da un feature flag (`casafolino.use_raw_pipeline`) senza documentazione su quale sia attiva in prod.

**3 file da leggere per primi**:
1. `__manifest__.py` + `__init__.py` (root) — capire struttura e post_init_hook
2. `casafolino_mail_account.py` — capire il fetch engine e il ciclo IMAP
3. `controllers/mail_v3_controllers.py` — capire l'API OWL e il pattern di ownership check

**Documentazione mancante**:
- Nessun README nel modulo
- Nessun docstring sulle classi principali
- Nessun diagramma di flusso della pipeline email (RAW → triage → message → thread)
- Nessun commento sulla scelta architetturale legacy vs RAW pipeline
- Le migrazioni (26 file!) non hanno changelog

---

## TOP 10 AZIONI PRIORITARIE

| # | Severity | Azione | Sforzo | Blast Radius | Beneficio |
|---|----------|--------|--------|-------------|-----------|
| 1 | 🔴 | **Fix `body_html sanitize=False`**: almeno aggiungere `sanitize_overridable=True` o sanitizzare in `_create_partner_mail_message` prima di iniettare nel chatter | 0.5 gg | Medio — cambia rendering email | Elimina vettore XSS più pericoloso |
| 2 | 🟠 | **Sostituire SQL DELETE in `_cascade_delete_emails`** con ORM `unlink()` + check account ownership | 0.5 gg | Alto — impatta dismiss flow | Elimina bypass record rules + fix thread orfani |
| 3 | 🟠 | **Aggiungere `groups='base.group_system'` a `imap_password`** o usare `ir.config_parameter` criptato | 0.25 gg | Basso | Password non leggibili da utenti base |
| 4 | 🟠 | **Cleanup 5.965 thread orfani** su stage (e 1 query per capire quanti in prod) | 0.25 gg | Basso | Pulizia DB, query più veloci |
| 5 | 🟠 | **Fix test non funzionante**: rimuovere campi inesistenti nel test, aggiungere almeno 3 test critici (dedup, cascade, XSS) | 1 gg | Nessuno | Regressioni catturate prima del deploy |
| 6 | 🟠 | **Eliminare N+1 nel fetch**: pre-caricare set `{message_id_rfc}`, mappa `{email: preference}`, set `{allowed_domains}` prima del loop | 1 gg | Medio — cambia fetch engine | Scala a 500 msg/giorno senza degradare |
| 7 | 🟠 | **Rimuovere `time.sleep()` dai cron**: usare queue asincrona o batch singolo senza sleep, gestire 429 con backoff + skip batch | 0.5 gg | Medio — cambia classify cron | Worker thread non bloccato per 60+ secondi |
| 8 | 🟡 | **Dedup indici**: rimuovere i 9 indici duplicati (3 su `direction_computed`, 2 su `is_deleted`, 2 su `is_archived`, 2 su `thread_id`) | 0.25 gg | Basso | ~20% riduzione write amplification |
| 9 | 🟡 | **Split `message_staging.py`**: estrarre AI classifier, email sending, e OWL API in file separati | 1 gg | Basso — solo riorganizzazione | Manutenibilità: da 2429 righe a ~4 file da 600 |
| 10 | 🟡 | **Aggiungere health check proattivo**: bus.bus notification se IMAP in error da >1h, se Groq fallisce 3 volte consecutive | 0.5 gg | Basso | L'utente scopre il problema in minuti, non giorni |

---

## COSA È FATTO BENE

1. **Record rules pervasive**: 12 modelli coperti con pattern coerente `account_id.responsible_user_id = user.id`. Admin bypass con `(1,'=',1)`. Nessun modello "dimenticato".

2. **Partial unique index per dedup** (message_staging.py:186-201): `CREATE UNIQUE INDEX ... WHERE message_id_rfc IS NOT NULL AND message_id_rfc != ''` — soluzione PostgreSQL corretta che combina idempotenza + tolleranza per email senza Message-ID. Confermato funzionante: zero duplicati su stage.

3. **Pipeline a due stadi (header-first)**: fetch solo header IMAP, body scaricato on-demand o via cron. Risparmia banda e tempo di sync. Pattern intelligente per "ponte selettivo".

4. **Cron con batch + commit**: tutti i cron hanno `limit` e `cr.commit()` per batch. Resilienza a crash parziali. Il `finally` block per `last_fetch_datetime` è corretto.

5. **Tracking email outbound** (pixel + link rewrite): implementazione completa con dedup aperture (5 min), forward detection (IP diverso), notifica real-time via bus.bus. Codice pulito e ben isolato in `tracking_controller.py`.

---

## DOMANDE PER L'AUTORE

1. **Legacy vs RAW pipeline**: quale è attiva in produzione? Il flag `casafolino.use_raw_pipeline` è `true` o `false` in prod? Su stage ci sono 837 messaggi (tutti `state=new`) e 669 raw — sembra che entrambe le pipeline siano state usate.

2. **5.965 thread orfani su stage**: sono il risultato del `_cascade_delete_emails` SQL o di un'altra operazione? Questo pattern esiste anche in prod?

3. **Account Antonio in `error` su stage**: il fetch cron non sta girando per nessun account su stage (nessun cron casafolino_mail attivo). È intenzionale?

4. **`sanitize=False` su `body_html`**: è una scelta consapevole per preservare il rendering email (CSS inline, immagini embedded)? Se sì, consideri almeno un sanitize lato Python prima di inserire nel chatter?

5. **`action_discard` fa `unlink()`**: è intenzionale che "Scarta" sia irreversibile (cancella il record)? Nella pipeline RAW esiste `triage_state='discarded'` che è reversibile. Perché il path legacy è distruttivo?

---

## APPENDICE: query SQL eseguite

Tutte su `folinofood_stage`:

```sql
-- 1. Indici su casafolino_mail_message
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'casafolino_mail_message' ORDER BY indexname;
-- Risultato: 24 indici, di cui 9 duplicati

-- 2. Duplicati message_id_rfc
SELECT message_id_rfc, COUNT(*) FROM casafolino_mail_message WHERE message_id_rfc IS NOT NULL GROUP BY message_id_rfc HAVING COUNT(*)>1 LIMIT 10;
-- Risultato: 0 righe (nessun duplicato)

-- 3. Conteggio record per tabella
SELECT 'messages' as entity, COUNT(*) FROM casafolino_mail_message
UNION ALL SELECT 'raw', COUNT(*) FROM casafolino_mail_raw
UNION ALL SELECT 'threads', COUNT(*) FROM casafolino_mail_thread
-- ... (8 tabelle)
-- Risultato: 837 msg, 669 raw, 6258 thread, 3 account, 2596 sender_pref

-- 4. Thread orfani (senza messaggi)
SELECT COUNT(*) as orphan_threads FROM casafolino_mail_thread t WHERE NOT EXISTS (SELECT 1 FROM casafolino_mail_message m WHERE m.thread_id = t.id);
-- Risultato: 5965 thread orfani

-- 5. Cron attivi
SELECT id, cron_name, active, interval_number, interval_type, nextcall FROM ir_cron WHERE cron_name ILIKE '%casafolino%' AND active=true ORDER BY nextcall;
-- Risultato: 1 solo cron attivo (Auto-Standby Lead inattivi)

-- 6. Dismiss crons accumulati
SELECT COUNT(*) as dismiss_crons FROM ir_cron WHERE cron_name LIKE '%Dismiss cascade%';
-- Risultato: 0

-- 7. Indici duplicati direction_computed
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'casafolino_mail_message' AND indexname LIKE '%direction_computed%';
-- Risultato: 3 indici identici

-- 8. Composito account_id + state
SELECT indexname FROM pg_indexes WHERE tablename = 'casafolino_mail_message' AND indexdef LIKE '%account_id%state%';
-- Risultato: solo idx_msg_read (parziale)

-- 9. Sender preference distribuzione
SELECT status, COUNT(*) FROM casafolino_mail_sender_preference GROUP BY status ORDER BY status;
-- Risultato: kept=2503, pending=93

-- 10. Indici su casafolino_mail_raw
SELECT indexname FROM pg_indexes WHERE tablename = 'casafolino_mail_raw' ORDER BY indexname;
-- Risultato: 12 indici (ben coperto)

-- 11. Stato messaggi
SELECT state, COUNT(*) FROM casafolino_mail_message GROUP BY state ORDER BY count DESC;
-- Risultato: tutti 837 in state='new'

-- 12. Account - verifica password storage
SELECT id, name, email_address, LENGTH(imap_password) as pwd_len, state FROM casafolino_mail_account ORDER BY id;
-- Risultato: 3 account, pwd_len 16-19, state: 1 error + 2 connected

-- 13. Body stats
SELECT COUNT(*) as total_messages, COUNT(CASE WHEN body_html IS NOT NULL AND body_html != '' THEN 1 END) as with_body, COUNT(CASE WHEN body_downloaded = true THEN 1 END) as body_downloaded FROM casafolino_mail_message;
-- Risultato: 837 totali, 143 con body, 143 body_downloaded
```
