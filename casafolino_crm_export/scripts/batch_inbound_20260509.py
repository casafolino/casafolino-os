#!/usr/bin/env python3
"""
Batch Inbound Leads — 9 maggio 2026
Step 1: Attach PDFs to 3 new templates
Step 2: Run 6 leads in sequence (TEST_MODE from env, default true)

Usage:
  docker exec -e TEST_MODE=true odoo-app bash -c \
    "odoo shell -d folinofood --no-http < /docker/enterprise18/addons/custom/casafolino_crm_export/scripts/batch_inbound_20260509.py"
"""
import json
import os
import re
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() in ('true', '1', 'yes')

print("\n" + "=" * 70)
print("BATCH INBOUND LEADS — 9 maggio 2026")
print(f"TEST_MODE: {TEST_MODE}")
print("=" * 70 + "\n")

# ═══════════════════════════════════════════════════════════════
# STEP 0: ATTACH PDFs TO NEW TEMPLATES
# ═══════════════════════════════════════════════════════════════

# Attachment IDs (verified)
ATT_CATALOGUE = 33380  # CasaFolino Catalogue EN 2026 — Master (7.3 MB)
ATT_NOVITA = 33377     # Novità CasaFolino (0.4 MB)
ATT_PROFILE = 33375    # Company Profile (4.3 MB)

FULL_ATTACHMENTS = [ATT_CATALOGUE, ATT_NOVITA, ATT_PROFILE]     # 3 PDF
PL_ATTACHMENTS = [ATT_CATALOGUE, ATT_PROFILE]                    # 2 PDF (no Novità for PL)

templates_config = {
    'casafolino_crm_export.mail_template_inbound_export_en': FULL_ATTACHMENTS,
    'casafolino_crm_export.mail_template_inbound_private_label_it': PL_ATTACHMENTS,
    'casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet_apology': FULL_ATTACHMENTS,
}

for xmlid, att_ids in templates_config.items():
    tpl = env.ref(xmlid, raise_if_not_found=False)
    if not tpl:
        print(f"  ✗ Template {xmlid} NOT FOUND — skip")
        continue
    current_att_ids = set(tpl.attachment_ids.ids)
    if set(att_ids).issubset(current_att_ids):
        print(f"  ✓ {tpl.name}: attachments already set ({len(tpl.attachment_ids)})")
    else:
        tpl.write({'attachment_ids': [(6, 0, att_ids)]})
        total_mb = sum(env['ir.attachment'].browse(a).file_size for a in att_ids) / 1048576
        print(f"  ✓ {tpl.name}: {len(att_ids)} allegati, {total_mb:.1f} MB")

# Also verify the original IT template
tpl_it = env.ref('casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet', raise_if_not_found=False)
if tpl_it:
    if not set(FULL_ATTACHMENTS).issubset(set(tpl_it.attachment_ids.ids)):
        tpl_it.write({'attachment_ids': [(6, 0, FULL_ATTACHMENTS)]})
        print(f"  ✓ {tpl_it.name}: attachments updated to 3 PDF")
    else:
        print(f"  ✓ {tpl_it.name}: attachments OK ({len(tpl_it.attachment_ids)})")

env.cr.commit()
print()

# ═══════════════════════════════════════════════════════════════
# STEP 1: RESOLVE COMMON REFERENCES
# ═══════════════════════════════════════════════════════════════

# Users
antonio = env['res.users'].search([('login', '=', 'antonio@casafolino.com')], limit=1)
martina = env['res.users'].search([('login', '=', 'martina.sinopoli@casafolino.com')], limit=1)
josefina = env['res.users'].search([('login', '=', 'josefina.lazzaro@casafolino.com')], limit=1)
maria = env['res.users'].search([('login', 'ilike', 'maria.mirabelli')], limit=1)

print(f"✓ Antonio: user_id={antonio.id}")
print(f"✓ Martina: user_id={martina.id}")
print(f"✓ Josefina: user_id={josefina.id}")
if maria:
    print(f"✓ Maria Mirabelli: user_id={maria.id}")
else:
    print("⚠ Maria Mirabelli: NON trovata (Coop Campo senza follower Maria)")

# Countries
italy = env['res.country'].search([('code', '=', 'IT')], limit=1)
france = env['res.country'].search([('code', '=', 'FR')], limit=1)
brazil = env['res.country'].search([('code', '=', 'BR')], limit=1)

# Stages
stage_qualifica = env['crm.stage'].search([('name', 'ilike', 'Qualifica')], limit=1)
if not stage_qualifica:
    stage_qualifica = env['crm.stage'].search([], order='sequence', limit=1)
    print(f"⚠ Stage 'Qualifica' non trovato — uso: {stage_qualifica.name}")
else:
    print(f"✓ Stage: {stage_qualifica.name}")

# Teams
team_italia = env['crm.team'].search([('name', 'ilike', 'Italia')], limit=1)
team_export = env['crm.team'].search([('name', 'ilike', 'Export')], limit=1)
print(f"✓ Team Italia: {team_italia.id if team_italia else 'N/A'} — {team_italia.name if team_italia else 'NOT FOUND'}")
print(f"✓ Team Export: {team_export.id if team_export else 'N/A'} — {team_export.name if team_export else 'NOT FOUND'}")

# UTM
def get_or_create_source(name):
    src = env['utm.source'].search([('name', '=ilike', name)], limit=1)
    if not src:
        src = env['utm.source'].create({'name': name})
    return src

def get_or_create_medium(name):
    med = env['utm.medium'].search([('name', '=ilike', name)], limit=1)
    if not med:
        med = env['utm.medium'].create({'name': name})
    return med

utm_shopify = get_or_create_source('Shopify Contact Form')
utm_reel = get_or_create_source('Reel Sponsorizzato')
utm_website = get_or_create_medium('Website')
utm_social = get_or_create_medium('Social Ads')

print()

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

TAG_COLORS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

def resolve_tags(tag_csv):
    """Resolve or create tags from CSV string."""
    tags = env['crm.tag']
    created = []
    if not tag_csv:
        return tags, created
    for i, name in enumerate(t.strip() for t in tag_csv.split(',') if t.strip()):
        tag = env['crm.tag'].search([('name', '=ilike', name)], limit=1)
        if not tag:
            tag = env['crm.tag'].create({'name': name, 'color': TAG_COLORS[i % len(TAG_COLORS)]})
            created.append(name)
        tags |= tag
    return tags, created

def resolve_state(state_name, country):
    """Resolve state by name or code."""
    if not state_name:
        return False
    st = env['res.country.state'].search([
        ('country_id', '=', country.id),
        ('name', 'ilike', state_name)
    ], limit=1)
    if not st:
        st = env['res.country.state'].search([
            ('country_id', '=', country.id),
            ('code', 'ilike', state_name)
        ], limit=1)
    return st or False

def create_lead(cfg):
    """Create or find lead. Returns dict with result."""
    res = {
        'name': cfg['label'],
        'partner_id': None, 'partner_existed': False,
        'child_contact_id': None,
        'lead_id': None, 'lead_existed': False, 'lead_url': None,
        'tags_applied': [], 'tags_created': [],
        'preview_path': None, 'attachments': 0,
        'warnings': [],
    }

    email = cfg['email']
    partner_name = cfg['partner_name']
    contact_name = cfg.get('contact_name', '')
    country = cfg['country']
    state = cfg.get('state', False)
    owner = cfg['owner']
    team = cfg.get('team') or owner.sale_team_id or env['crm.team'].search([], limit=1)
    template = cfg['template']
    source = cfg.get('source', utm_shopify)
    medium = cfg.get('medium', utm_website)

    # Tags
    tags, tags_created = resolve_tags(cfg.get('tags', ''))
    res['tags_applied'] = [t.name for t in tags]
    res['tags_created'] = tags_created

    # Partner (idempotent)
    partner = env['res.partner'].search([('email', '=', email), ('is_company', '=', True)], limit=1)
    if not partner:
        partner = env['res.partner'].search([('email', '=', email), ('parent_id', '=', False)], limit=1)

    partner_vals = {
        'name': partner_name, 'is_company': True, 'email': email,
        'country_id': country.id,
    }
    if cfg.get('phone'): partner_vals.update({'phone': cfg['phone'], 'mobile': cfg['phone']})
    if cfg.get('street'): partner_vals['street'] = cfg['street']
    if cfg.get('city'): partner_vals['city'] = cfg['city']
    if cfg.get('zip'): partner_vals['zip'] = cfg['zip']
    if state: partner_vals['state_id'] = state.id
    if cfg.get('notes'): partner_vals['comment'] = cfg['notes']

    if partner:
        res['partner_existed'] = True
        upd = {k: v for k, v in partner_vals.items() if k != 'name' and not partner[k]}
        if not partner.is_company:
            upd['is_company'] = True
        if upd:
            partner.write(upd)
    else:
        partner = env['res.partner'].create(partner_vals)

    res['partner_id'] = partner.id

    # Child contact
    if contact_name:
        child = env['res.partner'].search([
            ('parent_id', '=', partner.id), ('name', 'ilike', contact_name)
        ], limit=1)
        if not child:
            child_vals = {'parent_id': partner.id, 'name': contact_name, 'email': email, 'type': 'contact'}
            if cfg.get('phone'): child_vals['phone'] = cfg['phone']
            child = env['res.partner'].create(child_vals)
        res['child_contact_id'] = child.id

    # Lead (idempotent — 90 days)
    ninety_ago = datetime.now() - timedelta(days=90)
    existing = env['crm.lead'].search([
        ('email_from', '=', email),
        ('create_date', '>=', ninety_ago.strftime('%Y-%m-%d')),
        ('active', '=', True),
    ], limit=1)

    if existing:
        res['lead_existed'] = True
        lead = existing
        upd = {}
        if tags and not lead.tag_ids: upd['tag_ids'] = [(6, 0, tags.ids)]
        if not lead.partner_id: upd['partner_id'] = partner.id
        if not lead.user_id: upd['user_id'] = owner.id
        if upd: lead.write(upd)
    else:
        lead_name = f"{partner_name} — {cfg.get('city', '')}" if cfg.get('city') else partner_name
        lead_vals = {
            'name': lead_name,
            'partner_id': partner.id, 'partner_name': partner_name,
            'email_from': email, 'user_id': owner.id, 'team_id': team.id,
            'stage_id': stage_qualifica.id, 'source_id': source.id,
            'medium_id': medium.id, 'expected_revenue': 0, 'priority': '1',
            'country_id': country.id,
        }
        if contact_name: lead_vals['contact_name'] = contact_name
        if cfg.get('phone'): lead_vals.update({'phone': cfg['phone'], 'mobile': cfg['phone']})
        if cfg.get('street'): lead_vals['street'] = cfg['street']
        if cfg.get('city'): lead_vals['city'] = cfg['city']
        if cfg.get('zip'): lead_vals['zip'] = cfg['zip']
        if state: lead_vals['state_id'] = state.id
        if tags: lead_vals['tag_ids'] = [(6, 0, tags.ids)]
        if cfg.get('description'): lead_vals['description'] = cfg['description']
        lead = env['crm.lead'].create(lead_vals)
        lead.date_open = datetime.now()

    res['lead_id'] = lead.id
    res['lead_url'] = f"https://erp.casafolino.com/odoo/crm/{lead.id}"

    # Followers
    if cfg.get('followers'):
        for user in cfg['followers']:
            if user:
                lead.message_subscribe(partner_ids=[user.partner_id.id])

    env.cr.commit()

    # Render preview
    rendered = template._render_field('body_html', [lead.id], compute_lang=True)
    body_html = rendered.get(lead.id, '')
    subject_rendered = template._render_field('subject', [lead.id])
    subject_text = subject_rendered.get(lead.id, template.subject)
    email_to_rendered = template._render_field('email_to', [lead.id])
    email_to_text = email_to_rendered.get(lead.id, email)

    slug = re.sub(r'[^a-z0-9]', '_', email.lower())
    preview_path = f'/tmp/preview_{slug}.html'

    att_info = ', '.join(
        f"{a.name} ({round(a.file_size/1024/1024, 1)} MB)" for a in template.attachment_ids
    ) if template.attachment_ids else 'nessuno'
    res['attachments'] = len(template.attachment_ids)

    preview_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{cfg['label']}</title></head><body>
<div style="background:#f5f5f5;padding:20px;font-family:sans-serif;max-width:700px;margin:auto;">
  <h2 style="color:#6B4A1E;border-bottom:2px solid #6B4A1E;padding-bottom:8px;">{cfg['label']}</h2>
  <table style="width:100%;border-collapse:collapse;margin-bottom:15px;font-size:13px;">
    <tr><td style="padding:4px 8px;"><strong>Subject:</strong></td><td>{subject_text}</td></tr>
    <tr><td style="padding:4px 8px;"><strong>From:</strong></td><td>{template.email_from}</td></tr>
    <tr><td style="padding:4px 8px;"><strong>To:</strong></td><td>{email_to_text}</td></tr>
    <tr><td style="padding:4px 8px;"><strong>Cc:</strong></td><td>{template.email_cc or '—'}</td></tr>
    <tr><td style="padding:4px 8px;"><strong>Allegati:</strong></td><td>{att_info}</td></tr>
    <tr><td style="padding:4px 8px;"><strong>Lead ID:</strong></td><td><a href="{res['lead_url']}">{lead.id}</a></td></tr>
    <tr><td style="padding:4px 8px;"><strong>Owner:</strong></td><td>{owner.name}</td></tr>
  </table>
  <div style="background:white;padding:20px;border:1px solid #ddd;border-radius:4px;">
    {body_html}
  </div>
</div>
</body></html>"""

    with open(preview_path, 'w') as f:
        f.write(preview_html)
    res['preview_path'] = preview_path

    # Send mail (only if TEST_MODE=false)
    if not TEST_MODE:
        import time as _time
        mail_id = template.send_mail(lead.id, force_send=True)
        env.cr.commit()
        # Odoo deletes mail.mail after successful force_send — handle gracefully
        mail = env['mail.mail'].browse(mail_id)
        if mail.exists():
            res['mail_sent'] = {
                'mail_id': mail.id, 'state': mail.state,
                'message_id': mail.message_id or None,
                'failure_reason': mail.failure_reason or None,
            }
        else:
            # Deleted = successfully sent. Check chatter for message_id.
            chatter_msg = env['mail.message'].search([
                ('model', '=', 'crm.lead'), ('res_id', '=', lead.id),
                ('message_type', '=', 'email'),
            ], order='id desc', limit=1)
            res['mail_sent'] = {
                'mail_id': mail_id, 'state': 'sent',
                'message_id': chatter_msg.message_id if chatter_msg else None,
                'failure_reason': None,
            }
        # Rate-limit: 5 seconds between sends
        _time.sleep(5)

    return res, preview_html

# ═══════════════════════════════════════════════════════════════
# STEP 2: DEFINE 6 LEADS
# ═══════════════════════════════════════════════════════════════

tpl_export_en = env.ref('casafolino_crm_export.mail_template_inbound_export_en')
tpl_pl_it = env.ref('casafolino_crm_export.mail_template_inbound_private_label_it')
tpl_it = env.ref('casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet')
tpl_apology = env.ref('casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet_apology')

leads_config = [
    {
        'label': 'Pomona Groupe — Bruno Lagaillarde',
        'partner_name': 'Pomona Groupe',
        'email': 'b.lagaillarde@pomona-groupe.eu',
        'contact_name': 'Bruno Lagaillarde',
        'phone': '+33 6 74 25 98 09',
        'street': '3 Avenue du Docteur Tenine',
        'city': 'Antony',
        'zip': '92160',
        'country': france,
        'tags': 'Inbound Shopify,Distributore,Export,FR,Salón Gourmets 2026,Marca Bologna 2026,EN',
        'notes': 'Pomona Groupe — uno dei principali distributori food in Francia. Bruno Lagaillarde è Commercial and Marketing Director. TRIPLO touch point: Salón Gourmets (Madrid, marzo 2026) + Marca trade fair (Bologna, gennaio 2026) + 3 messaggi inbound dal sito CasaFolino.',
        'description': '3 messaggi inbound 9/5/2026 da Bruno Lagaillarde (Commercial and Marketing Director, Pomona Groupe). Chiede catalogue e price list per esplorare partnership long-term. Touch point: Salón Gourmets e Marca BolognaFiere.',
        'template': tpl_export_en,
        'owner': josefina,
        'team': team_export,
        'source': utm_shopify,
        'medium': utm_website,
    },
    {
        'label': 'Cooperativa Campo — Ylenia Franceschetti',
        'partner_name': 'Cooperativa Campo',
        'email': 'ylenia@coopcampo.it',
        'contact_name': 'Ylenia Franceschetti',
        'phone': '+39 0721 740559',
        'city': 'Fossombrone',
        'zip': '61034',
        'state_name': 'Pesaro Urbino',
        'country': italy,
        'tags': 'Inbound Shopify,Private Label,Co-development,Bio,Distributore,Marche,Australia (mercato finale),IT',
        'notes': 'Cooperativa Campo — distributore prodotti BIO Italia/mondo. Richiesta private label per cliente AUSTRALIANO. 2 ricette: (a) Crema Aglio+Peperoncino+Zenzero, (b) Crema Aglio+Peperoncino. Versione BIO. Vetro 200-250g. Volumi 5-6k vasetti per SKU.',
        'description': 'Richiesta co-development BIO. Ricetta 1: Crema di Aglio (67%), zenzero (17%), olio EVO, acido alimentare E260, peperoncino (0.3%), spezie, erbe aromatiche. Ricetta 2: Crema di Aglio (82%), olio EVO, peperoncino (3%), acido alimentare E260, erbe aromatiche, gomma xantana E415, sale, acido alimentare E330. Obiettivo: versione BIO entrambe. Cliente finale: Australia. Volumi: 5000-6000 vasetti per SKU. Formato vetro 200-250g.',
        'template': tpl_pl_it,
        'owner': antonio,
        'team': team_italia,
        'source': utm_shopify,
        'medium': utm_website,
        'followers': [maria] if maria else [],
    },
    {
        'label': 'Guglielmo Store — Francesca Bulotta',
        'partner_name': 'Guglielmo Store Catanzaro Lido',
        'email': 'guglielmostoreczlido@gmail.com',
        'contact_name': 'Francesca Bulotta',
        'phone': '+39 096 133546',
        'city': 'Catanzaro Lido',
        'state_name': 'Catanzaro',
        'country': italy,
        'tags': 'Inbound Shopify,Dettaglio gourmet,Calabria,Stagionalità estiva,IT',
        'notes': 'Guglielmo Store — punto vendita Catanzaro Lido (Calabria, territorio CasaFolino). Inserisce prodotti locali per stagione estiva turistica. Email Gmail (non aziendale). Telefono potrebbe essere incompleto: 096133546 (verificare in qualifica).',
        'description': 'Titolare di Guglielmo Store a Catanzaro Lido. Inserisce prodotti locali per stagione estiva in vista del gran turismo. Vuole catalogo per rivendita.',
        'template': tpl_it,
        'owner': martina,
        'team': team_italia,
        'source': utm_shopify,
        'medium': utm_website,
    },
    {
        'label': 'Apicoltura Ardesia — Renzo Abbondandolo',
        'partner_name': 'Apicoltura Ardesia',
        'email': 'ardesiasrls@libero.it',
        'contact_name': 'Renzo Abbondandolo',
        'phone': '+39 334 7075850',
        'country': italy,
        'tags': 'Inbound Shopify,Dettaglio gourmet,Apicoltura,Apologia,IT',
        'notes': 'Azienda Apistica Ardesia (Ardesia SRLs). FLAG: Renzo lamenta tentativi di contatto precedenti senza risposta — TONO MAIL = APOLOGIA. Potenziale cross-selling: lui vende miele, integra creme/risotti/spezie/cantucci/cioccolati CasaFolino come complemento.',
        'description': 'Renzo Abbondandolo (Apicoltura Ardesia, libero.it). Si propone come rivenditore retail. Lamentela: ha provato più volte a contattarci (telefono e mail) senza ricevere risposta. Va gestito con apologia esplicita.',
        'template': tpl_apology,
        'owner': martina,
        'team': team_italia,
        'source': utm_shopify,
        'medium': utm_website,
    },
    {
        'label': 'Hiperideal — Mariana Furquim',
        'partner_name': 'Hiperideal',
        'email': 'mariana.furquim@hiperideal.com.br',
        'contact_name': 'Mariana Furquim',
        'city': 'Salvador',
        'state_name': 'Bahia',
        'country': brazil,
        'tags': 'Inbound Shopify,Distributore,Retail Chain,Export,BR,Direct Import,EN',
        'notes': 'Hiperideal — catena retail con 28 store a Salvador (Bahia, Brasile). Mariana Furquim è Buyer Imports. Vuole valutare import diretto. Lead di valore: dimensione + ruolo qualificato + import diretto = potenziale serio.',
        'description': 'Mariana Furquim, Buyer Imports presso Hiperideal (food retail chain con 28 store, Salvador, Bahia, Brasile). Vuole conoscere prodotti e valutare direct import.',
        'template': tpl_export_en,
        'owner': josefina,
        'team': team_export,
        'source': utm_shopify,
        'medium': utm_website,
    },
    {
        'label': 'Negozio Luana — Pavia',
        'partner_name': 'Negozio Luana — Pavia',
        'email': 'luana_30@hotmail.it',
        'contact_name': 'Luana',
        'phone': '+39 340 9087341',
        'state_name': 'Pavia',
        'country': italy,
        'tags': 'Inbound Shopify,Dettaglio gourmet,Bio,Lombardia,Adv Social,IT',
        'notes': 'Luana F. (cognome non specificato). Piccolo negozio in provincia di Pavia: artigianali, BIO, caffè, tè, cioccolato. Origine siciliana, ama prodotti del Sud Italia. ARRIVATA DA REEL SPONSORIZZATO = adv social converte. Nome negozio da chiedere in qualifica.',
        'description': 'Luana F., titolare piccolo negozio prov. Pavia (artigianali, BIO, caffè, tè, cioccolato). Origini siciliane. Trovata CasaFolino tramite reel sponsorizzato qualche settimana fa. Chiede info su condizioni vendita, cataloghi e listini.',
        'template': tpl_it,
        'owner': martina,
        'team': team_italia,
        'source': utm_reel,
        'medium': utm_social,
    },
]

# ═══════════════════════════════════════════════════════════════
# STEP 3: EXECUTE 6 LEADS
# ═══════════════════════════════════════════════════════════════

all_results = []
all_previews = []

for i, cfg in enumerate(leads_config, 1):
    print(f"\n{'─' * 60}")
    print(f"LEAD {i}/6: {cfg['label']}")
    print(f"{'─' * 60}")

    # Resolve state
    if cfg.get('state_name'):
        cfg['state'] = resolve_state(cfg['state_name'], cfg['country'])

    result, preview_html = create_lead(cfg)
    all_results.append(result)
    all_previews.append(preview_html)

    status = "EXISTED" if result['lead_existed'] else "CREATED"
    print(f"  → Lead {status}: ID {result['lead_id']} — {result['lead_url']}")
    print(f"  → Partner {'existed' if result['partner_existed'] else 'created'}: ID {result['partner_id']}")
    print(f"  → Tags: {len(result['tags_applied'])} applied, {len(result['tags_created'])} created")
    print(f"  → Attachments: {result['attachments']}")
    print(f"  → Preview: {result['preview_path']}")
    if result.get('mail_sent'):
        print(f"  → Mail: {result['mail_sent']['state']}")

# ═══════════════════════════════════════════════════════════════
# STEP 4: COMBINED PREVIEW FILE
# ═══════════════════════════════════════════════════════════════

combined_path = '/tmp/all_previews_20260509.html'
combined_html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Batch Preview — 9 maggio 2026</title>
<style>
  body { font-family: sans-serif; background: #eee; }
  .separator { text-align: center; padding: 30px; color: #999; font-size: 18px; border-top: 3px solid #6B4A1E; margin: 40px 0; }
</style>
</head><body>
<div style="max-width:750px;margin:auto;padding:20px;">
  <h1 style="color:#6B4A1E;">Batch Inbound — 9 maggio 2026 (6 lead)</h1>
"""

for i, (cfg, preview) in enumerate(zip(leads_config, all_previews)):
    if i > 0:
        combined_html += f'<div class="separator">── Lead {i+1}/6 ──</div>\n'
    # Extract the body div from preview
    combined_html += preview.split('<body>')[1].split('</body>')[0] if '<body>' in preview else preview

combined_html += "\n</div></body></html>"

with open(combined_path, 'w') as f:
    f.write(combined_html)

print(f"\n✓ Combined preview: {combined_path}")

# ═══════════════════════════════════════════════════════════════
# STEP 5: BOJAN DRAFT
# ═══════════════════════════════════════════════════════════════

bojan_draft = """TO: bojanradul83@gmail.com
SUBJECT: CasaFolino — shipping to Croatia & online ordering

Hi Bojan,

Thanks for reaching out. Yes, we ship to Croatia from our online store at casafolino.com — Croatia is in the EU so shipping is straightforward (4-6 working days).

You can browse our full catalogue and order directly at https://casafolino.com.

If you'd like, let me know which products you're interested in and I can confirm shipping cost and total before you place the order.

Looking forward to your order,

Best regards,
Teresa Furgiule
CasaFolino Customer Care
"""

bojan_path = '/tmp/draft_email_bojan.txt'
with open(bojan_path, 'w') as f:
    f.write(bojan_draft)

print(f"✓ Bojan draft: {bojan_path}")

# ═══════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 90)
print(f"{'LEAD':<25} | {'ID':>5} | {'STATUS':<8} | {'TEMPLATE':<20} | {'OWNER':<10} | {'TAGS':>4} | {'ATT':>3}")
print("-" * 90)

tpl_short = {
    tpl_export_en.id: 'export_en',
    tpl_pl_it.id: 'private_label_it',
    tpl_it.id: 'inbound_it',
    tpl_apology.id: 'inbound_apology',
}

for cfg, res in zip(leads_config, all_results):
    label = cfg['label'][:24]
    lid = res['lead_id']
    status = 'EXISTED' if res['lead_existed'] else 'NEW'
    tpl_name = tpl_short.get(cfg['template'].id, '?')
    owner_name = cfg['owner'].name.split()[0]
    n_tags = len(res['tags_applied'])
    n_att = res['attachments']
    print(f"{label:<25} | {lid:>5} | {status:<8} | {tpl_name:<20} | {owner_name:<10} | {n_tags:>4} | {n_att:>3}")

print("=" * 90)
print(f"\nTest mode: {TEST_MODE}")
print(f"Combined preview: {combined_path}")
print(f"Bojan draft: {bojan_path}")

if not TEST_MODE:
    print("\n--- MAIL SEND RESULTS ---")
    for cfg, res in zip(leads_config, all_results):
        ms = res.get('mail_sent', {})
        if ms:
            print(f"  {cfg['label'][:30]}: state={ms.get('state')}, msg_id={ms.get('message_id','N/A')}")
            if ms.get('failure_reason'):
                print(f"    ✗ FAILURE: {ms['failure_reason']}")

print("\n" + "=" * 90)
print("RESULT JSON (all 6)")
print("=" * 90)
print(json.dumps(all_results, indent=2, ensure_ascii=False))
print("=" * 90 + "\n")
