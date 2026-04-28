# -*- coding: utf-8 -*-
import logging
import re
from collections import defaultdict
from datetime import date, timedelta

from odoo import api, models, fields

_logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r'<[^>]+>')

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

_MACRO_AREAS = [
    {"id": "pipeline", "label": "Pipeline lead", "icon": "fa-bullseye",
     "color": "#EEEDFE", "roles": ["antonio", "josefina"]},
    {"id": "projects", "label": "Progetti attivi", "icon": "fa-folder-open",
     "color": "#E1F5EE", "roles": ["antonio", "martina"]},
    {"id": "mail", "label": "Mail in sospeso", "icon": "fa-envelope",
     "color": "#FAECE7", "roles": ["antonio", "josefina", "martina", "maria"]},
    {"id": "agenda", "label": "Agenda oggi", "icon": "fa-calendar",
     "color": "#FBEAF0", "roles": ["antonio", "josefina", "martina", "maria"]},
    {"id": "cassa", "label": "Cassa & banca", "icon": "fa-university",
     "color": "#FAEEDA", "roles": ["antonio", "martina"]},
    {"id": "decisions", "label": "Decisioni in attesa", "icon": "fa-gavel",
     "color": "#E6F1FB", "roles": ["antonio"]},
    {"id": "investor", "label": "Investor & CdA", "icon": "fa-briefcase",
     "color": "#EAF3DE", "roles": ["antonio"]},
    {"id": "quality", "label": "Alert qualità", "icon": "fa-shield",
     "color": "#F1EFE8", "roles": ["antonio", "maria"]},
]

_BANK_JOURNAL_IDS = (6, 13, 22)


def _jsonb_str(val):
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

        hour = fields.Datetime.context_timestamp(self, fields.Datetime.now()).hour
        if hour < 13:
            saluto = "Buongiorno"
        elif hour < 18:
            saluto = "Buon pomeriggio"
        else:
            saluto = "Buonasera"

        greet = f"{saluto} {profile['name']}"
        wd = _WEEKDAYS_IT.get(today.weekday(), "")
        mn = _MONTHS_IT.get(today.month, "")
        week_num = today.isocalendar()[1]

        kpis = self._compute_kpis(cr, uid, today)
        progress = self._compute_progress(cr, uid, pid, today)

        sub = (
            f"{wd} {today.day} {mn} · settimana {week_num} · "
            f"{kpis[3]['raw']} critici, {progress['total']} oggi"
        )

        macro = self._compute_macro_batch(cr, uid, pid, today, role)
        today_data = self._compute_today(cr, uid, today)
        feed = self._compute_feed(cr, pid)
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

    # ─── KPIs ───────────────────────────────────────────
    @api.model
    def _compute_kpis(self, cr, uid, today):
        month_start = today.replace(day=1)
        d90 = today - timedelta(days=90)
        cr.execute("""
            SELECT
                (SELECT COALESCE(SUM(expected_revenue), 0)
                 FROM crm_lead
                 WHERE active = true
                   AND probability >= 30 AND probability < 100
                   AND type = 'opportunity') AS pipeline,

                (SELECT COALESCE(SUM(amount_total), 0)
                 FROM account_move
                 WHERE move_type = 'out_invoice'
                   AND state = 'posted'
                   AND invoice_date >= %s) AS fatturato,

                (SELECT COALESCE(SUM(aml.balance), 0)
                 FROM account_move_line aml
                 WHERE aml.journal_id IN %s
                   AND aml.parent_state = 'posted'
                   AND aml.account_id IN (
                       SELECT id FROM account_account
                       WHERE account_type = 'asset_cash'
                   )) AS cassa,

                (SELECT COUNT(*)
                 FROM mail_activity
                 WHERE user_id = %s
                   AND date_deadline < %s
                   AND date_deadline >= %s
                   AND res_model NOT IN ('mail.message', 'res.partner')) AS alert
        """, [month_start, _BANK_JOURNAL_IDS, uid, today, d90])
        row = cr.fetchone()
        pipeline, fatturato, cassa, alert = row

        return [
            {"id": "pipeline", "label": "Pipeline B2B",
             "value": self._fmt_euro(pipeline), "raw": float(pipeline or 0),
             "icon": "fa-rocket", "trend": "up"},
            {"id": "fatturato", "label": "Fatturato MTD",
             "value": self._fmt_euro(fatturato), "raw": float(fatturato or 0),
             "icon": "fa-line-chart", "trend": "up" if fatturato else "neutral"},
            {"id": "cassa", "label": "Cassa disponibile",
             "value": self._fmt_euro(cassa), "raw": float(cassa or 0),
             "icon": "fa-university", "trend": "up" if cassa and cassa > 0 else "down"},
            {"id": "alert", "label": "Alert critici",
             "value": str(alert or 0), "raw": int(alert or 0),
             "icon": "fa-exclamation-triangle", "trend": "down" if alert and alert > 5 else "neutral"},
        ]

    # ─── Progress ───────────────────────────────────────
    @api.model
    def _compute_progress(self, cr, uid, pid, today):
        cr.execute("""
            SELECT
                (SELECT COUNT(*) FROM mail_activity
                 WHERE user_id = %s AND date_deadline = %s) AS total_today,
                (SELECT COUNT(*) FROM mail_message
                 WHERE author_id = %s
                   AND subtype_id IS NOT NULL
                   AND date::date = %s
                   AND message_type IN ('notification', 'comment')) AS done
        """, [uid, today, pid, today])
        row = cr.fetchone()
        total_today = row[0] or 0
        done = row[1] or 0
        total = max(total_today, done)
        pct = int((done / total * 100)) if total > 0 else 0
        return {"done": done, "total": total, "pct": pct}

    # ─── Macro ──────────────────────────────────────────
    @api.model
    def _compute_macro_batch(self, cr, uid, pid, today, role):
        in_30d = today + timedelta(days=30)
        d14 = today - timedelta(days=14)

        cr.execute("""
            WITH
              pipeline AS (
                SELECT COUNT(*) c FROM crm_lead
                WHERE active = true AND probability >= 30 AND probability < 100
              ),
              projects AS (
                SELECT COUNT(*) c FROM project_project WHERE active = true
              ),
              mail_pending AS (
                SELECT COUNT(*) c FROM mail_activity
                WHERE user_id = %(uid)s
                  AND date_deadline <= %(today)s
                  AND date_deadline >= %(d14)s
              ),
              agenda AS (
                SELECT COUNT(*) c FROM calendar_event ce
                JOIN calendar_event_res_partner_rel r ON r.calendar_event_id = ce.id
                WHERE r.res_partner_id = %(pid)s
                  AND ce.start::date = %(today)s
              ),
              cassa AS (
                SELECT COALESCE(SUM(aml.balance), 0) c
                FROM account_move_line aml
                WHERE aml.journal_id IN (6, 13, 22)
                  AND aml.parent_state = 'posted'
                  AND aml.account_id IN (
                      SELECT id FROM account_account
                      WHERE account_type = 'asset_cash'
                  )
              ),
              decisions AS (
                SELECT COUNT(*) c FROM mail_activity
                WHERE user_id = %(uid)s
                  AND date_deadline >= %(today)s
                  AND date_deadline <= %(today)s + 7
                  AND res_model NOT IN ('mail.message', 'res.partner')
              ),
              investor AS (
                SELECT COUNT(*) c FROM calendar_event ce
                JOIN calendar_event_res_partner_rel r ON r.calendar_event_id = ce.id
                WHERE r.res_partner_id = %(pid)s
                  AND ce.start >= %(today)s AND ce.start < %(in_30d)s
                  AND (ce.name ILIKE '%%investor%%'
                       OR ce.name ILIKE '%%cda%%'
                       OR ce.name ILIKE '%%board%%'
                       OR ce.name ILIKE '%%consiglio%%'
                       OR ce.name ILIKE '%%crowdfunding%%')
              ),
              quality AS (
                SELECT (
                  SELECT COUNT(*) FROM project_task pt
                  JOIN project_project pp ON pp.id = pt.project_id
                  LEFT JOIN project_project_project_tags_rel ttr ON ttr.project_project_id = pp.id
                  LEFT JOIN project_tags ptag ON ptag.id = ttr.project_tags_id
                  WHERE (pt.state IS NULL OR pt.state NOT IN ('1_done', '1_canceled', '03_approved'))
                    AND pt.date_deadline IS NOT NULL AND pt.date_deadline < %(today)s
                    AND (ptag.name::text ILIKE '%%Qualit%%' OR pp.id IN (76, 77))
                ) + (
                  SELECT COUNT(*) FROM stock_lot
                  WHERE expiration_date IS NOT NULL AND expiration_date <= %(today)s + 30
                ) AS c
              )
            SELECT
              pipeline.c, projects.c, mail_pending.c, agenda.c,
              cassa.c, decisions.c, investor.c, quality.c
            FROM pipeline, projects, mail_pending, agenda,
                 cassa, decisions, investor, quality
        """, {
            "uid": uid, "pid": pid, "today": today,
            "in_30d": in_30d, "d14": d14,
        })
        row = cr.fetchone()

        raw_counts = {
            "pipeline": row[0] or 0,
            "projects": row[1] or 0,
            "mail": row[2] or 0,
            "agenda": row[3] or 0,
            "cassa": float(row[4] or 0),
            "decisions": row[5] or 0,
            "investor": row[6] or 0,
            "quality": row[7] or 0,
        }

        results = []
        for area in _MACRO_AREAS:
            visible = role in area["roles"]
            raw = raw_counts.get(area["id"], 0) if visible else 0
            # Format cassa as euro
            if area["id"] == "cassa" and visible:
                count = self._fmt_euro(raw)
            else:
                count = raw
            results.append({
                "id": area["id"],
                "label": area["label"],
                "icon": area["icon"],
                "color": area["color"],
                "count": count,
                "visible": visible,
            })
        return results

    # ─── Today ──────────────────────────────────────────
    @api.model
    def _compute_today(self, cr, uid, today):
        week_end = today + timedelta(days=(6 - today.weekday()))
        d90 = today - timedelta(days=90)

        cr.execute("""
            SELECT ma.id, ma.summary, ma.res_model, ma.res_id,
                   ma.date_deadline::text,
                   mat.name AS type_name,
                   CASE
                     WHEN ma.date_deadline < %(today)s THEN 'critical'
                     WHEN ma.date_deadline = %(today)s THEN 'today'
                     WHEN ma.date_deadline <= %(day3)s THEN 'upcoming'
                     ELSE 'week'
                   END AS bucket
            FROM mail_activity ma
            LEFT JOIN mail_activity_type mat ON mat.id = ma.activity_type_id
            WHERE ma.user_id = %(uid)s
              AND ma.date_deadline <= %(week_end)s
              AND ma.date_deadline >= %(d90)s
              AND ma.res_model NOT IN ('mail.message', 'res.partner')
            ORDER BY ma.date_deadline
            LIMIT 50
        """, {
            "uid": uid, "today": today,
            "day3": today + timedelta(days=3),
            "week_end": week_end, "d90": d90,
        })

        raw_rows = []
        buckets = {"critical": [], "today": [], "upcoming": [], "week": []}
        icons = {
            "critical": ("fa-exclamation-circle", "#DC2626"),
            "today": ("fa-clock-o", "#F59E0B"),
            "upcoming": ("fa-arrow-right", "#3B82F6"),
            "week": ("fa-calendar-check-o", "#6366F1"),
        }

        for row in cr.fetchall():
            raw_rows.append({
                "id": row[0],
                "summary": row[1] or _jsonb_str(row[5]),
                "res_model": row[2],
                "res_id": row[3],
                "deadline": row[4],
                "bucket": row[6],
            })

        # Resolve display names batch
        self._resolve_activity_labels(raw_rows)

        for item in raw_rows:
            bucket = item["bucket"]
            icon, color = icons.get(bucket, ("fa-circle", "#6B7280"))
            lst = buckets.get(bucket)
            if lst is not None and len(lst) < 10:
                lst.append({
                    "id": item["id"],
                    "title": item["title"],
                    "model": item["res_model"],
                    "res_id": item["res_id"],
                    "deadline": item["deadline"],
                    "type": bucket,
                    "icon": icon,
                    "color": color,
                })

        return {
            "critical": buckets["critical"],
            "oggi": buckets["today"],
            "prossimi": buckets["upcoming"],
            "week": buckets["week"],
        }

    @api.model
    def _resolve_activity_labels(self, activities):
        """Resolve display names for activity records batch."""
        by_model = defaultdict(list)
        for a in activities:
            if a.get("res_model") and a.get("res_id"):
                by_model[a["res_model"]].append(a["res_id"])

        resolved = {}
        for model, ids in by_model.items():
            if model not in self.env:
                continue
            try:
                recs = self.env[model].browse(list(set(ids))).exists()
                for r in recs:
                    resolved[(model, r.id)] = r.display_name or str(r.id)
            except Exception:
                pass

        for a in activities:
            ref_name = resolved.get((a["res_model"], a["res_id"]), "")
            model_short = (a["res_model"] or "").split(".")[-1].replace("_", " ").title()
            summary = a.get("summary") or "Attività"
            if ref_name:
                a["title"] = f"{model_short} · {ref_name} · {summary}"
            else:
                a["title"] = f"{model_short} · {summary}"

    # ─── Feed ───────────────────────────────────────────
    @api.model
    def _compute_feed(self, cr, pid):
        cr.execute("""
            SELECT mm.id, mm.body, mm.date,
                   rp.name AS author_name, rp.id AS author_id
            FROM mail_message mm
            LEFT JOIN res_partner rp ON rp.id = mm.author_id
            WHERE mm.message_type IN ('comment', 'notification')
              AND mm.body IS NOT NULL AND mm.body != ''
              AND mm.subtype_id IS NOT NULL
              AND mm.date > NOW() - INTERVAL '30 days'
              AND mm.author_id IN (
                  SELECT partner_id FROM res_users WHERE active = true AND share = false
              )
              AND COALESCE(mm.body, '') NOT ILIKE '%%ITALIAN FOOD EXCELLENCE%%'
            ORDER BY mm.date DESC
            LIMIT 5
        """)
        feed = []
        for row in cr.fetchall():
            body_clean = _HTML_TAG_RE.sub('', row[1] or '').strip()
            if len(body_clean) > 120:
                body_clean = body_clean[:117] + "..."
            if not body_clean:
                continue

            author_name = row[3] or "Sistema"
            if isinstance(author_name, dict):
                author_name = author_name.get("it_IT") or author_name.get("en_US") or "Sistema"
            parts = str(author_name).split()
            if len(parts) >= 2:
                initials = (parts[0][0] + parts[-1][0]).upper()
            elif parts:
                initials = parts[0][:2].upper()
            else:
                initials = "??"

            feed.append({
                "id": row[0],
                "body": body_clean,
                "date": row[2].isoformat() if row[2] else "",
                "author": str(author_name),
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
