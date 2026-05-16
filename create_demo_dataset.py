# -*- coding: utf-8 -*-
"""
Create DEMO dataset on folinofood PROD.
Run via: docker exec odoo-app odoo shell -d folinofood --no-http < /tmp/create_demo_dataset.py
Idempotent: skips existing records by name prefix 'DEMO- '.
"""
import json
from datetime import date, timedelta

demo_ids = {
    'partners': [], 'buyers': [], 'brokers': [], 'dossiers': [],
    'tasks': [], 'leads': [], 'initiatives': [], 'samples': [], 'actors': [],
}
errors = []

# ── Helpers ──────────────────────────────────────────────────────────
Partner = env['res.partner']
Project = env['project.project']
Task = env['project.task']
Lead = env['crm.lead']
Sample = env['cf.export.sample']
Actor = env['cf.dossier.actor']
Initiative = env['cf.initiative']
Template = env['cf.dossier.template']
Checkpoint = env['cf.dossier.template.checkpoint']

# User IDs
ANTONIO = 2
JOSEFINA = 6
MARTINA = 8

# Country IDs
COUNTRIES = {'CA': 38, 'US': 233, 'MA': 136, 'AT': 12, 'IT': 109, 'LU': 133}

# Certification IDs
CERTS = {'HALAL': 1, 'KOSHER': 2, 'BIO': 3, 'IFS': 4, 'BRC': 5, 'GF': 6,
         'VEGAN': 7, 'NON_GMO': 8, 'USDA_ORGANIC': 9, 'FSSC22000': 10, 'REX': 11, 'HACCP': 12}

# CRM Stage IDs
STAGES = {'primo_contatto': 15, 'interesse': 16, 'trattativa': 17,
          'preventivo': 18, 'campionatura': 19, 'negoziazione': 20,
          'vinta': 21, 'persa': 22, 'standby': 23}

# Sample Stage IDs
SAMPLE_STAGES = {'richiesta': 1, 'preparazione': 2, 'spedita': 3,
                 'consegnata': 4, 'valutazione': 5, 'positivo': 6, 'negativo': 7}

# Template IDs
TEMPLATES = {'PL_EU': 1, 'GDO_BRANDED': 2, 'IMPORT_DISTR': 3, 'AGENCY': 4,
             'MARKETPLACE': 5, 'FOODSERVICE': 6, 'NEW_PRODUCT_DEV': 7,
             'PRODUCT_LAUNCH': 8, 'MARKET_TEST': 9, 'TRADE_FAIR': 10,
             'ACQUISITION': 11, 'NEW_COUNTRY': 12}

today = date.today()


def find_or_create(model, domain, vals, label=''):
    """Find existing or create, returns record. Uses savepoint to isolate errors."""
    try:
        rec = model.search(domain, limit=1)
        if rec:
            print(f"  [SKIP] {label or vals.get('name', '?')} already exists (id={rec.id})")
            return rec
        sp = f"sp_{model._name.replace('.','_')}_{id(vals)}"
        env.cr.execute(f"SAVEPOINT {sp}")
        rec = model.create(vals)
        env.cr.execute(f"RELEASE SAVEPOINT {sp}")
        print(f"  [OK] {label or vals.get('name', '?')} created (id={rec.id})")
        return rec
    except Exception as e:
        env.cr.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        msg = f"[ERR] {label or vals.get('name', '?')}: {e}"
        print(msg)
        errors.append(msg)
        return model.browse()


# ═══════════════════════════════════════════════════════════════════
# A. Partner Clienti
# ═══════════════════════════════════════════════════════════════════
print("\n=== A. PARTNER CLIENTI ===")

PARTNERS_DATA = [
    {'name': 'DEMO- Costco Canada', 'country_id': COUNTRIES['CA'], 'lang_code': 'en'},
    {'name': 'DEMO- Gia Foods Inc', 'country_id': COUNTRIES['US'], 'lang_code': 'en'},
    {'name': 'DEMO- AKSAL Holding', 'country_id': COUNTRIES['MA'], 'lang_code': 'fr'},
    {'name': 'DEMO- BILLA AG', 'country_id': COUNTRIES['AT'], 'lang_code': 'de'},
    {'name': 'DEMO- Carrefour Italia', 'country_id': COUNTRIES['IT'], 'lang_code': 'it'},
    {'name': 'DEMO- Amazon EU FBA', 'country_id': COUNTRIES['LU'], 'lang_code': 'en'},
]

partners = {}
for pd in PARTNERS_DATA:
    p = find_or_create(Partner, [('name', '=', pd['name'])], {
        'name': pd['name'],
        'is_company': True,
        'country_id': pd['country_id'],
        'customer_rank': 1,
    })
    if p:
        partners[pd['name']] = p
        demo_ids['partners'].append(p.id)

# ═══════════════════════════════════════════════════════════════════
# B. Buyer Contatti (child of partner)
# ═══════════════════════════════════════════════════════════════════
print("\n=== B. BUYER CONTATTI ===")

BUYERS_DATA = [
    {'name': 'DEMO- Doug Carter', 'parent': 'DEMO- Costco Canada', 'email': 'doug.carter@costco.ca'},
    {'name': 'DEMO- Pete Khanna', 'parent': 'DEMO- Gia Foods Inc', 'email': 'pete@giafoods.com'},
    {'name': 'DEMO- Margee Villarreal', 'parent': 'DEMO- AKSAL Holding', 'email': 'margee.v@aksal.ma'},
    {'name': 'DEMO- Klaus Wagner', 'parent': 'DEMO- BILLA AG', 'email': 'k.wagner@billa.at'},
    {'name': 'DEMO- Marco Bianchi', 'parent': 'DEMO- Carrefour Italia', 'email': 'marco.bianchi@carrefour.it'},
]

buyers = {}
for bd in BUYERS_DATA:
    parent = partners.get(bd['parent'])
    if not parent:
        continue
    b = find_or_create(Partner, [('name', '=', bd['name'])], {
        'name': bd['name'],
        'is_company': False,
        'parent_id': parent.id,
        'email': bd['email'],
        'function': 'Buyer',
    })
    if b:
        buyers[bd['parent']] = b
        demo_ids['buyers'].append(b.id)

# ═══════════════════════════════════════════════════════════════════
# C. Broker
# ═══════════════════════════════════════════════════════════════════
print("\n=== C. BROKER ===")

BROKERS_DATA = [
    {'name': 'DEMO- BROKER Mario Rossi', 'email': 'mario.rossi@brokerit.com'},
    {'name': 'DEMO- BROKER Hans Mueller', 'email': 'hans.mueller@brokerDE.com'},
    {'name': 'DEMO- BROKER Pierre Dubois', 'email': 'pierre.dubois@agentFR.com'},
]

brokers = {}
for bk in BROKERS_DATA:
    br = find_or_create(Partner, [('name', '=', bk['name'])], {
        'name': bk['name'],
        'is_company': True,
        'email': bk['email'],
        'supplier_rank': 1,
    })
    if br:
        brokers[bk['name']] = br
        demo_ids['brokers'].append(br.id)

# ═══════════════════════════════════════════════════════════════════
# D. Dossier (project.project) con checkpoint tasks
# ═══════════════════════════════════════════════════════════════════
print("\n=== D. DOSSIER ===")

DOSSIER_DATA = [
    {
        'name': 'DEMO- Costco Canada — Miele 2026',
        'template_code': 'PL_EU',
        'status': 'active',
        'user_id': ANTONIO,
        'co_user_ids': [JOSEFINA],
        'partner': 'DEMO- Costco Canada',
        'lang': 'en',
        'volume': 50000, 'volume_unit': 'cartoni',
        'margin': 22.0,
        'cert_codes': ['BRC', 'KOSHER'],
        'incoterms': 'fob', 'payment': '30_70',
        'moq': '1 container 40ft', 'lead_time': 45, 'shelf_life': 24,
        'next_action': 'Inviare campionature miele acacia 220g',
        'next_action_date': today + timedelta(days=12),
        'target_date': today + timedelta(days=120),
        'broker': 'DEMO- BROKER Mario Rossi', 'broker_role': 'broker',
        'broker_basis': 'revenue', 'broker_value': 3.0,
        'priority': 'high',
    },
    {
        'name': 'DEMO- Gia Foods — 220g spreads',
        'template_code': 'IMPORT_DISTR',
        'status': 'active',
        'user_id': JOSEFINA,
        'co_user_ids': [ANTONIO],
        'partner': 'DEMO- Gia Foods Inc',
        'lang': 'en',
        'volume': 1, 'volume_unit': 'pallet',
        'margin': 28.0,
        'cert_codes': ['BRC', 'REX'],
        'incoterms': 'cif', 'payment': '50_50',
        'moq': '1 pallet misto', 'lead_time': 60, 'shelf_life': 18,
        'next_action': 'Follow-up pricing list aggiornata',
        'next_action_date': today + timedelta(days=7),
        'target_date': today + timedelta(days=90),
        'broker': 'DEMO- BROKER Mario Rossi', 'broker_role': 'broker',
        'broker_basis': 'revenue', 'broker_value': 3.0,
        'priority': 'medium',
    },
    {
        'name': 'DEMO- AKSAL — Halal range',
        'template_code': 'IMPORT_DISTR',
        'status': 'exploration',
        'user_id': JOSEFINA,
        'co_user_ids': [],
        'partner': 'DEMO- AKSAL Holding',
        'lang': 'fr',
        'volume': 500, 'volume_unit': 'pallet',
        'margin': 30.0,
        'cert_codes': ['HALAL', 'BRC'],
        'incoterms': 'ddp', 'payment': 'lc',
        'moq': '20 pallet', 'lead_time': 75, 'shelf_life': 24,
        'next_action': 'Richiedere certificato Halal aggiornato',
        'next_action_date': today + timedelta(days=20),
        'target_date': today + timedelta(days=180),
        'broker': 'DEMO- BROKER Pierre Dubois', 'broker_role': 'agent',
        'broker_basis': 'margin', 'broker_value': 5.0,
        'priority': 'medium',
    },
    {
        'name': 'DEMO- BILLA AT — GDO Branded',
        'template_code': 'GDO_BRANDED',
        'status': 'active',
        'user_id': JOSEFINA,
        'co_user_ids': [ANTONIO],
        'partner': 'DEMO- BILLA AG',
        'lang': 'de',
        'volume': 80, 'volume_unit': 'pallet',
        'margin': 32.0,
        'cert_codes': ['BRC', 'BIO'],
        'incoterms': 'fca', 'payment': '60_days',
        'moq': '10 pallet', 'lead_time': 30, 'shelf_life': 18,
        'next_action': 'Preparare quotazione GDO format 6x200g',
        'next_action_date': today + timedelta(days=5),
        'target_date': today + timedelta(days=60),
        'broker': 'DEMO- BROKER Hans Mueller', 'broker_role': 'broker',
        'broker_basis': 'revenue', 'broker_value': 2.5,
        'priority': 'high',
    },
    {
        'name': 'DEMO- Carrefour IT — PL ricorrente',
        'template_code': 'PL_EU',
        'status': 'won',
        'user_id': ANTONIO,
        'co_user_ids': [MARTINA],
        'partner': 'DEMO- Carrefour Italia',
        'lang': 'it',
        'volume': 30000, 'volume_unit': 'cartoni',
        'margin': 24.0,
        'cert_codes': ['BRC', 'BIO'],
        'incoterms': 'exw', 'payment': '60_days',
        'moq': '5000 cartoni', 'lead_time': 21, 'shelf_life': 24,
        'next_action': 'Conferma ordine ricorrente Q3',
        'next_action_date': today + timedelta(days=30),
        'target_date': today + timedelta(days=45),
        'broker': None,
        'priority': 'medium',
    },
    {
        'name': 'DEMO- Amazon EU — Honey range',
        'template_code': 'MARKETPLACE',
        'status': 'active',
        'user_id': MARTINA,
        'co_user_ids': [ANTONIO],
        'partner': 'DEMO- Amazon EU FBA',
        'lang': 'en',
        'volume': 5000, 'volume_unit': 'unit',
        'margin': 38.0,
        'cert_codes': ['BRC', 'BIO'],
        'incoterms': 'ddp', 'payment': 'advance',
        'moq': '500 unit', 'lead_time': 14, 'shelf_life': 24,
        'next_action': 'Upload listing A+ content su Seller Central',
        'next_action_date': today + timedelta(days=10),
        'target_date': today + timedelta(days=90),
        'broker': None,
        'priority': 'high',
    },
    {
        'name': 'DEMO- Tuttofood 2026 Lancio Pistacchio',
        'template_code': 'PRODUCT_LAUNCH',
        'status': 'exploration',
        'user_id': ANTONIO,
        'co_user_ids': [JOSEFINA, MARTINA],
        'partner': None,
        'lang': 'it',
        'volume': 0, 'volume_unit': 'unit',
        'margin': 0,
        'cert_codes': ['BRC', 'IFS'],
        'incoterms': None, 'payment': None,
        'moq': '', 'lead_time': 0, 'shelf_life': 0,
        'next_action': 'Finalizzare ricettario crema pistacchio',
        'next_action_date': today + timedelta(days=15),
        'target_date': today + timedelta(days=150),
        'broker': None,
        'priority': 'medium',
    },
]

dossiers = {}
for dd in DOSSIER_DATA:
    existing = Project.search([('name', '=', dd['name'])], limit=1)
    if existing:
        print(f"  [SKIP] {dd['name']} already exists (id={existing.id})")
        dossiers[dd['name']] = existing
        demo_ids['dossiers'].append(existing.id)
        continue

    try:
        tmpl_id = TEMPLATES[dd['template_code']]
        partner_rec = partners.get(dd['partner']) if dd['partner'] else False

        vals = {
            'name': dd['name'],
            'cf_status_dossier': dd['status'],
            'cf_template_origin_id': tmpl_id,
            'user_id': dd['user_id'],
            'partner_id': partner_rec.id if partner_rec else False,
            'cf_partner_id': partner_rec.id if partner_rec else False,
            'cf_dossier_lang': dd['lang'],
            'cf_volume_target': dd['volume'],
            'cf_volume_unit': dd['volume_unit'],
            'cf_margin_target': dd['margin'],
            'cf_certification_ids': [(6, 0, [CERTS[c] for c in dd['cert_codes']])],
            'cf_next_action': dd['next_action'],
            'cf_next_action_date': dd['next_action_date'].isoformat(),
            'date': dd['target_date'].isoformat(),
            'cf_target_date': dd['target_date'].isoformat(),
            'cf_dossier_priority': dd['priority'],
        }
        if dd['incoterms']:
            vals['cf_incoterms'] = dd['incoterms']
        if dd['payment']:
            vals['cf_payment_term'] = dd['payment']
        if dd['moq']:
            vals['cf_moq'] = dd['moq']
        if dd['lead_time']:
            vals['cf_lead_time'] = dd['lead_time']
        if dd['shelf_life']:
            vals['cf_shelf_life'] = dd['shelf_life']
        if dd['co_user_ids']:
            vals['cf_co_user_ids'] = [(6, 0, dd['co_user_ids'])]

        # Set buyer
        if dd['partner'] and dd['partner'] in buyers:
            vals['cf_buyer_id'] = buyers[dd['partner']].id

        proj = Project.create(vals)
        print(f"  [OK] {dd['name']} created (id={proj.id})")
        dossiers[dd['name']] = proj
        demo_ids['dossiers'].append(proj.id)

        # Create tasks from template checkpoints
        checkpoints = Checkpoint.search([('template_id', '=', tmpl_id)], order='sequence')
        task_count = 0
        for cp in checkpoints:
            Task.create({
                'name': cp.name,
                'project_id': proj.id,
                'description': cp.description or '',
                'sequence': cp.sequence,
            })
            task_count += 1
        demo_ids['tasks'].extend([])  # tracked by project
        print(f"    -> {task_count} checkpoint tasks created")

    except Exception as e:
        msg = f"[ERR] Dossier {dd['name']}: {e}"
        print(msg)
        errors.append(msg)

# ═══════════════════════════════════════════════════════════════════
# E. Lead collegati ai dossier
# ═══════════════════════════════════════════════════════════════════
print("\n=== E. LEAD ===")

LEADS_DATA = [
    {'name': 'DEMO- Costco miele acacia 220g primo ordine', 'dossier': 'DEMO- Costco Canada — Miele 2026',
     'revenue': 350000, 'probability': 50, 'stage': 'campionatura', 'deadline_days': 90},
    {'name': 'DEMO- Costco miele millefiori bulk 5kg', 'dossier': 'DEMO- Costco Canada — Miele 2026',
     'revenue': 180000, 'probability': 30, 'stage': 'interesse', 'deadline_days': 150},
    {'name': 'DEMO- Gia Foods spread collection US', 'dossier': 'DEMO- Gia Foods — 220g spreads',
     'revenue': 45000, 'probability': 70, 'stage': 'negoziazione', 'deadline_days': 45},
    {'name': 'DEMO- Gia Foods crema pistacchio limited', 'dossier': 'DEMO- Gia Foods — 220g spreads',
     'revenue': 28000, 'probability': 30, 'stage': 'primo_contatto', 'deadline_days': 120},
    {'name': 'DEMO- AKSAL halal honey range Morocco', 'dossier': 'DEMO- AKSAL — Halal range',
     'revenue': 95000, 'probability': 10, 'stage': 'primo_contatto', 'deadline_days': 180},
    {'name': 'DEMO- BILLA private label miele Bio AT', 'dossier': 'DEMO- BILLA AT — GDO Branded',
     'revenue': 120000, 'probability': 50, 'stage': 'preventivo', 'deadline_days': 60},
    {'name': 'DEMO- BILLA crema nocciola Bio display', 'dossier': 'DEMO- BILLA AT — GDO Branded',
     'revenue': 75000, 'probability': 30, 'stage': 'trattativa', 'deadline_days': 90},
    {'name': 'DEMO- Carrefour IT PL miele ricorrente Q3', 'dossier': 'DEMO- Carrefour IT — PL ricorrente',
     'revenue': 500000, 'probability': 90, 'stage': 'vinta', 'deadline_days': 30},
    {'name': 'DEMO- Amazon EU honey multipack FBA', 'dossier': 'DEMO- Amazon EU — Honey range',
     'revenue': 65000, 'probability': 70, 'stage': 'trattativa', 'deadline_days': 60},
    {'name': 'DEMO- Amazon EU crispy chili launch', 'dossier': 'DEMO- Amazon EU — Honey range',
     'revenue': 22000, 'probability': 10, 'stage': 'primo_contatto', 'deadline_days': 120},
    {'name': 'DEMO- Tuttofood crema pistacchio lancio', 'dossier': 'DEMO- Tuttofood 2026 Lancio Pistacchio',
     'revenue': 0, 'probability': 10, 'stage': 'primo_contatto', 'deadline_days': 150},
]

leads = {}
for ld in LEADS_DATA:
    dossier = dossiers.get(ld['dossier'])
    if not dossier:
        errors.append(f"[ERR] Lead {ld['name']}: dossier not found")
        continue
    lead = find_or_create(Lead, [('name', '=', ld['name'])], {
        'name': ld['name'],
        'partner_id': dossier.partner_id.id if dossier.partner_id else False,
        'cf_project_id': dossier.id,
        'expected_revenue': ld['revenue'],
        'probability': ld['probability'],
        'stage_id': STAGES[ld['stage']],
        'date_deadline': (today + timedelta(days=ld['deadline_days'])).isoformat(),
        'user_id': dossier.user_id.id,
    })
    if lead:
        leads[ld['name']] = lead
        demo_ids['leads'].append(lead.id)

# ═══════════════════════════════════════════════════════════════════
# F. Iniziative
# ═══════════════════════════════════════════════════════════════════
print("\n=== F. INIZIATIVE ===")

INIT_DATA = [
    {
        'name': 'DEMO- Tuttofood 2026',
        'family_id': 2,  # Evento
        'variant_id': 5,  # Medium
        'user_id': ANTONIO,
        'state': 'in_progress',
        'date_start': today - timedelta(days=30),
        'date_end': today + timedelta(days=60),
        'dossier_names': ['DEMO- BILLA AT — GDO Branded', 'DEMO- Tuttofood 2026 Lancio Pistacchio'],
    },
    {
        'name': 'DEMO- SIAL Canada 2026 Follow-up',
        'family_id': 2,  # Evento
        'variant_id': 6,  # Full
        'user_id': JOSEFINA,
        'state': 'in_progress',
        'date_start': today - timedelta(days=60),
        'date_end': today + timedelta(days=120),
        'dossier_names': ['DEMO- Costco Canada — Miele 2026', 'DEMO- Gia Foods — 220g spreads'],
    },
]

initiatives = {}
for init in INIT_DATA:
    rec = find_or_create(Initiative, [('name', '=', init['name'])], {
        'name': init['name'],
        'family_id': init['family_id'],
        'variant_id': init['variant_id'],
        'user_id': init['user_id'],
        'state': init['state'],
        'date_start': init['date_start'].isoformat(),
        'date_end': init['date_end'].isoformat(),
    })
    if rec:
        initiatives[init['name']] = rec
        demo_ids['initiatives'].append(rec.id)
        # Link dossiers via initiative_id on project.project
        for dn in init.get('dossier_names', []):
            d = dossiers.get(dn)
            if d:
                try:
                    d.write({'initiative_id': rec.id})
                    print(f"    -> linked {dn} to {init['name']}")
                except Exception as e:
                    errors.append(f"[ERR] Link {dn} to {init['name']}: {e}")

# ═══════════════════════════════════════════════════════════════════
# G. Campionature
# ═══════════════════════════════════════════════════════════════════
print("\n=== G. CAMPIONATURE ===")

SAMPLES_DATA = [
    {
        'reference': 'DEMO- Miele acacia 220g',
        'lead_name': 'DEMO- Costco miele acacia 220g primo ordine',
        'partner_name': 'DEMO- Costco Canada',
        'stage_id': SAMPLE_STAGES['spedita'],
    },
    {
        'reference': 'DEMO- Crema pistacchio 200g',
        'lead_name': 'DEMO- Carrefour IT PL miele ricorrente Q3',
        'partner_name': 'DEMO- Carrefour Italia',
        'stage_id': SAMPLE_STAGES['positivo'],
    },
    {
        'reference': 'DEMO- Crispy chili 90g',
        'lead_name': 'DEMO- Tuttofood crema pistacchio lancio',
        'partner_name': None,
        'stage_id': SAMPLE_STAGES['preparazione'],
    },
]

for sd in SAMPLES_DATA:
    lead = leads.get(sd['lead_name']) if sd['lead_name'] else False
    partner = partners.get(sd['partner_name']) if sd['partner_name'] else False
    vals = {
        'reference': sd['reference'],
        'stage_id': sd['stage_id'],
    }
    if lead:
        vals['lead_id'] = lead.id
    if partner:
        vals['partner_id'] = partner.id
    s = find_or_create(Sample, [('reference', '=', sd['reference'])], vals)
    if s:
        demo_ids['samples'].append(s.id)

# ═══════════════════════════════════════════════════════════════════
# H. Network Actors
# ═══════════════════════════════════════════════════════════════════
print("\n=== H. NETWORK ACTORS ===")

ACTORS_DATA = [
    # Broker actors
    {'dossier': 'DEMO- Costco Canada — Miele 2026', 'broker': 'DEMO- BROKER Mario Rossi',
     'role': 'broker', 'basis': 'revenue', 'value': 3.0},
    {'dossier': 'DEMO- Gia Foods — 220g spreads', 'broker': 'DEMO- BROKER Mario Rossi',
     'role': 'broker', 'basis': 'revenue', 'value': 3.0},
    {'dossier': 'DEMO- AKSAL — Halal range', 'broker': 'DEMO- BROKER Pierre Dubois',
     'role': 'agent', 'basis': 'margin', 'value': 5.0},
    {'dossier': 'DEMO- BILLA AT — GDO Branded', 'broker': 'DEMO- BROKER Hans Mueller',
     'role': 'broker', 'basis': 'revenue', 'value': 2.5},
    # Co-responsible actors
    {'dossier': 'DEMO- Costco Canada — Miele 2026', 'user_id': JOSEFINA,
     'role': 'co_responsible', 'basis': 'none', 'value': 0},
    {'dossier': 'DEMO- BILLA AT — GDO Branded', 'user_id': ANTONIO,
     'role': 'co_responsible', 'basis': 'none', 'value': 0},
    {'dossier': 'DEMO- Carrefour IT — PL ricorrente', 'user_id': MARTINA,
     'role': 'co_responsible', 'basis': 'none', 'value': 0},
]

for ad in ACTORS_DATA:
    dossier = dossiers.get(ad['dossier'])
    if not dossier:
        continue

    vals = {
        'project_id': dossier.id,
        'role': ad['role'],
        'commission_basis': ad['basis'],
        'commission_value': ad['value'],
    }

    if 'broker' in ad:
        broker = brokers.get(ad['broker'])
        if not broker:
            continue
        vals['partner_id'] = broker.id
        domain = [('project_id', '=', dossier.id), ('partner_id', '=', broker.id)]
    else:
        vals['user_id'] = ad['user_id']
        domain = [('project_id', '=', dossier.id), ('user_id', '=', ad['user_id']), ('role', '=', 'co_responsible')]

    a = find_or_create(Actor, domain, vals, label=f"Actor {ad['role']} on {ad['dossier']}")
    if a:
        demo_ids['actors'].append(a.id)

# ═══════════════════════════════════════════════════════════════════
# COMMIT & SAVE
# ═══════════════════════════════════════════════════════════════════
print("\n=== COMMIT ===")
env.cr.commit()

ts = today.isoformat()
json_path = f'/tmp/demo_ids_{ts}.json'
with open(json_path, 'w') as f:
    json.dump(demo_ids, f, indent=2)

print(f"\nTotal records created/found: {sum(len(v) for v in demo_ids.values())}")
print(f"IDs saved to {json_path}")

if errors:
    print(f"\n⚠ {len(errors)} errors:")
    for e in errors:
        print(f"  {e}")
else:
    print("\n✓ Zero errors")

print("\nDONE")
