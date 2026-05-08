# Brief #FINAL — Scoping chiusura progetto

**Data:** 2026-05-08

## Modello campionature

- **Model**: `cf.export.sample` (NOT `cf.sample.request` — brief had wrong name)
- **Table**: `cf_export_sample`
- **Key fields**: `reference`, `lead_id` (m2o crm.lead), `partner_id` (related lead_id.partner_id), `state` (selection: draft/prepared/sent/received/feedback_ok/feedback_ko/no_feedback), `stage_id`, `product_ids` (m2m product.template), `date_sent`, `tracking_number`, `feedback_score`
- **Linked via**: `crm.lead.cf_sample_ids` (One2many)

## Volume dati

- Sale orders per partner con dossier: da verificare in prod (struttura presente)
- Samples: legati ai lead, non direttamente ai partner → query via lead_id→partner_id

## File wizard CSS warm bands

- **Template**: `casafolino_crm_export/static/src/xml/cf_wizard_new.xml`
- **CSS**: `casafolino_crm_export/static/src/css/wizard_new.css`
- **Classi target**: `.cf-wizard-warm-dialog` (contentClass su Dialog), `.cf-warm-band-light`, `.cf-warm-band-cream`
- **Issue**: Dialog OWL `contentClass` mette la classe su `.modal-body`, ma CSS selettori come `.cf-wizard-warm-dialog .modal-dialog` cercano `.modal-dialog` DENTRO `.modal-body` → non matchano. Le band funzionano (sono dentro modal-body), ma overrides modali (max-width, padding:0, hidden header/footer) non si applicano.

## F8 composer entry point

- **Component**: `ComposeWizardDialog` in `casafolino_mail/static/src/js/mail_v3/compose_wizard_dialog.js`
- **Usage**: `dialogService.add(ComposeWizardDialog, { partnerEmail, defaultSubject, onSent })`
- **Approccio**: aggiungere `useService("dialog")` al dashboard, importare ComposeWizardDialog, usare in onQuickReply

## Stato cf_project_id nel form lead

- **Modello**: `cf_project_id = fields.Many2one('project.project')` su `crm.lead` (line 179)
- **Form premium**: esposto indirettamente (button "Progetto 360°" invisible senza cf_project_id)
- **Form inherited** (`cf_crm_lead_view_form`): **NON esposto** — lacuna Brief #3
- **Fix**: aggiungere tab "Dossier" nella form inherited con cf_project_id

## cf_managed_by_ids

- Esiste su `res.partner` (Many2many) — **NON** su crm.lead
- Non esporre nella form lead (non applicabile)

## File da modificare per Fase 1-7

| Fase | File |
|------|------|
| 1 | `casafolino_crm_export/views/crm_lead_views.xml` |
| 2 | `casafolino_crm_export/models/project_project.py` |
| 3 | `casafolino_crm_export/static/src/project_dashboard/project_dashboard.js` + `project_dashboard.xml` |
| 4 | `casafolino_crm_export/models/project_project.py` + `project_dashboard.js` + `project_dashboard.xml` |
| 5 | `casafolino_crm_export/static/src/project_dashboard/project_dashboard.scss` |
| 6 | `casafolino_crm_export/static/src/css/wizard_new.css` |
| 7 | `casafolino_crm_export/static/src/project_dashboard/project_dashboard.js` |

## Blocker

Nessuno. Tutti i modelli e campi esistono. F8 composer esportabile via dialogService.
