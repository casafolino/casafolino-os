# -*- coding: utf-8 -*-
"""Ensure POS configurations include the bank transfer payment method.

Run with:
    docker exec -i odoo-app odoo shell -d DB --no-http < scripts/ensure_pos_bank_transfer.py
"""

configs = env["pos.config"].with_context(active_test=False).sudo().search([])
PaymentMethod = env["pos.payment.method"].sudo()
Journal = env["account.journal"].sudo()

for company in configs.company_id:
    method = PaymentMethod.search(
        [
            ("company_id", "=", company.id),
            ("name", "ilike", "Bonifico"),
        ],
        limit=1,
    )

    if not method:
        journal = Journal.search(
            [
                ("company_id", "=", company.id),
                ("type", "=", "bank"),
                ("active", "=", True),
            ],
            order="sequence, id",
            limit=1,
        )
        vals = {
            "name": "Bonifico bancario",
            "company_id": company.id,
            "payment_method_type": "none",
            "split_transactions": False,
            "active": True,
        }
        if journal:
            vals["journal_id"] = journal.id
        if "it_payment_code" in PaymentMethod._fields:
            vals["it_payment_code"] = "5"
        method = PaymentMethod.create(vals)

    method.with_context(lang="it_IT").write({"name": "Bonifico bancario"})
    method.with_context(lang="en_US").write({"name": "Bank transfer"})
    if "it_payment_code" in PaymentMethod._fields and not method.it_payment_code:
        method.write({"it_payment_code": "5"})

    linked = []
    company_configs = configs.filtered(lambda config: config.company_id == company)
    for config in company_configs:
        if method not in config.payment_method_ids:
            env.cr.execute(
                """
                INSERT INTO pos_config_pos_payment_method_rel
                    (pos_config_id, pos_payment_method_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (config.id, method.id),
            )
            linked.append(config.display_name)

    print(
        "POS bank transfer ensured:",
        company.display_name,
        method.display_name,
        "linked=" + ", ".join(linked or ["already linked"]),
    )

env.cr.commit()
