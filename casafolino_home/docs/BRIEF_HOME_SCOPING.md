# Brief #HOME — Scoping 3 Scrivanie

## Decisione modulo

**Nuovo modulo `casafolino_home`** (NON estensione workspace).

Motivo: `casafolino_workspace` è monolitico SPA-like con navigazione interna
(state.page), controller custom `/workspace/dashboard/data`, 11 sub-component.
Non fork-friendly per 3 client action separate.

## Menu Odoo standard da nascondere (active=FALSE)

Target: Helpdesk, Live Chat, WhatsApp, IoT, Knowledge, Email Marketing,
Social Marketing, Marketing Automation, Survey, Website, eCommerce,
Forum, Slides, Events, Live Events.

Approccio: `UPDATE ir_ui_menu SET active = FALSE` — reversibile, nessun modulo disinstallato.

## Endpoint KPI riusabili

| Endpoint | Modulo | Modello |
|---|---|---|
| `cf_get_dashboard_data` | casafolino_crm_export | project.project |
| `cf_get_pending_summary` | casafolino_mail | casafolino.mail.message |

## Modelli target per KPI

| KPI | Modello | Campo chiave |
|---|---|---|
| Mail pending | casafolino.mail.message | cf_project_id = False |
| Lead aperti | crm.lead | type=lead, active=True |
| Progetti attivi | project.project | cf_status_dossier != False |
| HACCP scadenze | cf.haccp.reminder | (da verificare) |
| Lotti | stock.lot | expiration_date |
| Mock recall | cf.recall.session | reference, date |
| Fiere | cf.export.fair | (da verificare) |
| Banche | account.journal | id 6=Qonto, 13=Revolut, 22=BCC |

## File da creare

### Phase 1 — Backend
- `casafolino_home/models/__init__.py`
- `casafolino_home/models/cf_home_kpi.py`
- `casafolino_home/security/ir.model.access.csv`

### Phase 2 — Scrivania Commerciale
- `casafolino_home/static/src/scrivania_commerciale/scrivania_commerciale.js`
- `casafolino_home/static/src/scrivania_commerciale/scrivania_commerciale.xml`
- `casafolino_home/static/src/scrivania_commerciale/scrivania_commerciale.scss`

### Phase 3 — Scrivania Operativa + Admin
- `casafolino_home/static/src/scrivania_operativa/scrivania_operativa.js`
- `casafolino_home/static/src/scrivania_operativa/scrivania_operativa.xml`
- `casafolino_home/static/src/scrivania_admin/scrivania_admin.js`
- `casafolino_home/static/src/scrivania_admin/scrivania_admin.xml`

### Phase 4 — Actions + Menu
- `casafolino_home/views/home_actions.xml`
- Update `__init__.py` + `__manifest__.py`

### Phase 5 — Cleanup menu (SQL on server)

Menu da nascondere (active=FALSE, 15 voci):
- Helpdesk, Live Chat, WhatsApp, IoT, Knowledge
- Email Marketing, Social Marketing, Marketing Automation
- Survey, Website, eCommerce, Forum, Slides, Events, Live Events

SQL:
```sql
UPDATE ir_ui_menu SET active = FALSE
WHERE parent_id IS NULL
  AND name IN ('Helpdesk','Live Chat','WhatsApp','IoT','Knowledge',
               'Email Marketing','Social Marketing','Marketing Automation',
               'Survey','Website','eCommerce','Forum','Slides','Events','Live Events');
```

Menu rimasti visibili post-cleanup (stima):
- Casa (nuovo), Mail CRM, Export CRM, HACCP, Operazioni, Etichette,
  Contatti, Contabilità, Inventario, Vendite, Acquisti, Progetti, CRM,
  Calendario, Impostazioni

### Phase 6 — Deploy + smoke
### Phase 7 — Documentation

## Action XML IDs riusabili

| Action | XML ID |
|---|---|
| Posizionatore | casafolino_mail.action_cf_mail_posizionatore |
| Mia Casella | casafolino_mail.action_casafolino_mail_my_mailbox |
| Pipeline Lead | casafolino_crm_export.action_cf_crm_all |
| Progetti/Dossier | casafolino_crm_export.action_cf_project_dossier |
| Lavagna | casafolino_initiative_dashboard.action_lavagna_template |
| HACCP Dashboard | casafolino_haccp.action_cf_haccp_dashboard |
| Produzione | casafolino_operations.action_cf_production_jobs |
| Mock Recall | casafolino_operations.action_cf_recall_sessions |
| Etichette | casafolino_labels.action_cf_label_kanban |
| Fiere | casafolino_crm_export.action_cf_fair |
| Campioni | casafolino_crm_export.action_cf_sample |
