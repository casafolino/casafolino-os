#!/usr/bin/env python3
import argparse

import odoo
from odoo import SUPERUSER_ID, api
from odoo.tools import config


def main():
    parser = argparse.ArgumentParser(description="Riallinea fatture Europa Commerciale ai valori XML FatturaPA.")
    parser.add_argument("-d", "--database", required=True)
    parser.add_argument("-c", "--config", default="/etc/odoo/odoo.conf")
    parser.add_argument("--invoice", help="Numero fattura Odoo, es. ACQ/2024/01/0002")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config.parse_config(["-c", args.config, "-d", args.database, "--without-demo=all"])
    odoo.service.server.load_server_wide_modules()
    registry = odoo.registry(args.database)

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        partner = env["res.partner"].search([
            "|",
            ("vat", "=", "IT03201710799"),
            ("l10n_it_codice_fiscale", "=", "03201710799"),
        ], limit=1)
        if not partner:
            raise SystemExit("Partner EUROPA COMMERCIALE SRL non trovato.")

        domain = [
            ("move_type", "in", ["in_invoice", "in_refund"]),
            ("partner_id", "child_of", partner.commercial_partner_id.id),
        ]
        if args.invoice:
            domain.append(("name", "=", args.invoice))

        moves = env["account.move"].search(domain, order="invoice_date, name, id")
        print(f"Partner: {partner.display_name} ({partner.id})", flush=True)
        print(f"Fatture candidate: {len(moves)}", flush=True)
        for move in moves:
            print(f"BEFORE {move.name} id={move.id} state={move.state} payment={move.payment_state} total={move.amount_total:.2f}", flush=True)

        fixed = 0
        for move in moves:
            try:
                with cr.savepoint():
                    fixed += move._cf_fix_fatturapa_xml_lines()
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
