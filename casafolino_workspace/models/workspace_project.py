# -*- coding: utf-8 -*-
"""Workspace Project — backend data provider for Progetti section."""
import logging
import re
from datetime import date, timedelta

from odoo import api, models

_logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r'<[^>]+>')

_CATEGORY_MAP = {
    "acquisizione": {"icon": "fa-handshake-o", "color": "#FAECE7"},
    "infrastruttura": {"icon": "fa-building", "color": "#E1F5EE"},
    "finanza": {"icon": "fa-money", "color": "#FAEEDA"},
    "fiera": {"icon": "fa-flag", "color": "#FBEAF0"},
    "prodotto": {"icon": "fa-cube", "color": "#EAF3DE"},
    "qualità": {"icon": "fa-shield", "color": "#F1EFE8"},
    "export": {"icon": "fa-bullseye", "color": "#E6F1FB"},
}

_PROJ_MACRO = [
    {"id": "deadline", "label": "In scadenza", "icon": "fa-clock-o", "color": "#FAECE7"},
    {"id": "critical", "label": "Critici", "icon": "fa-exclamation-triangle", "color": "#FBEAF0"},
    {"id": "blocked", "label": "Bloccati", "icon": "fa-ban", "color": "#F1EFE8"},
    {"id": "review", "label": "In review", "icon": "fa-eye", "color": "#E6F1FB"},
    {"id": "acq", "label": "Acquisizioni", "icon": "fa-handshake-o", "color": "#FAEEDA"},
    {"id": "infra", "label": "Infrastruttura", "icon": "fa-building", "color": "#E1F5EE"},
    {"id": "product", "label": "Prodotto", "icon": "fa-cube", "color": "#EAF3DE"},
    {"id": "expo", "label": "Fiere & Export", "icon": "fa-globe", "color": "#EEEDFE"},
]


def _jsonb_str(val):
    if not val:
        return ""
    if isinstance(val, dict):
        return val.get("it_IT") or val.get("en_US") or next(iter(val.values()), "")
    return str(val)


class WorkspaceProject(models.AbstractModel):
    _name = "workspace.project"
    _description = "Workspace Project Data Provider"

    # ─── /workspace/proj/data ──────────────────────────
    @api.model
    def get_proj_data(self):
        user = self.env.user
        profile = self.env["res.users"]._get_workspace_profile(user)
        cr = self.env.cr
        today = date.today()

        kpis = self._kpis(cr, today)
        macro = self._macro_batch(cr, user.id, today)
        feed = self._feed(cr)

        hero = {
            "greet": "Progetti attivi",
            "sub": f"{kpis[0]['raw']} progetti · {kpis[1]['raw']} task aperte · {kpis[2]['raw']}% avanzamento medio",
            "tip": {
                "text": "Hai progetti in scadenza nelle prossime 2 settimane. Verifica milestone.",
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
            "filters": ["Tutti", "Critici", "In scadenza", "Solo i miei", "Bloccati"],
            "feed": feed,
        }

    # ─── /workspace/proj/list ──────────────────────────
    @api.model
    def get_proj_list(self, filter_key="tutti"):
        cr = self.env.cr
        today = date.today()
        uid = self.env.user.id

        where_extra = ""
        params = {"today": today, "uid": uid, "d14": today + timedelta(days=14)}

        if filter_key == "critici":
            where_extra = """AND (
                EXISTS(SELECT 1 FROM project_task pt2 WHERE pt2.project_id=pp.id AND pt2.date_deadline < %(today)s)
                OR (pp.date IS NOT NULL AND pp.date < %(today)s + 3)
            )"""
        elif filter_key == "scadenza":
            where_extra = "AND pp.date IS NOT NULL AND pp.date <= %(d14)s"
        elif filter_key == "miei":
            where_extra = "AND pp.user_id = %(uid)s"
        elif filter_key == "bloccati":
            where_extra = """AND EXISTS(
                SELECT 1 FROM project_task pt2
                WHERE pt2.project_id=pp.id AND pt2.priority='1'
                  AND pt2.date_deadline < %(today)s - 5
            )"""

        cr.execute(f"""
            SELECT pp.id, pp.name, pp.date, pp.user_id, pp.date_start,
                   rp_owner.name AS owner_name,
                   (SELECT COUNT(*) FROM project_task pt WHERE pt.project_id=pp.id) AS task_total,
                   (SELECT COUNT(*) FROM project_task pt
                    JOIN project_task_type ptt ON ptt.id=pt.stage_id
                    WHERE pt.project_id=pp.id AND ptt.fold=true) AS task_done,
                   (SELECT COUNT(*) FROM project_task pt
                    WHERE pt.project_id=pp.id AND pt.date_deadline < %(today)s
                      AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true)
                   ) AS overdue_cnt,
                   (SELECT pt.name FROM project_task pt
                    WHERE pt.project_id=pp.id AND pt.date_deadline >= %(today)s
                      AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true)
                    ORDER BY pt.date_deadline LIMIT 1) AS next_milestone,
                   (SELECT pt.date_deadline FROM project_task pt
                    WHERE pt.project_id=pp.id AND pt.date_deadline >= %(today)s
                      AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true)
                    ORDER BY pt.date_deadline LIMIT 1) AS next_date,
                   (SELECT string_agg(ptag.name::text, ',') FROM project_tags ptag
                    JOIN project_project_project_tags_rel rel ON rel.project_tags_id=ptag.id
                    WHERE rel.project_project_id=pp.id LIMIT 3) AS tag_names
            FROM project_project pp
            LEFT JOIN res_users ru ON ru.id = pp.user_id
            LEFT JOIN res_partner rp_owner ON rp_owner.id = ru.partner_id
            WHERE pp.active = true
              {where_extra}
            ORDER BY pp.date ASC NULLS LAST
            LIMIT 30
        """, params)

        projects = []
        for row in cr.fetchall():
            task_total = row[6] or 0
            task_done = row[7] or 0
            progress = int(task_done / task_total * 100) if task_total > 0 else 0
            overdue = row[8] or 0
            target_date = row[2]
            days_to_target = (target_date - today).days if target_date else 999

            # Status
            if overdue > 0 or (target_date and days_to_target < 3 and progress < 80):
                status = "red"
            elif overdue > 0 or (target_date and days_to_target < 14):
                status = "amber"
            else:
                status = "green"

            # Pill
            if target_date:
                if days_to_target < 0:
                    pill_status, pill_label = "red", f"{days_to_target} gg"
                elif days_to_target == 0:
                    pill_status, pill_label = "amber", "oggi"
                elif days_to_target <= 7:
                    pill_status, pill_label = "amber", f"+{days_to_target} gg"
                else:
                    pill_status, pill_label = "green", f"+{days_to_target} gg"
            else:
                pill_status, pill_label = "gray", "—"

            # Category from tags
            tag_raw = row[11] or ""
            category, cat_icon, cat_color = self._parse_category(tag_raw)

            owner_name = _jsonb_str(row[5]) or "—"
            parts = str(owner_name).split()
            initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else (parts[0][:2].upper() if parts else "??")

            projects.append({
                "id": row[0],
                "name": row[1] or "—",
                "category": category,
                "category_icon": cat_icon,
                "category_color": cat_color,
                "progress": progress,
                "status": status,
                "owner": {"id": row[3], "name": owner_name, "initials": initials},
                "next_milestone": row[9] or "—",
                "next_date": str(row[10]) if row[10] else None,
                "pill_status": pill_status,
                "pill_label": pill_label,
                "task_count": task_total,
                "task_done": task_done,
                "days_to_target": days_to_target,
                "overdue": overdue,
            })

        return {"projects": projects}

    # ─── /workspace/proj/kanban ─────────────────────────
    @api.model
    def get_proj_kanban(self):
        cr = self.env.cr
        today = date.today()

        cr.execute("""
            SELECT pp.id, pp.name, pp.date, pp.user_id,
                   (SELECT COUNT(*) FROM project_task pt WHERE pt.project_id=pp.id) AS task_total,
                   (SELECT COUNT(*) FROM project_task pt
                    JOIN project_task_type ptt ON ptt.id=pt.stage_id
                    WHERE pt.project_id=pp.id AND ptt.fold=true) AS task_done,
                   (SELECT COUNT(*) FROM project_task pt
                    WHERE pt.project_id=pp.id AND pt.date_deadline < %(today)s
                      AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true)
                   ) AS overdue_cnt,
                   (SELECT string_agg(ptag.name::text, ',') FROM project_tags ptag
                    JOIN project_project_project_tags_rel rel ON rel.project_tags_id=ptag.id
                    WHERE rel.project_project_id=pp.id LIMIT 3) AS tag_names
            FROM project_project pp
            WHERE pp.active = true
            ORDER BY pp.date ASC NULLS LAST
        """, {"today": today})

        cols = {
            "backlog": {"label": "Backlog", "projects": []},
            "doing": {"label": "In corso", "projects": []},
            "review": {"label": "Review", "projects": []},
            "done": {"label": "Fatto", "projects": []},
        }

        for row in cr.fetchall():
            total = row[4] or 0
            done = row[5] or 0
            progress = int(done / total * 100) if total > 0 else 0
            category, cat_icon, cat_color = self._parse_category(row[7] or "")

            item = {
                "id": row[0],
                "name": row[1] or "—",
                "progress": progress,
                "category": category,
                "category_icon": cat_icon,
                "category_color": cat_color,
                "task_count": total,
                "task_done": done,
            }

            if progress >= 100:
                cols["done"]["projects"].append(item)
            elif progress >= 70:
                cols["review"]["projects"].append(item)
            elif progress > 0:
                cols["doing"]["projects"].append(item)
            else:
                cols["backlog"]["projects"].append(item)

        return {"columns": [cols["backlog"], cols["doing"], cols["review"], cols["done"]]}

    # ─── /workspace/proj/timeline ───────────────────────
    @api.model
    def get_proj_timeline(self):
        cr = self.env.cr
        today = date.today()

        cr.execute("""
            SELECT pp.id, pp.name, pp.date, pp.user_id,
                   (SELECT COUNT(*) FROM project_task pt WHERE pt.project_id=pp.id) AS task_total,
                   (SELECT COUNT(*) FROM project_task pt
                    JOIN project_task_type ptt ON ptt.id=pt.stage_id
                    WHERE pt.project_id=pp.id AND ptt.fold=true) AS task_done,
                   (SELECT string_agg(ptag.name::text, ',') FROM project_tags ptag
                    JOIN project_project_project_tags_rel rel ON rel.project_tags_id=ptag.id
                    WHERE rel.project_project_id=pp.id LIMIT 3) AS tag_names
            FROM project_project pp
            WHERE pp.active = true AND pp.date IS NOT NULL
            ORDER BY pp.date ASC
        """)

        groups = {"sett": [], "mese": [], "trim": [], "oltre": []}

        for row in cr.fetchall():
            total = row[4] or 0
            done = row[5] or 0
            progress = int(done / total * 100) if total > 0 else 0
            target = row[2]
            days = (target - today).days if target else 999
            category, cat_icon, cat_color = self._parse_category(row[6] or "")

            item = {
                "id": row[0],
                "name": row[1] or "—",
                "date": str(target) if target else "",
                "days_to_target": days,
                "progress": progress,
                "category": category,
                "category_icon": cat_icon,
                "category_color": cat_color,
            }

            if days <= 7:
                groups["sett"].append(item)
            elif days <= 30:
                groups["mese"].append(item)
            elif days <= 90:
                groups["trim"].append(item)
            else:
                groups["oltre"].append(item)

        return {"timeline": [
            {"key": "sett", "label": "Questa settimana", "projects": groups["sett"]},
            {"key": "mese", "label": "Questo mese", "projects": groups["mese"]},
            {"key": "trim", "label": "Trimestre", "projects": groups["trim"]},
            {"key": "oltre", "label": "Oltre", "projects": groups["oltre"]},
        ]}

    # ─── /workspace/proj/detail ─────────────────────────
    @api.model
    def get_proj_detail(self, proj_id):
        cr = self.env.cr
        today = date.today()

        cr.execute("""
            SELECT pp.id, pp.name, pp.date, pp.user_id, pp.description, pp.partner_id,
                   rp_owner.name AS owner_name,
                   (SELECT COUNT(*) FROM project_task pt WHERE pt.project_id=pp.id) AS task_total,
                   (SELECT COUNT(*) FROM project_task pt
                    JOIN project_task_type ptt ON ptt.id=pt.stage_id
                    WHERE pt.project_id=pp.id AND ptt.fold=true) AS task_done,
                   (SELECT string_agg(ptag.name::text, ',') FROM project_tags ptag
                    JOIN project_project_project_tags_rel rel ON rel.project_tags_id=ptag.id
                    WHERE rel.project_project_id=pp.id) AS tag_names,
                   (SELECT pt.name FROM project_task pt
                    WHERE pt.project_id=pp.id AND pt.date_deadline >= %(today)s
                      AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true)
                    ORDER BY pt.date_deadline LIMIT 1) AS next_milestone,
                   (SELECT pt.date_deadline FROM project_task pt
                    WHERE pt.project_id=pp.id AND pt.date_deadline >= %(today)s
                      AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true)
                    ORDER BY pt.date_deadline LIMIT 1) AS next_date
            FROM project_project pp
            LEFT JOIN res_users ru ON ru.id = pp.user_id
            LEFT JOIN res_partner rp_owner ON rp_owner.id = ru.partner_id
            WHERE pp.id = %(pid)s
        """, {"pid": proj_id, "today": today})
        row = cr.fetchone()
        if not row:
            return {"error": "Project not found"}

        total = row[7] or 0
        done = row[8] or 0
        progress = int(done / total * 100) if total > 0 else 0
        category, cat_icon, cat_color = self._parse_category(row[9] or "")
        target = row[2]
        days_to = (target - today).days if target else 999

        # Chain
        partner_id = row[5] or 0
        cr.execute("""
            SELECT
                (SELECT COUNT(*) FROM mail_message WHERE model='project.project' AND res_id=%(pid)s) AS mail_cnt,
                (SELECT COUNT(*) FROM project_task WHERE project_id=%(pid)s) AS task_cnt,
                (SELECT COUNT(*) FROM ir_attachment WHERE res_model='project.project' AND res_id=%(pid)s) AS doc_cnt,
                (SELECT COUNT(*) FROM crm_lead WHERE partner_id=%(partner)s AND active=true) AS lead_cnt
        """, {"pid": proj_id, "partner": partner_id})
        ch = cr.fetchone()

        chain = [
            {"label": f"Task ({ch[1]})", "icon": "fa-tasks", "count": ch[1]},
            {"label": f"Mail ({ch[0]})", "icon": "fa-envelope", "count": ch[0]},
            {"label": f"Documenti ({ch[2]})", "icon": "fa-paperclip", "count": ch[2]},
            {"label": f"Lead ({ch[3]})", "icon": "fa-bullseye", "count": ch[3]},
        ]

        return {
            "project": {
                "id": row[0],
                "name": row[1] or "—",
                "date": str(target) if target else None,
                "days_to_target": days_to,
                "progress": progress,
                "category": category,
                "category_icon": cat_icon,
                "category_color": cat_color,
                "owner_name": _jsonb_str(row[6]) or "—",
                "description": row[4] or "",
                "task_count": total,
                "task_done": done,
                "next_milestone": row[10] or "—",
                "next_date": str(row[11]) if row[11] else None,
            },
            "chain": chain,
        }

    # ─── KPIs ──────────────────────────────────────────
    @api.model
    def _kpis(self, cr, today):
        cr.execute("""
            SELECT
                (SELECT COUNT(*) FROM project_project WHERE active=true) AS proj_cnt,
                (SELECT COUNT(*) FROM project_task pt
                 JOIN project_project pp ON pp.id=pt.project_id
                 WHERE pp.active=true
                   AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true)
                ) AS task_open,
                (SELECT ROUND(AVG(sub.pct))
                 FROM (
                    SELECT CASE WHEN COUNT(*)=0 THEN 0
                           ELSE COUNT(*) FILTER(WHERE ptt.fold=true)::float / COUNT(*) * 100
                           END AS pct
                    FROM project_task pt
                    JOIN project_task_type ptt ON ptt.id=pt.stage_id
                    JOIN project_project pp ON pp.id=pt.project_id
                    WHERE pp.active=true
                    GROUP BY pt.project_id
                 ) sub
                ) AS avg_progress,
                (SELECT COUNT(DISTINCT pp.id)
                 FROM project_project pp
                 WHERE pp.active=true AND (
                    EXISTS(SELECT 1 FROM project_task pt
                           WHERE pt.project_id=pp.id AND pt.date_deadline < %(today)s
                             AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true))
                    OR (pp.date IS NOT NULL AND pp.date < %(today)s + 3)
                 )
                ) AS critical_cnt
        """, {"today": today})
        row = cr.fetchone()
        return [
            {"id": "proj_cnt", "label": "Progetti attivi", "value": str(row[0] or 0),
             "raw": int(row[0] or 0), "icon": "fa-folder-open"},
            {"id": "task_open", "label": "Task aperte", "value": str(row[1] or 0),
             "raw": int(row[1] or 0), "icon": "fa-tasks"},
            {"id": "avg_pct", "label": "Avanzamento medio", "value": f"{int(row[2] or 0)}%",
             "raw": int(row[2] or 0), "icon": "fa-bar-chart"},
            {"id": "critical", "label": "Critici", "value": str(row[3] or 0),
             "raw": int(row[3] or 0), "icon": "fa-exclamation-triangle"},
        ]

    # ─── Macro batch ───────────────────────────────────
    @api.model
    def _macro_batch(self, cr, uid, today):
        cr.execute("""
            WITH
              deadline AS (
                SELECT COUNT(*) c FROM project_project
                WHERE active=true AND date IS NOT NULL AND date <= %(d14)s
              ),
              critical AS (
                SELECT COUNT(DISTINCT pp.id) c FROM project_project pp
                WHERE pp.active=true AND (
                  EXISTS(SELECT 1 FROM project_task pt WHERE pt.project_id=pp.id
                         AND pt.date_deadline < %(today)s
                         AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true))
                  OR (pp.date IS NOT NULL AND pp.date < %(today)s + 3)
                )
              ),
              blocked AS (
                SELECT COUNT(DISTINCT pp.id) c FROM project_project pp
                WHERE pp.active=true AND EXISTS(
                  SELECT 1 FROM project_task pt WHERE pt.project_id=pp.id
                    AND pt.priority='1' AND pt.date_deadline < %(today)s - 5
                    AND pt.stage_id NOT IN (SELECT id FROM project_task_type WHERE fold=true)
                )
              ),
              review AS (
                SELECT COUNT(DISTINCT pp.id) c FROM project_project pp
                WHERE pp.active=true AND (
                  SELECT COUNT(*) FILTER(WHERE ptt.fold=true)::float / NULLIF(COUNT(*),0) * 100
                  FROM project_task pt2 JOIN project_task_type ptt ON ptt.id=pt2.stage_id
                  WHERE pt2.project_id=pp.id
                ) >= 70
              ),
              acq AS (
                SELECT COUNT(*) c FROM project_project pp
                JOIN project_project_project_tags_rel rel ON rel.project_project_id=pp.id
                JOIN project_tags ptag ON ptag.id=rel.project_tags_id
                WHERE pp.active=true AND ptag.name::text ILIKE '%%Acquisizione%%'
              ),
              infra AS (
                SELECT COUNT(*) c FROM project_project pp
                JOIN project_project_project_tags_rel rel ON rel.project_project_id=pp.id
                JOIN project_tags ptag ON ptag.id=rel.project_tags_id
                WHERE pp.active=true AND (ptag.name::text ILIKE '%%Infrastruttura%%' OR ptag.name::text ILIKE '%%Finanza%%')
              ),
              product AS (
                SELECT COUNT(*) c FROM project_project pp
                JOIN project_project_project_tags_rel rel ON rel.project_project_id=pp.id
                JOIN project_tags ptag ON ptag.id=rel.project_tags_id
                WHERE pp.active=true AND ptag.name::text ILIKE '%%Prodotto%%'
              ),
              expo AS (
                SELECT COUNT(*) c FROM project_project pp
                JOIN project_project_project_tags_rel rel ON rel.project_project_id=pp.id
                JOIN project_tags ptag ON ptag.id=rel.project_tags_id
                WHERE pp.active=true AND (ptag.name::text ILIKE '%%Fiera%%' OR ptag.name::text ILIKE '%%Export%%')
              )
            SELECT deadline.c, critical.c, blocked.c, review.c,
                   acq.c, infra.c, product.c, expo.c
            FROM deadline, critical, blocked, review, acq, infra, product, expo
        """, {"today": today, "d14": today + timedelta(days=14)})
        row = cr.fetchone()
        counts = [row[i] or 0 for i in range(8)]

        results = []
        for i, area in enumerate(_PROJ_MACRO):
            results.append({
                "id": area["id"],
                "label": area["label"],
                "icon": area["icon"],
                "color": area["color"],
                "count": counts[i],
                "visible": True,
            })
        return results

    # ─── Feed ──────────────────────────────────────────
    @api.model
    def _feed(self, cr):
        cr.execute("""
            SELECT mm.id, mm.body, mm.date,
                   rp.name AS author_name, rp.id AS author_id
            FROM mail_message mm
            LEFT JOIN res_partner rp ON rp.id = mm.author_id
            WHERE mm.model IN ('project.project', 'project.task')
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
    def _parse_category(self, tag_str):
        """Extract first matching category from comma-separated tag names."""
        for part in str(tag_str).split(","):
            key = part.strip().strip('"{}').lower()
            # Handle jsonb string like {"en_US": "Acquisizione", ...}
            for cat_key, cat_data in _CATEGORY_MAP.items():
                if cat_key in key:
                    return cat_key.capitalize(), cat_data["icon"], cat_data["color"]
        return "Progetto", "fa-folder", "#F1EFE8"
