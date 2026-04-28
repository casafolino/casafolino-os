# -*- coding: utf-8 -*-
"""Workspace Investor & CdA — read-only data provider for Investor section.
NO DATA CREATION. Pure SELECT queries on existing data.
"""
import logging
import re
from datetime import date, timedelta

from odoo import api, models

_logger = logging.getLogger(__name__)
_HTML_RE = re.compile(r'<[^>]+>')

_INV_MACRO = [
    {"id": "events_next", "label": "Prossimi eventi", "icon": "fa-calendar-check-o", "color": "#E6F1FB"},
    {"id": "board_meetings", "label": "CdA", "icon": "fa-users", "color": "#EEEDFE"},
    {"id": "crowdfunding", "label": "Crowdfunding", "icon": "fa-rocket", "color": "#E1F5EE"},
    {"id": "investor_comms", "label": "Comunicazioni", "icon": "fa-envelope-o", "color": "#FAEEDA"},
    {"id": "pending_docs", "label": "Documenti", "icon": "fa-folder-open", "color": "#FAECE7"},
    {"id": "milestones", "label": "Milestone", "icon": "fa-flag-checkered", "color": "#FBEAF0"},
]

_INV_KEYWORDS = ['investor', 'cda', 'board', 'crowdfund', 'consiglio', 'assemblea', 'soci']


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


class WorkspaceInvestor(models.AbstractModel):
    _name = "workspace.investor"
    _description = "Workspace Investor & CdA Data Provider (read-only)"

    @api.model
    def get_inv_data(self):
        try:
            profile = self.env["res.users"]._get_workspace_profile(self.env.user)
            cr = self.env.cr
            today = date.today()
            thirty_days = today + timedelta(days=30)

            # Events next 30d
            keyword_filter = " OR ".join(["ce.name::text ILIKE %s" for _ in _INV_KEYWORDS])
            params = [f"%%{kw}%%" for kw in _INV_KEYWORDS]
            params.extend([today, thirty_days])

            events_30d = _safe_count(cr, f"""
                SELECT COUNT(*) FROM calendar_event ce
                WHERE ({keyword_filter})
                  AND ce.start >= %s AND ce.start <= %s
                  AND ce.active = true
            """, params)

            # Investors active (placeholder)
            investors_active = 0

            # Crowdfunding progress
            crowdfunding_pct = self._crowdfunding_progress(cr)

            # Board communications last 90d
            comm_kw_filter = " OR ".join(["mm.subject ILIKE %s" for _ in _INV_KEYWORDS])
            comm_params = [f"%%{kw}%%" for kw in _INV_KEYWORDS]
            board_comms = _safe_count(cr, f"""
                SELECT COUNT(*) FROM mail_message mm
                WHERE ({comm_kw_filter})
                  AND mm.date > NOW() - INTERVAL '90 days'
                  AND mm.message_type IN ('email', 'comment')
            """, comm_params)

            kpis = [
                {"id": "events_30d", "label": "Eventi 30gg", "value": str(events_30d), "raw": events_30d, "icon": "fa-calendar-check-o"},
                {"id": "investors_active", "label": "Investitori attivi", "value": str(investors_active), "raw": investors_active, "icon": "fa-user-circle"},
                {"id": "crowdfunding", "label": "Crowdfunding", "value": f"{crowdfunding_pct}%", "raw": crowdfunding_pct, "icon": "fa-rocket"},
                {"id": "board_comms", "label": "Comunicazioni CdA", "value": str(board_comms), "raw": board_comms, "icon": "fa-comments-o"},
            ]

            macro = self._macro_batch(cr, today)
            feed = self._feed(cr)

            hero = {
                "greet": "Investor & CdA",
                "sub": f"{events_30d} eventi prossimi · Crowdfunding {crowdfunding_pct}% · {board_comms} comunicazioni",
                "tip": {"text": "Verifica eventi in programma e comunicazioni con investitori.", "primary": "Vedi", "secondary": "Ignora"},
                "progress": {"done": 0, "total": 0, "pct": 0},
            }

            return {
                "user": profile, "hero": hero, "kpis": kpis, "macro": macro,
                "filters": ["Tutti", "CdA", "Crowdfunding", "Assemblea"],
                "feed": feed,
            }
        except Exception as e:
            _logger.error("get_inv_data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_inv_events(self, filter_key="tutti"):
        try:
            cr = self.env.cr
            today = date.today()

            if filter_key == "cda":
                keywords = ["cda", "board", "consiglio"]
            elif filter_key == "crowdfunding":
                keywords = ["crowdfund"]
            elif filter_key == "assemblea":
                keywords = ["assemblea", "soci"]
            else:
                keywords = _INV_KEYWORDS

            keyword_filter = " OR ".join(["ce.name::text ILIKE %s" for _ in keywords])
            params = [f"%%{kw}%%" for kw in keywords]
            params.append(today)

            cr.execute(f"""
                SELECT ce.id, ce.name, ce.start, ce.stop, ce.location, ce.description
                FROM calendar_event ce
                WHERE ({keyword_filter})
                  AND ce.start >= %s
                  AND ce.active = true
                ORDER BY ce.start ASC
                LIMIT 30
            """, params)

            items = []
            for row in cr.fetchall():
                name = _jsonb_str(row[1]) or f"Evento #{row[0]}"
                start_dt = row[2]
                days_until = (start_dt.date() - today).days if start_dt else 0

                # Get attendees
                attendees = self._get_event_attendees(cr, row[0])

                items.append({
                    "id": row[0], "type": "event", "item_id": row[0],
                    "title": name[:80],
                    "subtitle": (row[4] or "")[:60],
                    "start": start_dt.isoformat() if start_dt else "",
                    "stop": row[3].isoformat() if row[3] else "",
                    "attendees": attendees,
                    "attendee_count": len(attendees),
                    "cat": "Evento", "icon": "fa-calendar", "icon_color": "#2563EB",
                    "status": "upcoming",
                    "pill_status": "green" if days_until > 7 else ("amber" if days_until > 0 else "red"),
                    "pill_label": f"+{days_until} gg" if days_until > 0 else "oggi",
                    "days": days_until,
                })
            return {"items": items}
        except Exception as e:
            _logger.error("get_inv_events error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_inv_comms(self):
        try:
            cr = self.env.cr

            comm_kw_filter = " OR ".join(["mm.subject ILIKE %s" for _ in _INV_KEYWORDS])
            params = [f"%%{kw}%%" for kw in _INV_KEYWORDS]

            cr.execute(f"""
                SELECT mm.id, mm.subject, mm.body, mm.date, rp.name AS author_name,
                       mm.model, mm.res_id
                FROM mail_message mm
                LEFT JOIN res_partner rp ON rp.id = mm.author_id
                WHERE ({comm_kw_filter})
                  AND mm.date > NOW() - INTERVAL '90 days'
                  AND mm.message_type IN ('email', 'comment')
                ORDER BY mm.date DESC
                LIMIT 30
            """, params)

            items = []
            for row in cr.fetchall():
                body = _HTML_RE.sub('', row[2] or '').strip()
                if len(body) > 120:
                    body = body[:117] + "..."
                author = _jsonb_str(row[4]) or "Sistema"
                items.append({
                    "id": row[0], "type": "comm", "item_id": row[0],
                    "title": (row[1] or "")[:80] or "Comunicazione",
                    "subtitle": f"{author[:30]} · {body[:60]}",
                    "body": body,
                    "date": row[3].isoformat() if row[3] else "",
                    "author": str(author),
                    "cat": "Comunicazione", "icon": "fa-envelope-o", "icon_color": "#059669",
                    "status": "sent",
                    "pill_status": "green", "pill_label": "inviato",
                })
            return {"items": items}
        except Exception as e:
            _logger.error("get_inv_comms error: %s", e, exc_info=True)
            return {"error": str(e)}

    @api.model
    def get_inv_detail(self, item_type, item_id):
        try:
            cr = self.env.cr

            if item_type == "event":
                cr.execute("""
                    SELECT ce.id, ce.name, ce.start, ce.stop, ce.location,
                           ce.description
                    FROM calendar_event ce
                    WHERE ce.id = %s
                """, [item_id])
                row = cr.fetchone()
                if not row:
                    return {"error": "Evento non trovato"}
                attendees = self._get_event_attendees(cr, row[0])
                desc = _HTML_RE.sub('', row[5] or '').strip()[:300] if row[5] else ""
                return {
                    "item": {
                        "id": row[0], "type": "event",
                        "title": _jsonb_str(row[1])[:80] or f"Evento #{row[0]}",
                        "subtitle": (row[4] or "")[:100],
                        "start": row[2].isoformat() if row[2] else "",
                        "stop": row[3].isoformat() if row[3] else "",
                        "description": desc,
                        "attendees": attendees,
                        "status": "upcoming",
                    },
                    "chain": [],
                }

            if item_type == "comm":
                cr.execute("""
                    SELECT mm.id, mm.subject, mm.body, mm.date, rp.name AS author_name
                    FROM mail_message mm
                    LEFT JOIN res_partner rp ON rp.id = mm.author_id
                    WHERE mm.id = %s
                """, [item_id])
                row = cr.fetchone()
                if not row:
                    return {"error": "Comunicazione non trovata"}
                body = _HTML_RE.sub('', row[2] or '').strip()[:500]
                return {
                    "item": {
                        "id": row[0], "type": "comm",
                        "title": (row[1] or "Comunicazione")[:80],
                        "subtitle": _jsonb_str(row[4]) or "Sistema",
                        "body": body,
                        "date": row[3].isoformat() if row[3] else "",
                        "status": "sent",
                    },
                    "chain": [],
                }

            return {"item": {"id": item_id, "type": item_type, "title": f"{item_type} #{item_id}", "subtitle": "Dettaglio non disponibile"}, "chain": []}
        except Exception as e:
            _logger.error("get_inv_detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Helpers ──────────────────────────────────────────

    def _get_event_attendees(self, cr, event_id):
        try:
            cr.execute("""
                SELECT rp.id, rp.name, rp.email
                FROM calendar_event_res_partner_rel cepr
                JOIN res_partner rp ON rp.id = cepr.res_partner_id
                WHERE cepr.calendar_event_id = %s
                LIMIT 20
            """, [event_id])
            attendees = []
            for row in cr.fetchall():
                name = _jsonb_str(row[1]) or ""
                attendees.append({
                    "id": row[0], "name": str(name),
                    "email": row[2] or "",
                })
            return attendees
        except Exception:
            cr.connection.rollback()
            return []

    def _crowdfunding_progress(self, cr):
        try:
            cr.execute("""
                SELECT pp.id, pp.name
                FROM project_project pp
                WHERE pp.name::text ILIKE '%%Crowdfunding%%4M%%'
                  AND pp.active = true
                LIMIT 1
            """)
            row = cr.fetchone()
            if not row:
                return 0
            proj_id = row[0]
            # Get task completion ratio as proxy for progress
            total = _safe_count(cr, "SELECT COUNT(*) FROM project_task WHERE project_id = %s AND active = true", (proj_id,))
            if total == 0:
                return 0
            done = _safe_count(cr, """
                SELECT COUNT(*) FROM project_task
                WHERE project_id = %s AND active = true
                  AND stage_id IN (SELECT id FROM project_task_type WHERE fold = true)
            """, (proj_id,))
            return int(round(done / total * 100)) if total > 0 else 0
        except Exception:
            return 0

    @api.model
    def _macro_batch(self, cr, today):
        try:
            thirty_days = today + timedelta(days=30)
            keyword_filter = " OR ".join(["ce.name::text ILIKE %s" for _ in _INV_KEYWORDS])
            params = [f"%%{kw}%%" for kw in _INV_KEYWORDS]
            params.extend([today, thirty_days])

            events_next = _safe_count(cr, f"""
                SELECT COUNT(*) FROM calendar_event ce
                WHERE ({keyword_filter})
                  AND ce.start >= %s AND ce.start <= %s
                  AND ce.active = true
            """, params)

            board_kw = ["cda", "board", "consiglio"]
            board_filter = " OR ".join(["ce.name::text ILIKE %s" for _ in board_kw])
            board_params = [f"%%{kw}%%" for kw in board_kw]
            board_params.extend([today, thirty_days])

            board_meetings = _safe_count(cr, f"""
                SELECT COUNT(*) FROM calendar_event ce
                WHERE ({board_filter})
                  AND ce.start >= %s AND ce.start <= %s
                  AND ce.active = true
            """, board_params)

            crowdfunding = self._crowdfunding_progress(cr)

            comm_kw_filter = " OR ".join(["mm.subject ILIKE %s" for _ in _INV_KEYWORDS])
            comm_params = [f"%%{kw}%%" for kw in _INV_KEYWORDS]
            investor_comms = _safe_count(cr, f"""
                SELECT COUNT(*) FROM mail_message mm
                WHERE ({comm_kw_filter})
                  AND mm.date > NOW() - INTERVAL '90 days'
                  AND mm.message_type IN ('email', 'comment')
            """, comm_params)

            pending_docs = 0  # Placeholder
            milestones = 0  # Placeholder

            counts = [events_next, board_meetings, f"{crowdfunding}%", investor_comms, pending_docs, milestones]
            results = []
            for i, area in enumerate(_INV_MACRO):
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
            comm_kw_filter = " OR ".join(["mm.subject ILIKE %s" for _ in _INV_KEYWORDS])
            params = [f"%%{kw}%%" for kw in _INV_KEYWORDS]

            cr.execute(f"""
                SELECT mm.id, mm.body, mm.date, rp.name AS author_name
                FROM mail_message mm
                LEFT JOIN res_partner rp ON rp.id = mm.author_id
                WHERE ({comm_kw_filter})
                  AND mm.message_type IN ('email', 'comment', 'notification')
                  AND mm.body IS NOT NULL AND mm.body != ''
                  AND mm.date > NOW() - INTERVAL '90 days'
                ORDER BY mm.date DESC LIMIT 10
            """, params)
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
