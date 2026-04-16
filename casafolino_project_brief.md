# BRIEF TECNICO — Modulo `casafolino_project`

## CasaFolino OS — Odoo 18 Enterprise

**Versione:** 1.0
**Data:** 13 aprile 2026
**Autore:** Antonio Folino / Claude
**Destinatario:** Claude Code (sviluppo autonomo)

---

## 1. OBIETTIVO

Creare un modulo Odoo 18 che **estende** il modulo nativo `project` (NON lo sostituisce) aggiungendo funzionalità specifiche per i flussi operativi di CasaFolino: gestione campionature, etichette personalizzate, fiere, lanci prodotto e progetti strategici.

Il modulo deve essere **semplice da usare** per utenti non tecnici (Martina, Anna, Teresa) e dare una **visione immediata** di tutti i progetti attivi con semaforo, avanzamento e blocchi.

---

## 2. INFRASTRUTTURA E REGOLE

### 2.1 Stack

| Componente | Valore |
|---|---|
| Server | EC2 `51.44.170.55:4589` |
| Container | `odoo-app` + `odoo-db` (postgres:15) |
| DB Produzione | `folinofood` |
| DB Staging | `folinofood_stage` |
| GitHub | `github.com/casafolino/casafolino-os` |
| Path addons host | `/docker/enterprise18/addons/custom/` |
| Path repo server | `/home/ubuntu/casafolino-os/` |

### 2.2 Regole Odoo 18 OBBLIGATORIE

- **NO `attrs=`** → usare `invisible=` direttamente
- **NO `tree`** → usare `list`
- **NO `model_id ref=`** nei cron XML
- **Kanban**: usare `t-name="card"` NON `t-name="kanban-box"`
- **OWL components**: `static props = ["*"]` NON `static props = {}`
- **Root menuitem**: deve avere `web_icon="casafolino_project,static/description/icon.png"`
- **Actions prima delle view** nel file XML
- **Menuitem dopo act_window**
- **Priority view**: impostare `priority` a 99 per override sicuro
- **Bottoni in page**: usare `<div class="o_row">` NON `<header>`
- **Notebook**: usare `<xpath expr="//notebook" position="inside">`
- **Modelli `_inherit`**: NON vanno in `ir.model.access.csv`

### 2.3 Deploy

```bash
# Da Mac: git push
# Da EC2:
cd /home/ubuntu/casafolino-os && git pull && \
sudo cp -rf casafolino_project /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d folinofood -u casafolino_project --stop-after-init --no-http 2>&1 | tail -20 && \
docker restart odoo-app
```

---

## 3. DIPENDENZE

```python
'depends': [
    'project',          # modulo nativo Odoo
    'mail',             # chatter e email
    'casafolino_mail',  # CasaFolino Mail Hub (email IMAP importate)
],
```

**NON dipendere da**: `casafolino_crm_export`, `casafolino_commercial`, o altri moduli CasaFolino (usare soft-link opzionali dove serve).

---

## 4. STRUTTURA FILE

```
casafolino_project/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── cf_project.py              # Estensione project.project
│   ├── cf_project_task.py         # Estensione project.task
│   ├── cf_project_template.py     # Template progetto + task template
│   ├── cf_project_shipment.py     # Tracking spedizione campioni
│   └── cf_project_checklist.py    # Checklist obbligatoria per stage
├── views/
│   ├── cf_project_views.xml       # Viste progetto estese
│   ├── cf_project_task_views.xml  # Viste task estese
│   ├── cf_project_kanban.xml      # Kanban progetto con semaforo
│   ├── cf_project_dashboard.xml   # Dashboard portfolio
│   ├── cf_project_template_views.xml
│   ├── cf_project_shipment_views.xml
│   ├── cf_project_checklist_views.xml
│   └── cf_project_menus.xml       # Menu e azioni
├── security/
│   ├── ir.model.access.csv
│   └── cf_project_security.xml    # Gruppi (manager / user)
├── data/
│   ├── cf_project_template_data.xml  # Template pre-configurati
│   └── cf_project_stage_data.xml     # Stage task per tipo progetto
├── static/
│   └── description/
│       └── icon.png
└── README.md
```

---

## 5. MODELLI

### 5.1 `project.project` (estensione — `_inherit`)

```python
class CfProject(models.Model):
    _inherit = 'project.project'

    # === TIPO PROGETTO ===
    cf_project_type = fields.Selection([
        ('sample_fair', 'Campionatura Fiera'),
        ('sample_client', 'Campionatura Cliente'),
        ('custom_label', 'Etichetta Personalizzata'),
        ('new_product', 'Lancio Nuovo Prodotto'),
        ('fair_prep', 'Preparazione Fiera'),
        ('strategic', 'Progetto Strategico'),
    ], string="Tipo Progetto", tracking=True)

    # === PARTNER COLLEGATO ===
    cf_partner_id = fields.Many2one(
        'res.partner', string="Cliente/Partner",
        tracking=True, index=True,
    )
    cf_partner_country_id = fields.Many2one(
        related='cf_partner_id.country_id', string="Paese", store=True)
    cf_partner_email = fields.Char(
        related='cf_partner_id.email', string="Email Partner")

    # === DEADLINE E SEMAFORO ===
    cf_target_date = fields.Date(
        string="Data Target", tracking=True,
        help="Deadline finale del progetto (es. data fiera, data consegna)")
    cf_traffic_light = fields.Selection([
        ('green', 'In Linea'),
        ('yellow', 'Attenzione'),
        ('red', 'Critico'),
    ], string="Stato", compute='_compute_traffic_light', store=True)

    # === AVANZAMENTO ===
    cf_progress = fields.Float(
        string="Avanzamento %",
        compute='_compute_progress', store=True,
    )
    cf_tasks_total = fields.Integer(compute='_compute_progress', store=True)
    cf_tasks_done = fields.Integer(compute='_compute_progress', store=True)
    cf_tasks_blocked = fields.Integer(compute='_compute_progress', store=True)

    # === WAITING FOR (aggregato) ===
    cf_main_blocker = fields.Selection([
        ('none', 'Nessun blocco'),
        ('client', 'Cliente'),
        ('graphic', 'Grafico'),
        ('printer', 'Tipografia'),
        ('production', 'Produzione'),
        ('internal', 'Interno'),
        ('supplier', 'Fornitore'),
    ], string="Bloccato da", compute='_compute_main_blocker', store=True)

    # === FIERA PARENT ===
    cf_parent_project_id = fields.Many2one(
        'project.project', string="Progetto Padre (Fiera)",
        domain="[('cf_project_type', '=', 'fair_prep')]",
    )
    cf_child_project_ids = fields.One2many(
        'project.project', 'cf_parent_project_id',
        string="Sotto-progetti",
    )
    cf_child_count = fields.Integer(
        compute='_compute_child_count', string="N. Sotto-progetti")

    # === EMAIL COLLEGATE (dal Mail Hub) ===
    cf_email_count = fields.Integer(
        compute='_compute_email_count', string="Email")

    # === CONTATORE GIORNI ===
    cf_days_open = fields.Integer(
        compute='_compute_days_open', string="Giorni Aperti")

    # === TEMPLATE ===
    cf_template_id = fields.Many2one(
        'cf.project.template', string="Creato da Template")
```

**Metodi compute principali:**

- `_compute_traffic_light`: verde se tutte le task sono in tempo, giallo se almeno una task ha deadline < 3 giorni, rosso se almeno una task è in ritardo o il progetto supera `cf_target_date`
- `_compute_progress`: `tasks_done / tasks_total * 100`. Conta solo task di primo livello (no subtask)
- `_compute_main_blocker`: prende il `cf_waiting_for` più frequente tra le task non completate
- `_compute_email_count`: conta `casafolino_mail.message` dove il partner corrisponde a `cf_partner_id`
- `_compute_days_open`: `(today - create_date).days`

**Metodo `create` override:** se `cf_template_id` è valorizzato, genera automaticamente le task dal template con date relative a `cf_target_date`.

### 5.2 `project.task` (estensione — `_inherit`)

```python
class CfProjectTask(models.Model):
    _inherit = 'project.task'

    # === IN ATTESA DI ===
    cf_waiting_for = fields.Selection([
        ('none', 'Nessuno'),
        ('client', 'Cliente'),
        ('graphic', 'Grafico'),
        ('printer', 'Tipografia'),
        ('production', 'Produzione'),
        ('internal', 'Interno'),
        ('supplier', 'Fornitore'),
    ], string="In Attesa Di", default='none', tracking=True)

    # === CONTATORE GIORNI ===
    cf_days_in_stage = fields.Integer(
        compute='_compute_days_in_stage', string="Giorni in Stage")
    cf_stage_changed_date = fields.Datetime(
        string="Ultimo Cambio Stage", tracking=True)

    # === EMAIL COLLEGATE ===
    cf_email_ids = fields.Many2many(
        'casafolino_mail.message',  # modello del Mail Hub
        'cf_task_email_rel',
        'task_id', 'email_id',
        string="Email Collegate",
    )
    cf_email_count = fields.Integer(
        compute='_compute_email_count', string="Email")

    # === CHECKLIST ===
    cf_checklist_ids = fields.One2many(
        'cf.project.checklist.item', 'task_id',
        string="Checklist",
    )
    cf_checklist_progress = fields.Float(
        compute='_compute_checklist_progress',
        string="Checklist %",
    )
    cf_checklist_required = fields.Boolean(
        string="Checklist Obbligatoria",
        help="Se attivo, la task non può essere completata senza completare la checklist",
    )

    # === SPEDIZIONE (per task di tipo spedizione) ===
    cf_shipment_id = fields.Many2one(
        'cf.project.shipment', string="Spedizione Collegata")

    # === SEQUENZA NEL TEMPLATE ===
    cf_template_sequence = fields.Integer(
        string="Ordine nel Template", default=10)
    cf_relative_days = fields.Integer(
        string="Giorni Relativi",
        help="Numero di giorni PRIMA (-) o DOPO (+) la data target del progetto",
    )
    cf_auto_activate_next = fields.Boolean(
        string="Attiva Task Successiva",
        help="Quando completata, attiva automaticamente la task successiva nella sequenza",
    )
```

**Override `write`:** quando `stage_id` cambia, aggiorna `cf_stage_changed_date`. Se la task passa a stage "done" e `cf_checklist_required` è True, verifica che tutti gli item checklist siano completati — altrimenti `raise UserError`. Se `cf_auto_activate_next` è True, cerca la task successiva per sequenza e la sposta allo stage "in_progress".

### 5.3 `cf.project.template` (nuovo modello)

```python
class CfProjectTemplate(models.Model):
    _name = 'cf.project.template'
    _description = 'Template Progetto CasaFolino'

    name = fields.Char(string="Nome Template", required=True)
    cf_project_type = fields.Selection([...])  # stessa selection di project
    task_template_ids = fields.One2many(
        'cf.project.task.template', 'template_id',
        string="Task del Template",
    )
    active = fields.Boolean(default=True)
    description = fields.Html(string="Descrizione")
```

### 5.4 `cf.project.task.template` (nuovo modello)

```python
class CfProjectTaskTemplate(models.Model):
    _name = 'cf.project.task.template'
    _description = 'Task Template CasaFolino'
    _order = 'sequence'

    template_id = fields.Many2one('cf.project.template', required=True, ondelete='cascade')
    name = fields.Char(string="Nome Task", required=True)
    sequence = fields.Integer(string="Ordine", default=10)
    relative_days = fields.Integer(
        string="Giorni Relativi alla Deadline",
        help="Es: -30 = 30 giorni prima della deadline progetto",
    )
    default_user_id = fields.Many2one('res.users', string="Responsabile Default")
    cf_waiting_for = fields.Selection([...])  # default waiting for
    description = fields.Html(string="Istruzioni")
    auto_activate_next = fields.Boolean(string="Attiva Successiva", default=True)
    stage_name = fields.Char(
        string="Stage Iniziale",
        help="Nome dello stage in cui creare la task (es: 'Da Fare', 'In Attesa')",
    )
    checklist_template_ids = fields.One2many(
        'cf.project.checklist.template', 'task_template_id',
        string="Checklist Template",
    )
    checklist_required = fields.Boolean(string="Checklist Obbligatoria", default=False)
```

### 5.5 `cf.project.shipment` (nuovo modello)

```python
class CfProjectShipment(models.Model):
    _name = 'cf.project.shipment'
    _description = 'Spedizione Campioni'
    _inherit = ['mail.thread']

    project_id = fields.Many2one('project.project', required=True)
    partner_id = fields.Many2one(
        related='project_id.cf_partner_id', store=True)
    state = fields.Selection([
        ('draft', 'Da Preparare'),
        ('ready', 'Pronto'),
        ('shipped', 'Spedito'),
        ('delivered', 'Consegnato'),
        ('feedback', 'Feedback Ricevuto'),
    ], default='draft', tracking=True)
    carrier = fields.Char(string="Corriere")
    tracking_number = fields.Char(string="Tracking Number")
    tracking_url = fields.Char(
        compute='_compute_tracking_url', string="Link Tracking")
    ship_date = fields.Date(string="Data Spedizione")
    estimated_delivery = fields.Date(string="Consegna Stimata")
    actual_delivery = fields.Date(string="Consegna Effettiva")
    product_ids = fields.Many2many(
        'product.product', string="Prodotti Campionati")
    notes = fields.Text(string="Note Spedizione")
    weight = fields.Float(string="Peso (kg)")
    shipping_cost = fields.Float(string="Costo Spedizione €")
```

### 5.6 `cf.project.checklist.item` (nuovo modello)

```python
class CfProjectChecklistItem(models.Model):
    _name = 'cf.project.checklist.item'
    _description = 'Checklist Item'
    _order = 'sequence'

    task_id = fields.Many2one('project.task', required=True, ondelete='cascade')
    name = fields.Char(string="Voce", required=True)
    sequence = fields.Integer(default=10)
    is_done = fields.Boolean(string="Completato")
    done_by = fields.Many2one('res.users', string="Completato da")
    done_date = fields.Datetime(string="Data Completamento")
```

### 5.7 `cf.project.checklist.template` (nuovo modello)

```python
class CfProjectChecklistTemplate(models.Model):
    _name = 'cf.project.checklist.template'
    _description = 'Checklist Template Item'
    _order = 'sequence'

    task_template_id = fields.Many2one(
        'cf.project.task.template', required=True, ondelete='cascade')
    name = fields.Char(string="Voce", required=True)
    sequence = fields.Integer(default=10)
```

---

## 6. VISTE

### 6.1 Dashboard Portfolio (vista principale del modulo)

Vista **kanban** di `project.project` filtrata su `cf_project_type != False` (solo progetti CasaFolino).

Ogni card mostra:
- **Riga 1**: Nome progetto + badge tipo (colorato)
- **Riga 2**: Cliente + bandiera paese
- **Riga 3**: Barra avanzamento (progress bar)
- **Riga 4**: Semaforo (pallino colorato) + "In attesa di: [blocco]" + "X giorni"
- **Riga 5**: Data target + responsabile (avatar)

**Raggruppamento default**: per `cf_project_type`.
**Filtri rapidi**: I Miei Progetti, Bloccati, In Ritardo, Per Fiera.

### 6.2 Form Progetto Estesa

Aggiungere tab al form view nativo del progetto:

**Tab "Panoramica"** (il primo tab visibile):
- Header: semaforo grande + avanzamento % + data target + giorni aperti
- Sezione: partner info (nome, paese, email, telefono)
- Sezione: spedizione (se tipo campionatura) — stato con timeline visiva
- Sezione: ultimi 5 email dal Mail Hub

**Tab "Spedizioni"** (visibile solo se tipo = campionatura):
- Lista inline `cf_shipment_ids`

**Tab "Email"** (sempre visibile):
- Lista email collegate dal Mail Hub con bottone "Collega Email"

### 6.3 Form Task Estesa

Aggiungere al form view nativo della task:

- Campo `cf_waiting_for` visibile nell'header (dopo il responsabile)
- Badge `cf_days_in_stage` colorato (verde < 3gg, giallo 3-7gg, rosso > 7gg)
- Tab "Checklist" con lista inline editabile degli item checklist
- Tab "Email" con `cf_email_ids` (many2many widget)
- Tab "Spedizione" (visibile solo se presente) con form inline shipment

### 6.4 Kanban Task (estensione)

Sulla card task aggiungere:
- Badge "In attesa di: [nome]" con colore
- Badge "Xg" (giorni nello stage corrente) — rosso se > 7
- Icona busta se ci sono email collegate
- Progress bar checklist (se presente)

### 6.5 Vista "Le Mie Cose"

Action window separata con vista lista di `project.task` filtrata su `user_ids` = current user, raggruppata per `project_id`, ordinata per `date_deadline`.

Colonne: nome task, progetto, waiting_for, deadline, days_in_stage, checklist %.

---

## 7. TEMPLATE PRE-CONFIGURATI (data XML)

### 7.1 Campionatura Fiera

| # | Task | Giorni Relativi | Owner Default | Waiting For | Checklist |
|---|---|---|---|---|---|
| 1 | Selezione SKU da campionare | -45 | Martina | none | |
| 2 | Conferma disponibilità produzione | -40 | Maria | production | |
| 3 | Preparazione campioni | -30 | Produzione | production | ✅ Prodotti pronti, Confezionamento OK, Etichette applicate |
| 4 | Preparazione materiale marketing | -25 | Martina | graphic | |
| 5 | Imballaggio e preparazione spedizione | -15 | Anna | internal | ✅ Peso verificato, Documenti doganali, Tracking inserito |
| 6 | Spedizione | -10 | Martina | none | |
| 7 | Conferma ricezione | -5 | Martina | client | |
| 8 | Follow-up post consegna | +7 | Josefina | client | |

### 7.2 Campionatura Cliente

| # | Task | Giorni Relativi | Owner | Waiting | Checklist |
|---|---|---|---|---|---|
| 1 | Ricezione richiesta e briefing | 0 | Josefina | client | |
| 2 | Selezione prodotti | -20 | Martina | none | |
| 3 | Verifica disponibilità | -18 | Maria | production | |
| 4 | Preparazione campioni | -12 | Produzione | production | ✅ obbligatoria |
| 5 | Spedizione | -7 | Anna | internal | ✅ obbligatoria |
| 6 | Follow-up feedback | +5 | Josefina | client | |

### 7.3 Etichetta Personalizzata

| # | Task | Giorni Relativi | Owner | Waiting | Checklist |
|---|---|---|---|---|---|
| 1 | Briefing cliente (specifiche etichetta) | 0 | Josefina | client | |
| 2 | Invio brief a grafico | -25 | Martina | graphic | |
| 3 | Ricezione bozza v1 | -20 | Martina | graphic | |
| 4 | Revisione interna | -18 | Maria | internal | ✅ Allergeni corretti, Valori nutrizionali OK, Testi legali conformi |
| 5 | Invio bozza a cliente | -15 | Josefina | client | |
| 6 | Ricezione feedback/approvazione | -10 | Josefina | client | |
| 7 | Invio file definitivo a tipografia | -7 | Martina | printer | |
| 8 | Ricezione etichette stampate | -3 | Anna | printer | ✅ Colori conformi, Quantità corretta, Adesione OK |
| 9 | Applicazione su prodotti | -1 | Produzione | production | |

### 7.4 Lancio Nuovo Prodotto

| # | Task | Giorni Relativi | Owner | Waiting |
|---|---|---|---|---|
| 1 | Sviluppo ricetta / R&D | -60 | Antonio | none |
| 2 | Test produzione pilota | -50 | Maria | production |
| 3 | Analisi di laboratorio | -45 | Maria | supplier |
| 4 | Scheda tecnica | -40 | Maria | internal |
| 5 | Definizione etichetta | -35 | Martina | graphic |
| 6 | Pricing e MOQ | -30 | Antonio | none |
| 7 | Preparazione campionatura | -20 | Martina | production |
| 8 | Presentazione a clienti target | -10 | Josefina | client |
| 9 | Go-live catalogo e marketplace | 0 | Martina | none |

### 7.5 Preparazione Fiera

| # | Task | Giorni Relativi | Owner | Waiting |
|---|---|---|---|---|
| 1 | Prenotazione stand e logistica | -90 | Antonio | none |
| 2 | Design stand e materiali | -60 | Martina | graphic |
| 3 | Selezione campioni da esporre | -45 | Antonio | none |
| 4 | Preparazione catalogo/listino | -30 | Josefina | none |
| 5 | Organizzazione viaggio e hotel | -30 | Martina | none |
| 6 | Spedizione materiali allo stand | -15 | Anna | internal |
| 7 | Checklist pre-partenza | -3 | Martina | none |
| 8 | Follow-up contatti post-fiera | +3 | Josefina | none |

---

## 8. SICUREZZA

### 8.1 Gruppi

- `casafolino_project.group_cf_project_user` — può creare/modificare task, aggiornare checklist, collegare email
- `casafolino_project.group_cf_project_manager` — può creare/eliminare progetti, gestire template, vedere dashboard completa

### 8.2 Record Rules

- Tutti gli utenti interni vedono tutti i progetti CasaFolino
- Solo i manager possono eliminare progetti e modificare template

### 8.3 `ir.model.access.csv`

Accesso CRUD per entrambi i gruppi su:
- `cf.project.template`
- `cf.project.task.template`
- `cf.project.shipment`
- `cf.project.checklist.item`
- `cf.project.checklist.template`

**NON** includere `project.project` e `project.task` (sono `_inherit`, gestiti dal modulo nativo).

---

## 9. MENU

```
CasaFolino Project (root — web_icon)
├── Dashboard Progetti          → kanban project.project (filtro cf_project_type != False)
├── Le Mie Task                 → lista project.task (filtro user = me)
├── Tutti i Progetti            → lista project.project
├── Spedizioni                  → lista cf.project.shipment
└── Configurazione
    ├── Template Progetto       → lista cf.project.template
    ├── Template Task           → lista cf.project.task.template
    └── Tipi Progetto           → (futuro, per ora è selection field)
```

---

## 10. LOGICA CREAZIONE DA TEMPLATE

Quando un utente crea un progetto e seleziona un `cf_template_id`:

1. Il `cf_project_type` si auto-popola dal template
2. Per ogni `task_template` del template, ordinato per `sequence`:
   a. Crea una `project.task` con nome, responsabile, descrizione dal template
   b. Calcola la `date_deadline` come: `cf_target_date + relative_days`
   c. Imposta `cf_waiting_for` dal template
   d. Imposta `cf_auto_activate_next` dal template
   e. Imposta `cf_checklist_required` dal template
   f. Crea gli item checklist dal `checklist_template_ids`
3. La prima task nella sequenza va nello stage "Da Fare", le successive in "In Attesa"

**Se `cf_target_date` non è valorizzata**, le date deadline delle task restano vuote ma la sequenza e le altre proprietà vengono comunque create.

---

## 11. INTEGRAZIONE MAIL HUB

Il campo `cf_email_ids` sulle task è un Many2many verso `casafolino_mail.message`.

**Bottone "Collega Email"** sulla task apre un wizard con:
- Filtro automatico per partner del progetto
- Lista delle email non ancora collegate a nessuna task
- Selezione multipla
- Conferma → aggiunge le email selezionate a `cf_email_ids`

**Smart button "Email"** sul progetto:
- Mostra il conteggio email dove il mittente o destinatario corrisponde a `cf_partner_id`
- Click apre la lista email filtrata

**NOTA**: verificare che il modello `casafolino_mail.message` esista e abbia i campi: `partner_id`, `sender`, `recipients`, `subject`, `date`, `body_preview`. Adattare i nomi campo se necessario. Se il modello non esiste o ha struttura diversa, creare i campi `cf_email_ids` come `fields.Text` placeholder e commentare l'integrazione per la fase successiva.

---

## 12. NOTIFICHE

Implementare tramite `mail.activity` standard di Odoo (NON cron custom):

- Quando una task viene assegnata → attività per il responsabile
- Quando `cf_waiting_for` cambia → nota nel chatter con menzione
- Quando `cf_days_in_stage` > 7 per task non completate → attività "Sollecito" (cron giornaliero)

---

## 13. NOTE IMPLEMENTAZIONE

1. **Iniziare dalla struttura modelli** → poi viste → poi template data → poi logica compute
2. **Testare su `folinofood` direttamente** (staging ha problemi ambientali noti)
3. **La dashboard kanban è la priorità visiva** — deve funzionare bene prima di tutto
4. **Non usare Studio** — tutto via XML/Python
5. **Icon**: usare un'icona FA appropriata (es. `fa-tasks` o `fa-clipboard`)
6. **Colori semaforo nel kanban**: usare classi CSS Odoo `badge-success`, `badge-warning`, `badge-danger`
7. **Il campo `cf_waiting_for`** deve essere visibile e modificabile direttamente dalla card kanban (inline edit)

---

## 14. FASE 2 (non implementare ora, solo predisporre)

Questi campi/modelli possono essere creati come placeholder ma NON implementati:

- Auto-attivazione task successiva al completamento (feature #9)
- Invio email dalla task con template Odoo (feature #10)
- Versioning documenti con approvazione (feature #13)
- Log attività timeline custom (feature #14)
- Quick actions da kanban (feature #18)
- Notifiche intelligenti differenziate per ruolo (feature #20)

---

## 15. CRITERI DI ACCETTAZIONE

Il modulo è considerato completo quando:

1. ✅ Si installa senza errori su `folinofood`
2. ✅ Il menu "CasaFolino Project" appare con icona nel menu principale
3. ✅ Si può creare un progetto selezionando un template e le task si generano automaticamente
4. ✅ Le date delle task si calcolano correttamente dalla data target
5. ✅ Il kanban mostra semaforo, avanzamento, e "in attesa di" per ogni progetto
6. ✅ La vista "Le Mie Task" mostra solo le task dell'utente corrente
7. ✅ Le checklist funzionano e bloccano il completamento task se obbligatorie
8. ✅ Le spedizioni si possono creare e tracciare dal progetto
9. ✅ Le email del Mail Hub si possono collegare alle task (o il placeholder è in posizione)
10. ✅ I 5 template pre-configurati sono caricati e funzionanti
