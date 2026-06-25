# DISCOVERY — CasaFolino Operations (sistema task unico)

> SLICE 0, read-only. Deliverable #1 del brief GSD. Nessuna modifica eseguita.
> Data: 2026-06-25.

## 1. Dove vive `cf.task`

| Cosa | Dove |
|---|---|
| Modello base `cf.task` | `casafolino_task/models/cf_task.py` (modulo **CasaFolino Task Engine**) |
| Estensione PWA reparto | `cf_backoperation/models/cf_task_bo.py` (`_inherit = 'cf.task'`) |
| Altri inheritor | `casafolino_console_access` (cf.task), `casafolino_campionatura` (cf.task.step), `cf_backoperation/bo_orders.py`, `bo_report.py` |

### Modello dati attuale `cf.task` (base)
Eredita `mail.thread` + `mail.activity.mixin` ✅ (chatter/allegati/activity nativi — NON reinventare).

| Campo | Tipo | Note |
|---|---|---|
| `name` | Char req | titolo |
| `template_key` | Char | chiave per wizard futuri (non usata) |
| `originator_id` | m2o res.users | creatore (default user) |
| `partner_id` / `lead_id` | m2o | contatto / opportunità |
| `company_id` | m2o res.company | |
| `state` | Selection | **`bozza` / `in_corso` / `chiuso` / `annullato`** |
| `parallel` | bool | step paralleli vs handoff |
| `step_ids` | o2m cf.task.step | motore multi-ruolo (handoff, semaforo) |
| `current_step_id` / `traffic_light` | computed | semaforo verde/giallo/rosso |

**`cf.task` base è un motore multi-STEP/multi-RUOLO** (handoff fra ruoli via `cf.task.step`, timer su ore lavorative, semaforo, escalation cron `_cron_escalation_check`). Il brief vuole il caso "task generico a responsabile UNICO" → si aggiunge una *lente piatta* sopra lo stesso modello, senza usare gli step.

### Notifiche già presenti (riusare!)
`cf.task._cf_notify(user, event, ctx)` con canali `mail` (mail.mail via `ir.mail_server`, **mai smtplib**) + `inapp` (message_post). Parametro `casafolino_task.notify_channels`. → il fallback email del brief §8 **esiste già**: aggiungo solo il canale push come `_cf_notify_push`.

### Estensione `cf_backoperation` (già in prod)
13 campi `bo_*`: `bo_kind` (produzione/campionatura/ordine/generico), `bo_titolare_id`/`bo_operatore_id` (**hr.employee**, per firma audit), `bo_production_id`, `bo_sale_order_id`, `bo_checkin_at`/`bo_checkout_at`/`bo_worked_seconds`, `bo_firmata`/`bo_firma_*`, `bo_phase_ids`. Mappa stati: `bozza`=da_fare, `in_corso`=wip, `chiuso`=done. RPC esistenti: `bo_get_board`, `bo_action_claim/checkin/checkout/sign/close`, `bo_claim_production`, `bo_phase_*`.

## 2. Campi mancanti per il caso generico (da aggiungere)

Riuso dove possibile. Mancano:
- `description` (Text)
- `user_assigned_id` (m2o **res.users**) — responsabile UNICO *(base ha solo `originator_id`=creatore e gli assegnatari sono sugli step)*
- `date_deadline` (Datetime)
- `time_due` (Char "11:00")
- `priority` (Selection 0/1/2/3) — **assente nel base** (`traffic_light` è altra cosa, computed)
- `acknowledged_date` (Datetime)
- `category` (Selection: produzione/qualita/logistica/commerciale/fiera/admin/ecom)
- `is_routine` (bool), `template_id` (m2o cf.task.template), `task_date` (Date, chiave idempotenza)
- Stati `taken` + `blocked`: **NON presenti**. Vedi §4.

`created_uid` è nativo Odoo → non serve aggiungerlo.

## 3. Identità utente — DECISIONE

Confermata raccomandazione brief: **`res.users` per assegnazione + login PWA; `hr.employee` solo dove serve firma audit** (riusa `bo_operatore_id`).

**Motivo:** il sistema task deve indirizzare *tutto* il personale (Antonio, Martina, Josefina, Anna ufficio…), non solo le 4 operative reparto. Solo le 4 operative hanno oggi un `hr.employee` mappato nella PWA; gli altri esistono come `res.users`. Inoltre push/notifiche e permessi sono naturali su `res.users`.

**Caveat critico — i due mondi NON coincidono per id:**

| Persona | res.users (CRM) | hr.employee (BackOp) |
|---|---|---|
| Maria | 9 | 9 *(coincidenza)* |
| Teresa | 11 | 6 |
| Anna | 22 | 3 |
| Valentina | 23 | 10 |
| Josefina | 6 | — |
| Martina | 8 | — |

→ Serve una **mappa `email → res.users`** server-side nella PWA (analoga a `EMAIL_TO_EMPLOYEE` in `src/lib/operatives.ts`), mai dai `user_metadata` client (rischio impersonificazione). La firma audit resta su `hr.employee` solo per i task produzione che la richiedono.

## 4. Stati — DECISIONE (non-breaking)

Brief vuole: `new → taken → in_progress → blocked → done / cancelled`.
Base ha: `bozza / in_corso / chiuso / annullato`, e **3 moduli leggono queste stringhe** (cf_backoperation, console_access).

**Scelta conservativa:** NON rinominare. Mappare ai valori esistenti e aggiungere SOLO i due mancanti via `selection_add` nell'estensione:

| Brief | Implementazione |
|---|---|
| new | `bozza` (esistente) |
| taken | **`taken`** (selection_add) + setta `acknowledged_date` |
| in_progress | `in_corso` (esistente) |
| blocked | **`blocked`** (selection_add) |
| done | `chiuso` (esistente) |
| cancelled | `annullato` (esistente) |

`selection_add=[('taken',...),('blocked',...)]` con `ondelete` mappato a valori sicuri. Zero impatto sui record/flussi esistenti (nessun record viene forzato nei nuovi stati).

## 5. Piano di innesto PWA (`casafolino-backoperation`)

Stack: Next.js 14 + TS + Supabase SSR, deploy Vercel `casafolino/casafolino-backoperation`. Architettura: login Supabase → route `/api/*` server-side → service account Odoo (`ODOO_API_USER`/`ODOO_API_TOKEN` env = `backoperation_service` uid 26) → JSON-RPC `cf.task`.

- **Client RPC:** `src/lib/odoo.ts` (`callMethod`, `searchRead`) — SERVER-ONLY, token mai client. Riuso identico.
- **Identità:** `src/lib/operatives.ts` (`EMAIL_TO_EMPLOYEE`). Aggiungo `EMAIL_TO_USER` (res.users) per il sistema task.
- **API pattern:** route in `src/app/api/<x>/route.ts`, `getSessionUser()` da `src/lib/supabase/server`, employee/uid SEMPRE server-side.
- **Offline:** coda IndexedDB + replay idempotente (`src/lib/sync.ts`, `db.ts`) — riuso per le azioni task.
- **Shell:** `src/components` + `src/app`. Tab esistenti (Produzione/Ordini/Campionature/Giornata) **invariate**. Aggiungo tab **"La mia giornata"** (default), FAB crea ad-hoc, **Console CEO** (role-scoped).
- **PWA meta:** `public/manifest.json` (oggi name "CasaFolino BackOperation", theme `#5A6E3A`) → rinomino a "CasaFolino Operations". Service worker `public/sw.js` esistente → estendo per web push.

**Innesto senza toccare il gate go-live Produzione:** la nuova superficie task è additiva (nuove route `/api/ops/*`, nuovi componenti). Non tocca `src/lib/bo.ts`/`order.ts` né il flusso MO. Il blocco service_role Supabase (creazione account) resta indipendente.

## 6. Collisione naming — ATTENZIONE

Esiste già il modulo backend **`casafolino_operations`** (`name='CasaFolino Operations'`, scope: Produzione CF + Mock Recall). Il menu root del brief §5.4 "CasaFolino Operations" **NON deve** finire in quel modulo. Il nuovo backend task vive in **`cf_backoperation`** (estensione cf.task già lì) o in un nuovo `casafolino_ops_task`. Decisione conservativa: **estendere `cf_backoperation`** (stessa lente, stesso service account, zero nuovo modulo) e nominare il menu root backend per evitare collisione (es. "Operations · Task" o riusare il root BackOperation). La PWA può chiamarsi "CasaFolino Operations" senza conflitto (è un altro repo/prodotto).

## 7. Cron & convenzioni

- Cron **via UI/ORM, MAI XML** (ParseError noto Odoo 18: niente `model_id ref=` in `<record ir.cron>`). Pattern esistente: cron creati via ORM (es. report 18:00 BackOp, escalation `_cron_escalation_check`).
- Da creare (SLICE 1/8): `cf_task_routine_generate` (model `cf.task.template`, `generate_today`, daily ~05:00 Europe/Rome) e `cf_task_overdue_notify` (push ritardi, idempotente).
- Menu root con `web_icon="MODULO,static/description/icon.png"` (icona placeholder se manca).

## 8. Deploy target

- Backend: Mac `casafolino-os` (branch `main`) → git push → EC2 `51.44.170.55` git pull + `sudo cp -rf cf_backoperation /docker/enterprise18/addons/custom/` → update **`folinofood_stage`** prima → `docker restart odoo-app`. Prod `folinofood` solo dopo HARD GATE 1 + pg_dump.
- Frontend: branch dedicato → Vercel preview URL, NON promosso a prod fino al gate.

## 9. Gap / rimandati a Fase 2
Voce→task (Groq) — solo hook `op_create_task` predisposto, niente UI voce. Riscrittura MO. Scanner biglietti. Dipendenze tra task. Write-back MRP.
