#!/usr/bin/env python3
"""
Generic Inbound Lead Workflow — CasaFolino CRM Export

Creates partner + optional child contact + CRM lead + applies mail template.
All parameters via environment variables. Idempotent — safe to re-run.

Usage:
  docker exec -e PARTNER_NAME="..." -e EMAIL="..." -e TEMPLATE_XMLID="..." \
    [-e TEST_MODE=true] odoo-app \
    odoo shell -d folinofood --no-http < seed_inbound_lead.py
"""
import json
import os
import re
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 0. READ ENV VARS
# ═══════════════════════════════════════════════════════════════

PARTNER_NAME = os.environ.get('PARTNER_NAME', '').strip()
EMAIL = os.environ.get('EMAIL', '').strip()
CONTACT_NAME = os.environ.get('CONTACT_NAME', '').strip()
PHONE = os.environ.get('PHONE', '').strip()
STREET = os.environ.get('STREET', '').strip()
CITY = os.environ.get('CITY', '').strip()
ZIP_CODE = os.environ.get('ZIP', '').strip()
STATE_NAME = os.environ.get('STATE_NAME', '').strip()
COUNTRY_CODE = os.environ.get('COUNTRY_CODE', 'IT').strip()
NOTES = os.environ.get('NOTES', '').strip()
EXTRA_TAGS = os.environ.get('EXTRA_TAGS', '').strip()
TEMPLATE_XMLID = os.environ.get('TEMPLATE_XMLID', '').strip()
STAGE_NAME = os.environ.get('STAGE_NAME', 'Qualifica').strip()
OWNER_LOGIN = os.environ.get('OWNER_LOGIN', 'martina.sinopoli@casafolino.com').strip()
SOURCE_NAME = os.environ.get('SOURCE_NAME', 'Shopify Contact Form').strip()
MEDIUM_NAME = os.environ.get('MEDIUM_NAME', 'Website').strip()
LEAD_DESCRIPTION = os.environ.get('LEAD_DESCRIPTION', '').strip()
TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() in ('true', '1', 'yes')
FORCE_NEW_LEAD = os.environ.get('FORCE_NEW_LEAD', 'false').lower() in ('true', '1', 'yes')

# Output collector
result = {
    'status': 'ok',
    'test_mode': TEST_MODE,
    'partner_id': None,
    'partner_existed': False,
    'child_contact_id': None,
    'lead_id': None,
    'lead_existed': False,
    'lead_url': None,
    'tags_applied': [],
    'tags_created': [],
    'preview_path': None,
    'mail_sent': None,
    'warnings': [],
}

def fail(msg):
    result['status'] = 'error'
    print(f"\n✗ ERROR: {msg}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(1)

def blocker(msg):
    result['status'] = 'blocker'
    print(f"\n✗ BLOCKER: {msg}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(1)

def warn(msg):
    result['warnings'].append(msg)
    print(f"  ⚠ {msg}")

# ═══════════════════════════════════════════════════════════════
# 1. VALIDAZIONI PRELIMINARI
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("INBOUND LEAD WORKFLOW — Generic")
print(f"TEST_MODE: {TEST_MODE}")
print("=" * 60 + "\n")

if not PARTNER_NAME:
    fail("PARTNER_NAME obbligatorio (env var mancante)")
if not EMAIL:
    fail("EMAIL obbligatorio (env var mancante)")
if not TEMPLATE_XMLID:
    fail("TEMPLATE_XMLID obbligatorio (env var mancante)")

# Email validation
if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', EMAIL):
    fail(f"EMAIL non valido: {EMAIL}")

print(f"Partner: {PARTNER_NAME}")
print(f"Email: {EMAIL}")
print(f"Contact: {CONTACT_NAME or '(nessuno)'}")
print(f"Template: {TEMPLATE_XMLID}")
print()

# Owner
owner = env['res.users'].search([('login', '=', OWNER_LOGIN)], limit=1)
if not owner:
    blocker(f"Owner '{OWNER_LOGIN}' non trovato tra gli utenti Odoo")
print(f"✓ Owner: {owner.id} ({owner.name})")

# Country
country = env['res.country'].search([('code', '=', COUNTRY_CODE)], limit=1)
if not country:
    blocker(f"Country code '{COUNTRY_CODE}' non trovato")
print(f"✓ Country: {country.name} ({COUNTRY_CODE})")

# State (optional)
state = False
if STATE_NAME:
    state = env['res.country.state'].search([
        ('country_id', '=', country.id),
        ('name', 'ilike', STATE_NAME)
    ], limit=1)
    if not state:
        # Try matching by code (2-letter province code)
        state = env['res.country.state'].search([
            ('country_id', '=', country.id),
            ('code', 'ilike', STATE_NAME)
        ], limit=1)
    if state:
        print(f"✓ State: {state.name} ({state.code})")
    else:
        warn(f"State '{STATE_NAME}' non trovato — procedo senza state_id")

# Stage
stage = env['crm.stage'].search([('name', 'ilike', STAGE_NAME)], limit=1)
if not stage:
    blocker(f"Stage '{STAGE_NAME}' non trovato nel CRM — non creato automaticamente")
print(f"✓ Stage: {stage.id} ({stage.name})")

# Template
template = env.ref(TEMPLATE_XMLID, raise_if_not_found=False)
if not template:
    blocker(f"Template '{TEMPLATE_XMLID}' non trovato — eseguire -u casafolino_crm_export prima")
print(f"✓ Template: {template.id} — {template.name}")

# Team
team = owner.sale_team_id or env['crm.team'].search([], limit=1)
print(f"✓ Team: {team.id} — {team.name}")

# Mail server (best effort: match owner's email prefix)
owner_prefix = OWNER_LOGIN.split('@')[0] if '@' in OWNER_LOGIN else ''
mail_server = env['ir.mail_server'].search([
    ('smtp_user', 'ilike', owner_prefix)
], limit=1) if owner_prefix else False
if not mail_server:
    mail_server = env['ir.mail_server'].search([('active', '=', True)], limit=1)
if mail_server:
    print(f"✓ Mail server: {mail_server.id} — {mail_server.name}")
else:
    warn("Nessun mail server attivo — la mail potrebbe non partire")

# ═══════════════════════════════════════════════════════════════
# 2. TAGS (resolve or create)
# ═══════════════════════════════════════════════════════════════

TAG_COLORS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # Odoo tag color palette
tags = env['crm.tag']
tags_created_names = []

if EXTRA_TAGS:
    tag_names = [t.strip() for t in EXTRA_TAGS.split(',') if t.strip()]
    for i, tag_name in enumerate(tag_names):
        tag = env['crm.tag'].search([('name', '=ilike', tag_name)], limit=1)
        if not tag:
            tag = env['crm.tag'].create({
                'name': tag_name,
                'color': TAG_COLORS[i % len(TAG_COLORS)],
            })
            tags_created_names.append(tag_name)
            print(f"  + Tag creato: {tag_name}")
        else:
            print(f"  ✓ Tag: {tag.name}")
        tags |= tag

result['tags_applied'] = [t.name for t in tags]
result['tags_created'] = tags_created_names

# ═══════════════════════════════════════════════════════════════
# 3. UTM SOURCE / MEDIUM (resolve or create)
# ═══════════════════════════════════════════════════════════════

utm_source = env['utm.source'].search([('name', '=ilike', SOURCE_NAME)], limit=1)
if not utm_source:
    utm_source = env['utm.source'].create({'name': SOURCE_NAME})
    print(f"  + UTM source creato: {SOURCE_NAME}")
else:
    print(f"✓ UTM source: {utm_source.name}")

utm_medium = env['utm.medium'].search([('name', '=ilike', MEDIUM_NAME)], limit=1)
if not utm_medium:
    utm_medium = env['utm.medium'].create({'name': MEDIUM_NAME})
    print(f"  + UTM medium creato: {MEDIUM_NAME}")
else:
    print(f"✓ UTM medium: {utm_medium.name}")

print()

# ═══════════════════════════════════════════════════════════════
# 4. PARTNER AZIENDA (idempotente)
# ═══════════════════════════════════════════════════════════════

# Check duplicates
dup_partners = env['res.partner'].search([('email', '=', EMAIL)])
if len(dup_partners) > 1:
    company_partners = dup_partners.filtered(lambda p: p.is_company)
    if len(company_partners) > 1:
        blocker(
            f"Trovati {len(company_partners)} partner azienda con email {EMAIL}: "
            f"{', '.join(f'ID {p.id} ({p.name})' for p in company_partners)}. "
            "Risolvere duplicati manualmente prima di procedere."
        )

partner = env['res.partner'].search([
    ('email', '=', EMAIL),
    ('is_company', '=', True)
], limit=1)

# If no company partner, check individual
if not partner:
    partner = env['res.partner'].search([
        ('email', '=', EMAIL),
        ('is_company', '=', False),
        ('parent_id', '=', False),
    ], limit=1)

partner_vals = {
    'name': PARTNER_NAME,
    'is_company': True,
    'email': EMAIL,
    'country_id': country.id,
}
if PHONE:
    partner_vals['phone'] = PHONE
    partner_vals['mobile'] = PHONE
if STREET:
    partner_vals['street'] = STREET
if CITY:
    partner_vals['city'] = CITY
if ZIP_CODE:
    partner_vals['zip'] = ZIP_CODE
if state:
    partner_vals['state_id'] = state.id
if NOTES:
    partner_vals['comment'] = NOTES

if partner:
    result['partner_existed'] = True
    update_vals = {}
    for k, v in partner_vals.items():
        if k == 'name':
            continue  # Don't overwrite existing name
        try:
            if not partner[k]:
                update_vals[k] = v
        except Exception:
            update_vals[k] = v
    if not partner.is_company:
        update_vals['is_company'] = True
    if update_vals:
        partner.write(update_vals)
    print(f"✓ Partner azienda (esistente, aggiornato): ID {partner.id} — {partner.name}")
else:
    partner = env['res.partner'].create(partner_vals)
    print(f"✓ Partner azienda creato: ID {partner.id} — {partner.name}")

result['partner_id'] = partner.id

# ═══════════════════════════════════════════════════════════════
# 5. CONTATTO CHILD (opzionale, idempotente)
# ═══════════════════════════════════════════════════════════════

child_contact = None
if CONTACT_NAME:
    child_contact = env['res.partner'].search([
        ('parent_id', '=', partner.id),
        ('name', 'ilike', CONTACT_NAME)
    ], limit=1)

    if not child_contact:
        child_vals = {
            'parent_id': partner.id,
            'name': CONTACT_NAME,
            'email': EMAIL,
            'type': 'contact',
        }
        if PHONE:
            child_vals['phone'] = PHONE
        child_contact = env['res.partner'].create(child_vals)
        print(f"✓ Contatto child creato: ID {child_contact.id} — {CONTACT_NAME}")
    else:
        print(f"✓ Contatto child (esistente): ID {child_contact.id} — {child_contact.name}")

    result['child_contact_id'] = child_contact.id

# ═══════════════════════════════════════════════════════════════
# 6. LEAD (idempotente — cerca lead aperto ultimi 90gg)
# ═══════════════════════════════════════════════════════════════

ninety_days_ago = datetime.now() - timedelta(days=90)
existing_lead = env['crm.lead'].search([
    ('email_from', '=', EMAIL),
    ('create_date', '>=', ninety_days_ago.strftime('%Y-%m-%d')),
    ('active', '=', True),
], limit=1)

if existing_lead and not FORCE_NEW_LEAD:
    result['lead_existed'] = True
    result['lead_id'] = existing_lead.id
    result['lead_url'] = f"https://erp.casafolino.com/odoo/crm/{existing_lead.id}"
    lead = existing_lead
    # Update missing fields
    update_vals = {}
    if tags and not lead.tag_ids:
        update_vals['tag_ids'] = [(6, 0, tags.ids)]
    if not lead.partner_id:
        update_vals['partner_id'] = partner.id
    if not lead.user_id:
        update_vals['user_id'] = owner.id
    if update_vals:
        lead.write(update_vals)
    print(f"✓ Lead (esistente): ID {lead.id} — https://erp.casafolino.com/odoo/crm/{lead.id}")
    if FORCE_NEW_LEAD:
        warn("FORCE_NEW_LEAD ignorato perché lead trovato e flag non attivo")
else:
    if existing_lead and FORCE_NEW_LEAD:
        warn(f"Lead esistente ID {existing_lead.id} trovato, ma FORCE_NEW_LEAD=true — creo nuovo")

    lead_name = f"{PARTNER_NAME} — {CITY}" if CITY else PARTNER_NAME
    lead_vals = {
        'name': lead_name,
        'partner_id': partner.id,
        'partner_name': PARTNER_NAME,
        'email_from': EMAIL,
        'user_id': owner.id,
        'team_id': team.id,
        'stage_id': stage.id,
        'source_id': utm_source.id,
        'medium_id': utm_medium.id,
        'expected_revenue': 0,
        'priority': '1',
        'country_id': country.id,
    }
    if CONTACT_NAME:
        lead_vals['contact_name'] = CONTACT_NAME
    if PHONE:
        lead_vals['phone'] = PHONE
        lead_vals['mobile'] = PHONE
    if STREET:
        lead_vals['street'] = STREET
    if CITY:
        lead_vals['city'] = CITY
    if ZIP_CODE:
        lead_vals['zip'] = ZIP_CODE
    if state:
        lead_vals['state_id'] = state.id
    if tags:
        lead_vals['tag_ids'] = [(6, 0, tags.ids)]
    if LEAD_DESCRIPTION:
        lead_vals['description'] = LEAD_DESCRIPTION

    lead = env['crm.lead'].create(lead_vals)
    lead.date_open = datetime.now()
    print(f"✓ Lead creato: ID {lead.id}")

    result['lead_id'] = lead.id
    result['lead_url'] = f"https://erp.casafolino.com/odoo/crm/{lead.id}"

env.cr.commit()

# ═══════════════════════════════════════════════════════════════
# 7. RENDER PREVIEW
# ═══════════════════════════════════════════════════════════════

print("\n--- RENDER PREVIEW ---")

rendered = template._render_field('body_html', [lead.id], compute_lang=True)
body_html = rendered.get(lead.id, '')

subject_rendered = template._render_field('subject', [lead.id])
subject_text = subject_rendered.get(lead.id, template.subject)

email_to_rendered = template._render_field('email_to', [lead.id])
email_to_text = email_to_rendered.get(lead.id, EMAIL)

# Build preview HTML
email_slug = re.sub(r'[^a-z0-9]', '_', EMAIL.lower())
preview_path = f'/tmp/preview_{email_slug}.html'

preview_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Preview: {subject_text}</title></head>
<body>
<div style="background:#f5f5f5;padding:20px;font-family:sans-serif;max-width:700px;margin:auto;">
  <h3 style="color:#333;">PREVIEW — Mail Template Render</h3>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
    <tr><td><strong>Subject:</strong></td><td>{subject_text}</td></tr>
    <tr><td><strong>From:</strong></td><td>{template.email_from}</td></tr>
    <tr><td><strong>To:</strong></td><td>{email_to_text}</td></tr>
    <tr><td><strong>Cc:</strong></td><td>{template.email_cc or ''}</td></tr>
    <tr><td><strong>Allegati:</strong></td><td>{', '.join(a.name + ' (' + str(round(a.file_size/1024/1024, 1)) + ' MB)' for a in template.attachment_ids) if template.attachment_ids else 'nessuno'}</td></tr>
  </table>
  <div style="background:white;padding:20px;border:1px solid #ddd;border-radius:4px;">
    {body_html}
  </div>
</div>
</body>
</html>"""

with open(preview_path, 'w') as f:
    f.write(preview_html)

result['preview_path'] = preview_path

att_info = ', '.join(
    f"{a.name} ({round(a.file_size/1024/1024, 1)} MB)"
    for a in template.attachment_ids
) if template.attachment_ids else 'nessuno'

print(f"  Subject: {subject_text}")
print(f"  From: {template.email_from}")
print(f"  To: {email_to_text}")
print(f"  Cc: {template.email_cc or '—'}")
print(f"  Allegati: {att_info}")
print(f"  Preview: {preview_path}")

# ═══════════════════════════════════════════════════════════════
# 8. INVIO MAIL (solo TEST_MODE=false)
# ═══════════════════════════════════════════════════════════════

if not TEST_MODE:
    print("\n--- INVIO MAIL ---")
    mail_id = template.send_mail(lead.id, force_send=True)
    mail = env['mail.mail'].browse(mail_id)
    env.cr.commit()

    result['mail_sent'] = {
        'mail_id': mail.id,
        'state': mail.state,
        'message_id': mail.message_id or None,
        'failure_reason': mail.failure_reason or None,
    }

    print(f"  ✓ mail.mail ID: {mail.id}")
    print(f"  State: {mail.state}")
    print(f"  message_id: {mail.message_id or 'N/A'}")
    if mail.failure_reason:
        print(f"  ✗ Failure: {mail.failure_reason}")
else:
    print("\n--- TEST_MODE=true → Mail NON inviata ---")

# ═══════════════════════════════════════════════════════════════
# 9. OUTPUT JSON
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("RESULT JSON")
print("=" * 60)
print(json.dumps(result, indent=2, ensure_ascii=False))
print("=" * 60 + "\n")
