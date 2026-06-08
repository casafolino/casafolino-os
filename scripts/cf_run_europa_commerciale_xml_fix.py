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
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config.parse_config(["-c", args.config, "-d", args.database, "--without-demo=all"])
    odoo.service.server.load_server_wide_modules()
    registry = odoo.registry(args.database)

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        domain = [
            ("move_type", "in", ["in_invoice", "in_refund"]),
            ("state", "!=", "cancel"),
        ]
        if not args.include_paid:
            domain.append(("payment_state", "in", ["not_paid", "partial", "in_payment"]))
        if not args.all_vendors:
            partner = env["res.partner"].search([
                "|",
                ("vat", "=", "IT03201710799"),
                ("l10n_it_codice_fiscale", "=", "03201710799"),
            ], limit=1)
            if not partner:
                raise SystemExit("Partner EUROPA COMMERCIALE SRL non trovato.")
            domain.append(("partner_id", "child_of", partner.commercial_partner_id.id))
        if args.invoice:
            domain.append(("name", "=", args.invoice))

        moves = env["account.move"].search(domain, order="invoice_date, name, id", limit=args.limit)
        scope = "tutti i fornitori" if args.all_vendors else f"{partner.display_name} ({partner.id})"
        print(f"Ambito: {scope}", flush=True)
        print(f"Fatture candidate: {len(moves)}", flush=True)
        for move in moves:
            print(f"BEFORE {move.name} id={move.id} state={move.state} payment={move.payment_state} total={move.amount_total:.2f}", flush=True)

        fixed = 0
        for move in moves:
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

        if args.dry_run:
            cr.rollback()
            print(f"DRY-RUN rollback eseguito. Fatture elaborate: {fixed}", flush=True)
        else:
            cr.commit()
            print(f"COMMIT eseguito. Fatture elaborate: {fixed}", flush=True)


if __name__ == "__main__":
    main()
