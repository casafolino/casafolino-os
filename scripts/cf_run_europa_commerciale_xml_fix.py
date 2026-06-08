#!/usr/bin/env python3
import argparse

import odoo
from odoo import SUPERUSER_ID, api
from odoo.tools import config
from odoo.tools.float_utils import float_compare


def main():
    parser = argparse.ArgumentParser(description="Riallinea fatture fornitore ai valori XML FatturaPA.")
    parser.add_argument("-d", "--database", required=True)
    parser.add_argument("-c", "--config", default="/etc/odoo/odoo.conf")
    parser.add_argument("--invoice", help="Numero fattura Odoo, es. ACQ/2024/01/0002")
    parser.add_argument("--all-vendors", action="store_true", help="Elabora tutte le fatture fornitore, non solo Europa Commerciale.")
    parser.add_argument("--include-paid", action="store_true", help="Include anche fatture gia' pagate/riconciliate.")
    parser.add_argument("--only-mismatches", action="store_true", help="Salta le fatture gia' corrispondenti al totale XML.")
    parser.add_argument("--limit", type=int, help="Limite massimo di fatture candidate.")
    parser.add_argument("--commit-every", type=int, default=100, help="Commit ogni N fatture elaborate, disattivato in dry-run.")
    parser.add_argument("--verbose", action="store_true", help="Stampa anche le righe BEFORE.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config.parse_config(["-c", args.config, "-d", args.database, "--without-demo=all"])
    odoo.service.server.load_server_wide_modules()
    registry = odoo.registry(args.database)

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        if not args.all_vendors:
            partner = env["res.partner"].search([
                "|",
                ("vat", "=", "IT03201710799"),
                ("l10n_it_codice_fiscale", "=", "03201710799"),
            ], limit=1)
            if not partner:
                raise SystemExit("Partner EUROPA COMMERCIALE SRL non trovato.")
            domain = [
                ("move_type", "in", ["in_invoice", "in_refund"]),
                ("state", "!=", "cancel"),
                ("partner_id", "child_of", partner.commercial_partner_id.id),
            ]
            if not args.include_paid:
                domain.append(("payment_state", "in", ["not_paid", "partial", "in_payment"]))
            if args.invoice:
                domain.append(("name", "=", args.invoice))
            moves = env["account.move"].search(domain, order="invoice_date, name, id", limit=args.limit)
        else:
            where = [
                "am.move_type IN ('in_invoice', 'in_refund')",
                "am.state != 'cancel'",
                "(ia.mimetype = 'text/xml' OR ia.name ILIKE '%.xml%')",
            ]
            params = []
            if not args.include_paid:
                where.append("am.payment_state IN ('not_paid', 'partial', 'in_payment')")
            if args.invoice:
                where.append("am.name = %s")
                params.append(args.invoice)
            limit_sql = " LIMIT %s" if args.limit else ""
            if args.limit:
                params.append(args.limit)
            env.cr.execute(f"""
                SELECT DISTINCT am.id, am.invoice_date, am.name
                  FROM account_move am
                  JOIN ir_attachment ia
                    ON ia.res_model = 'account.move'
                   AND ia.res_id = am.id
                 WHERE {' AND '.join(where)}
                 ORDER BY am.invoice_date, am.name, am.id
                 {limit_sql}
            """, params)
            moves = env["account.move"].browse([row[0] for row in env.cr.fetchall()]).exists()

        scope = "tutti i fornitori" if args.all_vendors else f"{partner.display_name} ({partner.id})"
        print(f"Ambito: {scope}", flush=True)
        print(f"Fatture candidate: {len(moves)}", flush=True)
        if args.verbose:
            for move in moves:
                print(f"BEFORE {move.name} id={move.id} state={move.state} payment={move.payment_state} total={move.amount_total:.2f}", flush=True)

        fixed = 0
        processed = 0
        for move in moves:
            processed += 1
            try:
                with cr.savepoint():
                    if args.only_mismatches:
                        xml_content = move._cf_get_fatturapa_xml_attachment_content()
                        parsed = move._cf_parse_fatturapa_xml(xml_content) if xml_content else {}
                        xml_total = parsed.get("amount_total")
                        if xml_total is None:
                            move._cf_validate_fatturapa_xml_amounts(parsed=parsed)
                            print(f"SKIP {move.name} id={move.id}: XML mancante/non parsabile", flush=True)
                            continue
                        if float_compare(move.amount_total, float(xml_total), precision_rounding=move.currency_id.rounding) == 0:
                            print(f"SKIP {move.name} id={move.id}: gia' corrisponde a XML {float(xml_total):.2f}", flush=True)
                            continue

                    fixed += move._cf_fix_fatturapa_xml_lines(restrict_europa=not args.all_vendors)
                    move.invalidate_recordset()
                    print(
                        "AFTER "
                        f"{move.name} id={move.id} state={move.state} payment={move.payment_state} "
                        f"total={move.amount_total:.2f} xml={move.cf_fatturapa_xml_amount_total:.2f} "
                        f"check={move.cf_fatturapa_xml_check_state}",
                        flush=True,
                    )
                    if move.cf_fatturapa_xml_check_message:
                        print(f"  {move.cf_fatturapa_xml_check_message}", flush=True)
            except Exception as exc:
                print(f"ERROR {move.name} id={move.id}: {exc}", flush=True)
            if not args.dry_run and args.commit_every and processed % args.commit_every == 0:
                cr.commit()
                print(f"PROGRESS commit: processate={processed} corrette={fixed}", flush=True)

        if args.dry_run:
            cr.rollback()
            print(f"DRY-RUN rollback eseguito. Fatture elaborate: {fixed}", flush=True)
        else:
            cr.commit()
            print(f"COMMIT eseguito. Fatture elaborate: {fixed}", flush=True)


if __name__ == "__main__":
    main()
