# DEPLOY — CasaFolino Operations (sistema task unico)

> Deliverable #2. Stato: **stage `folinofood_stage` + preview Vercel**. Prod `folinofood` NON ancora toccato (HARD GATE 1 pendente).

## Backend — modulo `cf_backoperation`

### Comandi eseguiti (Mac → EC2 → stage)
```bash
# Mac
cd /Users/antoniofolino/casafolino-os
git add -A && git commit -m "..." && git push origin main

# EC2 (51.44.170.55)
cd /home/ubuntu/casafolino-os && git pull
sudo cp -rf cf_backoperation /docker/enterprise18/addons/custom/
docker exec odoo-app odoo -d folinofood_stage -u cf_backoperation --stop-after-init --no-http
docker restart odoo-app
```

### Esito stage
- `Module cf_backoperation loaded` — `Registry loaded` OK, nessun ParseError.
- RPC verdi (smoke su odoo shell, poi rollback): `op_get_my_day`, `op_create_task`,
  `op_set_state`/`op_ack` (ack→`acknowledged_date`), `op_get_board`, `generate_today`
  (idempotente: GEN1=1, GEN2=0), `created_by`→`bo_assegnata_da_id` ("Antonio Folino").
- Isolamento viste verificato: `ISO_OK True` (board BackOp solo task bo-linked, Console solo ops/routine).

### Modello dati aggiunto
- `cf.task` (estensione, file `models/cf_task_ops.py`): `description`, `user_assigned_id`
  (res.users), `date_deadline`, `time_due`, `priority` (0/1/2/3), `acknowledged_date`,
  `category` (7 valori), `is_routine`, `template_id`, `task_date`, `ops_overdue` (computed),
  `ops_overdue_notified`. Stati: `selection_add` **taken**, **blocked** (additivi, non-breaking).
- `cf.task.template` (nuovo, `models/cf_task_template.py`): routine + `generate_today()` idempotente.
- Gruppo `cf_backoperation.group_ops_manager` (Console CEO).

### Cron creati (via ORM, MAI XML)
| id | cron_name | model | metodo | schedule | nextcall |
|----|-----------|-------|--------|----------|----------|
| 142 | `cf_task_routine_generate` | cf.task.template | `generate_today()` | 1 giorno | 2026-06-26 03:00 UTC (05:00 Rome) |
| 143 | `cf_task_overdue_notify` | cf.task | `_cron_ops_overdue_notify()` | 1 ora | 2026-06-25 07:00 UTC |

### Verifica viste impattate (per HARD GATE 1)
- **`console_access`**: nessuna vista su `cf.task` → **zero impatto UI**. Solo inheritance modello; stati additivi → nessun break funzionale.
- **`casafolino_task`** form/list base: dropdown stato ora elenca taken/blocked → **cosmetico**.
- **`cf_backoperation` `cf.task.bo.kanban`** (action "Task BackOperation"): era `group_by=state` senza dominio → potenziale crossover. **Isolato**: aggiunto dominio (solo task con `bo_titolare_id`/`bo_operatore_id`/`bo_production_id`/`bo_sale_order_id`). Console ops = dominio complementare (`user_assigned_id` set OR `is_routine`).
- **Da ri-verificare in UI su stage prima di prod** (gate): aprire viste Produzione/Console esistenti, confermare assenza colonne/filtri taken/blocked indesiderati LIVE.
- **Evidenza prod (read-only):** `folinofood` ha 4 record cf_task totali — `in_corso`(3) + `bozza`(1), **zero in taken/blocked**. `selection_add` e' additivo → nessun record retro-riempie i nuovi stati al deploy → nessuna colonna a sorpresa nelle viste prod. I nuovi stati appaiono solo quando gira il flusso ops. (Stage cf_task = 0 record.)

### Notifiche
- Eventi: (1) nuovo task assegnato (`op_create_task`→`_ops_notify_assigned`), (2) ritardo (`_cron_ops_overdue_notify`).
- Canali: `_cf_notify` esistente = **mail (`ir.mail_server`) + inapp**. Web-push (VAPID/SW/pywebpush) = **RIMANDATO** (transport): email/inapp coprono entrambi gli eventi nel frattempo.

## Frontend — PWA `casafolino-backoperation`
- Branch `main`, commit `b75938e`. Build locale: `✓ Compiled successfully`, `tsc --noEmit` pulito.
- Rinominata "CasaFolino Operations" (manifest + layout). Identita `EMAIL_TO_USER` (res.users), server-side.
- Tab default **La mia giornata** (`op_get_my_day`), FAB crea ad-hoc, **Console** (manager), **Produzione** (Board esistente, invariata, solo per operative con hr.employee).
- Offline: store IndexedDB separato `ops_actions` (v2) + replay idempotente `/api/ops/task`.
- Deploy: Vercel **preview** (NON prod) — URL in fondo.

## Config params (nomi, SENZA valori segreti)
- (futuro push) `casafolino.vapid_public_key`, `casafolino.vapid_private_key` — non ancora creati.
- `casafolino_task.notify_channels` (default `mail,inapp`).

## URL
- Preview PWA: _(in fase di deploy — vedi output)_
- Prod PWA: https://casafolino-backoperation.vercel.app (NON promosso)
- Odoo: erp.casafolino.com (porta 4589)

## DA VERIFICARE prima di prod (HARD GATE 1)
1. UI stage: viste Produzione/Console esistenti senza regressioni taken/blocked.
2. `EMAIL_TO_USER`: confermare uid/email reali res.users (specie Antonio manager).
3. Eventuale web-push (SLICE 4 transport) se richiesto prima del go-live.
