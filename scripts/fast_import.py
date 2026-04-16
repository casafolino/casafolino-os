#!/usr/bin/env python3
"""
Fast bank statement import via odoo shell (runs INSIDE the container).
Copy this file to the server, then:
  cat fast_import.py | docker exec -i odoo-app odoo shell -d folinofood --no-http
"""
import csv
import time
import logging

_logger = logging.getLogger(__name__)

JOURNALS = {
    'qonto': {
        'id': 6,
        'csv': '/tmp/QONTO_pre2025_mancanti.csv',
        'name': 'Qonto',
        'existing_count': 1080,
    },
    'revolut': {
        'id': 13,
        'csv': '/tmp/REVOLUT_post_mar2026_mancanti.csv',
        'name': 'Revolut',
        'existing_count': 2236,
    },
}


def find_partner(env, name, cache):
    if not name or not name.strip():
        return False
    key = name.strip().lower()
    if key in cache:
        return cache[key]
    p = env['res.partner'].search([('name', '=ilike', name.strip())], limit=1)
    if not p:
        p = env['res.partner'].search([('name', 'ilike', name.strip())], limit=1)
    pid = p.id if p else False
    cache[key] = pid
    return pid


def import_journal(env, journal_key):
    cfg = JOURNALS[journal_key]
    journal_id = cfg['id']
    csv_path = cfg['csv']
    StmtLine = env['account.bank.statement.line']

    print("\n" + "=" * 60)
    print("IMPORT: %s (journal %d)" % (cfg['name'], journal_id))
    print("=" * 60)

    # Pre-check: count existing
    existing = StmtLine.search_count([('journal_id', '=', journal_id)])
    print("Existing lines in DB: %d" % existing)

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    total = len(rows)
    print("CSV rows: %d" % total)

    # Build set of existing (date, amount, payment_ref) for fast dedup
    print("Loading existing lines for dedup...")
    existing_lines = StmtLine.search_read(
        [('journal_id', '=', journal_id)],
        ['date', 'amount', 'payment_ref'],
    )
    existing_set = set()
    for el in existing_lines:
        d = str(el['date']) if el['date'] else ''
        a = round(float(el['amount']), 2)
        r = (el['payment_ref'] or '').strip()
        existing_set.add((d, a, r))
    print("Dedup set: %d entries" % len(existing_set))

    # Partner cache
    partner_cache = {}
    imported = 0
    skipped = 0
    errors = 0
    t0 = time.time()

    for i, row in enumerate(rows):
        date = row['date'].strip()
        payment_ref = row['payment_ref'].strip()
        amount = round(float(row['amount'].strip()), 2)
        partner_name = row.get('partner_name', '').strip()
        ref = row.get('ref', '').strip()

        # Dedup check
        if (date, amount, payment_ref) in existing_set:
            skipped += 1
            continue

        partner_id = find_partner(env, partner_name, partner_cache)

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
            StmtLine.create(vals)
            imported += 1
            existing_set.add((date, amount, payment_ref))
        except Exception as e:
            errors += 1
            if errors <= 10:
                print("  ERROR row %d: %s" % (i + 1, str(e)[:120]))

        # Commit every 200 rows
        if imported > 0 and imported % 200 == 0:
            env.cr.commit()
            elapsed = time.time() - t0
            rate = imported / elapsed if elapsed > 0 else 0
            print("  %d/%d imported (skip=%d, err=%d) %.1f/s" % (
                i + 1, total, skipped, errors, rate))

    # Final commit
    env.cr.commit()
    elapsed = time.time() - t0

    final_count = StmtLine.search_count([('journal_id', '=', journal_id)])
    unrec = StmtLine.search_count([('journal_id', '=', journal_id), ('is_reconciled', '=', False)])

    print("\n--- RESULT %s ---" % cfg['name'])
    print("CSV rows:     %d" % total)
    print("Imported:     %d" % imported)
    print("Skipped(dup): %d" % skipped)
    print("Errors:       %d" % errors)
    print("Time:         %.1fs (%.1f rows/s)" % (elapsed, imported / elapsed if elapsed > 0 else 0))
    print("DB total now: %d" % final_count)
    print("Unreconciled: %d" % unrec)
    return imported


# ── RUN ───────────────────────────────────────────────────────────────

print("Starting fast import...")

# Import Qonto
try:
    import_journal(env, 'qonto')
except Exception as e:
    print("QONTO IMPORT FAILED: %s" % e)

# Import Revolut
try:
    import_journal(env, 'revolut')
except Exception as e:
    print("REVOLUT IMPORT FAILED: %s" % e)

# Final stats
print("\n" + "=" * 60)
print("FINAL STATS")
print("=" * 60)
for key, cfg in JOURNALS.items():
    total = env['account.bank.statement.line'].search_count([('journal_id', '=', cfg['id'])])
    unrec = env['account.bank.statement.line'].search_count([
        ('journal_id', '=', cfg['id']), ('is_reconciled', '=', False)])
    print("%s (journal %d): %d total, %d unreconciled" % (cfg['name'], cfg['id'], total, unrec))

# Open invoices
recv = env['account.move'].search_count([
    ('move_type', 'in', ['out_invoice', 'out_refund']),
    ('state', '=', 'posted'),
    ('payment_state', 'in', ['not_paid', 'partial'])])
payable = env['account.move'].search_count([
    ('move_type', 'in', ['in_invoice', 'in_refund']),
    ('state', '=', 'posted'),
    ('payment_state', 'in', ['not_paid', 'partial'])])
print("Open customer invoices: %d" % recv)
print("Open vendor bills: %d" % payable)
print("\nPer riconciliare: Contabilita > Banca > Journal > Riconcilia")
print("=" * 60)
