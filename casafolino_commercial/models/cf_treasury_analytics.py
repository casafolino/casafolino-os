# -*- coding: utf-8 -*-
from odoo import models, api
from datetime import date, timedelta


class CfTreasuryAnalytics(models.Model):
    _inherit = "cf.treasury.snapshot"

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    @staticmethod
    def _pct_delta(curr, prev):
        delta = round(curr - prev, 2)
        pct = round((curr - prev) / abs(prev) * 100, 1) if prev else 0.0
        return {"abs": delta, "pct": pct, "up": delta >= 0}

    @api.model
    def _revenue_sum(self, d_from, d_to):
        groups = self.env["account.move"].read_group(
            domain=[
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", str(d_from)),
                ("invoice_date", "<=", str(d_to)),
            ],
            fields=["amount_untaxed:sum"],
            groupby=[],
        )
        return (groups[0]["amount_untaxed"] or 0.0) if groups else 0.0

    # ------------------------------------------------------------------
    # 1. Confronto YoY / MoM / QoQ
    # ------------------------------------------------------------------
    @api.model
    def get_comparison_data(self):
        """Fatturato: confronto MoM, YoY, QoQ. Usato da dashboard e forecast."""
        today = date.today()

        m_start = today.replace(day=1)
        prev_m_end = m_start - timedelta(days=1)
        prev_m_start = prev_m_end.replace(day=1)
        yoy_start = m_start.replace(year=m_start.year - 1)
        yoy_end = today.replace(year=today.year - 1)

        q_idx = (today.month - 1) // 3
        q_start = today.replace(month=q_idx * 3 + 1, day=1)
        pq_end = q_start - timedelta(days=1)
        pq_start = pq_end.replace(month=((pq_end.month - 1) // 3) * 3 + 1, day=1)
        days_in_q = (today - q_start).days
        pq_point = pq_start + timedelta(days=days_in_q)

        rev_mtd = self._revenue_sum(m_start, today)
        rev_prev = self._revenue_sum(
            prev_m_start,
            prev_m_start + timedelta(days=today.day - 1),
        )
        rev_yoy = self._revenue_sum(yoy_start, yoy_end)
        rev_qtd = self._revenue_sum(q_start, today)
        rev_pqtd = self._revenue_sum(pq_start, pq_point)

        journals = self.env["account.journal"].search([("type", "in", ("bank", "cash"))])
        balance = sum(
            j.default_account_id.current_balance
            for j in journals if j.default_account_id
        )

        return {
            "revenue_mtd": round(rev_mtd, 2),
            "mom": self._pct_delta(rev_mtd, rev_prev),
            "yoy": self._pct_delta(rev_mtd, rev_yoy),
            "revenue_qtd": round(rev_qtd, 2),
            "qoq": self._pct_delta(rev_qtd, rev_pqtd),
            "balance": round(balance, 2),
        }

    # ------------------------------------------------------------------
    # 2. Analisi Clienti
    # ------------------------------------------------------------------
    @api.model
    def get_client_analysis(self):
        """Top 10 clienti fatturato e credito scaduto, DSO per cliente."""
        today = date.today()
        today_str = str(today)
        d_12m = str(today - timedelta(days=365))

        top_rev = self.env["account.move"].read_group(
            domain=[
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", d_12m),
                ("invoice_date", "<=", today_str),
                ("partner_id", "!=", False),
            ],
            fields=["partner_id", "amount_untaxed:sum"],
            groupby=["partner_id"],
            orderby="amount_untaxed:sum desc",
            limit=10,
        )

        aml = self.env["account.move.line"]
        overdue_lines = aml.search([
            ("account_id.account_type", "=", "asset_receivable"),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("date_maturity", "<", today_str),
            ("partner_id", "!=", False),
        ])
        by_partner = {}
        for line in overdue_lines:
            pid = line.partner_id.id
            by_partner.setdefault(pid, {"id": pid, "name": line.partner_id.name, "amount": 0.0})
            by_partner[pid]["amount"] += line.amount_residual
        top_overdue = sorted(by_partner.values(), key=lambda x: -x["amount"])[:10]
        for r in top_overdue:
            r["amount"] = round(r["amount"], 2)

        dso_list = []
        for g in top_rev:
            if not g.get("partner_id"):
                continue
            pid, pname = g["partner_id"][0], g["partner_id"][1]
            rev = g["amount_untaxed"] or 0.0
            open_recv = sum(aml.search([
                ("account_id.account_type", "=", "asset_receivable"),
                ("parent_state", "=", "posted"),
                ("reconciled", "=", False),
                ("partner_id", "=", pid),
            ]).mapped("amount_residual"))
            dso = round(open_recv / rev * 365, 1) if rev > 0 else 0.0
            partner = self.env["res.partner"].browse(pid)
            dso_list.append({
                "id": pid,
                "name": pname,
                "revenue_12m": round(rev, 2),
                "open_recv": round(open_recv, 2),
                "dso": dso,
                "country": partner.country_id.name or "",
            })

        return {
            "top_revenue": [
                {
                    "id": g["partner_id"][0],
                    "name": g["partner_id"][1],
                    "amount": round(g["amount_untaxed"] or 0, 2),
                }
                for g in top_rev if g.get("partner_id")
            ],
            "top_overdue": top_overdue,
            "dso_per_client": dso_list,
        }

    # ------------------------------------------------------------------
    # 3. Analisi per Categoria
    # ------------------------------------------------------------------
    @api.model
    def get_category_analysis(self):
        """Fatturato per categoria prodotto e top 20 conti contabili."""
        today = date.today()
        today_str = str(today)
        d_12m = str(today - timedelta(days=365))
        d_24m = str(today - timedelta(days=730))

        base_domain = [
            ("move_id.move_type", "=", "out_invoice"),
            ("move_id.state", "=", "posted"),
            ("product_id", "!=", False),
            ("price_subtotal", ">", 0),
            ("display_type", "=", False),
        ]
        curr_lines = self.env["account.move.line"].search(
            base_domain + [
                ("move_id.invoice_date", ">=", d_12m),
                ("move_id.invoice_date", "<=", today_str),
            ]
        )
        prev_lines = self.env["account.move.line"].search(
            base_domain + [
                ("move_id.invoice_date", ">=", d_24m),
                ("move_id.invoice_date", "<", d_12m),
            ]
        )

        def _aggregate_by_cat(lines):
            result = {}
            for line in lines:
                cat = line.product_id.categ_id
                if not cat:
                    continue
                key = (cat.id, cat.complete_name)
                result.setdefault(key, 0.0)
                result[key] += line.price_subtotal
            return result

        cat_curr = _aggregate_by_cat(curr_lines)
        cat_prev = _aggregate_by_cat(prev_lines)
        total_rev = sum(cat_curr.values())

        categories = []
        for (cat_id, cat_name), curr in sorted(cat_curr.items(), key=lambda x: -x[1])[:20]:
            prev = cat_prev.get((cat_id, cat_name), 0.0)
            delta = curr - prev
            pct = round(delta / abs(prev) * 100, 1) if prev else 0.0
            categories.append({
                "id": cat_id,
                "name": cat_name,
                "amount": round(curr, 2),
                "pct_total": round(curr / total_rev * 100, 1) if total_rev else 0.0,
                "yoy_delta": round(delta, 2),
                "yoy_pct": pct,
                "yoy_up": delta >= 0,
            })

        top_acc = self.env["account.move.line"].read_group(
            domain=[
                ("parent_state", "=", "posted"),
                ("date", ">=", d_12m),
                ("date", "<=", today_str),
                ("account_id.account_type", "not in", [
                    "asset_receivable", "liability_payable",
                ]),
            ],
            fields=["account_id", "debit:sum", "credit:sum"],
            groupby=["account_id"],
            orderby="debit:sum desc",
            limit=20,
        )
        top_accounts = [
            {
                "id": g["account_id"][0] if g.get("account_id") else 0,
                "name": g["account_id"][1] if g.get("account_id") else "—",
                "debit": round(g.get("debit") or 0, 2),
                "credit": round(g.get("credit") or 0, 2),
                "net": round((g.get("debit") or 0) - (g.get("credit") or 0), 2),
            }
            for g in top_acc
        ]

        return {
            "categories": categories,
            "total_revenue": round(total_rev, 2),
            "top_accounts": top_accounts,
        }

    # ------------------------------------------------------------------
    # 4. Forecast con scenari regolabili
    # ------------------------------------------------------------------
    @api.model
    def get_forecast_data(self, opt_pct=15.0, pes_pct_in=25.0, pes_pct_out=10.0):
        """Proiezione 30/60/90gg con tre scenari. I parametri sono regolabili dal JS."""
        d = self._compute_live_data()
        base_b = d["total_balance"]
        cf = d["cashflow"]

        if len(cf) >= 3:
            avg_in = sum(m["inflow"] for m in cf[-3:]) / 3.0
            avg_out = sum(m["outflow"] for m in cf[-3:]) / 3.0
        elif cf:
            avg_in = sum(m["inflow"] for m in cf) / len(cf)
            avg_out = sum(m["outflow"] for m in cf) / len(cf)
        else:
            avg_in = avg_out = 0.0

        opt_mult = 1 + opt_pct / 100
        pes_in_mult = 1 - pes_pct_in / 100
        pes_out_mult = 1 + pes_pct_out / 100

        def _proj(months, in_m=avg_in, out_m=avg_out):
            return round(base_b + (in_m - out_m) * months, 2)

        return {
            "base_balance": round(base_b, 2),
            "avg_monthly_inflow": round(avg_in, 2),
            "avg_monthly_outflow": round(avg_out, 2),
            "opt_pct": opt_pct,
            "pes_pct_in": pes_pct_in,
            "pes_pct_out": pes_pct_out,
            "scenarios": {
                "30d": {
                    "base": _proj(1),
                    "opt": _proj(1, avg_in * opt_mult),
                    "pes": _proj(1, avg_in * pes_in_mult, avg_out * pes_out_mult),
                },
                "60d": {
                    "base": _proj(2),
                    "opt": _proj(2, avg_in * opt_mult),
                    "pes": _proj(2, avg_in * pes_in_mult, avg_out * pes_out_mult),
                },
                "90d": {
                    "base": _proj(3),
                    "opt": _proj(3, avg_in * opt_mult),
                    "pes": _proj(3, avg_in * pes_in_mult, avg_out * pes_out_mult),
                },
            },
            "chart_points": [
                {
                    "label": f"M+{i}",
                    "base": _proj(i),
                    "opt": _proj(i, avg_in * opt_mult),
                    "pes": _proj(i, avg_in * pes_in_mult, avg_out * pes_out_mult),
                }
                for i in range(1, 4)
            ],
            "comparison": self.get_comparison_data(),
        }
