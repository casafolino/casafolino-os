# -*- coding: utf-8 -*-
"""Workspace Decisions — read-only data provider for Decisioni section.
NO DATA CREATION. Pure SELECT queries on existing data.
"""
import logging
import re
from datetime import date, timedelta

from odoo import api, models

_logger = logging.getLogger(__name__)
_HTML_RE = re.compile(r'<[^>]+>')

_DEC_MACRO = [
    {"id": "urgent_activities", "label": "Attività urgenti", "icon": "fa-bolt", "color": "#FAECE7"},
    {"id": "awaiting", "label": "In attesa", "icon": "fa-hourglass-half", "color": "#FAEEDA"},
    {"id": "high_leads", "label": "Lead caldi", "icon": "fa-fire", "color": "#FBEAF0"},
    {"id": "draft_invoices", "label": "Bozze importanti", "icon": "fa-file-text-o", "color": "#EEEDFE"},
    {"id": "overdue_tasks", "label": "Task scaduti", "icon": "fa-clock-o", "color": "#E1F5EE"},
    {"id": "blocked", "label": "Bloccati", "icon": "fa-ban", "color": "#F1EFE8"},
]


def _jsonb_str(val):
    if not val:
        return ""
    if isinstance(val, dict):
        return val.get("it_IT") or val.get("en_US") or next(iter(val.values()), "")
    return str(val)


def _safe_count(cr, sql, params=None):
    """Execute count query, return 0 if table doesn't exist."""
    try:
        cr.execute(sql, params or {})
        return cr.fetchone()[0] or 0
    except Exception:
        cr.connection.rollback()
        return 0


class WorkspaceDecisions(models.AbstractModel):
    _name = "workspace.decisions"
    _description = "Workspace Decisions Data Provider (read-only)"

    @api.model
    def get_dec_data(self):
        try:
            profile = self.env["res.users"]._get_workspace_profile(self.env.user)
            cr = self.env.cr
            today = date.today()
            uid = self.env.uid

            # KPIs
            urgent = _safe_count(cr, """
                SELECT COUNT(*) FROM mail_activity
                WHERE user_id = %s AND date_deadline <= %s
            """, (uid, today))

            awaiting = _safe_count(cr, """
                SELECT COUNT(*) FROM mail_activity
                WHERE user_id = %s AND date_deadline > %s
            """, (uid, today))

            approvals = _safe_count(cr, """
                SELECT COUNT(*) FROM account_move
                WHERE state = 'draft' AND amount_total > 1000
            """)

            blocked = _safe_count(cr, """
                SELECT COUNT(*) FROM project_task
                WHERE active = true AND kanban_state = 'blocked'
            """)

            kpis = [
                {"id": "urgent", "label": "Urgenti", "value": str(urgent), "raw": urgent, "icon": "fa-bolt"},
                {"id": "awaiting", "label": "In attesa", "value": str(awaiting), "raw": awaiting, "icon": "fa-hourglass-half"},
                {"id": "approvals", "label": "Approvazioni", "value": str(approvals), "raw": approvals, "icon": "fa-check-circle"},
                {"id": "blocked", "label": "Bloccati", "value": str(blocked), "raw": blocked, "icon": "fa-ban"},
            ]

            macro = self._macro_batch(cr, today, uid)
            feed = self._feed(cr)

            hero = {
                "greet": "Decisioni",
                "sub": f"{urgent} urgenti · {awaiting} in attesa · {approvals} da approvare · {blocked} bloccati",
                "tip": {"text": "Prioritizza le attività urgenti e le approvazioni in sospeso.", "primary": "Vedi", "secondary": "Ignora"},
                "progress": {"done": 0, "total": 0, "pct": 0},
            }

            return {
                "user": profile, "hero": hero, "kpis": kpis, "macro": macro,
                "filters": ["Tutte", "Urgenti", "Lead", "Bozze", "Task"],
                "feed": feed,
            }
        except Exception as e:
            _logger.error("get_dec_data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_dec_list(self, filter_key="tutte"):
        try:
            cr = self.env.cr
            today = date.today()
            uid = self.env.uid
            items = []

            # Urgent activities (mail.activity) for current user
            if filter_key in ("tutte", "urgenti"):
                try:
                    cr.execute("""
                        SELECT ma.id, ma.summary, ma.date_deadline, ma.res_model, ma.res_id,
                               mat.name AS type_name
                        FROM mail_activity ma
                        LEFT JOIN mail_activity_type mat ON mat.id = ma.activity_type_id
                        WHERE ma.user_id = %s
                          AND ma.date_deadline <= %s
                        ORDER BY ma.date_deadline ASC
                        LIMIT 20
                    """, [uid, today])
                    for row in cr.fetchall():
                        days = (today - row[2]).days if row[2] else 0
                        type_name = _jsonb_str(row[5]) or "Attività"
                        items.append({
                            "id": row[0], "type": "activity", "item_id": row[0],
                            "title": (row[1] or type_name)[:80],
                            "subtitle": f"{row[3] or ''} #{row[4] or ''}",
                            "cat": "Attività urgente", "icon": "fa-bolt", "icon_color": "#DC2626",
                            "status": "overdue", "pill_status": "red",
                            "pill_label": f"-{days} gg" if days > 0 else "oggi",
                            "days": days, "priority": 1,
                        })
                except Exception:
                    cr.connection.rollback()

            # High-probability leads with activities
            if filter_key in ("tutte", "lead"):
                try:
                    cr.execute("""
                        SELECT cl.id, cl.name, cl.probability, cl.expected_revenue,
                               rp.name AS partner_name
                        FROM crm_lead cl
                        LEFT JOIN res_partner rp ON rp.id = cl.partner_id
                        WHERE cl.active = true
                          AND cl.probability >= 70
                          AND cl.id IN (SELECT res_id FROM mail_activity WHERE res_model = 'crm.lead')
                        ORDER BY cl.probability DESC, cl.expected_revenue DESC
                        LIMIT 15
                    """)
                    for row in cr.fetchall():
                        partner = _jsonb_str(row[4]) or ""
                        items.append({
                            "id": row[0], "type": "lead", "item_id": row[0],
                            "title": (row[1] or "")[:80] or f"Lead #{row[0]}",
                            "subtitle": f"{partner[:40]} · {int(row[2] or 0)}%",
                            "cat": "Lead caldo", "icon": "fa-fire", "icon_color": "#EA580C",
                            "status": "active", "pill_status": "amber",
                            "pill_label": f"{int(row[2] or 0)}%",
                            "days": 0, "priority": 2,
                        })
                except Exception:
                    cr.connection.rollback()

            # Overdue project tasks on Acquisizione/Finanza projects
            if filter_key in ("tutte", "task"):
                try:
                    cr.execute("""
                        SELECT pt.id, pt.name AS task_name, pt.date_deadline,
                               pp.name AS proj_name
                        FROM project_task pt
                        JOIN project_project pp ON pp.id = pt.project_id
                        WHERE pt.active = true
                          AND pt.date_deadline IS NOT NULL
                          AND pt.date_deadline < %s
                          AND pt.stage_id IN (
                              SELECT id FROM project_task_type WHERE fold = false
                          )
                          AND (pp.name::text ILIKE '%%Acquisizion%%' OR pp.name::text ILIKE '%%Finanz%%')
                        ORDER BY pt.date_deadline ASC
                        LIMIT 15
                    """, [today])
                    for row in cr.fetchall():
                        days = (today - row[2]).days if row[2] else 0
                        items.append({
                            "id": row[0], "type": "task", "item_id": row[0],
                            "title": _jsonb_str(row[1])[:80] or f"Task #{row[0]}",
                            "subtitle": _jsonb_str(row[3])[:60] or "",
                            "cat": "Task scaduto", "icon": "fa-clock-o", "icon_color": "#7C3AED",
                            "status": "overdue", "pill_status": "red",
                            "pill_label": f"-{days} gg",
                            "days": days, "priority": 3,
                        })
                except Exception:
                    cr.connection.rollback()

            # Draft invoices > 1000 EUR
            if filter_key in ("tutte", "bozze"):
                try:
                    cr.execute("""
                        SELECT am.id, am.name, am.amount_total, am.move_type,
                               rp.name AS partner_name
                        FROM account_move am
                        LEFT JOIN res_partner rp ON rp.id = am.partner_id
                        WHERE am.state = 'draft'
                          AND am.amount_total > 1000
                          AND am.move_type IN ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
                        ORDER BY am.amount_total DESC
                        LIMIT 15
                    """)
                    for row in cr.fetchall():
                        partner = _jsonb_str(row[4]) or ""
                        amt = row[2] or 0
                        items.append({
                            "id": row[0], "type": "draft_invoice", "item_id": row[0],
                            "title": (row[1] or "")[:80] or f"Bozza #{row[0]}",
                            "subtitle": f"{partner[:40]} · {_fmt_euro(amt)}",
                            "cat": "Bozza da approvare", "icon": "fa-file-text-o", "icon_color": "#2563EB",
                            "status": "draft", "pill_status": "amber",
                            "pill_label": _fmt_euro(amt),
                            "days": 0, "priority": 4,
                        })
                except Exception:
                    cr.connection.rollback()

            # Sort by priority then days
            items.sort(key=lambda x: (x.get("priority", 99), -x.get("days", 0)))
            return {"items": items}
        except Exception as e:
            _logger.error("get_dec_list error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_dec_detail(self, item_type, item_id):
        try:
            cr = self.env.cr

            if item_type == "activity":
                cr.execute("""
                    SELECT ma.id, ma.summary, ma.date_deadline, ma.res_model, ma.res_id,
                           ma.note, mat.name AS type_name
                    FROM mail_activity ma
                    LEFT JOIN mail_activity_type mat ON mat.id = ma.activity_type_id
                    WHERE ma.id = %s
                """, [item_id])
                row = cr.fetchone()
                if not row:
                    return {"error": "Attività non trovata"}
                return {
                    "item": {
                        "id": row[0], "type": "activity",
                        "title": (row[1] or _jsonb_str(row[6]) or "Attività")[:80],
                        "subtitle": f"{row[3] or ''} #{row[4] or ''}",
                        "deadline": str(row[2]) if row[2] else "",
                        "note": _HTML_RE.sub('', row[5] or '').strip()[:200] if row[5] else "",
                        "status": "urgente",
                    },
                    "chain": [],
                }

            if item_type == "lead":
                cr.execute("""
                    SELECT cl.id, cl.name, cl.probability, cl.expected_revenue,
                           rp.name AS partner_name, cl.stage_id,
                           cs.name AS stage_name
                    FROM crm_lead cl
                    LEFT JOIN res_partner rp ON rp.id = cl.partner_id
                    LEFT JOIN crm_stage cs ON cs.id = cl.stage_id
                    WHERE cl.id = %s
                """, [item_id])
                row = cr.fetchone()
                if not row:
                    return {"error": "Lead non trovato"}
                return {
                    "item": {
                        "id": row[0], "type": "lead",
                        "title": (row[1] or "")[:80],
                        "subtitle": _jsonb_str(row[4]) or "",
                        "probability": int(row[2] or 0),
                        "revenue": row[3] or 0,
                        "stage": _jsonb_str(row[6]) or "",
                        "status": "active",
                    },
                    "chain": [],
                }

            if item_type == "task":
                cr.execute("""
                    SELECT pt.id, pt.name, pt.date_deadline,
                           pp.name AS proj_name, pts.name AS stage_name
                    FROM project_task pt
                    LEFT JOIN project_project pp ON pp.id = pt.project_id
                    LEFT JOIN project_task_type pts ON pts.id = pt.stage_id
                    WHERE pt.id = %s
                """, [item_id])
                row = cr.fetchone()
                if not row:
                    return {"error": "Task non trovato"}
                return {
                    "item": {
                        "id": row[0], "type": "task",
                        "title": _jsonb_str(row[1])[:80] or f"Task #{row[0]}",
                        "subtitle": _jsonb_str(row[3]) or "",
                        "deadline": str(row[2]) if row[2] else "",
                        "stage": _jsonb_str(row[4]) or "",
                        "status": "overdue",
                    },
                    "chain": [],
                }

            if item_type == "draft_invoice":
                cr.execute("""
                    SELECT am.id, am.name, am.amount_total, am.move_type,
                           rp.name AS partner_name
                    FROM account_move am
                    LEFT JOIN res_partner rp ON rp.id = am.partner_id
                    WHERE am.id = %s
                """, [item_id])
                row = cr.fetchone()
                if not row:
                    return {"error": "Bozza non trovata"}
                return {
                    "item": {
                        "id": row[0], "type": "draft_invoice",
                        "title": (row[1] or "")[:80],
                        "subtitle": _jsonb_str(row[4]) or "",
                        "amount_fmt": _fmt_euro(row[2]),
                        "direction": "out" if "out" in (row[3] or "") else "in",
                        "status": "draft",
                    },
                    "chain": [],
                }

            return {"item": {"id": item_id, "type": item_type, "title": f"{item_type} #{item_id}", "subtitle": "Dettaglio non disponibile"}, "chain": []}
        except Exception as e:
            _logger.error("get_dec_detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Macro ─────────────────────────────────────────

    @api.model
    def _macro_batch(self, cr, today, uid):
        try:
            urgent = _safe_count(cr, """
                SELECT COUNT(*) FROM mail_activity
                WHERE user_id = %s AND date_deadline <= %s
            """, (uid, today))

            awaiting = _safe_count(cr, """
                SELECT COUNT(*) FROM mail_activity
                WHERE user_id = %s AND date_deadline > %s
            """, (uid, today))

            high_leads = _safe_count(cr, """
                SELECT COUNT(*) FROM crm_lead
                WHERE active = true AND probability >= 70
                  AND id IN (SELECT res_id FROM mail_activity WHERE res_model = 'crm.lead')
            """)

            draft_inv = _safe_count(cr, """
                SELECT COUNT(*) FROM account_move
                WHERE state = 'draft' AND amount_total > 1000
                  AND move_type IN ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
            """)

            overdue_tasks = _safe_count(cr, """
                SELECT COUNT(*) FROM project_task
                WHERE active = true AND date_deadline IS NOT NULL AND date_deadline < CURRENT_DATE
                  AND stage_id IN (SELECT id FROM project_task_type WHERE fold = false)
            """)

            blocked = _safe_count(cr, """
                SELECT COUNT(*) FROM project_task
                WHERE active = true AND kanban_state = 'blocked'
            """)

            counts = [urgent, awaiting, high_leads, draft_inv, overdue_tasks, blocked]
            results = []
            for i, area in enumerate(_DEC_MACRO):
                results.append({
                    "id": area["id"], "label": area["label"],
                    "icon": area["icon"], "color": area["color"],
                    "count": counts[i], "visible": True,
                })
            return results
        except Exception as e:
            _logger.error("_macro_batch error: %s", e, exc_info=True)
            return []

    # ─── Feed ──────────────────────────────────────────

    @api.model
    def _feed(self, cr):
        try:
            cr.execute("""
                SELECT mm.id, mm.body, mm.date, rp.name AS author_name
                FROM mail_message mm
                LEFT JOIN res_partner rp ON rp.id = mm.author_id
                WHERE mm.model IN ('account.move', 'crm.lead', 'project.task', 'mail.activity')
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
