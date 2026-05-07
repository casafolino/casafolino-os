# Dashboard 360° — Smoke Test Checklist

**Brief:** #5.0
**Data:** 2026-05-07
**Prerequisito:** CTRL+SHIFT+R per svuotare cache browser

## Prerequisito DB

Servono almeno 1 `project.project` con `cf_status_dossier` valorizzato e almeno 1 `crm.lead` con `cf_project_id` che punta a quel progetto.

Se non esistono:
```
ERP → Progetto → Crea nuovo progetto → tab "Dossier commerciale" → imposta Status = "Attivo"
ERP → Export CRM → Apri un lead → tab "Dettagli" o sidebar → campo "Dossier / Progetto" → seleziona il progetto
```

---

## Path 1: Da lead form → bottone "Progetto 360°"

### Step 1 — Apri lead con progetto collegato
- [ ] Vai a Export CRM → Tutte le Pipeline
- [ ] Click su una card kanban per aprire la form lead
- [ ] Verifica: bottone "Progetto 360°" visibile nella header (solo se cf_project_id valorizzato)
- [ ] Se non visibile: verifica che il lead abbia un progetto collegato

### Step 2 — Apri dashboard
- [ ] Click "Progetto 360°"
- [ ] Verifica: la dashboard 360° si carica (no spinner infinito)
- [ ] DevTools Console (F12): nessun errore JS rosso

### Step 3 — Verifica header
- [ ] Nome progetto visibile in alto
- [ ] Pill status (Esplorativo/Attivo/etc.) colorata
- [ ] Avatar operatore con iniziali + bordo colorato
- [ ] Nome partner con bandiera emoji
- [ ] Location (città, paese)
- [ ] Nome lead cliccabile
- [ ] Stage progress: 9 segmenti, quelli completati in verde

### Step 4 — Verifica KPI rail
- [ ] 4 card KPI visibili: Ricavi, Campioni, Email, Prossima
- [ ] Valori popolati (non tutti zero — dipende dai dati)

### Step 5 — Verifica tabs
- [ ] Tab "Timeline" attiva di default
- [ ] Click "Cliente" → mostra panel cliente
- [ ] Click "Commerciale" → notification "Brief #5.1"
- [ ] Click "Campionature" → notification "Brief #5.1"
- [ ] Click "Documenti" → notification "Brief #5.2"
- [ ] Click "Mail" → notification "B6"

### Step 6 — Verifica timeline
- [ ] Eventi visibili (se ci sono mail/attività collegate)
- [ ] Filtri "Tutti", "Email", "Attività", "Note" funzionano
- [ ] Icone colorate per tipo
- [ ] Date relative ("3gg fa", "2h fa", etc.)

### Step 7 — Verifica customer panel
- [ ] Card "Cliente" con nome, email, telefono, sito, location
- [ ] Card "Contatti" con lista contatti figli (se esistono)
- [ ] Click su contatto → apre form res.partner
- [ ] Card "Lead principale" con stage, revenue, probabilità, score, giorni in fase

### Step 8 — Verifica quick actions
- [ ] "Email" → notification "Brief #8"
- [ ] "Campione" → apre form nuova campionatura
- [ ] "Offerta" → apre form sale.order con partner precompilato
- [ ] "Attività" → apre form mail.activity

### Step 9 — Verifica navigazione
- [ ] Click freccia back (←) → torna a pipeline kanban
- [ ] Click nome partner → apre form partner
- [ ] Click nome lead → apre form lead
- [ ] Click refresh (↻) → ricarica dati

---

## Path 2: Da inherited lead form (CRM nativo)

### Step 1 — Apri lead dal CRM standard
- [ ] Menu CRM → My Pipeline → click lead con progetto collegato
- [ ] Verifica: stat button "360°" visibile nel button_box
- [ ] Click "360°" → dashboard si carica come Path 1

---

## Path 3: Da menu "Progetti 360°"

### Step 1 — Apri lista progetti
- [ ] Menu Export CRM → Progetti 360°
- [ ] Verifica: lista progetti con cf_status_dossier filtrato
- [ ] Click su un progetto → apre form standard del progetto (non la dashboard — la dashboard si apre solo da lead)

---

## Responsive (opzionale)

- [ ] Riduci finestra browser a < 900px larghezza
- [ ] Customer panel collassa sotto la timeline
- [ ] Quick actions si dispongono 2x2
- [ ] KPI rail rimane scrollabile orizzontalmente
