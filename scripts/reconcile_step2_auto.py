#!/usr/bin/env python3
"""
Riconciliazione automatica - match per importo esatto + partner.
Solo match UNIVOCI (1 fattura per 1 pagamento).

Eseguire DENTRO il container Docker:
  docker cp /tmp/reconcile_step2_auto.py odoo-app:/tmp/
  docker exec -i odoo-app python3 /tmp/reconcile_step2_auto.py
"""
import xmlrpc.client
import sys

url = "http://localhost:4589"
db = "folinofood"
user = "antonio@casafolino.com"
pwd = "admin#folino"

common = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/common')
uid = common.authenticate(db, user, pwd, {})
if not uid:
    print("AUTH FAILED")
    sys.exit(1)
models = xmlrpc.client.ServerProxy(url + '/xmlrpc/2/object')
print("Auth OK uid=%d" % uid)


def call(model, method, *args, **kw):
    return models.execute_kw(db, uid, pwd, model, method, *args, **kw)


# ── Pre-check ────────────────────────────────────────────────────────
total_bsl = call('account.bank.statement.line', 'search_count', [[]])
unrec_bsl = call('account.bank.statement.line', 'search_count',
                 [[('is_reconciled', '=', False)]])
print("Total BSL: %d, Unreconciled: %d" % (total_bsl, unrec_bsl))

open_cust = call('account.move', 'search_count',
                 [[('move_type', 'in', ['out_invoice', 'out_refund']),
                   ('state', '=', 'posted'),
                   ('payment_state', 'in', ['not_paid', 'partial'])]])
open_vend = call('account.move', 'search_count',
                 [[('move_type', 'in', ['in_invoice', 'in_refund']),
                   ('state', '=', 'posted'),
                   ('payment_state', 'in', ['not_paid', 'partial'])]])
print("Open invoices: %d customer, %d vendor" % (open_cust, open_vend))

# ── Load unreconciled BSL with partner ────────────────────────────────
print("\nLoading unreconciled bank lines...")
bsl_ids = call('account.bank.statement.line', 'search',
               [[('is_reconciled', '=', False)]], {'limit': 10000})
print("Unreconciled BSL: %d" % len(bsl_ids))

# Read in batches
all_bsl = []
batch = 200
for i in range(0, len(bsl_ids), batch):
    chunk = bsl_ids[i:i + batch]
    data = call('account.bank.statement.line', 'read',
                [chunk], {'fields': ['id', 'amount', 'move_id', 'payment_ref']})
    all_bsl.extend(data)
    if (i + batch) % 1000 == 0:
        print("  Loaded %d/%d BSL..." % (min(i + batch, len(bsl_ids)), len(bsl_ids)))

print("BSL loaded: %d" % len(all_bsl))

# Read partner from account_move
move_ids = list(set(b['move_id'][0] for b in all_bsl if b.get('move_id')))
print("Loading %d account_moves..." % len(move_ids))
move_partner = {}
for i in range(0, len(move_ids), batch):
    chunk = move_ids[i:i + batch]
    data = call('account.move', 'read', [chunk], {'fields': ['id', 'partner_id']})
    for m in data:
        move_partner[m['id']] = m['partner_id'][0] if m['partner_id'] else None

with_partner = sum(1 for v in move_partner.values() if v)
print("Moves with partner: %d/%d" % (with_partner, len(move_partner)))

# ── Match and reconcile ──────────────────────────────────────────────
print("\n=== STARTING RECONCILIATION ===")
matched = 0
skipped_no_partner = 0
skipped_no_match = 0
skipped_ambiguous = 0
errors = 0

for idx, bsl in enumerate(all_bsl):
    move_id = bsl['move_id'][0] if bsl.get('move_id') else None
    if not move_id:
        continue

    partner_id = move_partner.get(move_id)
    if not partner_id:
        skipped_no_partner += 1
        continue

    amount = bsl['amount']
    if amount == 0:
        continue

    # Determine search criteria
    if amount > 0:
        # Customer payment -> match receivable invoice
        inv_domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('partner_id', '=', partner_id),
            ('amount_residual', '>=', amount - 0.02),
            ('amount_residual', '<=', amount + 0.02),
        ]
        account_type = 'asset_receivable'
    else:
        # Vendor payment -> match payable invoice
        search_amount = abs(amount)
        inv_domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('partner_id', '=', partner_id),
            ('amount_residual', '>=', search_amount - 0.02),
            ('amount_residual', '<=', search_amount + 0.02),
        ]
        account_type = 'liability_payable'

    candidates = call('account.move', 'search_read',
                       [inv_domain], {'fields': ['id', 'name', 'amount_residual'], 'limit': 5})

    if len(candidates) == 0:
        skipped_no_match += 1
        continue

    if len(candidates) > 1:
        skipped_ambiguous += 1
        continue

    invoice = candidates[0]

    try:
        # Find invoice's receivable/payable line
        inv_lines = call('account.move.line', 'search',
                          [[('move_id', '=', invoice['id']),
                            ('account_type', '=', account_type),
                            ('reconciled', '=', False)]], {'limit': 1})

        # Find BSL's receivable/payable line
        bsl_lines = call('account.move.line', 'search',
                          [[('move_id', '=', move_id),
                            ('account_type', '=', account_type),
                            ('reconciled', '=', False)]], {'limit': 1})

        if inv_lines and bsl_lines:
            call('account.move.line', 'reconcile', [inv_lines + bsl_lines])
            matched += 1
            ref = (bsl.get('payment_ref') or '')[:50]
            if matched <= 30 or matched % 50 == 0:
                print("  OK #%d: %s <-> %s (%.2f)" % (
                    matched, ref, invoice['name'], abs(amount)))
    except Exception as e:
        errors += 1
        if errors <= 10:
            print("  ERR: %s" % str(e)[:150])

    if (idx + 1) % 500 == 0:
        print("  Progress: %d/%d (matched=%d)" % (idx + 1, len(all_bsl), matched))

# ── Final report ─────────────────────────────────────────────────────
print("\n" + "=" * 50)
print("RECONCILIATION RESULT")
print("=" * 50)
print("BSL processed:      %d" % len(all_bsl))
print("Matched/reconciled:  %d" % matched)
print("Skip (no partner):   %d" % skipped_no_partner)
print("Skip (no match):     %d" % skipped_no_match)
print("Skip (ambiguous):    %d" % skipped_ambiguous)
print("Errors:              %d" % errors)

# Post-check
unrec_after = call('account.bank.statement.line', 'search_count',
                    [[('is_reconciled', '=', False)]])
print("\nUnreconciled BSL: %d -> %d (-%d)" % (unrec_bsl, unrec_after, unrec_bsl - unrec_after))

open_cust2 = call('account.move', 'search_count',
                   [[('move_type', 'in', ['out_invoice', 'out_refund']),
                     ('state', '=', 'posted'),
                     ('payment_state', 'in', ['not_paid', 'partial'])]])
open_vend2 = call('account.move', 'search_count',
                   [[('move_type', 'in', ['in_invoice', 'in_refund']),
                     ('state', '=', 'posted'),
                     ('payment_state', 'in', ['not_paid', 'partial'])]])
print("Open invoices: %d -> %d customer, %d -> %d vendor" % (
    open_cust, open_cust2, open_vend, open_vend2))
print("=" * 50)
