# CasaFolino OS — Home Dashboard v1

## Architettura
- Menu 'Casa' è l'unica icona principale post-login (sequence=1)
- Apre Scrivania Commerciale di default (action_id su uid 2/6/8)
- 3 cluster cliccabili in alto: Commerciale | Operativa | Admin

## Componenti

| Componente | Tipo | Descrizione |
|---|---|---|
| `cf.home.kpi` | AbstractModel | 4 endpoint KPI con fallback |
| `CFScrivaniaCommerciale` | OWL Component | Blu, KPI mail/lead/progetti |
| `CFScrivaniaOperativa` | OWL Component | Verde, KPI lotti/HACCP |
| `CFScrivaniaAdmin` | OWL Component | Ambra, KPI banche/fatture |

## Quick Actions per scrivania

### Commerciale
1. **Nuovo Progetto** (primary blu) — punto di partenza flusso CRM
2. Nuovo Lead
3. Nuovo Contatto
4. Posizionatore (con counter live)
5. Mia Casella

### Operativa
1. **Nuovo Lotto** (primary verde) — tracciabilità
2. Nuova Produzione
3. HACCP
4. Etichette
5. Fornitori

### Admin
1. **Nuova Fattura** (primary ambra) — fatturazione attiva
2. Mov. Banca
3. Documenti
4. Calendario
5. Nuova Fiera

## KPI per scrivania

### Commerciale (6)
- Mail da smistare (count casafolino.mail.message cf_project_id=NULL)
- Lead aperti (count crm.lead active probability<100)
- Lead caldi (probability >= 70%)
- Progetti attivi (count project.project cf_status_dossier!=NULL)
- SLA scadenza (mail tracked > 48h)
- Fatturato mese (sum out_invoice posted)

### Operativa (5)
- Lotti attivi (count stock.lot)
- HACCP scadenze < 7gg (cf.haccp.reminder)
- NC aperte (cf.haccp.nc)
- Produzioni attive (cf.production.job)
- Lotti in scadenza < 30gg

### Admin (5)
- Cassa Qonto (journal 6 balance)
- Cassa Revolut (journal 13 balance)
- Cassa BCC (journal 22 balance)
- Fatture aperte (out_invoice not_paid/partial)
- Prossima fiera (cf.export.fair o calendar.event)

## Menu Odoo nascosti (Phase 5)

21 voci nascoste via `active=FALSE`:
Helpdesk, Live Chat, WhatsApp, IoT, Knowledge, Email Marketing,
Social Marketing, Marketing Automation, Survey, Website, eCommerce,
Forum, Slides, Events, Live Events, Link Tracker, Shop Floor,
Barcode, Payroll, Point of Sale, Tests, Discuss, To-do,
Appointments, Employees, Dashboards, Quality, Apps, Calendar, Documents.

31 menu rimasti visibili (Casa + moduli CasaFolino + core Odoo).

## Fallback graceful
Ogni KPI ha try/except. Se modulo target non installato o errore → mostra '—'.
Ogni quick action ha try/catch. Se action XML non trovata → fallback inline.

## Per ripristinare i menu nascosti
```sql
UPDATE ir_ui_menu SET active = TRUE
WHERE parent_id IS NULL AND active = FALSE;
```

## Pattern OWL18 confermati
0 match per: useService("user"), this.user., t-on-X="this."

## KPI snapshot al deploy (2026-05-08)
- commerciale: mail=311, lead=16, fatturato=€16k
- operativa: lotti=1036, nc=0
- admin: Revolut=€246k, BCC=€10k, fatture=750
