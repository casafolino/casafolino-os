#!/usr/bin/env python3
"""
Send remaining 5 leads (728-732) — Pomona (727) already sent.
Uses auto_delete=False to preserve chatter entries.
5-second rate-limit between sends.
"""
import json
import time
import logging

_logger = logging.getLogger(__name__)

print("\n" + "=" * 60)
print("FASE 2 — INVIO REALE — 5 lead rimanenti (728-732)")
print("Pomona (727) già inviata — skipped")
print("=" * 60 + "\n")

# Lead configs: (lead_id, template_xmlid, label)
LEADS = [
    (728, 'casafolino_crm_export.mail_template_inbound_private_label_it', 'Cooperativa Campo'),
    (729, 'casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet', 'Guglielmo Store'),
    (730, 'casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet_apology', 'Apicoltura Ardesia'),
    (731, 'casafolino_crm_export.mail_template_inbound_export_en', 'Hiperideal'),
    (732, 'casafolino_crm_export.mail_template_inbound_it_dettaglio_gourmet', 'Negozio Luana'),
]

results = []

for i, (lead_id, tpl_xmlid, label) in enumerate(LEADS, 1):
    print(f"\n--- {i}/5: {label} (lead {lead_id}) ---")

    lead = env['crm.lead'].browse(lead_id)
    if not lead.exists():
        print(f"  ✗ Lead {lead_id} NOT FOUND — skip")
        results.append({'lead_id': lead_id, 'label': label, 'state': 'error', 'reason': 'lead not found'})
        continue

    template = env.ref(tpl_xmlid, raise_if_not_found=False)
    if not template:
        print(f"  ✗ Template {tpl_xmlid} NOT FOUND — skip")
        results.append({'lead_id': lead_id, 'label': label, 'state': 'error', 'reason': 'template not found'})
        continue

    # Send with auto_delete=False to keep chatter trace
    mail_id = template.send_mail(lead_id, force_send=False, email_values={'auto_delete': False})
    mail = env['mail.mail'].browse(mail_id)

    if not mail.exists():
        print(f"  ✗ mail.mail not created — skip")
        results.append({'lead_id': lead_id, 'label': label, 'state': 'error', 'reason': 'mail not created'})
        continue

    # Now send manually
    mail.send(raise_exception=False)
    env.cr.commit()

    # Re-read state after send
    mail = env['mail.mail'].browse(mail_id)
    if mail.exists():
        state = mail.state
        message_id = mail.mail_message_id.message_id if mail.mail_message_id else None
        failure = mail.failure_reason
    else:
        # Was sent and deleted anyway
        state = 'sent'
        message_id = None
        failure = None
        # Check chatter
        msg = env['mail.message'].search([
            ('model', '=', 'crm.lead'), ('res_id', '=', lead_id),
            ('message_type', '=', 'email'),
        ], order='id desc', limit=1)
        if msg:
            message_id = msg.message_id

    print(f"  email_to: {lead.email_from}")
    print(f"  state: {state}")
    print(f"  message_id: {message_id or 'N/A'}")
    if failure:
        print(f"  ✗ FAILURE: {failure}")

    results.append({
        'lead_id': lead_id,
        'label': label,
        'email': lead.email_from,
        'state': state,
        'message_id': message_id,
        'failure_reason': failure,
    })

    # Rate-limit
    if i < len(LEADS):
        print("  (sleep 5s...)")
        time.sleep(5)

# Summary
print("\n" + "=" * 60)
print("RISULTATO INVIO")
print("=" * 60)
print(f"{'LEAD':<25} | {'ID':>4} | {'STATE':<10} | {'MSG_ID':<50}")
print("-" * 100)
for r in results:
    lbl = r['label'][:24]
    lid = r['lead_id']
    st = r['state']
    mid = (r.get('message_id') or 'N/A')[:49]
    print(f"{lbl:<25} | {lid:>4} | {st:<10} | {mid}")

# Add Pomona (known sent)
print(f"{'Pomona Groupe':<25} | { 727:>4} | {'sent':<10} | {'(sent 03:35 UTC, auto_deleted)'}")

print("=" * 60)

# Check failures
failures = [r for r in results if r['state'] not in ('sent', 'outgoing')]
if failures:
    print(f"\n✗ {len(failures)} FAILURES:")
    for f in failures:
        print(f"  - {f['label']}: {f.get('failure_reason') or f.get('reason')}")
else:
    print(f"\n✓ 5/5 sent + Pomona (already sent) = 6/6 DONE")

print("\nJSON:")
print(json.dumps(results, indent=2, ensure_ascii=False))
