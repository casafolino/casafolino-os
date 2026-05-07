# casafolino_crm_export — TODO Backlog

## Brief #4.5 — Wizard "Nuovo Lead" — Completamenti pendenti

### CSS warm bands rendering
- File: `static/src/css/wizard_new.css`
- Issue: Odoo CSS variables `var(--color-*)` may not resolve in all contexts
- Stato: diagnosed in Brief #4.4.1 Phase C
- Da fare: verify CSS variable cascading in prod, add fallback values if needed
- Effort stimato: 30min

## Brief #5.1 — Vista progetto 360° iterazione 1

### Sezione Commerciale
- Tab "Commerciale" sostituisce notification con UI reale
- Mostra: lista quote/sale.order, listini condivisi, MOQ accordati
- File: project_dashboard.js / project_dashboard.xml
- Effort stimato: 1.5h Code

### Sezione Campionature
- Tab "Campionature" mostra lista cf.export.sample del partner
- Filtro per stato (in attesa, inviato, consegnato, feedback positivo/negativo)
- Effort stimato: 1h Code

## Brief #5.2 — Vista progetto 360° iterazione 2

### Sezione Documenti
- Schede tecniche, certificazioni, contratti, NDA
- Upload + filter
- Effort: 2h Code

### Note interne strategy
- Textarea collaborativo con menzioni
- Effort: 1h Code

## Brief #6 / B6 — Mail timeline integration
- Tab "Mail" carica thread email organizzato dal modulo casafolino_mail
- Effort: dipende da Brief #6

## Brief #8 — Composer mail
- Quick action "Email" nella dashboard 360° attiva il composer
- Attualmente notification placeholder
- Effort: dipende da casafolino_mail integration
