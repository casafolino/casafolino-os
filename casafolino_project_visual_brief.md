# BRIEF VISIVO — Viste `casafolino_project`

## Per Claude Code — Rebuild completo delle viste XML

**Data:** 14 aprile 2026  
**Obiettivo:** Rifare TUTTE le viste del modulo `casafolino_project` con design ricco, ispirato a Monday.com, Asana, ClickUp e Notion.  
**Regola base:** Le viste attuali sono brutte e generiche. Vanno riscritte da zero con attenzione al dettaglio visivo.

---

## REGOLE ODOO 18 (da rispettare sempre)

- Kanban: usare `t-name="card"` NON `t-name="kanban-box"`
- NO `attrs=` → usare `invisible=` direttamente
- NO `tree` → usare `list`
- Actions prima delle view nel file XML
- Menuitem dopo act_window
- Priority view: 99 per override sicuro
- Bottoni in page: `<div class="o_row">` NON `<header>`
- `quick_create="false"` direttamente sul tag `<kanban>`
- Tutte le viste devono essere STANDALONE (non inherit delle viste native project) per le action CasaFolino
- Le viste inherit del form nativo di project.project e project.task restano inherit — aggiungono i campi CF ai form standard

---

## 1. DASHBOARD KANBAN — `cf_project_kanban.xml`

Vista kanban standalone per `project.project`, usata dall'action Dashboard.

### Specifiche del tag kanban
```xml
<kanban quick_create="false" default_group_by="cf_project_type" class="o_kanban_small_column">
```

### Card progetto — template QWeb `t-name="card"`

Ogni card deve contenere questi elementi, in quest'ordine:

**A. Banda colore laterale sinistra (4px)**
Usare `style` inline con colore basato su `cf_project_type`:
- `sample_fair` → `border-left: 4px solid #534AB7` (viola)
- `sample_client` → `border-left: 4px solid #1D9E75` (verde)
- `custom_label` → `border-left: 4px solid #D85A30` (arancione)
- `new_product` → `border-left: 4px solid #378ADD` (blu)
- `fair_prep` → `border-left: 4px solid #534AB7` (viola)
- `strategic` → `border-left: 4px solid #888780` (grigio)

Implementare con `t-attf-style`:
```xml
<div t-attf-style="border-left: 4px solid #{record.cf_project_type.raw_value == 'sample_fair' ? '#534AB7' : record.cf_project_type.raw_value == 'sample_client' ? '#1D9E75' : record.cf_project_type.raw_value == 'custom_label' ? '#D85A30' : record.cf_project_type.raw_value == 'new_product' ? '#378ADD' : record.cf_project_type.raw_value == 'fair_prep' ? '#534AB7' : '#888780'}; border-radius: 8px; padding: 12px;">
```

**B. Riga 1: Nome progetto + Semaforo**
```xml
<div class="d-flex justify-content-between align-items-start mb-1">
    <strong class="o_kanban_record_title">
        <field name="name"/>
    </strong>
    <!-- Semaforo: pallino colorato 12x12px -->
    <div t-attf-style="width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; background: #{record.cf_traffic_light.raw_value == 'green' ? '#639922' : record.cf_traffic_light.raw_value == 'yellow' ? '#EF9F27' : '#E24B4A'};"/>
</div>
```

**C. Riga 2: Badge tipo progetto**
Badge piccolo con sfondo colorato e testo scuro, stesse associazioni colore della banda laterale ma versione chiara:
```xml
<div class="mb-2">
    <span t-attf-style="font-size: 10px; padding: 2px 8px; border-radius: 8px; font-weight: 600; background: #{record.cf_project_type.raw_value == 'sample_fair' ? '#EEEDFE' : record.cf_project_type.raw_value == 'sample_client' ? '#E1F5EE' : record.cf_project_type.raw_value == 'custom_label' ? '#FAECE7' : record.cf_project_type.raw_value == 'new_product' ? '#E6F1FB' : '#F1EFE8'}; color: #{record.cf_project_type.raw_value == 'sample_fair' ? '#3C3489' : record.cf_project_type.raw_value == 'sample_client' ? '#085041' : record.cf_project_type.raw_value == 'custom_label' ? '#712B13' : record.cf_project_type.raw_value == 'new_product' ? '#0C447C' : '#444441'};">
        <field name="cf_project_type"/>
    </span>
</div>
```

**D. Riga 3: Cliente con paese**
```xml
<div style="font-size: 12px; color: #666; margin-bottom: 8px;">
    <field name="cf_partner_id"/> 
    <t t-if="record.cf_partner_country_id.value">
        — <field name="cf_partner_country_id"/>
    </t>
</div>
```

**E. Riga 4: Progress bar**
Usare il widget `field` con widget="progressbar" oppure costruirla manualmente:
```xml
<div class="mb-1">
    <div style="height: 6px; background: #e9ecef; border-radius: 3px; overflow: hidden;">
        <div t-attf-style="height: 100%; width: #{record.cf_progress.raw_value}%; border-radius: 3px; background: #{record.cf_traffic_light.raw_value == 'green' ? '#639922' : record.cf_traffic_light.raw_value == 'yellow' ? '#EF9F27' : '#E24B4A'};"/>
    </div>
    <div style="font-size: 11px; color: #999; margin-top: 2px;">
        <field name="cf_tasks_done"/>/<field name="cf_tasks_total"/> task completate
    </div>
</div>
```

**F. Riga 5: Footer — Badge "In attesa di" + Giorni + Avatar**
```xml
<div class="d-flex justify-content-between align-items-center mt-2">
    <!-- Badge "In attesa di" con colore per tipo -->
    <span t-if="record.cf_main_blocker.raw_value != 'none'" 
          t-attf-style="font-size: 11px; padding: 3px 8px; border-radius: 10px; font-weight: 500; background: #{record.cf_main_blocker.raw_value == 'client' ? '#E6F1FB' : record.cf_main_blocker.raw_value == 'graphic' ? '#EEEDFE' : record.cf_main_blocker.raw_value == 'printer' ? '#FAECE7' : record.cf_main_blocker.raw_value == 'production' ? '#EAF3DE' : record.cf_main_blocker.raw_value == 'supplier' ? '#FAEEDA' : '#F1EFE8'}; color: #{record.cf_main_blocker.raw_value == 'client' ? '#0C447C' : record.cf_main_blocker.raw_value == 'graphic' ? '#3C3489' : record.cf_main_blocker.raw_value == 'printer' ? '#712B13' : record.cf_main_blocker.raw_value == 'production' ? '#27500A' : record.cf_main_blocker.raw_value == 'supplier' ? '#633806' : '#444441'};">
        In attesa: <field name="cf_main_blocker"/>
    </span>
    <span t-else="" style="font-size: 11px; color: #ccc;">Nessun blocco</span>
    
    <div class="d-flex align-items-center" style="gap: 8px;">
        <!-- Giorni aperti con colore -->
        <span t-attf-style="font-size: 11px; color: #{record.cf_days_open.raw_value > 30 ? '#E24B4A' : record.cf_days_open.raw_value > 14 ? '#BA7517' : '#999'};">
            <field name="cf_days_open"/>g
        </span>
        <!-- Avatar responsabile -->
        <field name="user_id" widget="many2one_avatar_user"/>
    </div>
</div>
```

### Campi da includere nel kanban (NON visibili ma necessari per i template)
```xml
<field name="name"/>
<field name="cf_project_type"/>
<field name="cf_partner_id"/>
<field name="cf_partner_country_id"/>
<field name="cf_traffic_light"/>
<field name="cf_progress"/>
<field name="cf_tasks_done"/>
<field name="cf_tasks_total"/>
<field name="cf_main_blocker"/>
<field name="cf_days_open"/>
<field name="user_id"/>
<field name="cf_target_date"/>
```

### Raggruppamento e filtri
- Default group by: `cf_project_type`
- Filtri nel search view: "I miei progetti" (user_id = uid), "Bloccati" (cf_main_blocker != none), "In ritardo" (cf_traffic_light = red), "Per tipo" (group by cf_project_type)

---

## 2. FORM PROGETTO — `cf_project_views.xml`

Vista form INHERIT di `project.project.view.form`. Aggiunge elementi al form nativo.

### A. Header con metriche (dopo il nome progetto)

Usare xpath per inserire DOPO il div `oe_title`:

```xml
<xpath expr="//div[hasclass('oe_title')]" position="after">
```

Inserire un blocco con:

**Riga metriche** — 4 card affiancate con sfondo leggero:
```xml
<div class="d-flex gap-3 mb-3" style="margin-top: 12px;">
    <!-- Card Avanzamento -->
    <div style="flex: 1; background: #f8f9fa; border-radius: 8px; padding: 12px 14px;">
        <div style="font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.3px;">Avanzamento</div>
        <div style="font-size: 20px; font-weight: 500;">
            <field name="cf_progress" widget="progressbar"/>
        </div>
    </div>
    <!-- Card Task count -->
    <div style="flex: 1; background: #f8f9fa; border-radius: 8px; padding: 12px 14px;">
        <div style="font-size: 11px; color: #666; text-transform: uppercase;">Task</div>
        <div style="font-size: 20px; font-weight: 500;">
            <field name="cf_tasks_done"/>/<field name="cf_tasks_total"/>
        </div>
        <div style="font-size: 11px; color: #999;">
            <field name="cf_tasks_blocked"/> bloccate
        </div>
    </div>
    <!-- Card Giorni -->
    <div style="flex: 1; background: #f8f9fa; border-radius: 8px; padding: 12px 14px;">
        <div style="font-size: 11px; color: #666; text-transform: uppercase;">Giorni aperti</div>
        <div style="font-size: 20px; font-weight: 500;">
            <field name="cf_days_open"/>
        </div>
    </div>
    <!-- Card Bloccato da -->
    <div style="flex: 1; background: #f8f9fa; border-radius: 8px; padding: 12px 14px;">
        <div style="font-size: 11px; color: #666; text-transform: uppercase;">Bloccato da</div>
        <div style="font-size: 14px; font-weight: 500;">
            <field name="cf_main_blocker"/>
        </div>
    </div>
</div>
```

**Semaforo grande** — inserire accanto al nome progetto o nel button_box:
```xml
<xpath expr="//div[@name='button_box']" position="inside">
    <button class="oe_stat_button" icon="fa-circle" 
            style="pointer-events: none;">
        <field name="cf_traffic_light" widget="badge" 
               decoration-success="cf_traffic_light == 'green'"
               decoration-warning="cf_traffic_light == 'yellow'"
               decoration-danger="cf_traffic_light == 'red'"/>
    </button>
</xpath>
```

### B. Campi CasaFolino nel form

Inserire PRIMA del notebook (tab), un gruppo con i campi principali:

```xml
<xpath expr="//notebook" position="before">
    <group string="CasaFolino">
        <group>
            <field name="cf_template_id"/>
            <field name="cf_project_type"/>
            <field name="cf_target_date"/>
        </group>
        <group>
            <field name="cf_partner_id"/>
            <field name="cf_partner_country_id"/>
            <field name="cf_partner_email" widget="email"/>
        </group>
    </group>
    
    <!-- Progetto padre (per sotto-progetti fiera) -->
    <group string="Fiera Collegata" invisible="cf_project_type not in ('sample_fair', 'sample_client')">
        <field name="cf_parent_project_id"/>
    </group>
</xpath>
```

### C. Tab aggiuntivi nel notebook

Aggiungere dentro il notebook:

```xml
<xpath expr="//notebook" position="inside">
    <!-- Tab Spedizioni -->
    <page string="Spedizioni" name="cf_shipments" 
          invisible="cf_project_type not in ('sample_fair', 'sample_client', 'custom_label')">
        <field name="cf_shipment_ids" mode="list">
            <!-- Lista spedizioni con colonne: stato (con widget badge colorato), corriere, tracking, data spedizione, consegna stimata, peso -->
        </field>
    </page>
    
    <!-- Tab Email -->
    <page string="Email" name="cf_emails">
        <div class="o_row mb-3">
            <button name="action_link_emails" string="Collega Email" type="object" class="btn btn-primary" icon="fa-link"/>
        </div>
        <!-- Smart button count email nel button_box -->
    </page>
    
    <!-- Tab Sotto-progetti (solo per tipo fair_prep) -->
    <page string="Sotto-progetti" name="cf_children" 
          invisible="cf_project_type != 'fair_prep'">
        <field name="cf_child_project_ids">
            <!-- Lista sotto-progetti con colonne: nome, tipo, partner, avanzamento, semaforo -->
        </field>
    </page>
</xpath>
```

### D. Smart buttons nel button_box

```xml
<xpath expr="//div[@name='button_box']" position="inside">
    <!-- Conteggio email -->
    <button class="oe_stat_button" icon="fa-envelope"
            name="action_view_emails" type="object">
        <field name="cf_email_count" string="Email" widget="statinfo"/>
    </button>
    
    <!-- Conteggio sotto-progetti (solo per fiere) -->
    <button class="oe_stat_button" icon="fa-folder" 
            invisible="cf_project_type != 'fair_prep'"
            name="action_view_children" type="object">
        <field name="cf_child_count" string="Sotto-progetti" widget="statinfo"/>
    </button>
</xpath>
```

---

## 3. FORM TASK — `cf_project_task_views.xml`

Vista form INHERIT di `project.task.view.form`.

### A. Campi principali nell'header della task

Aggiungere il campo `cf_waiting_for` con widget badge colorato DOPO il campo `user_ids`:

```xml
<xpath expr="//field[@name='user_ids']" position="after">
    <field name="cf_waiting_for" widget="badge"
           decoration-info="cf_waiting_for == 'client'"
           decoration-muted="cf_waiting_for == 'none'"
           decoration-warning="cf_waiting_for == 'production'"
           decoration-success="cf_waiting_for == 'internal'"
           decoration-danger="cf_waiting_for == 'printer'"/>
    <field name="cf_days_in_stage" widget="badge"
           decoration-danger="cf_days_in_stage > 7"
           decoration-warning="cf_days_in_stage > 3"
           string="Giorni"/>
</xpath>
```

### B. Tab Checklist

```xml
<xpath expr="//notebook" position="inside">
    <page string="Checklist" name="cf_checklist">
        <div class="o_row mb-2" invisible="not cf_checklist_required">
            <span class="badge bg-warning text-dark">Checklist obbligatoria per completare questa task</span>
        </div>
        <field name="cf_checklist_ids">
            <list editable="bottom">
                <field name="sequence" widget="handle"/>
                <field name="name"/>
                <field name="is_done" widget="boolean_toggle"/>
                <field name="done_by" readonly="1"/>
                <field name="done_date" readonly="1"/>
            </list>
        </field>
        <div class="mt-2">
            <field name="cf_checklist_progress" widget="progressbar"/>
        </div>
    </page>
    
    <!-- Tab Email collegate -->
    <page string="Email" name="cf_task_emails">
        <field name="cf_email_ids">
            <!-- many2many con colonne: data, mittente, oggetto, body preview -->
        </field>
    </page>
    
    <!-- Tab Spedizione (se collegata) -->
    <page string="Spedizione" name="cf_task_shipment" 
          invisible="not cf_shipment_id">
        <field name="cf_shipment_id"/>
    </page>
</xpath>
```

---

## 4. LISTA "LE MIE TASK" — `cf_project_task_views.xml`

Vista lista STANDALONE per `project.task`. Deve essere raggruppata per progetto con design ricco.

### Colonne della lista

```xml
<list default_group_by="project_id" decoration-danger="cf_days_in_stage > 7" decoration-warning="cf_days_in_stage > 3">
    <field name="priority" widget="priority"/>
    <field name="name" string="Titolo"/>
    <field name="project_id" string="Progetto"/>
    <field name="cf_waiting_for" string="In attesa di" widget="badge"
           decoration-info="cf_waiting_for == 'client'"
           decoration-warning="cf_waiting_for == 'production'"
           decoration-danger="cf_waiting_for == 'printer'"/>
    <field name="date_deadline" string="Scadenza" widget="remaining_days"/>
    <field name="cf_days_in_stage" string="Giorni" widget="badge"
           decoration-danger="cf_days_in_stage > 7"
           decoration-warning="cf_days_in_stage > 3"/>
    <field name="cf_checklist_progress" string="Checklist %" widget="progressbar"/>
    <field name="stage_id" string="Stage"/>
    <field name="user_ids" string="Responsabile" widget="many2many_tags_avatar"/>
    <field name="cf_email_count" string="Email" optional="show"/>
</list>
```

### Search view con filtri predefiniti

```xml
<search>
    <field name="name"/>
    <field name="project_id"/>
    <field name="cf_waiting_for"/>
    <separator/>
    <filter name="my_tasks" string="Le mie task" domain="[('user_ids', 'in', uid)]"/>
    <filter name="overdue" string="Scadute" domain="[('date_deadline', '&lt;', context_today().strftime('%Y-%m-%d'))]"/>
    <filter name="blocked" string="Bloccate" domain="[('cf_waiting_for', '!=', 'none')]"/>
    <filter name="today_week" string="Oggi/questa settimana" domain="[('date_deadline', '&lt;=', (context_today() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'))]"/>
    <separator/>
    <group expand="0" string="Raggruppa per">
        <filter name="group_project" string="Progetto" context="{'group_by': 'project_id'}"/>
        <filter name="group_waiting" string="In attesa di" context="{'group_by': 'cf_waiting_for'}"/>
        <filter name="group_stage" string="Stage" context="{'group_by': 'stage_id'}"/>
        <filter name="group_user" string="Responsabile" context="{'group_by': 'user_ids'}"/>
    </group>
</search>
```

### Action "Le Mie Task"
Deve avere il filtro `my_tasks` attivo di default e raggruppamento per `project_id`:
```xml
<field name="context">{'search_default_my_tasks': 1, 'search_default_group_project': 1}</field>
```

---

## 5. LISTA PROGETTI — `cf_project_views.xml`

Vista lista standalone per `project.project` nella sezione "Tutti i Progetti".

```xml
<list decoration-danger="cf_traffic_light == 'red'" decoration-warning="cf_traffic_light == 'yellow'">
    <field name="name" string="Progetto"/>
    <field name="cf_project_type" string="Tipo" widget="badge"/>
    <field name="cf_partner_id" string="Cliente"/>
    <field name="cf_partner_country_id" string="Paese"/>
    <field name="cf_target_date" string="Target" widget="remaining_days"/>
    <field name="cf_progress" string="Avanzamento" widget="progressbar"/>
    <field name="cf_traffic_light" string="Stato" widget="badge"
           decoration-success="cf_traffic_light == 'green'"
           decoration-warning="cf_traffic_light == 'yellow'"  
           decoration-danger="cf_traffic_light == 'red'"/>
    <field name="cf_main_blocker" string="Bloccato da" widget="badge"/>
    <field name="cf_tasks_done" string="Done" optional="show"/>
    <field name="cf_tasks_total" string="Tot" optional="show"/>
    <field name="cf_days_open" string="Giorni"/>
    <field name="user_id" string="Resp." widget="many2one_avatar_user"/>
</list>
```

---

## 6. SPEDIZIONI — `cf_project_shipment_views.xml`

### Form spedizione
Con timeline visiva dello stato (5 step):

```xml
<form>
    <header>
        <field name="state" widget="statusbar" statusbar_visible="draft,ready,shipped,delivered,feedback"/>
    </header>
    <sheet>
        <group>
            <group string="Spedizione">
                <field name="project_id"/>
                <field name="partner_id"/>
                <field name="carrier"/>
                <field name="tracking_number"/>
                <field name="tracking_url" widget="url"/>
            </group>
            <group string="Date e dettagli">
                <field name="ship_date"/>
                <field name="estimated_delivery"/>
                <field name="actual_delivery"/>
                <field name="weight"/>
                <field name="shipping_cost"/>
            </group>
        </group>
        <group string="Prodotti campionati">
            <field name="product_ids" widget="many2many_tags"/>
        </group>
        <group string="Note">
            <field name="notes"/>
        </group>
    </sheet>
    <chatter/>
</form>
```

### Lista spedizioni
```xml
<list decoration-info="state == 'shipped'" decoration-success="state == 'delivered'" decoration-muted="state == 'draft'">
    <field name="project_id"/>
    <field name="partner_id"/>
    <field name="state" widget="badge"
           decoration-info="state == 'shipped'"
           decoration-success="state in ('delivered', 'feedback')"
           decoration-warning="state == 'ready'"
           decoration-muted="state == 'draft'"/>
    <field name="carrier"/>
    <field name="tracking_number"/>
    <field name="ship_date"/>
    <field name="estimated_delivery" widget="remaining_days"/>
</list>
```

---

## 7. TEMPLATE — `cf_project_template_views.xml`

### Form template
```xml
<form>
    <sheet>
        <group>
            <group>
                <field name="name"/>
                <field name="cf_project_type"/>
                <field name="active"/>
            </group>
            <group>
                <field name="description"/>
            </group>
        </group>
        <notebook>
            <page string="Task del template">
                <field name="task_template_ids">
                    <list editable="bottom">
                        <field name="sequence" widget="handle"/>
                        <field name="name"/>
                        <field name="relative_days"/>
                        <field name="default_user_id"/>
                        <field name="cf_waiting_for"/>
                        <field name="auto_activate_next"/>
                        <field name="checklist_required"/>
                        <field name="stage_name"/>
                    </list>
                </field>
            </page>
        </notebook>
    </sheet>
</form>
```

---

## 8. MENUS E ACTIONS — `cf_project_menus.xml`

OGNI action deve avere binding espliciti via `ir.actions.act_window.view`:

```xml
<!-- Dashboard -->
<record id="cf_project_action_dashboard" model="ir.actions.act_window">
    <field name="name">Dashboard Progetti</field>
    <field name="res_model">project.project</field>
    <field name="view_mode">kanban,list,form</field>
    <field name="domain">[('cf_project_type', '!=', False)]</field>
    <field name="context">{'quick_create': False, 'default_group_by': 'cf_project_type'}</field>
</record>
<!-- Binding kanban standalone -->
<record id="cf_dashboard_view_kanban" model="ir.actions.act_window.view">
    <field name="sequence">1</field>
    <field name="view_mode">kanban</field>
    <field name="view_id" ref="cf_project_kanban_view"/>
    <field name="act_window_id" ref="cf_project_action_dashboard"/>
</record>
<!-- Binding lista standalone -->
<record id="cf_dashboard_view_list" model="ir.actions.act_window.view">
    <field name="sequence">2</field>
    <field name="view_mode">list</field>
    <field name="view_id" ref="cf_project_list_view"/>
    <field name="act_window_id" ref="cf_project_action_dashboard"/>
</record>

<!-- Le Mie Task -->
<record id="cf_my_tasks_action" model="ir.actions.act_window">
    <field name="name">Le Mie Task</field>
    <field name="res_model">project.task</field>
    <field name="view_mode">list,form</field>
    <field name="context">{'search_default_my_tasks': 1, 'search_default_group_project': 1}</field>
    <field name="search_view_id" ref="cf_task_search_view"/>
</record>
<record id="cf_my_tasks_view_list" model="ir.actions.act_window.view">
    <field name="sequence">1</field>
    <field name="view_mode">list</field>
    <field name="view_id" ref="cf_my_tasks_list_view"/>
    <field name="act_window_id" ref="cf_my_tasks_action"/>
</record>

<!-- Ripetere per: Tutti i Progetti, Spedizioni, Template, Task Template -->
```

---

## 9. COLORI DI RIFERIMENTO

### Per tipo progetto
| Tipo | Banda/bordo | Badge bg | Badge text |
|---|---|---|---|
| Campionatura Fiera | #534AB7 | #EEEDFE | #3C3489 |
| Campionatura Cliente | #1D9E75 | #E1F5EE | #085041 |
| Etichetta Personalizzata | #D85A30 | #FAECE7 | #712B13 |
| Lancio Prodotto | #378ADD | #E6F1FB | #0C447C |
| Preparazione Fiera | #534AB7 | #EEEDFE | #3C3489 |
| Strategico | #888780 | #F1EFE8 | #444441 |

### Per "In attesa di"
| Interlocutore | Badge bg | Badge text |
|---|---|---|
| Cliente | #E6F1FB | #0C447C |
| Grafico | #EEEDFE | #3C3489 |
| Tipografia | #FAECE7 | #712B13 |
| Produzione | #EAF3DE | #27500A |
| Interno | #F1EFE8 | #444441 |
| Fornitore | #FAEEDA | #633806 |

### Per semaforo
| Stato | Colore |
|---|---|
| Verde (In linea) | #639922 |
| Giallo (Attenzione) | #EF9F27 |
| Rosso (Critico) | #E24B4A |

### Per giorni in stage
| Condizione | Colore testo |
|---|---|
| < 3 giorni | #999 (neutro) |
| 3-7 giorni | #BA7517 (warning) |
| > 7 giorni | #E24B4A (danger) |

---

## 10. CHECKLIST

- Il campo `cf_checklist_progress` deve mostrare un widget progressbar nella lista task
- Nella form task, la checklist è editabile inline con handle per riordinare
- Il toggle `is_done` deve auto-popolare `done_by` e `done_date` quando marcato (override `write` sul modello)
- Se `cf_checklist_required = True` e non tutti i checklist item sono done, il passaggio allo stage "Done" deve dare `UserError`

---

## 11. NOTE FINALI

1. **NON usare CSS esterni** — tutto inline style o classi Bootstrap/Odoo native
2. **Testare ogni vista** singolarmente prima di committare
3. **Le viste standalone** (kanban, lista progetti, lista task, spedizioni, template) devono avere ID XML univoci e essere referenziate esplicitamente nelle action
4. **Le viste inherit** (form progetto, form task) aggiungono campi ai form nativi
5. **Il file `__manifest__.py`** deve listare TUTTI i file XML nell'ordine corretto: security prima, poi views (actions prima delle view), poi menus, poi data
6. **Validare ogni XML** con `python3 -c "from xml.etree import ElementTree; ElementTree.parse('file.xml'); print('OK')"`
