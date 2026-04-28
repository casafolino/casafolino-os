# -*- coding: utf-8 -*-
"""
Workspace Lead — backend data provider for Pipeline Lead section.
All queries use direct SQL for performance (<500ms target).
"""
import logging
import re
from datetime import date, timedelta

from odoo import api, models

_logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r'<[^>]+>')

# ─── Stage mapping ──────────────────────────────────────
# Odoo stage_id → workspace stage (1-5)
# Based on actual folinofood stages:
#   1=New/Contatto, 2=Qualified, 6=Preventivo, 3=Negoziazione, 4=Won, 5=Persa
_STAGE_MAP = {
    1: 1,  # New → Qualifica
    2: 2,  # Qualified → Campionatura
    6: 3,  # Preventivo → Offerta
    3: 4,  # Negoziazione → Negoziazione
    4: 5,  # Won → Chiusura
}

_STAGE_LABELS = {
    1: "Qualifica",
    2: "Campionatura",
    3: "Offerta",
    4: "Negoziazione",
    5: "Chiusura",
}

_STAGE_COLORS = {
    1: "#9CA3AF",  # gray
    2: "#8B5CF6",  # purple
    3: "#3B82F6",  # blue
    4: "#F59E0B",  # amber
    5: "#10B981",  # green
}

# Macro areas for lead section
_LEAD_MACRO = [
    {"id": "today", "label": "Da chiamare oggi", "icon": "fa-phone", "color": "#FBEAF0"},
    {"id": "silent", "label": "Lead silenti", "icon": "fa-moon-o", "color": "#FAECE7"},
    {"id": "closing", "label": "In chiusura", "icon": "fa-trophy", "color": "#EAF3DE"},
    {"id": "new_week", "label": "Nuovi settimana", "icon": "fa-star", "color": "#FAEEDA"},
    {"id": "sampling", "label": "Da campionare", "icon": "fa-flask", "color": "#EEEDFE"},
    {"id": "offer", "label": "In offerta", "icon": "fa-file-text-o", "color": "#E6F1FB"},
    {"id": "negotiation", "label": "In negoziazione", "icon": "fa-handshake-o", "color": "#E1F5EE"},
    {"id": "markets", "label": "Mercati attivi", "icon": "fa-globe", "color": "#F1EFE8"},
]


def _jsonb_str(val):
    if not val:
        return ""
    if isinstance(val, dict):
        return val.get("it_IT") or val.get("en_US") or next(iter(val.values()), "")
    return str(val)


def _ws_stage(stage_id, probability):
    """Map stage_id to workspace stage 1-5, fallback on probability."""
    if stage_id in _STAGE_MAP:
        return _STAGE_MAP[stage_id]
    if probability is None:
        return 1
    if probability >= 80:
        return 5
    if probability >= 60:
        return 4
    if probability >= 40:
        return 3
    if probability >= 25:
        return 2
    return 1


def _pill(next_deadline, probability, today):
    """Compute pill status/label for a lead."""
    if next_deadline:
        delta = (next_deadline - today).days
        if delta < 0:
            return "red", f"{delta} gg"
        if delta == 0:
            return "amber", "oggi"
        if delta <= 3:
            return "amber", f"+{delta} gg"
    if probability is not None and probability < 30:
        return "amber", "low"
    if probability is not None and probability >= 70 and (not next_deadline or (next_deadline - today).days >= 0):
        return "green", "on track"
    return "gray", "—"


class WorkspaceLead(models.AbstractModel):
    _name = "workspace.lead"
    _description = "Workspace Lead Data Provider"

    # ─── /workspace/lead/data ───────────────────────────
    @api.model
    def get_lead_data(self):
        user = self.env.user
        profile = self.env["res.users"]._get_workspace_profile(user)
        cr = self.env.cr
        today = date.today()

        kpis = self._kpis(cr, today)
        macro = self._macro_batch(cr, user.id, user.partner_id.id, today)
        feed = self._feed(cr)

        # Hero
        hero = {
            "greet": "Pipeline lead",
            "sub": f"{kpis[0]['raw']} in pipeline · {kpis[1]['raw']} caldi · {kpis[2]['raw']} in chiusura",
            "tip": {
                "text": "Hai lead silenti da oltre 14 giorni. Considera un follow-up.",
                "primary": "Vedi",
                "secondary": "Ignora",
            },
            "progress": {"done": 0, "total": 0, "pct": 0},
        }

        return {
            "user": profile,
            "hero": hero,
            "kpis": kpis,
            "macro": macro,
            "filters": ["Tutti", "Caldi", "Silenti", "Nuovi sett.", "In chiusura"],
            "feed": feed,
        }

    # ─── /workspace/lead/list ───────────────────────────
    @api.model
    def get_lead_list(self, filter_key="tutti"):
        cr = self.env.cr
        today = date.today()

        where_extra = ""
        params = {"today": today}

        if filter_key == "caldi":
            where_extra = "AND cl.probability >= 50"
        elif filter_key == "silenti":
            where_extra = """AND cl.id NOT IN (
                SELECT DISTINCT res_id FROM mail_message
                WHERE model='crm.lead' AND date > NOW() - INTERVAL '14 days'
            )"""
        elif filter_key == "nuovi":
            where_extra = "AND cl.create_date >= date_trunc('week', CURRENT_DATE)"
        elif filter_key == "chiusura":
            where_extra = "AND cl.probability >= 70"

        cr.execute(f"""
            SELECT cl.id, cl.name, cl.expected_revenue, cl.probability,
                   cl.stage_id, cl.country_id, cl.user_id, cl.create_date,
                   rc.code AS country_code,
                   rp_owner.name AS owner_name,
                   rp_owner.id AS owner_partner_id,
                   (SELECT ma.summary FROM mail_activity ma
                    WHERE ma.res_model='crm.lead' AND ma.res_id=cl.id
                    ORDER BY ma.date_deadline LIMIT 1) AS next_action,
                   (SELECT ma.date_deadline FROM mail_activity ma
                    WHERE ma.res_model='crm.lead' AND ma.res_id=cl.id
                    ORDER BY ma.date_deadline LIMIT 1) AS next_deadline
            FROM crm_lead cl
            LEFT JOIN res_country rc ON rc.id = cl.country_id
            LEFT JOIN res_users ru ON ru.id = cl.user_id
            LEFT JOIN res_partner rp_owner ON rp_owner.id = ru.partner_id
            WHERE cl.active = true
              AND cl.probability >= 30
              AND cl.probability < 100
              {where_extra}
            ORDER BY (cl.expected_revenue * cl.probability / 100.0) DESC NULLS LAST
            LIMIT 50
        """, params)

        leads = []
        for row in cr.fetchall():
            stage_num = _ws_stage(row[4], row[3])
            pill_status, pill_label = _pill(row[12], row[3], today)
            days = (today - row[7].date()).days if row[7] else 0

            owner_name = _jsonb_str(row[9]) or "—"
            owner_parts = owner_name.split()
            owner_initials = ""
            if len(owner_parts) >= 2:
                owner_initials = (owner_parts[0][0] + owner_parts[-1][0]).upper()
            elif owner_parts:
                owner_initials = owner_parts[0][:2].upper()

            leads.append({
                "id": row[0],
                "name": row[1] or "—",
                "value": float(row[2] or 0),
                "probability": int(row[3] or 0),
                "stage_num": stage_num,
                "stage_label": _STAGE_LABELS.get(stage_num, "?"),
                "stage_color": _STAGE_COLORS.get(stage_num, "#9CA3AF"),
                "country_code": (row[8] or "??").upper(),
                "owner": {
                    "id": row[6],
                    "name": owner_name,
                    "initials": owner_initials,
                },
                "days_in_pipeline": days,
                "next_action": row[11] or "—",
                "next_deadline": str(row[12]) if row[12] else None,
                "pill_status": pill_status,
                "pill_label": pill_label,
            })

        return {"leads": leads}

    # ─── /workspace/lead/pipeline ───────────────────────
    @api.model
    def get_lead_pipeline(self):
        cr = self.env.cr
        today = date.today()

        cr.execute("""
            SELECT cl.id, cl.name, cl.expected_revenue, cl.probability,
                   cl.stage_id, cl.country_id, cl.user_id, cl.create_date,
                   rc.code AS country_code,
                   rp_owner.name AS owner_name
            FROM crm_lead cl
            LEFT JOIN res_country rc ON rc.id = cl.country_id
            LEFT JOIN res_users ru ON ru.id = cl.user_id
            LEFT JOIN res_partner rp_owner ON rp_owner.id = ru.partner_id
            WHERE cl.active = true
              AND cl.probability >= 30
              AND cl.probability < 100
            ORDER BY cl.expected_revenue DESC NULLS LAST
        """)

        stages = {i: {"num": i, "label": _STAGE_LABELS[i], "color": _STAGE_COLORS[i], "leads": [], "total": 0}
                  for i in range(1, 6)}

        for row in cr.fetchall():
            sn = _ws_stage(row[4], row[3])
            pill_status, pill_label = _pill(None, row[3], today)
            days = (today - row[7].date()).days if row[7] else 0
            owner_name = _jsonb_str(row[9]) or "—"
            owner_parts = owner_name.split()
            initials = (owner_parts[0][0] + owner_parts[-1][0]).upper() if len(owner_parts) >= 2 else (owner_parts[0][:2].upper() if owner_parts else "??")

            stages[sn]["leads"].append({
                "id": row[0],
                "name": row[1] or "—",
                "value": float(row[2] or 0),
                "probability": int(row[3] or 0),
                "country_code": (row[8] or "??").upper(),
                "owner_initials": initials,
                "days": days,
                "pill_status": pill_status,
                "pill_label": pill_label,
            })
            stages[sn]["total"] += float(row[2] or 0)

        return {"stages": [stages[i] for i in range(1, 6)]}

    # ─── /workspace/lead/markets ────────────────────────
    @api.model
    def get_lead_markets(self):
        cr = self.env.cr
        cr.execute("""
            SELECT rc.code, rc.name AS country_name,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(cl.expected_revenue), 0) AS val,
                   ARRAY_AGG(cl.name ORDER BY cl.expected_revenue DESC NULLS LAST) AS names
            FROM crm_lead cl
            LEFT JOIN res_country rc ON rc.id = cl.country_id
            WHERE cl.active = true AND cl.probability >= 30 AND cl.probability < 100
            GROUP BY rc.code, rc.name
            ORDER BY val DESC
            LIMIT 30
        """)
        markets = []
        for row in cr.fetchall():
            country_name = _jsonb_str(row[1]) or "Sconosciuto"
            names_list = [n for n in (row[4] or []) if n][:3]
            markets.append({
                "country": country_name,
                "flag": (row[0] or "??").upper(),
                "cnt": row[2] or 0,
                "value": float(row[3] or 0),
                "names": ", ".join(names_list),
            })
        return {"markets": markets}

    # ─── /workspace/lead/<id> ───────────────────────────
    @api.model
    def get_lead_detail(self, lead_id):
        cr = self.env.cr
        today = date.today()

        cr.execute("""
            SELECT cl.id, cl.name, cl.expected_revenue, cl.probability,
                   cl.stage_id, cl.country_id, cl.user_id, cl.create_date,
                   cl.description, cl.partner_id,
                   rc.code AS country_code, rc.name AS country_name,
                   rp_owner.name AS owner_name,
                   (SELECT ma.summary FROM mail_activity ma
                    WHERE ma.res_model='crm.lead' AND ma.res_id=cl.id
                    ORDER BY ma.date_deadline LIMIT 1) AS next_action,
                   (SELECT ma.date_deadline FROM mail_activity ma
                    WHERE ma.res_model='crm.lead' AND ma.res_id=cl.id
                    ORDER BY ma.date_deadline LIMIT 1) AS next_deadline
            FROM crm_lead cl
            LEFT JOIN res_country rc ON rc.id = cl.country_id
            LEFT JOIN res_users ru ON ru.id = cl.user_id
            LEFT JOIN res_partner rp_owner ON rp_owner.id = ru.partner_id
            WHERE cl.id = %s
        """, [lead_id])
        row = cr.fetchone()
        if not row:
            return {"error": "Lead not found"}

        stage_num = _ws_stage(row[4], row[3])
        pill_status, pill_label = _pill(row[14], row[3], today)
        days = (today - row[7].date()).days if row[7] else 0

        # Chain counts
        partner_id = row[9]
        cr.execute("""
            SELECT
                (SELECT COUNT(*) FROM mail_message
                 WHERE model='crm.lead' AND res_id=%(lid)s) AS mail_cnt,
                (SELECT COUNT(*) FROM project_project
                 WHERE partner_id=%(pid)s AND active=true) AS proj_cnt,
                (SELECT COUNT(*) FROM project_task
                 WHERE project_id IN (SELECT id FROM project_project WHERE partner_id=%(pid)s AND active=true)
                ) AS task_cnt,
                (SELECT COUNT(*) FROM ir_attachment
                 WHERE res_model='crm.lead' AND res_id=%(lid)s) AS doc_cnt
        """, {"lid": lead_id, "pid": partner_id or 0})
        chain_row = cr.fetchone()

        chain = [
            {"label": f"Mail ({chain_row[0]})", "icon": "fa-envelope", "count": chain_row[0]},
            {"label": f"Progetti ({chain_row[1]})", "icon": "fa-folder", "count": chain_row[1]},
            {"label": f"Task ({chain_row[2]})", "icon": "fa-tasks", "count": chain_row[2]},
            {"label": f"Documenti ({chain_row[3]})", "icon": "fa-paperclip", "count": chain_row[3]},
        ]

        return {
            "lead": {
                "id": row[0],
                "name": row[1] or "—",
                "value": float(row[2] or 0),
                "probability": int(row[3] or 0),
                "stage_num": stage_num,
                "stage_label": _STAGE_LABELS.get(stage_num, "?"),
                "stage_color": _STAGE_COLORS.get(stage_num, "#9CA3AF"),
                "country_code": (row[10] or "??").upper(),
                "country_name": _jsonb_str(row[11]) or "—",
                "owner_name": _jsonb_str(row[12]) or "—",
                "days_in_pipeline": days,
                "next_action": row[13] or "—",
                "next_deadline": str(row[14]) if row[14] else None,
                "pill_status": pill_status,
                "pill_label": pill_label,
                "description": row[8] or "",
            },
            "chain": chain,
        }

    # ─── KPIs ───────────────────────────────────────────
    @api.model
    def _kpis(self, cr, today):
        cr.execute("""
            SELECT
                (SELECT COALESCE(SUM(expected_revenue),0)
                 FROM crm_lead WHERE active=true AND probability>=30 AND probability<100) AS pipeline_val,
                (SELECT COUNT(*)
                 FROM crm_lead WHERE active=true AND probability>=50 AND probability<100) AS hot_cnt,
                (SELECT COALESCE(SUM(expected_revenue),0)
                 FROM crm_lead WHERE active=true AND probability>=70 AND probability<100) AS closing_val,
                (SELECT ROUND(AVG(CURRENT_DATE - create_date::date))
                 FROM crm_lead WHERE active=true AND probability>=30 AND probability<100) AS avg_days
        """)
        row = cr.fetchone()
        return [
            {"id": "pipeline_val", "label": "Pipeline totale", "value": self._fmt(row[0]),
             "raw": int(row[0] or 0), "icon": "fa-rocket"},
            {"id": "hot_cnt", "label": "Lead caldi", "value": str(row[1] or 0),
             "raw": int(row[1] or 0), "icon": "fa-fire"},
            {"id": "closing_val", "label": "In chiusura", "value": self._fmt(row[2]),
             "raw": int(row[2] or 0), "icon": "fa-trophy"},
            {"id": "avg_days", "label": "Tempo medio", "value": f"{int(row[3] or 0)} gg",
             "raw": int(row[3] or 0), "icon": "fa-clock-o"},
        ]

    # ─── Macro batch ────────────────────────────────────
    @api.model
    def _macro_batch(self, cr, uid, pid, today):
        week_start = today - timedelta(days=today.weekday())
        cr.execute("""
            WITH
              today_act AS (
                SELECT COUNT(*) c FROM mail_activity
                WHERE res_model='crm.lead' AND user_id=%(uid)s AND date_deadline=%(today)s
              ),
              silent AS (
                SELECT COUNT(*) c FROM crm_lead cl
                WHERE cl.active=true AND cl.probability>=30 AND cl.probability<100
                  AND cl.id NOT IN (
                    SELECT DISTINCT res_id FROM mail_message
                    WHERE model='crm.lead' AND date > NOW() - INTERVAL '14 days'
                  )
              ),
              closing AS (
                SELECT COUNT(*) c FROM crm_lead
                WHERE active=true AND probability>=70 AND probability<100
              ),
              new_week AS (
                SELECT COUNT(*) c FROM crm_lead
                WHERE active=true AND probability>=30 AND create_date >= %(week_start)s
              ),
              sampling AS (
                SELECT COUNT(*) c FROM crm_lead
                WHERE active=true AND probability>=30 AND probability<100 AND stage_id=2
              ),
              offer AS (
                SELECT COUNT(*) c FROM crm_lead
                WHERE active=true AND probability>=30 AND probability<100 AND stage_id=6
              ),
              negotiation AS (
                SELECT COUNT(*) c FROM crm_lead
                WHERE active=true AND probability>=30 AND probability<100 AND stage_id=3
              ),
              markets AS (
                SELECT COUNT(DISTINCT country_id) c FROM crm_lead
                WHERE active=true AND probability>=30 AND probability<100 AND country_id IS NOT NULL
              )
            SELECT today_act.c, silent.c, closing.c, new_week.c,
                   sampling.c, offer.c, negotiation.c, markets.c
            FROM today_act, silent, closing, new_week,
                 sampling, offer, negotiation, markets
        """, {"uid": uid, "today": today, "week_start": week_start})
        row = cr.fetchone()
        counts = [row[i] or 0 for i in range(8)]

        results = []
        for i, area in enumerate(_LEAD_MACRO):
            results.append({
                "id": area["id"],
                "label": area["label"],
                "icon": area["icon"],
                "color": area["color"],
                "count": counts[i],
                "visible": True,
            })
        return results

    # ─── Feed ───────────────────────────────────────────
    @api.model
    def _feed(self, cr):
        cr.execute("""
            SELECT mm.id, mm.body, mm.date,
                   rp.name AS author_name, rp.id AS author_id
            FROM mail_message mm
            LEFT JOIN res_partner rp ON rp.id = mm.author_id
            WHERE mm.model = 'crm.lead'
              AND mm.message_type = 'comment'
              AND mm.body IS NOT NULL AND mm.body != ''
              AND mm.date > NOW() - INTERVAL '90 days'
            ORDER BY mm.date DESC
            LIMIT 10
        """)
        feed = []
        for row in cr.fetchall():
            body = _HTML_TAG_RE.sub('', row[1] or '').strip()
            if len(body) > 120:
                body = body[:117] + "..."
            author = _jsonb_str(row[3]) or "Sistema"
            parts = str(author).split()
            initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else (parts[0][:2].upper() if parts else "??")
            feed.append({
                "id": row[0],
                "body": body,
                "date": row[2].isoformat() if row[2] else "",
                "author": str(author),
                "initials": initials,
            })
        return feed

    @api.model
    def _fmt(self, val):
        val = float(val or 0)
        if abs(val) >= 1_000_000:
            return f"€ {val/1_000_000:.2f}M"
        if abs(val) >= 1_000:
            return f"€ {val/1_000:.1f}K"
        return f"€ {val:.0f}"
