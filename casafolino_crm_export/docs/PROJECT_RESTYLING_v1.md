# CasaFolino OS — Project restyling v1

**Status:** COMPLETATO
**Last updated:** 2026-05-08

## Roadmap eseguita

| # | Cosa | Stato |
|---|---|---|
| #1 | Pipeline kanban arricchita (9 stage progress, badge, avatar) | done |
| #2 | List view con metric strip + 4 widget OWL | done |
| #3 | Modello dati (cf_partner_role, cf_managed_by, cf_status_dossier, cf_project_id) | done |
| #4 | Wizard "Nuovo lead da biglietto" con AI Groq | done |
| #4.4.1 | Chiusura debt wizard (CONTRACT.md, audit handler, CSS fallbacks) | done |
| #4.4.2 | Hotfix user OWL18 (`import { user }` non `useService`) | done |
| #5.0 | Dashboard 360° MVP (Header, KPI, Timeline, Cliente, Quick actions) | done |
| #6.0 | Demolizione mirata casafolino_mail (sender_policy, triage, fetch_totale) | done |
| #6.1 | Riorientamento ingestion (mail_tracked, fetch+match, body lazy) | done |
| #6.2 | UI Posizionatore mail (3 dinamiche AI confidence) | done |
| #6.3 | AI feedback loop (accuracy per partner, threshold dinamico) | done |
| #6.4 | F8 + AI assist panel (tono, lingua, firma, risposte) | done |
| #6.5 | Inbox selector "vedo come Josefina/Martina" | done |
| #6.6 | Test prod + migrazione modulo mail | done |
| #B6 | Tab Mail dashboard 360° (popolazione) | done |
| #FINAL | Sezioni Commerciale/Campionature/Documenti/Note + 3 mini-fix | done |

## Architettura finale

### Moduli principali
- `casafolino_crm_export` — pipeline + wizard + dashboard 360°
- `casafolino_mail` — ingestion + posizionatore + AI + F8 + multi-casella

### Documenti di riferimento
- `casafolino_crm_export/static/src/project_dashboard/CONTRACT_DASHBOARD.md`
- `casafolino_crm_export/static/src/CONTRACT_WIZARD.md`
- `casafolino_mail/CONTRACT_MAIL.md`
- `casafolino_mail/docs/MAIL_MODULE_v6.md`

### Pattern OWL18 obbligatori per future modifiche
- `import { user } from "@web/core/user"` (mai `useService("user")`)
- `t-on-click="onClick"` (mai `"this.onClick"`)
- `<list>` (mai `<tree>`)
- `invisible="..."` (mai `attrs=`)
- `class="x y"` (mai duplicato)
- `var(--x, #fallback)` sempre con fallback

## cf_get_dashboard_data — schema finale (13 keys)

```
{
  project, lead, partner, kpi         — Brief #5.0
  timeline, contacts, owner           — Brief #5.0
  mail, mail_count                    — Brief #B6
  commerciale, campionature           — Brief #FINAL
  documenti, note                     — Brief #FINAL
}
```

## Stato post-deployment

### Setup richiesto Antonio (one-time, 15 min)
1. Crea cron AI suggestion (ogni 5 min): `model._cron_run_ai_suggestion()`
2. Crea cron Accuracy refresh (ogni 24h): `model._cron_refresh_ai_accuracy()`
3. Smoke test reale: linka cf_project_id su un lead -> apri dashboard 360° -> verifica tutte le tab

### Backlog noto (non bloccante)
- Vedere TODO.md di entrambi i moduli per micro-fix futuri
- Eventuale evoluzione AI structured output (Brief #4.5)
- Manuale utente per Josefina/Martina

## Metriche finali

- **Brief eseguiti:** 16 (Brief #1..#FINAL)
- **Modelli aggiunti:** cf.partner.role, cf.mail.position.feedback, cf.mail.compose.ai + estensioni
- **Componenti OWL nuovi:** 5 (Wizard, Dashboard, Posizionatore, ComposeAIPanel, InboxSelector)

## Per chi prenderà in mano il sistema

1. Leggi i 4 CONTRACT_*.md sopra
2. Rispetta la tabella pattern OWL18
3. Per ogni nuovo brief che modifica un componente: leggi il suo CONTRACT prima
4. Backup PROD obbligatorio prima di ogni `-u` distruttivo
5. Validator XML pre-commit: `python3 -c "import xml.etree.ElementTree as ET; ET.parse('<file>')"`
