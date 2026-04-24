# Radiografia Cron — casafolino_mail

**Data analisi**: 2026-04-24 03:11 UTC (DB NOW)  
**Database**: folinofood (produzione)  
**Modulo**: casafolino_mail

---

## 1. Inventario Completo

Tutti i cron sono creati **dinamicamente** via `ir.cron.create()` nel codice Python — nessun file XML data, nessun record `ir_model_data` con `module='casafolino_mail'`.

### CORE (4 attivi)

| ID | Nome | Active | Freq | Metodo | Modello | lastcall | nextcall | failure_count |
|----|------|--------|------|--------|---------|----------|----------|---------------|
| 82 | CasaFolino Mail Sync V2 | ✅ | 15 min | `_cron_fetch_all_accounts()` | casafolino.mail.account | 2026-04-24 03:00 | 2026-04-24 03:15 | 0 |
| 83 | CasaFolino Silent Partners | ✅ | 1 day | `_cron_silent_partners_alert()` | casafolino.mail.account | 2026-04-24 02:20 | 2026-04-25 02:16 | 0 |
| 84 | CasaFolino AI Classify | ✅ | 5 min | `_cron_ai_classify_pending()` | casafolino.mail.message | 2026-04-24 03:01 | 2026-04-24 03:06 | 0 |
| 85 | CasaFolino Body Fetch Pending | ✅ | 10 min | `_cron_fetch_pending_bodies()` | casafolino.mail.message | 2026-04-24 03:00 | 2026-04-24 03:10 | 0 |

### CORE (disattivati — backfill/migrazione completata)

| ID | Nome | Active | Freq | Metodo | Modello | lastcall | nextcall |
|----|------|--------|------|--------|---------|----------|----------|
| 96 | Mail V3: Policy Backfill | ❌ | 6 hours | `_cron_backfill_policies()` | casafolino.mail.sender_policy | 2026-04-21 18:27 | 2026-04-22 00:18 |
| 97 | Mail Hub: Backfill AI Classification | ❌ | 10 min | `_cron_backfill_ai_classification()` | casafolino.mail.message | 2026-04-21 18:27 | 2026-04-21 18:33 |
| 98 | CasaFolino: Auto-Attach Email a Lead | ❌ | 15 min | `_cron_auto_attach_leads()` | casafolino.mail.message | 2026-04-23 22:32 | 2026-04-23 22:47 |

### CORE (attivo, mai eseguito)

| ID | Nome | Active | Freq | Metodo | Modello | lastcall | nextcall |
|----|------|--------|------|--------|---------|----------|----------|
| 99 | CasaFolino: Digest Mittenti Fuori-CRM | ✅ | 1 week | `_cron_digest_fuori_crm()` | casafolino.mail.message | _(null)_ | 2026-04-27 06:00 |

### ONE-SHOT — Dismiss Cascade (10 totali)

| ID | Sender | Active | lastcall | nextcall |
|----|--------|--------|----------|----------|
| 100 | redazione@foodweb.it | ❌ | 2026-04-23 21:44 | 2026-05-23 21:43 |
| 101 | flyingbluecrm@info-flyingblue.com | ❌ | 2026-04-23 21:44 | 2026-05-23 21:44 |
| 102 | ncecchetto@vidasoftware.it | ❌ | 2026-04-23 22:05 | 2026-05-23 22:04 |
| 103 | amministrazione@thatsagrowth.com | ❌ | 2026-04-23 22:06 | 2026-05-23 22:05 |
| 104 | alex.dampolo@sensorfact.it | ❌ | 2026-04-23 22:06 | 2026-05-23 22:05 |
| 105 | a.sicilia@gruppofood.com | ❌ | 2026-04-23 22:06 | 2026-05-23 22:06 |
| 106 | news@mistercredit.it | ❌ | 2026-04-23 22:06 | 2026-05-23 22:06 |
| 107 | gbizzotto@wetalentia.com | ❌ | 2026-04-24 02:24 | 2026-05-24 02:23 |
| 108 | sanafood@bolognafiere.it | ❌ | 2026-04-24 02:24 | 2026-05-24 02:24 |
| 109 | sanafood@bolognafiere.it _(duplicato)_ | ❌ | 2026-04-24 02:26 | 2026-05-24 02:26 |

> Tutti i ONE-SHOT si auto-disattivano dopo esecuzione (`_cascade_delete_emails` → `cron.write({'active': False})`). Rimangono in DB come record inattivi.

---

## 2. Metodi Cron in Codice SENZA Cron in DB

Metodi `_cron_*` definiti nel codice Python ma **non presenti** come record `ir_cron`:

| Metodo | File | Modello | Stato |
|--------|------|---------|-------|
| `_cron_check_snooze()` | casafolino_mail_snooze.py:30 | casafolino.mail.snooze | ⚠️ ORFANO — nessun cron lo invoca |
| `_cron_auto_link_leads()` | casafolino_mail_lead_rule.py:249 | casafolino.mail.lead.rule | ⚠️ ORFANO — nessun cron lo invoca |
| `_cron_scheduled_send()` | casafolino_mail_draft.py:56 | casafolino.mail.draft | ⚠️ ORFANO — nessun cron lo invoca |
| `_cron_cleanup_old_drafts()` | casafolino_mail_draft.py:88 | casafolino.mail.draft | ⚠️ ORFANO — nessun cron lo invoca |
| `_cron_process_outbox()` | casafolino_mail_outbox.py:226 | casafolino.mail.outbox | ⚠️ ORFANO — nessun cron lo invoca |
| `_cron_cleanup_old_outbox()` | casafolino_mail_outbox.py:259 | casafolino.mail.outbox | ⚠️ ORFANO — nessun cron lo invoca |
| `_cron_cleanup_discarded()` | casafolino_mail_message_staging.py:1039 | casafolino.mail.message | ⚠️ ORFANO — nessun cron lo invoca |

> **7 metodi cron definiti ma mai registrati in DB.** Questi funzionerebbero solo se un record `ir_cron` viene creato manualmente o via XML data.

---

## 3. Anomalie

### 3a. Nextcall CORE attivi

| ID | Nome | nextcall | Atteso (freq) | Stato |
|----|------|----------|---------------|-------|
| 82 | Mail Sync V2 | 03:15 | ~03:15 (15min) | ✅ OK |
| 83 | Silent Partners | 2026-04-25 02:16 | ~24h dopo last | ✅ OK |
| 84 | AI Classify | 03:06 | ~03:06 (5min) | ✅ OK |
| 85 | Body Fetch | 03:10 | ~03:10 (10min) | ✅ OK |
| 99 | Digest Fuori-CRM | 2026-04-27 06:00 | 1 week, mai run | ⚠️ Mai eseguito — lastcall NULL |

### 3b. ONE-SHOT zombie

| Tipo | Count | Dettaglio |
|------|-------|-----------|
| ONE-SHOT inattivi (executed + auto-disabled) | 10 | ID 100-109, tutti `active=False` |
| Duplicati (stesso sender) | 1 | sanafood@bolognafiere.it ha 2 cron (108, 109) |
| Zombie attivi | 0 | Nessun ONE-SHOT rimasto attivo dopo esecuzione |

### 3c. Metodi orfani

7 metodi `_cron_*` nel codice senza record `ir_cron` in DB. Funzionalità potenzialmente morta o non ancora attivata:
- Snooze check, auto-link leads, scheduled send, cleanup drafts/outbox/discarded

---

## 4. Esecuzione Recente (da log container, ultimi ~30min visibili)

| Cron | Esecuzioni osservate | Durata tipica | Errori |
|------|---------------------|---------------|--------|
| #82 Mail Sync V2 | 2 run | 1-4s | 0 |
| #84 AI Classify | 3 run | 0.007s-0.65s | 0 |
| #85 Body Fetch | 2 run | 0.007s-0.078s | 0 |
| #83 Silent Partners | _(daily, non nel window)_ | — | 0 |
| #99 Digest Fuori-CRM | _(weekly, mai eseguito)_ | — | — |

> Log completo 48h non estraibile via SSH (volume troppo alto). Da dati disponibili: **zero errori, zero failure_count su tutti i cron CORE attivi.**

---

## 5. Sommario

| Metrica | Valore |
|---------|--------|
| **Cron totali in DB** | 18 |
| **CORE attivi** | 5 (82, 83, 84, 85, 99) |
| **CORE disattivati** (backfill) | 3 (96, 97, 98) |
| **ONE-SHOT (dismiss cascade)** | 10 (tutti inattivi, eseguiti) |
| **Zombie attivi** | 0 |
| **ONE-SHOT duplicati** | 1 (sanafood@bolognafiere.it) |
| **Nextcall anomali** | 0 su CORE attivi |
| **Metodi orfani (codice senza cron)** | 7 |
| **Failure count > 0** | 0 |
| **Cron con lastcall NULL** | 1 (#99 Digest Fuori-CRM) |

### Raccomandazioni (non azioni)

1. **10 ONE-SHOT inattivi** (ID 100-109): candidati a `DELETE FROM ir_cron WHERE id IN (100..109)` per pulizia
2. **7 metodi orfani**: decidere se registrare cron (draft scheduled send, outbox processing, snooze check) o rimuovere il codice morto
3. **#99 Digest Fuori-CRM**: attivo ma mai eseguito — verificare che `nextcall 2026-04-27` sia corretto e il metodo funzioni
4. **Duplicato sanafood** (108+109): uno è ridondante
