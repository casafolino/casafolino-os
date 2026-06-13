# STATO ARTE CasaFolino OS — 2026-06-12

Data analisi: 2026-06-12. Modalita: **sola lettura** su server/DB.
Nessun update modulo, nessun restart, nessun deploy, nessun commit/push.

---

## SINTESI ESECUTIVA (5 righe)

Il sistema Odoo 18.0-20250320 Enterprise e **parzialmente operativo**: la UI risponde e la creazione di `crm.lead` via shell ORM **funziona senza errori** (CREATE OK id 1215, rollback immediato). Il blocco percepito non e un errore Python sulla create del lead. La causa reale del degrado e che **12 moduli custom sono bloccati in stato `to upgrade`** nel DB, il che impedisce a Odoo di eseguire qualsiasi cron (warning `Skipping database folinofood because of modules to install/upgrade/remove` — 30 volte oggi). In parallelo `casafolino_pipeline_control` (Sala Controllo) crasha ad ogni richiesta inbox con `KeyError: 'cf.ai.router'`. Il CRM standard Odoo rimane usabile ma tutto il layer custom (Mail Hub, Sala Controllo, Dossier, automazioni) e degradato.

---

## 1. AMBIENTE

| Parametro | Valore |
|-----------|--------|
| Server | EC2 `51.44.170.55` |
| Container `odoo-app` | `odoo:18.0` — Up (riavviato di recente) |
| Container `odoo-db` | `postgres:15` — Up 5 days |
| Versione Odoo | **18.0-20250320** (FINAL) |
| Comando | `/usr/bin/odoo` |
| Edition | **Enterprise** (repos_heads include chiave `enterprise`: `b37efce0839dc5424f16d69ccaab49146e86f88f`) |
| Addons path | `/usr/lib/python3/dist-packages/odoo/addons`, `/var/lib/odoo/addons/18.0`, `/mnt/extra-addons`, `/mnt/extra-addons/enterprise`, `/mnt/extra-addons/custom` |
| Config workers | `workers=3`, `max_cron_threads=1` |
| DB filter | `^folinofood$` |
| Timeout | `limit_time_cpu=600`, `limit_time_real=1200` |
| DB disponibili | `folinofood` (prod), `folinofood_stage`, `folinofood_stage_old_20260418_0654` |

---

## 2. CAUSA ESATTA BLOCCO CREAZIONE LEAD

### Risultato test diagnostico

```
CREATE OK - id: 1215
```

Rollback eseguito immediatamente — nessuna scrittura persistita.
Verifica post-test: `SELECT id FROM crm_lead WHERE name='DIAG TEST'` → 0 righe. Corretto.

**La creazione ORM di `crm.lead` NON e bloccata.**

### Causa reale del degrado percepito

**BLOCCO 1 — 12 moduli in stato `to upgrade` (CRITICO):**

```sql
SELECT name, state, latest_version FROM ir_module_module
WHERE state = 'to upgrade' ORDER BY name;
```

| nome modulo | versione DB |
|-------------|-------------|
| casafolino_b2b_portal | 18.0.1.0.0 |
| casafolino_b2b_theme | 18.0.1.0.0 |
| casafolino_cockpit | 18.0.1.0.0 |
| casafolino_crm_360 | 18.0.1.0.0 |
| casafolino_crm_export | 18.0.13.0.0 |
| casafolino_home | 18.0.2.5.0 |
| casafolino_initiative_dashboard | 18.0.4.3.1 |
| casafolino_mail_stats | 18.0.0.4.0 |
| casafolino_mail_templates | 18.0.1.0.0 |
| casafolino_pipeline_control | 18.0.1.17.0 |
| casafolino_sala_commerciale | 18.0.1.0.0 |
| casafolino_workspace | 18.0.0.7.0 |

Finche questi 12 moduli hanno `state='to upgrade'`, Odoo salta l'esecuzione di tutti i cron su `folinofood`. Non viene eseguita automaticamente nessuna migrazione — serve un restart con `--update`.

**BLOCCO 2 — `casafolino_pipeline_control` crasha ad ogni accesso inbox:**

Traceback completo dai log:

```
File "/mnt/extra-addons/custom/casafolino_pipeline_control/models/pipeline_control.py",
  line 361, in <lambda>
File "/mnt/extra-addons/custom/casafolino_pipeline_control/models/pipeline_control.py",
  line 2406, in _safe_section
    status = self.env['cf.ai.router'].provider_status()
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  line 3254, in _get_inbox_data
  line 3262, in _get_ai_readiness_status
KeyError: 'cf.ai.router'
```

`cf.ai.router` e definito come `AbstractModel` in `casafolino_mail/models/cf_ai_router.py` (riga 12: `class CFAIRouter(models.AbstractModel)`). I modelli AbstractModel **non appaiono in `ir.model`** e non sono raggiungibili via `self.env['cf.ai.router']` — questa chiamata genera `KeyError` nel registry Odoo. Il bug e in `pipeline_control.py`: occorre usare `self.env.get('cf.ai.router')` con guardia `None`.

**BLOCCO 3 — Campo `numbercall` obsoleto su `ir.cron`:**

```
ValueError: Invalid field 'numbercall' on model 'ir.cron'
while evaluating 'records.action_keep()'
```

Il campo `numbercall` e stato rimosso in Odoo 18. Una server action o vista lo referenzia ancora (compare quando un utente interagisce con un cron dalla UI).

---

## 3. MODULI CUSTOM — INVENTARIO COMPLETO

| Nome | Stato DB | Versione DB | Problemi |
|------|----------|-------------|----------|
| casafolino_allergen | uninstalled | — | Non installato |
| casafolino_b2b_portal | **to upgrade** | 18.0.1.0.0 | Bloccato — dipende da pipeline_control |
| casafolino_b2b_theme | **to upgrade** | 18.0.1.0.0 | Bloccato |
| casafolino_cockpit | **to upgrade** | 18.0.1.0.0 | Bloccato |
| casafolino_commercial | installed | 18.0.2.4.5 | OK |
| casafolino_company_website | installed | 18.0.1.0.0 | OK |
| casafolino_corrispettivi | installed | 18.0.1.1.0 | OK |
| casafolino_crm_360 | **to upgrade** | 18.0.1.0.0 | Bloccato — dipende da initiative_dashboard |
| casafolino_crm_export | **to upgrade** | 18.0.13.0.0 | Bloccato — modulo CRM piu invasivo |
| casafolino_custom | uninstalled | — | Non installato |
| casafolino_fair_report | uninstalled | 18.0.0.1.0 | Non installato |
| casafolino_followup_tuttofood | installed | 18.0.1.0.0 | OK |
| casafolino_gdo | uninstalled | — | Non installato |
| casafolino_haccp | installed | 18.0.2.0.0 | OK prod; cron reminder rotti su `folinofood_stage` |
| casafolino_home | **to upgrade** | 18.0.2.5.0 | Bloccato — aggregatore di tutti i moduli |
| casafolino_initiative | installed | 18.0.2.0.1 | OK |
| casafolino_initiative_dashboard | **to upgrade** | 18.0.4.3.1 | Bloccato |
| casafolino_kpi | installed | 18.0.1.0.0 | OK |
| casafolino_labels | installed | 18.0.1.0.0 | OK |
| casafolino_mail | installed | 18.0.19.9.0 | OK funzionale; cf.ai.router AbstractModel (non in ir.model) |
| casafolino_mail_OLD_BACKUP | uninstalled | — | Backup — non usato |
| casafolino_mail_stats | **to upgrade** | 18.0.0.4.0 | Bloccato |
| casafolino_mail_templates | **to upgrade** | 18.0.1.0.0 | Bloccato |
| casafolino_operations | installed | 18.0.1.1.0 | OK |
| casafolino_pipeline_control | **to upgrade** | 18.0.1.17.0 | Bloccato + crash runtime cf.ai.router |
| casafolino_pos_guard | installed | 18.0.1.0.0 | OK |
| casafolino_product | installed | 18.0.1.1.0 | OK |
| casafolino_project | installed | 18.0.1.5.0 | OK |
| casafolino_reverse_charge_safe | installed | 18.0.1.0.0 | OK |
| casafolino_sala_commerciale | **to upgrade** | 18.0.1.0.0 | Bloccato |
| casafolino_shopify_sync | installed | 18.0.1.0.0 | OK |
| casafolino_supplier_qual | installed | 18.0.1.2.0 | OK |
| casafolino_voice_ai | installed | 18.0.8.0.1 | OK — cron attivi |
| casafolino_web_editor_patch | installed | 18.0.1.0.1 | OK |
| casafolino_workspace | **to upgrade** | 18.0.0.7.0 | Bloccato |

**Totale installed (inclusi to upgrade): 30 moduli**
**Totale to upgrade: 12 moduli**
**Totale uninstalled: 12 moduli**

---

## 4. ERRORI RICORRENTI DAI LOG

Analisi `docker logs odoo-app` (ultime 10.000 righe, oggi 12/06/2026):

| # | Errore | Freq. oggi | Fonte |
|---|--------|-----------|-------|
| 1 | `Skipping database folinofood because of modules to install/upgrade/remove` | **30x** | `ir_cron` — 12 moduli `to upgrade` bloccano tutti i cron |
| 2 | `FileNotFoundError: /var/lib/odoo/filestore/folinofood/bd/bd931059…` | **20x** | Attachment orfano — record in DB ma file eliminato dal filestore |
| 3 | `KeyError: 'cf.ai.router'` in `pipeline_control.py` righe 2406/3254/3262 | **5x** | Sala Controllo crasha ad ogni accesso inbox |
| 4 | `cf.gdo.listing: inconsistent 'store' for computed fields` (UserWarning) | **4x** | Modello `cf.gdo.listing` con campo computed `store` incoerente |
| 5 | `psycopg2.errors.UndefinedTable: relation "cf_raw_material_summary_wizard"` | **2x** | Autovacuum cerca tabella di wizard non installato |
| 6 | `psycopg2.errors.UndefinedTable: relation "cf_raw_material_summary_line"` | **2x** | Idem |
| 7 | `ValueError: Invalid field 'numbercall' on model 'ir.cron'` | **1x** | Campo obsoleto referenziato da server action UI |
| 8 | `.map should have been generated through debug assets (version outdated)` | **2x** | Asset sourcemap obsoleti — bassa priorita |
| 9 | `psycopg2.errors.UniqueViolation: bus_presence_user_unique` | **1x** | Race condition bus presence — non critico |
| 10 | `AttributeError: 'cf.haccp.reminder' object has no attribute '_send_daily_reminders'` | su `folinofood_stage` | HACCP cron puntano a metodi rimossi — non impatta prod |

**Cron con failure count cronico:**

| ID cron | Nome | Failures | Dal |
|---------|------|----------|-----|
| 145 | Backfill mail partner 100818 (Claudia Perini) | **3550** | 2026-05-18 |
| 152 | Backfill mail partner 101539 (Style Italy) | 10 | 2026-05-23 |
| 531/234/441 | Backfill mail partner 5012 (EUROPA COMMERCIALE SRL) | 3 ciascuno | 2026-05-27 |

---

## 5. MAPPA DIPENDENZE MODULI CUSTOM

```
casafolino_mail (v19.9.0)
  dipende da: base, mail, web, utm, crm
  USATO DA: crm_export, pipeline_control, crm_360, initiative_dashboard,
            cockpit, mail_stats, workspace, home

casafolino_initiative (v2.0.1)
  dipende da: base, mail, crm, project, sale, account, stock, mrp
  USATO DA: crm_export, initiative_dashboard, cockpit, home

casafolino_crm_export (v13.0.0) [TO UPGRADE]
  dipende da: crm, sale, mail, contacts, documents, project, account,
              stock, casafolino_mail, casafolino_project, casafolino_initiative
  USATO DA: pipeline_control, crm_360, mail_stats, home

casafolino_pipeline_control (v1.17.0) [TO UPGRADE] [CRASH RUNTIME]
  dipende da: crm, mail, sale, project,
              casafolino_crm_export, casafolino_mail, casafolino_project
  USATO DA: home, sala_commerciale (indiretto)

casafolino_initiative_dashboard (v4.3.1) [TO UPGRADE]
  dipende da: casafolino_initiative, casafolino_mail,
              project, mail, crm, calendar
  USATO DA: crm_360, mail_stats, cockpit

casafolino_crm_360 (v1.0.0) [TO UPGRADE]
  dipende da: crm, project, sale, mail, contacts, documents,
              casafolino_project, casafolino_mail, casafolino_crm_export,
              casafolino_initiative_dashboard

casafolino_mail_stats (v0.4.0) [TO UPGRADE]
  dipende da: mail, mass_mailing, mass_mailing_crm, crm,
              casafolino_mail, casafolino_initiative_dashboard,
              casafolino_crm_export

casafolino_home (v2.5.0) [TO UPGRADE]
  dipende da: base, web, website, casafolino_commercial,
              casafolino_crm_export, casafolino_haccp, casafolino_initiative,
              casafolino_kpi, casafolino_labels, casafolino_mail,
              casafolino_operations, casafolino_pipeline_control,
              casafolino_product, casafolino_project,
              casafolino_supplier_qual, casafolino_workspace

casafolino_workspace (v0.7.0) [TO UPGRADE]
  dipende da: base, web, mail, calendar, crm, project, account,
              stock, casafolino_mail

casafolino_cockpit (v1.0.0) [TO UPGRADE]
  dipende da: casafolino_initiative, casafolino_initiative_dashboard,
              casafolino_mail, base

casafolino_voice_ai (v8.0.1)
  dipende da: base, mail, contacts, crm

casafolino_commercial (v2.4.5)
  dipende da: base, mail, sale_management, product, account, purchase
```

**Punti fragili identificati:**

1. **`casafolino_mail` e il pilastro** — tutti i moduli CRM custom dipendono da lui. E installed correttamente ma `cf.ai.router` (AbstractModel) non e nel registry come modello accessibile via `env[]`.
2. **`casafolino_crm_export` e il modulo piu invasivo su `crm.lead`** — aggiunge campi, view, stage gate sulla write. In stato `to upgrade`: le sue migration non sono state applicate.
3. **`casafolino_home` e aggregatore** — dipende da 15 moduli custom. Se uno di essi e rotto, Home e fragile.
4. **Nessuna dipendenza circolare** rilevata nei manifest.
5. **Il flag `to upgrade` e a cascata**: se `casafolino_crm_export` e in `to upgrade`, tutti i moduli che ne dipendono (pipeline_control, crm_360, mail_stats, home) rischiano inconsistenza fino all'update.

---

## 6. INTEGRITA DATI

| Metrica | Valore |
|---------|--------|
| Lead totali | **502** |
| Lead attivi (`active=true`) | **498** |
| Lead archiviati (`active=false`) | **4** |
| Lead senza email nel chatter Odoo nativo | **441 (87,85%)** |
| Lead con almeno 1 email tracciata nel chatter | **61 (12,15%)** |

**Nota sull'87,85%:** La percentuale alta di lead senza email nel chatter Odoo standard (`mail_message`) e attesa — le email vengono gestite dal sistema custom `casafolino.mail.message` separato. Non indica perdita di dati: le email esistono nel sistema custom ma non sono linkate come `mail_message` sul record `crm.lead`. Per avere la vera metrica occorre interrogare la tabella `casafolino_mail_message`.

---

## 7. CRON ATTIVI

**Totale cron attivi: 93** (di cui ~36 custom CasaFolino)

**ATTENZIONE CRITICA:** I cron sono **tutti saltati** finche i 12 moduli in `to upgrade` non vengono processati. Il cron worker e attivo ma non esegue nulla su `folinofood`.

**Cron standard Odoo (selezione):**

| ID | Nome | Modello |
|----|------|---------|
| 1 | Base: Auto-vacuum internal data | ir.autovacuum |
| 3 | Mail: Email Queue Manager | mail.mail |
| 18 | Account: Post draft entries auto_post | account.move |
| 41 | CRM: enrich leads (IAP) | crm.lead |
| 63 | IT EDI: Receive invoices from SdI | account.move |

**Cron custom CasaFolino principali:**

| ID | Nome | Modello | Stato |
|----|------|---------|-------|
| 85 | CasaFolino Body Fetch Pending | casafolino.mail.message | OK (saltato per to_upgrade) |
| 99 | CasaFolino: Digest Mittenti Fuori-CRM | casafolino.mail.message | OK (saltato) |
| 110 | CasaFolino Triage RAW | casafolino.mail.raw | OK funzionante quando non saltato |
| 111 | CasaFolino Cleanup RAW | casafolino.mail.raw | OK |
| 117 | CasaFolino Cleanup Trash | casafolino.mail.message | OK |
| 118 | CasaFolino Cleanup Mass Action Logs | casafolino.mail.mass.action.log | OK |
| 119 | CasaFolino Send Scheduled Drafts | casafolino.mail.draft | OK |
| 123 | Mail Stats: Rebuild Engagement Cache | casafolino.mail.engagement | OK |
| 124 | Mail Stats: Auto-Activity Hot Leads | casafolino.mail.engagement | OK |
| 138 | CasaFolino — AI suggestion mail | casafolino.mail.message | OK |
| 141 | CF: Bonifica bank account archiviati | res.partner.bank | OK |
| 145 | Backfill mail partner 100818 (Claudia Perini) | — | **3550 failures — ZOMBIE** |
| 149 | CasaFolino Voice AI: process outbound | casafolino.voice.outbound.queue | OK |
| 53216 | CasaFolino Voice AI: Send Daily Recap | casafolino.voice.call | OK |
| 112-140+ | Dismiss cascade: [vari mittenti] | casafolino.mail.sender_preference | ~20 cron, alcuni con 2 failures |

---

## 8. GIT STATUS

**Repo Mac `/Users/antoniofolino/casafolino-os`:**

- Branch: `feature/sale-order-internal-print-no-prices`
- Tracking: `origin/feature/sale-order-internal-print-no-prices` (up to date)
- File non tracciati pre-analisi: `AUDIT_COMMERCIALE_2026-06-02.md`, `docs/.DS_Store`

```
On branch feature/sale-order-internal-print-no-prices
Your branch is up to date with 'origin/feature/sale-order-internal-print-no-prices'.

Untracked files:
  AUDIT_COMMERCIALE_2026-06-02.md
  docs/.DS_Store
  STATO_ARTE.md    ← aggiunto da questa analisi

nothing added to commit but untracked files present
```

**Ultimi 10 commit:**
```
f0c3e53 Add carton counts to internal sale print
0f04c67 Add internal sale order print without prices
e037f82 Add creme work centers
e3be1e6 Fix vendor bill six-decimal amounts
ed2f8b9 Fix treasury supplier expense line filter
82fef86 Add treasury turnover expense comparison
b912352 casafolino_cockpit: parallel OWL cockpit beta (Regia + Dossier, Sprint 1)
77d4b46 fix(initiative): corregge AttributeError in wizard._generate_tasks
2a0c677 Merge BLOCCO A - Staffetta multi-ruolo cf.initiative
9a2c942 fix(initiative-staffetta): bump version a 18.0.2.0.1 per saltare migration stale
```

**Worktrees attivi (6 branch con working tree locale separato):**
- `codex/all-fatturapa-xml-decimal-fix`
- `codex/commercial-redesign-odv-tax`
- `codex/crm-ripartenza`
- `codex/mail-retry-error-accounts`
- `codex/pipeline-mail-delete-ui`
- `codex/voice-bridge-giulia-direct`

---

## 9. VERDETTO

### Cosa funziona

- Odoo 18 Enterprise avviato e registry caricato correttamente
- `crm.lead.create` ORM funziona — nessun blocco sulla creazione base del lead
- Triage email RAW operativo quando i cron girano (85 promoted + 10 promoted oggi nei log di stamattina)
- Voice AI operativo (endpoint `/voice_ai/config` risponde 200)
- Tesoreria, HACCP prod, Initiative, Commercial — tutti installati e funzionanti
- Contabilita (fatture, SdI, pagamenti) — cron in lista ma saltati per il blocco `to upgrade`

### Cosa e rotto

1. **12 moduli in `to upgrade` bloccano TUTTI i 93 cron** — nessuna automazione gira finche non risolto
2. **Sala Controllo (`casafolino_pipeline_control`)** — crasha 5+ volte/ora con `KeyError: 'cf.ai.router'`
3. **Cron zombie id=145** — 3550 failures su partner Claudia Perini dal 18/05 — inutile continuare
4. **Attachment orfano `bd931059…`** — cercato 20 volte oggi, file assente dal filestore
5. **Tabelle transiente orfane** — `cf_raw_material_summary_wizard/line` referenziate da autovacuum ma non esistenti
6. **Campo obsoleto `numbercall`** — server action UI referenzia campo rimosso in Odoo 18

### MODULO DA DISATTIVARE per sbloccare CRM standard

**Nessuno da disattivare** — la create del lead standard funziona. Il CRM Odoo nativo e usabile.

Per sbloccare la Sala Controllo senza restart: patch `pipeline_control.py` riga 2406:
```python
# DA:
status = self.env['cf.ai.router'].provider_status()
# A:
router = self.env.get('cf.ai.router')
status = router.provider_status() if router else {'available': False, 'provider': None}
```

### Percorso minimo per CRM e automazioni pienamente operative

1. **Priorita 1 — Sblocca i 12 moduli `to upgrade`:**
   ```bash
   docker exec odoo-app odoo -d folinofood \
     --update=casafolino_crm_export,casafolino_pipeline_control,\
   casafolino_initiative_dashboard,casafolino_mail_stats,\
   casafolino_home,casafolino_workspace,casafolino_crm_360,\
   casafolino_cockpit,casafolino_sala_commerciale,\
   casafolino_b2b_portal,casafolino_b2b_theme,casafolino_mail_templates \
     --stop-after-init --no-http 2>&1 | tail -30
   docker restart odoo-app
   ```

2. **Priorita 2 — Fix pipeline_control** (patch `_safe_section` con `env.get`)

3. **Priorita 3 — Disattiva cron zombie id=145** (Claudia Perini backfill, 3550 failures)

4. **Priorita 4 — Cleanup filestore** — trovare attachment con sha `bd931059…` e nullificare il record orfano in `ir_attachment`

5. **Priorita 5 — Rimuovere server action** con campo `numbercall` obsoleto su `ir.cron`
