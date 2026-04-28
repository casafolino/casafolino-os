# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta

from odoo import api, models, fields

_logger = logging.getLogger(__name__)

# Static tips per role (placeholder for future AI)
_TIPS = {
    "antonio": {
        "text": "Hai lead silenti da oltre 14 giorni. Considera un follow-up.",
        "primary": "Delega",
        "secondary": "Vedi quali",
    },
    "josefina": {
        "text": "3 lead export in attesa di campione. Verifica spedizioni.",
        "primary": "Verifica",
        "secondary": "Dettaglio",
    },
    "martina": {
        "text": "Ci sono fatture da registrare questa settimana.",
        "primary": "Registra",
        "secondary": "Vedi lista",
    },
    "maria": {
        "text": "Calibrazioni strumenti in scadenza nei prossimi 7 giorni.",
        "primary": "Pianifica",
        "secondary": "Dettaglio",
    },
}

_WEEKDAYS_IT = {
    0: "Lun", 1: "Mar", 2: "Mer", 3: "Gio", 4: "Ven", 5: "Sab", 6: "Dom",
}

_MONTHS_IT = {
    1: "gen", 2: "feb", 3: "mar", 4: "apr", 5: "mag", 6: "giu",
    7: "lug", 8: "ago", 9: "set", 10: "ott", 11: "nov", 12: "dic",
}

# Macro area definitions per role
_MACRO_AREAS = [
    {
        "id": "pipeline",
        "label": "Pipeline lead",
        "icon": "fa-bullseye",
        "color": "#EEEDFE",
        "roles": ["antonio", "josefina"],
    },
    {
        "id": "projects",
        "label": "Progetti attivi",
        "icon": "fa-folder-open",
        "color": "#E1F5EE",
        "roles": ["antonio", "martina"],
    },
    {
        "id": "mail",
        "label": "Mail in sospeso",
        "icon": "fa-envelope",
        "color": "#FAECE7",
        "roles": ["antonio", "josefina", "martina", "maria"],
    },
    {
        "id": "agenda",
        "label": "Agenda oggi",
        "icon": "fa-calendar",
        "color": "#FBEAF0",
        "roles": ["antonio", "josefina", "martina", "maria"],
    },
    {
        "id": "cassa",
        "label": "Cassa & banca",
        "icon": "fa-university",
        "color": "#FAEEDA",
        "roles": ["antonio", "martina"],
    },
    {
        "id": "decisions",
        "label": "Decisioni in attesa",
        "icon": "fa-gavel",
        "color": "#E6F1FB",
        "roles": ["antonio"],
    },
    {
        "id": "investor",
        "label": "Investor & CdA",
        "icon": "fa-briefcase",
        "color": "#EAF3DE",
        "roles": ["antonio"],
    },
    {
        "id": "quality",
        "label": "Alert qualità",
        "icon": "fa-shield",
        "color": "#F1EFE8",
        "roles": ["antonio", "maria"],
    },
]


def _jsonb_str(val):
    """Extract string from JSONB name field (dict or str)."""
    if not val:
        return "Attività"
    if isinstance(val, dict):
        return val.get("it_IT") or val.get("en_US") or next(iter(val.values()), "Attività")
    return str(val)


class WorkspaceDashboard(models.AbstractModel):
    _name = "workspace.dashboard"
    _description = "Workspace Dashboard Data Provider"

    @api.model
    def get_dashboard_data(self):
        user = self.env.user
        profile = self.env["res.users"]._get_workspace_profile(user)
        role = profile["role"]
        uid = user.id
        pid = user.partner_id.id
        today = date.today()
        cr = self.env.cr

        # Greeting
        hour = fields.Datetime.context_timestamp(
            self, fields.Datetime.now()
        ).hour
        if hour < 13:
            saluto = "Buongiorno"
        elif hour < 18:
            saluto = "Buon pomeriggio"
        else:
            saluto = "Buonasera"

        greet = f"{saluto} {profile['name']}"

        # Date string
        wd = _WEEKDAYS_IT.get(today.weekday(), "")
        mn = _MONTHS_IT.get(today.month, "")
        week_num = today.isocalendar()[1]

        # KPIs
        kpis = self._compute_kpis(cr, uid, today, role)

        # Progress
        progress = self._compute_progress(cr, uid, today)

        # Sub line
        sub = (
            f"{wd} {today.day} {mn} · settimana {week_num} · "
            f"{kpis[3]['raw']} critici, {progress['total']} oggi"
        )

        # Macro areas
        macro = self._compute_macro(cr, uid, pid, today, role)

        # Today section
        today_data = self._compute_today(cr, uid, pid, today)

        # Feed
        feed = self._compute_feed(cr, pid, today)

        # Tip
        tip = _TIPS.get(role, _TIPS["antonio"])

        return {
            "user": profile,
            "greet": greet,
            "sub": sub,
            "progress": progress,
            "tip": tip,
            "kpis": kpis,
            "macro": macro,
            "today": today_data,
            "feed": feed,
        }

    @api.model
    def _compute_kpis(self, cr, uid, today, role):
        month_start = today.replace(day=1)

        # 1. Pipeline B2B
        cr.execute("""
            SELECT COALESCE(SUM(expected_revenue), 0)
            FROM crm_lead
            WHERE active = true
              AND stage_id NOT IN (SELECT id FROM crm_stage WHERE is_won = true)
              AND probability > 0
        """)
        pipeline = cr.fetchone()[0] or 0

        # 2. Fatturato MTD
        cr.execute("""
            SELECT COALESCE(SUM(amount_untaxed_signed), 0)
            FROM account_move
            WHERE move_type = 'out_invoice'
              AND state = 'posted'
              AND invoice_date >= %s
        """, [month_start])
        fatturato = cr.fetchone()[0] or 0

        # 3. Cassa disponibile
        cr.execute("""
            SELECT COALESCE(SUM(aml.balance), 0)
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE am.state = 'posted'
              AND aa.account_type = 'asset_cash'
        """)
        cassa = cr.fetchone()[0] or 0

        # 4. Alert critici (overdue activities for user)
        cr.execute("""
            SELECT COUNT(*)
            FROM mail_activity
            WHERE date_deadline < %s
              AND user_id = %s
        """, [today, uid])
        alert = cr.fetchone()[0] or 0

        return [
            {
                "id": "pipeline",
                "label": "Pipeline B2B",
                "value": self._fmt_euro(pipeline),
                "raw": pipeline,
                "icon": "fa-rocket",
                "trend": "up",
            },
            {
                "id": "fatturato",
                "label": "Fatturato MTD",
                "value": self._fmt_euro(fatturato),
                "raw": fatturato,
                "icon": "fa-line-chart",
                "trend": "up" if fatturato > 0 else "neutral",
            },
            {
                "id": "cassa",
                "label": "Cassa disponibile",
                "value": self._fmt_euro(cassa),
                "raw": cassa,
                "icon": "fa-university",
                "trend": "up" if cassa > 0 else "down",
            },
            {
                "id": "alert",
                "label": "Alert critici",
                "value": str(alert),
                "raw": alert,
                "icon": "fa-exclamation-triangle",
                "trend": "down" if alert > 5 else "neutral",
            },
        ]

    @api.model
    def _compute_progress(self, cr, uid, today):
        # Total activities today
        cr.execute("""
            SELECT COUNT(*) FROM mail_activity
            WHERE user_id = %s AND date_deadline = %s
        """, [uid, today])
        total_today = cr.fetchone()[0] or 0

        # Done today (activities completed = logged in mail_message today)
        cr.execute("""
            SELECT COUNT(*) FROM mail_message
            WHERE author_id = (SELECT partner_id FROM res_users WHERE id = %s)
              AND subtype_id IS NOT NULL
              AND date::date = %s
              AND message_type IN ('notification', 'comment')
        """, [uid, today])
        done = cr.fetchone()[0] or 0

        total = max(total_today, done)
        pct = int((done / total * 100)) if total > 0 else 0

        return {"done": done, "total": total, "pct": pct}

    @api.model
    def _compute_macro(self, cr, uid, pid, today, role):
        results = []
        for area in _MACRO_AREAS:
            if role not in area["roles"]:
                count = 0
            else:
                count = self._macro_count(cr, uid, pid, today, area["id"])
            results.append({
                "id": area["id"],
                "label": area["label"],
                "icon": area["icon"],
                "color": area["color"],
                "count": count,
                "visible": role in area["roles"],
            })
        return results

    @api.model
    def _macro_count(self, cr, uid, pid, today, area_id):
        try:
            if area_id == "pipeline":
                cr.execute("""
                    SELECT COUNT(*) FROM crm_lead
                    WHERE active = true AND probability >= 30
                      AND stage_id NOT IN (SELECT id FROM crm_stage WHERE is_won = true)
                """)
            elif area_id == "projects":
                cr.execute("""
                    SELECT COUNT(*) FROM project_project WHERE active = true
                """)
            elif area_id == "mail":
                cr.execute("""
                    SELECT COUNT(*) FROM mail_activity
                    WHERE user_id = %s AND date_deadline <= %s
                """, [uid, today])
            elif area_id == "agenda":
                cr.execute("""
                    SELECT COUNT(*) FROM calendar_event
                    WHERE start::date = %s
                """, [today])
            elif area_id == "cassa":
                cr.execute("""
                    SELECT COALESCE(SUM(aml.balance), 0)
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN account_account aa ON aa.id = aml.account_id
                    WHERE am.state = 'posted' AND aa.account_type = 'asset_cash'
                """)
                return int(cr.fetchone()[0] or 0)
            elif area_id == "decisions":
                cr.execute("""
                    SELECT COUNT(*) FROM mail_activity
                    WHERE user_id = %s
                      AND (summary ILIKE '%%decisione%%' OR activity_type_id IN (
                          SELECT id FROM mail_activity_type WHERE name ILIKE '%%approval%%'
                      ))
                """, [uid])
            elif area_id == "investor":
                cr.execute("""
                    SELECT COUNT(*) FROM calendar_event ce
                    WHERE ce.start >= %s AND ce.start < %s
                      AND (ce.name ILIKE '%%cda%%' OR ce.name ILIKE '%%investor%%'
                           OR ce.name ILIKE '%%board%%')
                """, [today, today + timedelta(days=30)])
            elif area_id == "quality":
                cr.execute("""
                    SELECT COUNT(*) FROM mail_activity
                    WHERE date_deadline < %s
                      AND (res_model ILIKE '%%haccp%%' OR res_model ILIKE '%%quality%%')
                """, [today])
            else:
                return 0
            return cr.fetchone()[0] or 0
        except Exception:
            _logger.warning("Macro count error for %s", area_id, exc_info=True)
            return 0

    @api.model
    def _compute_today(self, cr, uid, pid, today):
        tomorrow = today + timedelta(days=1)
        week_end = today + timedelta(days=(6 - today.weekday()))

        # Critical: overdue activities
        cr.execute("""
            SELECT ma.id, ma.summary, ma.res_model, ma.res_id,
                   ma.date_deadline::text, mat.name as type_name
            FROM mail_activity ma
            LEFT JOIN mail_activity_type mat ON mat.id = ma.activity_type_id
            WHERE ma.user_id = %s AND ma.date_deadline < %s
            ORDER BY ma.date_deadline
            LIMIT 10
        """, [uid, today])
        critical = []
        for row in cr.fetchall():
            critical.append({
                "id": row[0],
                "title": row[1] or _jsonb_str(row[5]),
                "model": row[2],
                "res_id": row[3],
                "deadline": row[4],
                "type": "critical",
                "icon": "fa-exclamation-circle",
                "color": "#DC2626",
            })

        # Today activities
        cr.execute("""
            SELECT ma.id, ma.summary, ma.res_model, ma.res_id,
                   ma.date_deadline::text, mat.name as type_name
            FROM mail_activity ma
            LEFT JOIN mail_activity_type mat ON mat.id = ma.activity_type_id
            WHERE ma.user_id = %s AND ma.date_deadline = %s
            ORDER BY ma.date_deadline
            LIMIT 10
        """, [uid, today])
        oggi = []
        for row in cr.fetchall():
            oggi.append({
                "id": row[0],
                "title": row[1] or _jsonb_str(row[5]),
                "model": row[2],
                "res_id": row[3],
                "deadline": row[4],
                "type": "today",
                "icon": "fa-clock-o",
                "color": "#F59E0B",
            })

        # Upcoming (next 3 days)
        cr.execute("""
            SELECT ma.id, ma.summary, ma.res_model, ma.res_id,
                   ma.date_deadline::text, mat.name as type_name
            FROM mail_activity ma
            LEFT JOIN mail_activity_type mat ON mat.id = ma.activity_type_id
            WHERE ma.user_id = %s
              AND ma.date_deadline > %s
              AND ma.date_deadline <= %s
            ORDER BY ma.date_deadline
            LIMIT 10
        """, [uid, tomorrow, today + timedelta(days=3)])
        prossimi = []
        for row in cr.fetchall():
            prossimi.append({
                "id": row[0],
                "title": row[1] or _jsonb_str(row[5]),
                "model": row[2],
                "res_id": row[3],
                "deadline": row[4],
                "type": "upcoming",
                "icon": "fa-arrow-right",
                "color": "#3B82F6",
            })

        # Week activities
        cr.execute("""
            SELECT ma.id, ma.summary, ma.res_model, ma.res_id,
                   ma.date_deadline::text, mat.name as type_name
            FROM mail_activity ma
            LEFT JOIN mail_activity_type mat ON mat.id = ma.activity_type_id
            WHERE ma.user_id = %s
              AND ma.date_deadline >= %s
              AND ma.date_deadline <= %s
            ORDER BY ma.date_deadline
            LIMIT 20
        """, [uid, today, week_end])
        week = []
        for row in cr.fetchall():
            week.append({
                "id": row[0],
                "title": row[1] or _jsonb_str(row[5]),
                "model": row[2],
                "res_id": row[3],
                "deadline": row[4],
                "type": "week",
                "icon": "fa-calendar-check-o",
                "color": "#6366F1",
            })

        return {
            "critical": critical,
            "oggi": oggi,
            "prossimi": prossimi,
            "week": week,
        }

    @api.model
    def _compute_feed(self, cr, pid, today):
        cr.execute("""
            SELECT mm.id, mm.body, mm.date,
                   rp.name as author_name, rp.id as author_id
            FROM mail_message mm
            LEFT JOIN res_partner rp ON rp.id = mm.author_id
            WHERE mm.message_type = 'comment'
              AND mm.body IS NOT NULL
              AND mm.body != ''
              AND mm.date > NOW() - INTERVAL '30 days'
            ORDER BY mm.date DESC
            LIMIT 5
        """)
        feed = []
        for row in cr.fetchall():
            body_raw = row[1] or ""
            # Strip HTML tags for preview
            import re
            body_clean = re.sub(r'<[^>]+>', '', body_raw).strip()
            if len(body_clean) > 120:
                body_clean = body_clean[:117] + "..."

            author_name = row[3] or "Sistema"
            initials = ""
            parts = author_name.split()
            if len(parts) >= 2:
                initials = (parts[0][0] + parts[-1][0]).upper()
            elif parts:
                initials = parts[0][:2].upper()

            feed.append({
                "id": row[0],
                "body": body_clean,
                "date": row[2].isoformat() if row[2] else "",
                "author": author_name,
                "author_id": row[4],
                "initials": initials,
            })
        return feed

    @api.model
    def _fmt_euro(self, val):
        if val is None:
            return "€ 0"
        val = float(val)
        if abs(val) >= 1_000_000:
            return f"€ {val / 1_000_000:.2f}M"
        if abs(val) >= 1_000:
            return f"€ {val / 1_000:.1f}K"
        return f"€ {val:.0f}"
