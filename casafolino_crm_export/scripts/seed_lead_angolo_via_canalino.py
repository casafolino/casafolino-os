#!/usr/bin/env python3
"""
Seed script: Angolo Via Canalino — Modena (gift gourmet)
Inbound Shopify 2026-05-09

Usage (inside odoo-app container):
  TEST_MODE=true  → crea partner/lead + render preview, NON invia mail
  TEST_MODE=false → crea partner/lead + invia mail realmente

  docker exec -e TEST_MODE=true odoo-app odoo shell -d folinofood --no-http < script.py
"""
import os
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() in ('true', '1', 'yes')

# ═══════════════════════════════════════════════════════════════
# 1. VERIFICHE PRELIMINARI
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("SEED: Angolo Via Canalino — Modena (Inbound IT Dettaglio Gourmet)")
print(f"TEST_MODE: {TEST_MODE}")
print("=" * 60 + "\n")

# Martina user
martina = env['res.users'].search([('login', '=', 'martina.sinopoli@casafolino.com')], limit=1)
if not martina:
    print("✗ BLOCKER: Utente Martina (martina.sinopoli@casafolino.com) non trovato!")
    raise SystemExit(1)
print(f"✓ Martina user_id: {martina.id} ({martina.name})")

# Country Italia
italy = env['res.country'].search([('code', '=', 'IT')], limit=1)
assert italy, "BLOCKER: res.country IT non trovato"
print(f"✓ Italia country_id: {italy.id}")

# Provincia Modena
modena_state = env['res.country.state'].search([
    ('country_id', '=', italy.id),
    ('name', 'ilike', 'Modena')
], limit=1)
if not modena_state:
    # Try code-based search
    modena_state = env['res.country.state'].search([
        ('country_id', '=', italy.id),
        ('code', '=', 'MO')
    ], limit=1)
if modena_state:
    print(f"✓ Provincia Modena: {modena_state.id} ({modena_state.name})")
else:
    print("⚠ Provincia Modena non trovata — procedo senza state_id")

# Stage Qualifica
stage_qualifica = env['crm.stage'].search([('name', 'ilike', 'Qualifica')], limit=1)
if not stage_qualifica:
    # Try common Odoo names
    stage_qualifica = env['crm.stage'].search([('name', 'ilike', 'Qualif')], limit=1)
if not stage_qualifica:
    # Fallback: first stage (Nuovo/New)
    stage_qualifica = env['crm.stage'].search([], order='sequence', limit=1)
    print(f"⚠ Stage 'Qualifica' non trovato — uso primo stage: {stage_qualifica.name}")
else:
    print(f"✓ Stage Qualifica: {stage_qualifica.id} ({stage_qualifica.name})")

# Template
template_xmlid = 'casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet'
template = env.ref(template_xmlid, raise_if_not_found=False)
if not template:
    print(f"✗ BLOCKER: Template {template_xmlid} non trovato! Eseguire -u casafolino_crm_export prima.")
    raise SystemExit(1)
print(f"✓ Template: {template.id} — {template.name}")

# Tags
tag_xmlids = [
    'casafolino_crm_export.tag_inbound_shopify',
    'casafolino_crm_export.tag_dettaglio_gourmet',
    'casafolino_crm_export.tag_gift_ceste',
    'casafolino_crm_export.tag_geo_emilia_romagna',
    'casafolino_crm_export.tag_geo_it',
]
tags = env['crm.tag']
for xmlid in tag_xmlids:
    tag = env.ref(xmlid, raise_if_not_found=False)
    if tag:
        tags |= tag
        print(f"  ✓ Tag: {tag.name}")
    else:
        print(f"  ⚠ Tag {xmlid} non trovato — skip")

# UTM source
utm_source = env.ref('casafolino_crm_export.utm_source_shopify_contact_form', raise_if_not_found=False)
if not utm_source:
    utm_source = env['utm.source'].search([('name', '=', 'Shopify Contact Form')], limit=1)
    if not utm_source:
        utm_source = env['utm.source'].create({'name': 'Shopify Contact Form'})
print(f"✓ UTM source: {utm_source.id} — {utm_source.name}")

# UTM medium Website
utm_medium = env['utm.medium'].search([('name', 'ilike', 'Website')], limit=1)
if not utm_medium:
    utm_medium = env['utm.medium'].create({'name': 'Website'})
print(f"✓ UTM medium: {utm_medium.id} — {utm_medium.name}")

# Team di Martina
team = martina.sale_team_id or env['crm.team'].search([], limit=1)
print(f"✓ Team: {team.id} — {team.name}")

# Outgoing mail server Martina
mail_server = env['ir.mail_server'].search([
    ('smtp_user', 'ilike', 'martina')
], limit=1)
if not mail_server:
    mail_server = env['ir.mail_server'].search([('active', '=', True)], limit=1)
if mail_server:
    print(f"✓ Mail server: {mail_server.id} — {mail_server.name} (smtp_user: {mail_server.smtp_user})")
else:
    print("⚠ Nessun mail server attivo trovato — la mail potrebbe non partire")

print()

# ═══════════════════════════════════════════════════════════════
# 2. PARTNER AZIENDA (idempotente)
# ═══════════════════════════════════════════════════════════════

EMAIL = 'angoloviacanalino@gmail.com'
PHONE = '+39 340 8250303'

partner = env['res.partner'].search([
    ('email', '=', EMAIL),
    ('is_company', '=', True)
], limit=1)

partner_vals = {
    'name': 'Angolo Via Canalino',
    'is_company': True,
    'street': 'Via Canalino, 61',
    'zip': '41121',
    'city': 'Modena',
    'state_id': modena_state.id if modena_state else False,
    'country_id': italy.id,
    'email': EMAIL,
    'phone': PHONE,
    'mobile': PHONE,
    'comment': (
        "Negozio di casalinghi + tipicità alimentari modenesi. "
        "Brand trattati: La Porcellana Bianca, Easy Life, Tognana, Muha. "
        "Attivo su ceste/confezioni regalo. ~2.200 follower IG (@angolo_via_canalino). "
        "Fonte: contatto Shopify 2026-05-09."
    ),
}

if partner:
    # Update missing fields only
    update_vals = {k: v for k, v in partner_vals.items() if not partner[k]}
    if update_vals:
        partner.write(update_vals)
    print(f"✓ Partner azienda (esistente, aggiornato): ID {partner.id}")
else:
    partner = env['res.partner'].create(partner_vals)
    print(f"✓ Partner azienda creato: ID {partner.id}")

# ═══════════════════════════════════════════════════════════════
# 3. CONTATTO CHILD — Debora (idempotente)
# ═══════════════════════════════════════════════════════════════

contact = env['res.partner'].search([
    ('parent_id', '=', partner.id),
    ('name', 'ilike', 'Debora')
], limit=1)

if not contact:
    contact = env['res.partner'].create({
        'parent_id': partner.id,
        'name': 'Debora',
        'function': 'Contatto commerciale',
        'email': EMAIL,
        'phone': PHONE,
        'type': 'contact',
    })
    print(f"✓ Contatto Debora creato: ID {contact.id}")
else:
    print(f"✓ Contatto Debora (esistente): ID {contact.id}")

# ═══════════════════════════════════════════════════════════════
# 4. LEAD (idempotente — cerca lead aperto ultimi 30gg)
# ═══════════════════════════════════════════════════════════════

thirty_days_ago = datetime.now() - timedelta(days=30)
lead = env['crm.lead'].search([
    ('email_from', '=', EMAIL),
    ('create_date', '>=', thirty_days_ago.strftime('%Y-%m-%d')),
    ('active', '=', True),
], limit=1)

lead_vals = {
    'name': 'Angolo Via Canalino — Modena (gift gourmet)',
    'partner_id': partner.id,
    'partner_name': 'Angolo Via Canalino',
    'contact_name': 'Debora',
    'email_from': EMAIL,
    'phone': PHONE,
    'mobile': PHONE,
    'street': 'Via Canalino, 61',
    'zip': '41121',
    'city': 'Modena',
    'state_id': modena_state.id if modena_state else False,
    'country_id': italy.id,
    'user_id': martina.id,
    'team_id': team.id,
    'stage_id': stage_qualifica.id,
    'tag_ids': [(6, 0, tags.ids)] if tags else False,
    'source_id': utm_source.id,
    'medium_id': utm_medium.id,
    'description': (
        "Buongiorno, sono interessata ai vostri prodotti, è possibile avere il catalogo "
        "con listino prezzi e condizioni economiche. Grazie. Cordiali Saluti. Debora."
    ),
    'expected_revenue': 0,
    'priority': '1',
}

if lead:
    # Update missing fields
    update_vals = {}
    for k, v in lead_vals.items():
        if k == 'tag_ids':
            if not lead.tag_ids:
                update_vals[k] = v
        elif not lead[k]:
            update_vals[k] = v
    if update_vals:
        lead.write(update_vals)
    print(f"✓ Lead (esistente, aggiornato): ID {lead.id}")
else:
    lead = env['crm.lead'].create(lead_vals)
    print(f"✓ Lead creato: ID {lead.id}")

# Set date_open
if not lead.date_open:
    lead.date_open = datetime.now()

env.cr.commit()
print()

# ═══════════════════════════════════════════════════════════════
# 5. CATALOGO — identifica in Odoo Documents e rendi pubblico
# ═══════════════════════════════════════════════════════════════

import os as _os

ATT_MASTER_NAME = 'CasaFolino Catalogue EN 2026 \u2014 Master'

# Cerca catalogo EN tra tutti i PDF in Documents (ricerca per nome, poi per dimensione)
keywords = ['catalogue', 'catalog', 'catalogo']

# Step 1: search in "Cataloghi" folders
cataloghi_folders = env['documents.document'].search([
    ('name', 'ilike', 'Cataloghi'),
    ('type', '=', 'folder'),
])
candidates = env['documents.document']
if cataloghi_folders:
    candidates = env['documents.document'].search([
        ('folder_id', 'in', cataloghi_folders.ids),
        ('type', '!=', 'folder'),
    ])
    print(f"✓ Folders 'Cataloghi' trovati: {[(f.id, f.name) for f in cataloghi_folders]}")

# Step 2: filter by keyword
matches = [d for d in candidates if d.attachment_id and any(kw in (d.name or '').lower() for kw in keywords)]

# Step 3: if nothing in Cataloghi folders, broaden search
if not matches:
    all_pdfs = env['documents.document'].search([
        ('type', '!=', 'folder'),
    ], limit=100)
    matches = [d for d in all_pdfs if d.attachment_id and any(kw in (d.name or '').lower() for kw in keywords)]
    if matches:
        print(f"✓ Catalogo trovato via ricerca globale")

if not matches:
    print("⚠ Nessun PDF con nome catalogue/catalog/catalogo trovato in Documents")
    raise Exception("Catalogo non identificabile — caricare il PDF nel folder 'Cataloghi' di Documents")

# Filter for EN specifically if multiple
en_matches = [d for d in matches if 'en' in (d.name or '').lower()]
if en_matches:
    matches = en_matches

# Pick largest
matches.sort(key=lambda d: d.attachment_id.file_size if d.attachment_id else 0, reverse=True)
if len(matches) > 1:
    print(f"⚠ {len(matches)} candidati — uso il piu grande:")
    for d in matches:
        size = d.attachment_id.file_size if d.attachment_id else 0
        print(f"   - {d.name} (id={d.id}, {round(size/1024/1024, 1)} MB)")

doc = matches[0]
attachment = doc.attachment_id
if not attachment:
    raise Exception(f"documents.document id={doc.id} non ha attachment_id collegato")

# Rendi pubblico + rinomina attachment per matching controller
attachment.write({
    'public': True,
    'name': ATT_MASTER_NAME,
})
print(f"✓ Catalogo identificato in Documents:")
print(f"   documents.document: id={doc.id}, name={doc.name}")
print(f"   ir.attachment: id={attachment.id}, name={attachment.name}, public=True, size={attachment.file_size} bytes")

# Rimuovi eventuali vecchi attachment dal template (il catalogo ora va via link)
if template.attachment_ids:
    template.write({'attachment_ids': [(5, 0, 0)]})
    print("✓ Vecchi attachment rimossi dal template (catalogo ora via link CTA)")

env.cr.commit()

# ═══════════════════════════════════════════════════════════════
# 6. RENDER PREVIEW
# ═══════════════════════════════════════════════════════════════

print("\n--- RENDER PREVIEW ---")

# Render template
rendered = template._render_field('body_html', [lead.id], compute_lang=True)
body_html = rendered.get(lead.id, '')

subject_rendered = template._render_field('subject', [lead.id])
subject_text = subject_rendered.get(lead.id, template.subject)

email_to_rendered = template._render_field('email_to', [lead.id])
email_to_text = email_to_rendered.get(lead.id, EMAIL)

# Build preview HTML
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
    <tr><td><strong>Cc:</strong></td><td>{template.email_cc}</td></tr>
    <tr><td><strong>Allegati:</strong></td><td>{', '.join(a.name + ' (' + str(round(a.file_size/1024/1024, 1)) + ' MB)' for a in template.attachment_ids)}</td></tr>
  </table>
  <div style="background:white;padding:20px;border:1px solid #ddd;border-radius:4px;">
    {body_html}
  </div>
</div>
</body>
</html>"""

preview_path = '/tmp/preview_angolo_via_canalino.html'
with open(preview_path, 'w') as f:
    f.write(preview_html)

print(f"  Subject: {subject_text}")
print(f"  From: {template.email_from}")
print(f"  To: {email_to_text}")
print(f"  Cc: {template.email_cc}")
att_info = ', '.join(f"{a.name} ({round(a.file_size/1024/1024, 1)} MB)" for a in template.attachment_ids)
print(f"  Allegati: {att_info or 'nessuno'}")
print(f"  Preview: {preview_path} ({_os.path.getsize(preview_path)} bytes)")

# ═══════════════════════════════════════════════════════════════
# 7. INVIO MAIL (solo se TEST_MODE=false)
# ═══════════════════════════════════════════════════════════════

if not TEST_MODE:
    print("\n--- INVIO MAIL ---")
    mail_id = template.send_mail(lead.id, force_send=True)
    mail = env['mail.mail'].browse(mail_id)
    env.cr.commit()

    print(f"  ✓ mail.mail ID: {mail.id}")
    print(f"  State: {mail.state}")
    print(f"  email_from: {mail.email_from}")
    print(f"  email_to: {mail.email_to}")
    print(f"  message_id SMTP: {mail.message_id or 'N/A'}")

    # Verify chatter
    last_msg = env['mail.message'].search([
        ('model', '=', 'crm.lead'),
        ('res_id', '=', lead.id),
        ('message_type', '=', 'email'),
    ], order='id desc', limit=1)
    if last_msg:
        print(f"  ✓ Chatter message: ID {last_msg.id}")
    else:
        print("  ⚠ Chatter message non trovato")
else:
    print("\n--- TEST_MODE=true → Mail NON inviata ---")

# ═══════════════════════════════════════════════════════════════
# 8. OUTPUT FINALE
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("RISULTATO FINALE")
print("=" * 60)
print(f"✓ Partner azienda: ID {partner.id}")
print(f"✓ Partner contatto (Debora): ID {contact.id}")
print(f"✓ Lead ID: {lead.id} — https://erp.casafolino.com/odoo/crm/{lead.id}")
print(f"✓ Template ID: {template.id}")
print(f"✓ Tags applicati: {', '.join(t.name for t in lead.tag_ids)}")
print(f"✓ Preview: {preview_path}")
print(f"✓ Mail inviata: {'SI' if not TEST_MODE else 'NO (TEST_MODE)'}")
if not TEST_MODE:
    print(f"✓ message_id SMTP: {mail.message_id or 'N/A'}")
print("=" * 60 + "\n")
