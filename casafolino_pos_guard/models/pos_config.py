# -*- coding: utf-8 -*-

from odoo import api, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    @api.model
    def cf_ensure_bank_transfer_payment_method(self):
        """Ensure bank transfer is available as a selectable POS payment method."""
        configs = self.with_context(active_test=False).sudo().search([])
        companies = configs.company_id
        PaymentMethod = self.env["pos.payment.method"].sudo()
        Journal = self.env["account.journal"].sudo()

        for company in companies:
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

            company_configs = configs.filtered(lambda config: config.company_id == company)
            for config in company_configs:
                if method not in config.payment_method_ids:
                    self.env.cr.execute(
                        """
                        INSERT INTO pos_config_pos_payment_method_rel
                            (pos_config_id, pos_payment_method_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (config.id, method.id),
                    )

        return True
