# -*- coding: utf-8 -*-
"""Workspace Quality — read-only data provider for Qualità section.
NO DATA CREATION. Pure SELECT queries on existing data.
"""
import logging
import re
from datetime import date, timedelta

from odoo import api, models

_logger = logging.getLogger(__name__)
_HTML_RE = re.compile(r'<[^>]+>')

_QA_MACRO = [
    {"id": "nc_open", "label": "NC aperte", "icon": "fa-exclamation-triangle", "color": "#FAECE7"},
    {"id": "ccp_pending", "label": "CCP da firmare", "icon": "fa-thermometer-half", "color": "#FAEEDA"},
    {"id": "doc_expiring", "label": "Doc in scadenza", "icon": "fa-file-text", "color": "#FBEAF0"},
    {"id": "audit_days", "label": "Audit IFS", "icon": "fa-shield", "color": "#EEEDFE"},
    {"id": "lots_expiring", "label": "Lotti in scadenza", "icon": "fa-cube", "color": "#E1F5EE"},
    {"id": "calibrations", "label": "Calibrazioni", "icon": "fa-wrench", "color": "#E6F1FB"},
    {"id": "quarantine", "label": "Quarantena", "icon": "fa-ban", "color": "#F1EFE8"},
    {"id": "training", "label": "Formazione", "icon": "fa-graduation-cap", "color": "#EAF3DE"},
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


class WorkspaceQuality(models.AbstractModel):
    _name = "workspace.quality"
    _description = "Workspace Quality Data Provider (read-only)"

    @api.model
    def get_qa_data(self):
        profile = self.env["res.users"]._get_workspace_profile(self.env.user)
        cr = self.env.cr
        today = date.today()

        kpis = self._kpis(cr, today)
        macro = self._macro_batch(cr, today)
        feed = self._feed(cr)

        hero = {
            "greet": "Qualità & Sicurezza",
            "sub": f"{kpis[0]['raw']} NC · {kpis[3]['raw']} lotti in scadenza · audit IFS tra {kpis[2]['raw']} gg",
            "tip": {"text": "Verifica lotti con data avviso raggiunta nei prossimi 7 giorni.", "primary": "Vedi", "secondary": "Ignora"},
            "progress": {"done": 0, "total": 0, "pct": 0},
        }

        return {
            "user": profile, "hero": hero, "kpis": kpis, "macro": macro,
            "filters": ["Tutto", "Critici", "NC", "CCP", "Documenti", "Lotti"],
            "feed": feed,
        }

    @api.model
    def get_qa_list(self, filter_key="tutto"):
        cr = self.env.cr
        today = date.today()
        items = []

        # NC open
        if filter_key in ("tutto", "critici", "nc"):
            nc_count = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_nc WHERE state NOT IN ('closed','done')")
            if nc_count > 0:
                try:
                    cr.execute("""
                        SELECT id, reference, description, state, severity, date
                        FROM cf_haccp_nc WHERE state NOT IN ('closed','done')
                        ORDER BY date DESC LIMIT 10
                    """)
                    for row in cr.fetchall():
                        days = (today - row[5]).days if row[5] else 0
                        items.append({
                            "id": row[0], "type": "nc", "item_id": row[0],
                            "title": row[1] or f"NC #{row[0]}",
                            "subtitle": (row[2] or "")[:80],
                            "cat": "Non conformità", "icon": "fa-exclamation-triangle", "icon_color": "#DC2626",
                            "status": row[3] or "open",
                            "pill_status": "red" if row[4] == "critical" else "amber",
                            "pill_label": f"-{days} gg" if days > 0 else "oggi",
                            "days": days,
                        })
                except Exception:
                    cr.connection.rollback()

        # CCP pending
        if filter_key in ("tutto", "critici", "ccp"):
            ccp_count = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_ccp")
            if ccp_count > 0:
                try:
                    cr.execute("SELECT id, name, description FROM cf_haccp_ccp ORDER BY id LIMIT 10")
                    for row in cr.fetchall():
                        items.append({
                            "id": row[0], "type": "ccp", "item_id": row[0],
                            "title": _jsonb_str(row[1]) or f"CCP #{row[0]}",
                            "subtitle": (_jsonb_str(row[2]) or "")[:80],
                            "cat": "HACCP", "icon": "fa-thermometer-half", "icon_color": "#D97706",
                            "status": "active", "pill_status": "green", "pill_label": "attivo", "days": 0,
                        })
                except Exception:
                    cr.connection.rollback()

        # Stock lots expiring 30d
        if filter_key in ("tutto", "critici", "lotti"):
            cr.execute("""
                SELECT sl.id, sl.name, sl.expiration_date, pp.name AS product_name
                FROM stock_lot sl
                LEFT JOIN product_product pprod ON pprod.id = sl.product_id
                LEFT JOIN product_template pp ON pp.id = pprod.product_tmpl_id
                WHERE sl.expiration_date IS NOT NULL
                  AND sl.expiration_date <= %s
                ORDER BY sl.expiration_date ASC
                LIMIT 20
            """, [today + timedelta(days=30)])
            for row in cr.fetchall():
                days = (row[2] - today).days if row[2] else 0
                prod_name = _jsonb_str(row[3]) or ""
                if days < 0:
                    ps, pl = "red", f"{days} gg"
                elif days <= 7:
                    ps, pl = "amber", f"+{days} gg"
                else:
                    ps, pl = "green", f"+{days} gg"
                items.append({
                    "id": row[0], "type": "lot", "item_id": row[0],
                    "title": f"Lotto {row[1] or '?'}",
                    "subtitle": prod_name[:80],
                    "cat": "Lotti", "icon": "fa-cube", "icon_color": "#6B7280",
                    "status": "expiring", "pill_status": ps, "pill_label": pl, "days": days,
                })

        # Documents/certifications
        if filter_key in ("tutto", "documenti"):
            doc_count = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_document")
            if doc_count > 0:
                try:
                    cr.execute("SELECT id, name, date_to FROM cf_haccp_document ORDER BY date_to ASC NULLS LAST LIMIT 10")
                    for row in cr.fetchall():
                        days = (row[2] - today).days if row[2] else 999
                        items.append({
                            "id": row[0], "type": "cert", "item_id": row[0],
                            "title": _jsonb_str(row[1]) or f"Doc #{row[0]}",
                            "subtitle": "", "cat": "Certificazione",
                            "icon": "fa-file-text", "icon_color": "#EC4899",
                            "status": "active",
                            "pill_status": "red" if days < 30 else ("amber" if days < 90 else "green"),
                            "pill_label": f"+{days} gg" if days >= 0 else f"{days} gg",
                            "days": days,
                        })
                except Exception:
                    cr.connection.rollback()

        # Sort by urgency
        items.sort(key=lambda x: x["days"])
        return {"items": items}

    @api.model
    def get_ccp_grid(self):
        cr = self.env.cr
        ccps = []
        count = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_ccp")
        if count > 0:
            try:
                cr.execute("SELECT id, name, description FROM cf_haccp_ccp ORDER BY id")
                for row in cr.fetchall():
                    ccps.append({
                        "id": row[0],
                        "title": _jsonb_str(row[1]) or f"CCP #{row[0]}",
                        "description": (_jsonb_str(row[2]) or "")[:120],
                        "status": "green", "status_label": "Conforme",
                    })
            except Exception:
                cr.connection.rollback()
        return {"ccps": ccps, "empty_msg": "Modulo HACCP non popolato — nessun CCP registrato." if not ccps else ""}

    @api.model
    def get_docs_grid(self):
        cr = self.env.cr
        docs = []
        today = date.today()
        count = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_document")
        if count > 0:
            try:
                cr.execute("SELECT id, name, date_to FROM cf_haccp_document ORDER BY date_to ASC NULLS LAST LIMIT 20")
                for row in cr.fetchall():
                    days = (row[2] - today).days if row[2] else 999
                    docs.append({
                        "id": row[0],
                        "title": _jsonb_str(row[1]) or f"Doc #{row[0]}",
                        "expiry": str(row[2]) if row[2] else "—",
                        "days_to_expiry": days,
                        "status": "red" if days < 30 else ("amber" if days < 90 else "green"),
                        "status_label": "Scaduto" if days < 0 else ("In scadenza" if days < 30 else "Valido"),
                    })
            except Exception:
                cr.connection.rollback()
        return {"docs": docs, "empty_msg": "Nessun certificato registrato nel modulo HACCP." if not docs else ""}

    @api.model
    def get_qa_detail(self, item_type, item_id):
        cr = self.env.cr
        today = date.today()

        if item_type == "lot":
            cr.execute("""
                SELECT sl.id, sl.name, sl.expiration_date, sl.removal_date, sl.alert_date,
                       pp.name AS product_name
                FROM stock_lot sl
                LEFT JOIN product_product pprod ON pprod.id = sl.product_id
                LEFT JOIN product_template pp ON pp.id = pprod.product_tmpl_id
                WHERE sl.id = %s
            """, [item_id])
            row = cr.fetchone()
            if not row:
                return {"error": "Lotto non trovato"}
            days = (row[2] - today).days if row[2] else 999
            return {
                "item": {
                    "id": row[0], "type": "lot",
                    "title": f"Lotto {row[1] or '?'}",
                    "subtitle": _jsonb_str(row[5]) or "",
                    "expiry": str(row[2]) if row[2] else "—",
                    "alert_date": str(row[4]) if row[4] else "—",
                    "days_to_expiry": days,
                    "status": "red" if days < 0 else ("amber" if days < 30 else "green"),
                },
                "chain": [],
            }

        if item_type == "nc":
            try:
                cr.execute("SELECT id, reference, description, state, severity, date, corrective_action FROM cf_haccp_nc WHERE id = %s", [item_id])
                row = cr.fetchone()
                if row:
                    return {
                        "item": {
                            "id": row[0], "type": "nc", "title": row[1] or f"NC #{row[0]}",
                            "subtitle": (row[2] or "")[:200], "status": row[3] or "open",
                            "severity": row[4] or "—", "date": str(row[5]) if row[5] else "—",
                            "corrective_action": (row[6] or "")[:200],
                        },
                        "chain": [],
                    }
            except Exception:
                cr.connection.rollback()

        return {"item": {"id": item_id, "type": item_type, "title": f"{item_type} #{item_id}", "subtitle": "Dettaglio non disponibile"}, "chain": []}

    # ─── KPIs ──────────────────────────────────────────
    @api.model
    def _kpis(self, cr, today):
        nc_open = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_nc WHERE state NOT IN ('closed','done')")
        ccp_pending = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_ccp_log WHERE create_date >= CURRENT_DATE - INTERVAL '7 days'")

        # IFS audit days (from seed project)
        cr.execute("SELECT date FROM project_project WHERE name ILIKE '%%IFS%%' AND active=true LIMIT 1")
        ifs_row = cr.fetchone()
        ifs_days = (ifs_row[0] - today).days if ifs_row and ifs_row[0] else 999

        cr.execute("SELECT COUNT(*) FROM stock_lot WHERE expiration_date IS NOT NULL AND expiration_date <= %s", [today + timedelta(days=30)])
        lots_exp = cr.fetchone()[0] or 0

        return [
            {"id": "nc", "label": "NC aperte", "value": str(nc_open), "raw": nc_open, "icon": "fa-exclamation-triangle"},
            {"id": "ccp", "label": "CCP log recenti", "value": str(ccp_pending), "raw": ccp_pending, "icon": "fa-thermometer-half"},
            {"id": "ifs", "label": "Audit IFS", "value": f"{ifs_days} gg", "raw": ifs_days, "icon": "fa-shield"},
            {"id": "lots", "label": "Lotti in scadenza", "value": str(lots_exp), "raw": lots_exp, "icon": "fa-cube"},
        ]

    # ─── Macro ─────────────────────────────────────────
    @api.model
    def _macro_batch(self, cr, today):
        nc = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_nc WHERE state NOT IN ('closed','done')")
        ccp = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_ccp")
        docs = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_document WHERE date_to IS NOT NULL AND date_to <= CURRENT_DATE + 30")

        cr.execute("SELECT date FROM project_project WHERE name ILIKE '%%IFS%%' AND active=true LIMIT 1")
        r = cr.fetchone()
        ifs = (r[0] - today).days if r and r[0] else 0

        cr.execute("SELECT COUNT(*) FROM stock_lot WHERE expiration_date IS NOT NULL AND expiration_date <= %s", [today + timedelta(days=30)])
        lots = cr.fetchone()[0] or 0

        cal = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_calibration WHERE create_date >= CURRENT_DATE - INTERVAL '30 days'")
        quar = _safe_count(cr, "SELECT COUNT(*) FROM cf_haccp_quarantine WHERE create_date >= CURRENT_DATE - INTERVAL '90 days'")

        cr.execute("""SELECT COUNT(*) FROM cf_haccp_formazione WHERE create_date >= CURRENT_DATE - INTERVAL '90 days'""")
        train = cr.fetchone()[0] or 0

        counts = [nc, ccp, docs, ifs, lots, cal, quar, train]
        results = []
        for i, area in enumerate(_QA_MACRO):
            results.append({"id": area["id"], "label": area["label"], "icon": area["icon"], "color": area["color"], "count": counts[i], "visible": True})
        return results

    # ─── Feed ──────────────────────────────────────────
    @api.model
    def _feed(self, cr):
        cr.execute("""
            SELECT mm.id, mm.body, mm.date, rp.name AS author_name
            FROM mail_message mm
            LEFT JOIN res_partner rp ON rp.id=mm.author_id
            WHERE mm.model IN ('cf.haccp.nc','cf.haccp.ccp','cf.haccp.document','stock.lot','quality.alert')
              AND mm.message_type IN ('comment','notification')
              AND mm.body IS NOT NULL AND mm.body != ''
              AND mm.date > NOW() - INTERVAL '90 days'
            ORDER BY mm.date DESC LIMIT 10
        """)
        feed = []
        for row in cr.fetchall():
            body = _HTML_RE.sub('', row[1] or '').strip()
            if len(body) > 120: body = body[:117] + "..."
            if not body: continue
            author = _jsonb_str(row[3]) or "Sistema"
            parts = str(author).split()
            ini = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else parts[0][:2].upper() if parts else "??"
            feed.append({"id": row[0], "body": body, "date": row[2].isoformat() if row[2] else "", "author": str(author), "initials": ini})
        return feed
