#!/usr/bin/env python3
"""Fast bank statement import via XML-RPC with batch partner lookup."""
import csv
import sys
import time
import xmlrpc.client

URL = 'http://erp.casafolino.com:4589'
DB = 'folinofood'
USER = 'antonio@casafolino.com'
PWD = 'admin#folino'

common = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common', allow_none=True)
uid = common.authenticate(DB, USER, PWD, {})
models = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
print("Connected uid=%d" % uid)

def call(model, method, *args, **kw):
    return models.execute_kw(DB, uid, PWD, model, method, *args, **kw)


# ── Pre-load all partners ────────────────────────────────────────────
print("Loading partners...")
all_partners = call('res.partner', 'search_read', [[]], {'fields': ['id', 'name'], 'limit': 50000})
partner_map = {}  # lowercase name -> id
for p in all_partners:
    if p['name']:
        partner_map[p['name'].lower().strip()] = p['id']
print("Partners loaded: %d" % len(partner_map))


def find_partner(name):
    if not name or not name.strip():
        return False
    key = name.strip().lower()
    if key in partner_map:
        return partner_map[key]
    # Partial match — try contains
    for pname, pid in partner_map.items():
        if key in pname or pname in key:
            return pid
    return False


def import_journal(journal_id, csv_path, journal_name):
    print("\n" + "=" * 60)
    print("IMPORTING: %s (journal %d)" % (journal_name, journal_id))
    print("=" * 60)

    with open(csv_path, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    total = len(rows)
    print("Rows: %d" % total)

    imported = 0
    skipped = 0
    errors = 0
    no_partner = 0
    t0 = time.time()

    for i, row in enumerate(rows):
        date = row['date'].strip()
        payment_ref = row['payment_ref'].strip()
        amount = float(row['amount'].strip())
        partner_name = row.get('partner_name', '').strip()
        ref = row.get('ref', '').strip()

        partner_id = find_partner(partner_name)
        if partner_name and not partner_id:
            no_partner += 1

        vals = {
            'journal_id': journal_id,
            'date': date,
            'payment_ref': payment_ref,
            'amount': amount,
            'partner_id': partner_id,
        }
        if ref:
            vals['ref'] = ref

        try:
            call('account.bank.statement.line', 'create', [vals])
            imported += 1
        except xmlrpc.client.Fault as e:
            err_msg = str(e.faultString)[:100] if hasattr(e, 'faultString') else str(e)[:100]
            # If it's a duplicate constraint error, skip
            if 'duplicate' in err_msg.lower() or 'unique' in err_msg.lower():
                skipped += 1
            else:
                errors += 1
                if errors <= 10:
                    print("  ERROR row %d: %s" % (i + 1, err_msg))
        except Exception as e:
            errors += 1
            if errors <= 10:
                print("  ERROR row %d: %s" % (i + 1, str(e)[:100]))

        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print("  %d/%d (imported=%d, skip=%d, err=%d) %.1f rows/s" % (
                i + 1, total, imported, skipped, errors, rate))

    elapsed = time.time() - t0
    print("\n--- RESULT %s ---" % journal_name)
    print("Total:     %d" % total)
    print("Imported:  %d" % imported)
    print("Skipped:   %d" % skipped)
    print("Errors:    %d" % errors)
    print("No partner: %d" % no_partner)
    print("Time:      %.1fs (%.1f rows/s)" % (elapsed, total / elapsed if elapsed > 0 else 0))

    # Post-import count
    count = call('account.bank.statement.line', 'search_count',
                 [[('journal_id', '=', journal_id)]])
    unrec = call('account.bank.statement.line', 'search_count',
                 [[('journal_id', '=', journal_id), ('is_reconciled', '=', False)]])
    print("DB total:   %d" % count)
    print("Unreconciled: %d" % unrec)
    return imported


# ── RECONCILE INFO ────────────────────────────────────────────────────

def show_reconcile_info(journal_id, journal_name):
    print("\n--- RECONCILIATION INFO: %s ---" % journal_name)
    unrec = call('account.bank.statement.line', 'search_count',
                 [[('journal_id', '=', journal_id), ('is_reconciled', '=', False)]])
    print("Unreconciled statement lines: %d" % unrec)

    # Check reconcile models
    try:
        recon = call('account.reconcile.model', 'search_read',
                     [[('rule_type', '=', 'invoice_matching')]],
                     {'fields': ['name', 'rule_type', 'auto_reconcile']})
        print("Reconciliation models (invoice matching):")
        for r in recon:
            print("  - %s (auto=%s)" % (r['name'], r['auto_reconcile']))
    except Exception as e:
        print("Error: %s" % str(e)[:80])

    # Open invoices
    receivable = call('account.move', 'search_count',
                      [[('move_type', 'in', ['out_invoice', 'out_refund']),
                        ('state', '=', 'posted'),
                        ('payment_state', 'in', ['not_paid', 'partial'])]])
    payable = call('account.move', 'search_count',
                   [[('move_type', 'in', ['in_invoice', 'in_refund']),
                     ('state', '=', 'posted'),
                     ('payment_state', 'in', ['not_paid', 'partial'])]])
    print("Open customer invoices: %d" % receivable)
    print("Open vendor bills: %d" % payable)


# ── MAIN ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if action in ('qonto', 'all'):
        import_journal(6, '/Users/antoniofolino/Downloads/QONTO_pre2025_mancanti.csv', 'Qonto')
        show_reconcile_info(6, 'Qonto')

    if action in ('revolut', 'all'):
        import_journal(13, '/Users/antoniofolino/Downloads/REVOLUT_post_mar2026_mancanti.csv', 'Revolut')
        show_reconcile_info(13, 'Revolut')

    if action == 'info':
        show_reconcile_info(6, 'Qonto')
        show_reconcile_info(13, 'Revolut')

    print("\n=== DONE ===")
    print("Per la riconciliazione automatica, vai in Odoo:")
    print("  Contabilita > Banca > Seleziona journal > Riconcilia")
    print("  Odoo 18 usa i Reconciliation Models per il matching automatico.")
