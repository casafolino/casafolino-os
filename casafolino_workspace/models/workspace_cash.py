# -*- coding: utf-8 -*-
"""Workspace Cash & Bank — read-only data provider for Cassa & Banca section.
NO DATA CREATION. Pure SELECT queries on existing data.
"""
import logging
import re
from datetime import date, timedelta

from odoo import api, models

_logger = logging.getLogger(__name__)
_HTML_RE = re.compile(r'<[^>]+>')

_BANK_JOURNALS = {6: "Qonto", 13: "Revolut", 22: "BCC"}

_CASH_MACRO = [
    {"id": "qonto_saldo", "label": "Qonto saldo", "icon": "fa-university", "color": "#E6F1FB"},
    {"id": "revolut_saldo", "label": "Revolut saldo", "icon": "fa-credit-card", "color": "#EEEDFE"},
    {"id": "bcc_saldo", "label": "BCC saldo", "icon": "fa-building-o", "color": "#E1F5EE"},
    {"id": "bsl_unreconciled", "label": "BSL non riconciliate", "icon": "fa-random", "color": "#FAEEDA"},
    {"id": "overdue_out", "label": "Fatture scadute (out)", "icon": "fa-arrow-up", "color": "#FAECE7"},
    {"id": "overdue_in", "label": "Fatture scadute (in)", "icon": "fa-arrow-down", "color": "#FBEAF0"},
    {"id": "refund_mtd", "label": "Note credito MTD", "icon": "fa-undo", "color": "#F1EFE8"},
    {"id": "gap", "label": "Gap cassa", "icon": "fa-balance-scale", "color": "#EAF3DE"},
]


def _jsonb_str(val):
    if not val:
        return ""
    if isinstance(val, dict):
        return val.get("it_IT") or val.get("en_US") or next(iter(val.values()), "")
    return str(val)


def _fmt_euro(amount):
    """Format amount as Euro string."""
    if amount is None:
        return "€ 0,00"
    try:
        sign = "-" if amount < 0 else ""
        abs_val = abs(amount)
        euros = int(abs_val)
        cents = int(round((abs_val - euros) * 100))
        return f"{sign}€ {euros:,}.{cents:02d}".replace(",", ".")
    except Exception:
        return "€ 0,00"


def _safe_count(cr, sql, params=None):
    """Execute count query, return 0 if table doesn't exist."""
    try:
        cr.execute(sql, params or {})
        return cr.fetchone()[0] or 0
    except Exception:
        cr.connection.rollback()
        return 0


class WorkspaceCash(models.AbstractModel):
    _name = "workspace.cash"
    _description = "Workspace Cash & Bank Data Provider (read-only)"

    @api.model
    def get_cash_data(self):
        try:
            profile = self.env["res.users"]._get_workspace_profile(self.env.user)
            cr = self.env.cr
            today = date.today()
            first_of_month = today.replace(day=1)

            # KPI data
            liquidity = self._total_bank_balance(cr)
            overdue_out = self._overdue_total(cr, today, "out_invoice")
            overdue_in = self._overdue_total(cr, today, "in_invoice")

            # Fatturato MTD
            cr.execute("""
                SELECT COALESCE(SUM(am.amount_total_signed), 0)
                FROM account_move am
                WHERE am.move_type = 'out_invoice'
                  AND am.state = 'posted'
                  AND am.invoice_date >= %s
                  AND am.invoice_date <= %s
            """, [first_of_month, today])
            fatturato_mtd = cr.fetchone()[0] or 0

            kpis = [
                {"id": "liquidita", "label": "Liquidità", "value": _fmt_euro(liquidity), "raw": liquidity, "icon": "fa-euro"},
                {"id": "crediti", "label": "Crediti scaduti", "value": _fmt_euro(overdue_out), "raw": overdue_out, "icon": "fa-arrow-up"},
                {"id": "debiti", "label": "Debiti scaduti", "value": _fmt_euro(overdue_in), "raw": overdue_in, "icon": "fa-arrow-down"},
                {"id": "fatturato_mtd", "label": "Fatturato MTD", "value": _fmt_euro(fatturato_mtd), "raw": fatturato_mtd, "icon": "fa-line-chart"},
            ]

            macro = self._macro_batch(cr, today, first_of_month)
            feed = self._feed(cr)

            hero = {
                "greet": "Cassa & Banca",
                "sub": f"Liquidità {_fmt_euro(liquidity)} · Crediti scaduti {_fmt_euro(overdue_out)} · Fatturato MTD {_fmt_euro(fatturato_mtd)}",
                "tip": {"text": "Controlla le BSL non riconciliate e le fatture scadute.", "primary": "Vedi", "secondary": "Ignora"},
                "progress": {"done": 0, "total": 0, "pct": 0},
            }

            return {
                "user": profile, "hero": hero, "kpis": kpis, "macro": macro,
                "filters": ["Tutte", "Qonto", "Revolut", "BCC"],
                "feed": feed,
            }
        except Exception as e:
            _logger.error("get_cash_data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_accounts(self):
        try:
            cr = self.env.cr
            accounts = []
            for jid, jname in _BANK_JOURNALS.items():
                cr.execute("""
                    SELECT COALESCE(SUM(aml.balance), 0)
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    WHERE aml.journal_id = %s
                      AND am.state = 'posted'
                      AND aml.account_id IN (
                          SELECT id FROM account_account WHERE account_type = 'asset_cash'
                      )
                """, [jid])
                bal = cr.fetchone()[0] or 0
                accounts.append({
                    "id": jid, "name": jname,
                    "balance": bal, "balance_fmt": _fmt_euro(bal),
                    "icon": "fa-university" if jid == 22 else ("fa-credit-card" if jid == 13 else "fa-university"),
                })
            return {"accounts": accounts}
        except Exception as e:
            _logger.error("get_accounts error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_bsl(self, filter_key="tutte"):
        try:
            cr = self.env.cr
            where_extra = ""
            params = []
            if filter_key in ("qonto", "revolut", "bcc"):
                jmap = {"qonto": 6, "revolut": 13, "bcc": 22}
                where_extra = " AND absl.journal_id = %s"
                params.append(jmap[filter_key])

            cr.execute("""
                SELECT absl.id, absl.payment_ref, absl.amount, absl.journal_id,
                       am.date AS move_date, aj.name AS journal_name
                FROM account_bank_statement_line absl
                JOIN account_move am ON am.id = absl.move_id
                LEFT JOIN account_journal aj ON aj.id = absl.journal_id
                WHERE NOT absl.is_reconciled
                """ + where_extra + """
                ORDER BY am.date DESC
                LIMIT 50
            """, params)

            items = []
            for row in cr.fetchall():
                jname = _jsonb_str(row[5]) or _BANK_JOURNALS.get(row[3], "?")
                items.append({
                    "id": row[0], "type": "bsl", "item_id": row[0],
                    "title": (row[1] or "")[:80] or f"BSL #{row[0]}",
                    "subtitle": jname,
                    "amount": row[2] or 0, "amount_fmt": _fmt_euro(row[2]),
                    "date": str(row[4]) if row[4] else "",
                    "journal_id": row[3],
                    "cat": "BSL", "icon": "fa-random", "icon_color": "#D97706",
                    "status": "unreconciled",
                    "pill_status": "amber", "pill_label": "non riconciliata",
                })
            return {"items": items}
        except Exception as e:
            _logger.error("get_bsl error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_invoices(self, filter_key="tutte"):
        try:
            cr = self.env.cr
            today = date.today()
            where_extra = ""
            params = [today]

            if filter_key == "out":
                where_extra = " AND am.move_type = 'out_invoice'"
            elif filter_key == "in":
                where_extra = " AND am.move_type = 'in_invoice'"

            cr.execute("""
                SELECT am.id, am.name, am.move_type, am.amount_total, am.amount_residual,
                       am.invoice_date_due, am.partner_id, rp.name AS partner_name
                FROM account_move am
                LEFT JOIN res_partner rp ON rp.id = am.partner_id
                WHERE am.state = 'posted'
                  AND am.move_type IN ('out_invoice', 'in_invoice')
                  AND am.amount_residual > 0
                  AND am.invoice_date_due < %s
                """ + where_extra + """
                ORDER BY am.invoice_date_due ASC
                LIMIT 50
            """, params)

            items = []
            for row in cr.fetchall():
                days = (today - row[5]).days if row[5] else 0
                is_out = row[2] == "out_invoice"
                partner = _jsonb_str(row[7]) or ""
                items.append({
                    "id": row[0], "type": "invoice", "item_id": row[0],
                    "title": row[1] or f"Fattura #{row[0]}",
                    "subtitle": partner[:60],
                    "amount": row[4] or 0, "amount_fmt": _fmt_euro(row[4]),
                    "total": row[3] or 0, "total_fmt": _fmt_euro(row[3]),
                    "due_date": str(row[5]) if row[5] else "",
                    "days_overdue": days,
                    "direction": "out" if is_out else "in",
                    "cat": "Fattura cliente" if is_out else "Fattura fornitore",
                    "icon": "fa-arrow-up" if is_out else "fa-arrow-down",
                    "icon_color": "#DC2626" if is_out else "#7C3AED",
                    "status": "overdue",
                    "pill_status": "red" if days > 30 else "amber",
                    "pill_label": f"-{days} gg",
                })
            return {"items": items}
        except Exception as e:
            _logger.error("get_invoices error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_cash_detail(self, item_type, item_id):
        try:
            cr = self.env.cr
            today = date.today()

            if item_type == "bsl":
                cr.execute("""
                    SELECT absl.id, absl.payment_ref, absl.amount, absl.journal_id,
                           am.date AS move_date, aj.name AS journal_name,
                           absl.is_reconciled, am.name AS move_name
                    FROM account_bank_statement_line absl
                    JOIN account_move am ON am.id = absl.move_id
                    LEFT JOIN account_journal aj ON aj.id = absl.journal_id
                    WHERE absl.id = %s
                """, [item_id])
                row = cr.fetchone()
                if not row:
                    return {"error": "BSL non trovata"}
                return {
                    "item": {
                        "id": row[0], "type": "bsl",
                        "title": (row[1] or "")[:80] or f"BSL #{row[0]}",
                        "subtitle": _jsonb_str(row[5]) or _BANK_JOURNALS.get(row[3], ""),
                        "amount_fmt": _fmt_euro(row[2]),
                        "date": str(row[4]) if row[4] else "",
                        "reconciled": bool(row[6]),
                        "move_name": row[7] or "",
                        "status": "riconciliata" if row[6] else "non riconciliata",
                    },
                    "chain": [],
                }

            if item_type == "invoice":
                cr.execute("""
                    SELECT am.id, am.name, am.move_type, am.amount_total, am.amount_residual,
                           am.invoice_date_due, am.invoice_date, am.state,
                           rp.name AS partner_name
                    FROM account_move am
                    LEFT JOIN res_partner rp ON rp.id = am.partner_id
                    WHERE am.id = %s
                """, [item_id])
                row = cr.fetchone()
                if not row:
                    return {"error": "Fattura non trovata"}
                days = (today - row[5]).days if row[5] else 0
                return {
                    "item": {
                        "id": row[0], "type": "invoice",
                        "title": row[1] or f"Fattura #{row[0]}",
                        "subtitle": _jsonb_str(row[8]) or "",
                        "total_fmt": _fmt_euro(row[3]),
                        "residual_fmt": _fmt_euro(row[4]),
                        "due_date": str(row[5]) if row[5] else "",
                        "invoice_date": str(row[6]) if row[6] else "",
                        "days_overdue": days,
                        "direction": "out" if row[2] == "out_invoice" else "in",
                        "status": row[7] or "",
                    },
                    "chain": [],
                }

            return {"item": {"id": item_id, "type": item_type, "title": f"{item_type} #{item_id}", "subtitle": "Dettaglio non disponibile"}, "chain": []}
        except Exception as e:
            _logger.error("get_cash_detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Helpers ──────────────────────────────────────────

    def _total_bank_balance(self, cr):
        try:
            cr.execute("""
                SELECT COALESCE(SUM(aml.balance), 0)
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE aml.journal_id IN (6, 13, 22)
                  AND am.state = 'posted'
                  AND aml.account_id IN (
                      SELECT id FROM account_account WHERE account_type = 'asset_cash'
                  )
            """)
            return cr.fetchone()[0] or 0
        except Exception:
            cr.connection.rollback()
            return 0

    def _overdue_total(self, cr, today, move_type):
        try:
            cr.execute("""
                SELECT COALESCE(SUM(am.amount_residual), 0)
                FROM account_move am
                WHERE am.state = 'posted'
                  AND am.move_type = %s
                  AND am.amount_residual > 0
                  AND am.invoice_date_due < %s
            """, [move_type, today])
            return cr.fetchone()[0] or 0
        except Exception:
            cr.connection.rollback()
            return 0

    def _bank_balance(self, cr, journal_id):
        try:
            cr.execute("""
                SELECT COALESCE(SUM(aml.balance), 0)
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE aml.journal_id = %s
                  AND am.state = 'posted'
                  AND aml.account_id IN (
                      SELECT id FROM account_account WHERE account_type = 'asset_cash'
                  )
            """, [journal_id])
            return cr.fetchone()[0] or 0
        except Exception:
            cr.connection.rollback()
            return 0

    @api.model
    def _macro_batch(self, cr, today, first_of_month):
        try:
            qonto = self._bank_balance(cr, 6)
            revolut = self._bank_balance(cr, 13)
            bcc = self._bank_balance(cr, 22)

            bsl_unrec = _safe_count(cr, "SELECT COUNT(*) FROM account_bank_statement_line WHERE NOT is_reconciled")

            overdue_out_count = _safe_count(cr, """
                SELECT COUNT(*) FROM account_move
                WHERE state = 'posted' AND move_type = 'out_invoice'
                  AND amount_residual > 0 AND invoice_date_due < CURRENT_DATE
            """)
            overdue_in_count = _safe_count(cr, """
                SELECT COUNT(*) FROM account_move
                WHERE state = 'posted' AND move_type = 'in_invoice'
                  AND amount_residual > 0 AND invoice_date_due < CURRENT_DATE
            """)

            cr.execute("""
                SELECT COALESCE(SUM(am.amount_total_signed), 0)
                FROM account_move am
                WHERE am.move_type = 'out_refund'
                  AND am.state = 'posted'
                  AND am.invoice_date >= %s
                  AND am.invoice_date <= %s
            """, [first_of_month, today])
            refund_mtd = cr.fetchone()[0] or 0

            gap = (qonto + revolut + bcc) - self._overdue_total(cr, today, "in_invoice")

            counts = [
                _fmt_euro(qonto), _fmt_euro(revolut), _fmt_euro(bcc),
                bsl_unrec, overdue_out_count, overdue_in_count,
                _fmt_euro(refund_mtd), _fmt_euro(gap),
            ]

            results = []
            for i, area in enumerate(_CASH_MACRO):
                results.append({
                    "id": area["id"], "label": area["label"],
                    "icon": area["icon"], "color": area["color"],
                    "count": counts[i], "visible": True,
                })
            return results
        except Exception as e:
            _logger.error("_macro_batch error: %s", e, exc_info=True)
            return []

    @api.model
    def _feed(self, cr):
        try:
            cr.execute("""
                SELECT mm.id, mm.body, mm.date, rp.name AS author_name
                FROM mail_message mm
                LEFT JOIN res_partner rp ON rp.id = mm.author_id
                WHERE mm.model = 'account.move'
                  AND mm.message_type IN ('comment', 'notification')
                  AND mm.body IS NOT NULL AND mm.body != ''
                  AND mm.date > NOW() - INTERVAL '30 days'
                ORDER BY mm.date DESC LIMIT 10
            """)
            feed = []
            for row in cr.fetchall():
                body = _HTML_RE.sub('', row[1] or '').strip()
                if len(body) > 120:
                    body = body[:117] + "..."
                if not body:
                    continue
                author = _jsonb_str(row[3]) or "Sistema"
                parts = str(author).split()
                ini = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else parts[0][:2].upper() if parts else "??"
                feed.append({"id": row[0], "body": body, "date": row[2].isoformat() if row[2] else "", "author": str(author), "initials": ini})
            return feed
        except Exception as e:
            _logger.error("_feed error: %s", e, exc_info=True)
            return []
