# -*- coding: utf-8 -*-
"""Workspace Calendar — backend data provider for Agenda section."""
import logging
from datetime import date, datetime, timedelta
from collections import defaultdict

from odoo import api, models

_logger = logging.getLogger(__name__)

_WEEKDAYS_IT = {0: "Lun", 1: "Mar", 2: "Mer", 3: "Gio", 4: "Ven", 5: "Sab", 6: "Dom"}
_MONTHS_IT = {1:"gen",2:"feb",3:"mar",4:"apr",5:"mag",6:"giu",7:"lug",8:"ago",9:"set",10:"ott",11:"nov",12:"dic"}

_TYPE_COLORS = {"team":"#9CA3AF","buyer":"#0D9488","investor":"#D97706","deal":"#DC2626","internal":"#8B5CF6"}
_TYPE_ICONS = {"team":"fa-users","buyer":"fa-handshake-o","investor":"fa-money","deal":"fa-gavel","internal":"fa-calendar"}

_CAL_MACRO = [
    {"id": "today_ev", "label": "Eventi oggi", "icon": "fa-calendar-check-o", "color": "#FAEEDA"},
    {"id": "week_ev", "label": "Questa settimana", "icon": "fa-calendar", "color": "#EEEDFE"},
    {"id": "external", "label": "Call esterne", "icon": "fa-phone", "color": "#E1F5EE"},
    {"id": "buyer_ev", "label": "Meeting buyer", "icon": "fa-handshake-o", "color": "#FAECE7"},
    {"id": "investor_ev", "label": "Investor/CdA", "icon": "fa-money", "color": "#FBEAF0"},
    {"id": "team_ev", "label": "Team interni", "icon": "fa-users", "color": "#E6F1FB"},
    {"id": "allday_ev", "label": "Giornata intera", "icon": "fa-sun-o", "color": "#EAF3DE"},
    {"id": "next_7d", "label": "Prossimi 7 gg", "icon": "fa-arrow-right", "color": "#F1EFE8"},
]

_PREP = {
    "investor": ["Deck v3 con Q3 numbers", "Talking points crescita", "Lista domande investor", "Backup financials"],
    "buyer": ["Listino aggiornato 2027", "Schede tecniche EN", "Thread mail buyer", "Talking points pricing"],
    "deal": ["Documento principale (LOI/contratto)", "Punti aperti notaio", "Cronologia decisioni", "Doc due diligence"],
    "team": ["Agenda condivisa", "Note 1:1 precedenti", "Punti aperti"],
    "internal": ["Agenda", "Materiali condivisi"],
}

_INVESTOR_KW = ('investor', 'cda', 'crowdfund', 'fund', 'consiglio', 'board')
_DEAL_KW = ('loi', 'firma', 'notaio', 'contratto', 'signing')


def _event_type(name, location, attendee_emails):
    """Classify event type from name and attendees."""
    nm = (name or "").lower()
    if any(k in nm for k in _INVESTOR_KW):
        return "investor"
    if any(k in nm for k in _DEAL_KW):
        return "deal"
    external = [e for e in (attendee_emails or []) if e and "@casafolino.com" not in e and "@caffelove" not in e]
    if external:
        return "buyer"
    return "team"


def _fmt_time(dt_val, tz_offset=1):
    """Format datetime to HH:MM in local time."""
    if not dt_val:
        return ""
    # Simple offset (Europe/Rome is UTC+1 or +2 in summer)
    local = dt_val + timedelta(hours=tz_offset)
    return local.strftime("%H:%M")


class WorkspaceCalendar(models.AbstractModel):
    _name = "workspace.calendar"
    _description = "Workspace Calendar Data Provider"

    def _tz_offset(self):
        """Get timezone offset hours for current user."""
        tz = self.env.user.tz or "Europe/Rome"
        try:
            import pytz
            from datetime import datetime
            local_tz = pytz.timezone(tz)
            now = datetime.now(pytz.utc)
            offset = local_tz.utcoffset(now)
            return offset.total_seconds() / 3600
        except Exception:
            return 2  # CEST default

    @api.model
    def get_cal_data(self):
        profile = self.env["res.users"]._get_workspace_profile(self.env.user)
        cr = self.env.cr
        today = date.today()
        pid = self.env.user.partner_id.id

        kpis = self._kpis(cr, pid, today)
        macro = self._macro_batch(cr, pid, today)
        feed = self._feed(cr)

        hero = {
            "greet": "Agenda di oggi",
            "sub": f"{kpis[0]['raw']} eventi oggi · {kpis[1]['raw']} questa settimana · {kpis[2]['raw']}h focus",
            "tip": {"text": "Hai meeting buyer questa settimana. Prepara listino aggiornato.", "primary": "Vedi", "secondary": "Ignora"},
            "progress": {"done": 0, "total": 0, "pct": 0},
        }

        return {
            "user": profile, "hero": hero, "kpis": kpis, "macro": macro,
            "filters": ["Tutti", "Buyer", "Investor", "Team", "Deal"],
            "feed": feed, "today_str": str(today),
        }

    @api.model
    def get_day_events(self, day_str=None):
        cr = self.env.cr
        pid = self.env.user.partner_id.id
        tz_off = self._tz_offset()
        target = date.fromisoformat(day_str) if day_str else date.today()
        wd = _WEEKDAYS_IT.get(target.weekday(), "")
        mn = _MONTHS_IT.get(target.month, "")
        label = f"{wd} {target.day} {mn}"

        cr.execute("""
            SELECT ce.id, ce.name, ce.start, ce.stop, ce.allday, ce.location, ce.user_id,
                   (SELECT array_agg(rp.email) FROM calendar_event_res_partner_rel r
                    JOIN res_partner rp ON rp.id=r.res_partner_id
                    WHERE r.calendar_event_id=ce.id) AS emails,
                   (SELECT array_agg(rp.name::text || '|' || COALESCE(rp.email,'')) FROM calendar_event_res_partner_rel r
                    JOIN res_partner rp ON rp.id=r.res_partner_id
                    WHERE r.calendar_event_id=ce.id) AS attendee_info
            FROM calendar_event ce
            JOIN calendar_event_res_partner_rel rel ON rel.calendar_event_id=ce.id
            WHERE rel.res_partner_id = %s AND ce.active=true
              AND ce.start::date = %s
            ORDER BY ce.allday DESC, ce.start
        """, [pid, target])

        events = []
        occupied_min = 0
        for row in cr.fetchall():
            etype = _event_type(row[1], row[5], row[7])
            color = _TYPE_COLORS.get(etype, "#9CA3AF")
            icon = _TYPE_ICONS.get(etype, "fa-calendar")
            dur = 0
            if row[2] and row[3]:
                dur = max(0, int((row[3] - row[2]).total_seconds() / 60))
            occupied_min += dur

            attendees = []
            for info in (row[8] or []):
                parts = info.split("|")
                nm = parts[0] if parts else "?"
                nm_parts = nm.split()
                ini = (nm_parts[0][0] + nm_parts[-1][0]).upper() if len(nm_parts) >= 2 else nm[:2].upper()
                attendees.append({"name": nm, "initials": ini})

            events.append({
                "id": row[0],
                "title": row[1] or "—",
                "start": _fmt_time(row[2], tz_off) if not row[4] else "All day",
                "end": _fmt_time(row[3], tz_off) if not row[4] else "",
                "duration_min": dur,
                "allday": row[4] or False,
                "location": row[5] or "",
                "type": etype,
                "color": color,
                "icon": icon,
                "attendees": attendees[:5],
            })

        total_h = 9  # 09:00-18:00
        occ_h = round(occupied_min / 60, 1)
        free_h = max(0, round(total_h - occ_h, 1))

        return {
            "date": str(target), "label": label,
            "summary": {"events": len(events), "occupied_h": occ_h, "free_h": free_h},
            "events": events,
        }

    @api.model
    def get_week_events(self, week_start_str=None):
        cr = self.env.cr
        pid = self.env.user.partner_id.id
        tz_off = self._tz_offset()
        today = date.today()

        if week_start_str:
            ws = date.fromisoformat(week_start_str)
        else:
            ws = today - timedelta(days=today.weekday())

        we = ws + timedelta(days=5)
        mn_s = _MONTHS_IT.get(ws.month, "")
        mn_e = _MONTHS_IT.get(we.month, "")
        week_label = f"{ws.day}-{we.day} {mn_e} {we.year}" if ws.month == we.month else f"{ws.day} {mn_s} - {we.day} {mn_e}"

        cr.execute("""
            SELECT ce.id, ce.name, ce.start, ce.stop, ce.allday, ce.location,
                   (SELECT array_agg(rp.email) FROM calendar_event_res_partner_rel r
                    JOIN res_partner rp ON rp.id=r.res_partner_id
                    WHERE r.calendar_event_id=ce.id) AS emails,
                   (SELECT rp.name::text FROM calendar_event_res_partner_rel r
                    JOIN res_partner rp ON rp.id=r.res_partner_id
                    WHERE r.calendar_event_id=ce.id AND rp.id != %s LIMIT 1) AS other_name
            FROM calendar_event ce
            JOIN calendar_event_res_partner_rel rel ON rel.calendar_event_id=ce.id
            WHERE rel.res_partner_id = %s AND ce.active=true
              AND ce.start::date >= %s AND ce.start::date < %s
            ORDER BY ce.start
        """, [pid, pid, ws, we])

        by_day = defaultdict(list)
        for row in cr.fetchall():
            d = row[2].date() if row[2] else ws
            etype = _event_type(row[1], row[5], row[6])
            by_day[d].append({
                "id": row[0],
                "time": _fmt_time(row[2], tz_off) if not row[4] else "All day",
                "title": row[1] or "—",
                "meta": row[7] or "",
                "color": _TYPE_COLORS.get(etype, "#9CA3AF"),
                "type": etype,
            })

        days = []
        for i in range(5):
            d = ws + timedelta(days=i)
            wd = _WEEKDAYS_IT.get(d.weekday(), "")
            days.append({
                "id": wd.lower(),
                "label": wd,
                "day_num": d.day,
                "date": str(d),
                "is_today": d == today,
                "events": by_day.get(d, []),
            })

        return {"week": week_label, "week_start": str(ws), "days": days}

    @api.model
    def get_month_events(self, month_start_str=None):
        cr = self.env.cr
        pid = self.env.user.partner_id.id
        today = date.today()

        if month_start_str:
            ms = date.fromisoformat(month_start_str)
        else:
            ms = today.replace(day=1)

        # End of month
        if ms.month == 12:
            me = ms.replace(year=ms.year + 1, month=1)
        else:
            me = ms.replace(month=ms.month + 1)

        mn = _MONTHS_IT.get(ms.month, "")
        month_label = f"{mn.capitalize()} {ms.year}"

        cr.execute("""
            SELECT ce.start::date as d, COUNT(*) as cnt,
                   array_agg(DISTINCT substring(ce.name from 1 for 20)) as names
            FROM calendar_event ce
            JOIN calendar_event_res_partner_rel rel ON rel.calendar_event_id=ce.id
            WHERE rel.res_partner_id = %s AND ce.active=true
              AND ce.start::date >= %s AND ce.start::date < %s
            GROUP BY ce.start::date
        """, [pid, ms, me])

        day_data = {}
        for row in cr.fetchall():
            day_data[row[0]] = {"count": row[1], "names": row[2] or []}

        # Build 6-week grid
        first_weekday = ms.weekday()
        grid_start = ms - timedelta(days=first_weekday)

        weeks = []
        for w in range(6):
            week = []
            for d in range(7):
                current = grid_start + timedelta(days=w * 7 + d)
                dd = day_data.get(current, {"count": 0, "names": []})
                week.append({
                    "day_num": current.day,
                    "date": str(current),
                    "is_other_month": current.month != ms.month,
                    "is_today": current == today,
                    "event_count": dd["count"],
                })
            weeks.append(week)
            if grid_start + timedelta(days=(w + 1) * 7) >= me and w >= 4:
                break

        return {"month": month_label, "month_start": str(ms), "weeks": weeks}

    @api.model
    def get_event_detail(self, event_id):
        cr = self.env.cr
        tz_off = self._tz_offset()

        cr.execute("""
            SELECT ce.id, ce.name, ce.start, ce.stop, ce.allday, ce.location,
                   ce.description, ce.user_id
            FROM calendar_event ce WHERE ce.id = %s
        """, [event_id])
        row = cr.fetchone()
        if not row:
            return {"error": "Event not found"}

        etype = "team"
        cr.execute("""
            SELECT rp.id, rp.name, rp.email,
                   ca.state
            FROM calendar_event_res_partner_rel rel
            JOIN res_partner rp ON rp.id = rel.res_partner_id
            LEFT JOIN calendar_attendee ca ON ca.event_id = %s AND ca.partner_id = rp.id
            WHERE rel.calendar_event_id = %s
        """, [event_id, event_id])

        attendees = []
        emails = []
        for a_row in cr.fetchall():
            nm = a_row[1] or "?"
            if isinstance(nm, dict):
                nm = nm.get("it_IT") or nm.get("en_US") or "?"
            nm = str(nm)
            parts = nm.split()
            ini = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else nm[:2].upper()
            attendees.append({
                "id": a_row[0], "name": nm, "email": a_row[2] or "",
                "initials": ini, "status": a_row[3] or "needsAction",
            })
            if a_row[2]:
                emails.append(a_row[2])

        etype = _event_type(row[1], row[5], emails)
        color = _TYPE_COLORS.get(etype, "#9CA3AF")
        prep = _PREP.get(etype, _PREP["internal"])

        # Chain
        chain = [{"label": f"Partecipanti ({len(attendees)})", "icon": "fa-users", "count": len(attendees)}]
        if row[5]:
            chain.append({"label": f"Luogo: {row[5]}", "icon": "fa-map-marker", "count": 0})

        return {
            "event": {
                "id": row[0], "title": row[1] or "—",
                "start": _fmt_time(row[2], tz_off), "end": _fmt_time(row[3], tz_off),
                "allday": row[4] or False,
                "location": row[5] or "", "description": row[6] or "",
                "type": etype, "color": color, "icon": _TYPE_ICONS.get(etype, "fa-calendar"),
            },
            "attendees": attendees,
            "prep_items": prep,
            "chain": chain,
        }

    # ─── KPIs ──────────────────────────────────────────
    @api.model
    def _kpis(self, cr, pid, today):
        week_end = today + timedelta(days=(6 - today.weekday()))
        cr.execute("""
            SELECT
                (SELECT COUNT(*) FROM calendar_event ce
                 JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id
                 WHERE r.res_partner_id=%(pid)s AND ce.active=true AND ce.start::date=%(today)s) AS today_cnt,
                (SELECT COUNT(*) FROM calendar_event ce
                 JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id
                 WHERE r.res_partner_id=%(pid)s AND ce.active=true
                   AND ce.start::date >= %(today)s AND ce.start::date <= %(we)s) AS week_cnt,
                (SELECT COALESCE(ROUND(SUM(EXTRACT(EPOCH FROM (ce.stop-ce.start))/3600)::numeric, 1), 0)
                 FROM calendar_event ce
                 JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id
                 WHERE r.res_partner_id=%(pid)s AND ce.active=true
                   AND ce.start::date=%(today)s AND ce.allday=false) AS focus_h,
                (SELECT COUNT(*) FROM calendar_event ce
                 JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id
                 WHERE r.res_partner_id=%(pid)s AND ce.active=true
                   AND ce.start::date >= %(today)s AND ce.start::date <= %(we)s
                   AND EXISTS(SELECT 1 FROM calendar_event_res_partner_rel r2
                              JOIN res_partner rp2 ON rp2.id=r2.res_partner_id
                              WHERE r2.calendar_event_id=ce.id
                                AND rp2.email NOT LIKE '%%casafolino.com' AND rp2.email NOT LIKE '%%caffelove%%'
                                AND rp2.email IS NOT NULL)) AS external_cnt
        """, {"pid": pid, "today": today, "we": week_end})
        row = cr.fetchone()
        return [
            {"id": "today", "label": "Eventi oggi", "value": str(row[0] or 0), "raw": int(row[0] or 0), "icon": "fa-calendar-check-o"},
            {"id": "week", "label": "Questa settimana", "value": str(row[1] or 0), "raw": int(row[1] or 0), "icon": "fa-calendar"},
            {"id": "focus", "label": "Ore focus oggi", "value": f"{float(row[2] or 0)}h", "raw": float(row[2] or 0), "icon": "fa-clock-o"},
            {"id": "external", "label": "Call esterne", "value": str(row[3] or 0), "raw": int(row[3] or 0), "icon": "fa-phone"},
        ]

    # ─── Macro ─────────────────────────────────────────
    @api.model
    def _macro_batch(self, cr, pid, today):
        we = today + timedelta(days=(6 - today.weekday()))
        d7 = today + timedelta(days=7)
        cr.execute("""
            WITH
              today_ev AS (SELECT COUNT(*) c FROM calendar_event ce JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id WHERE r.res_partner_id=%(pid)s AND ce.active=true AND ce.start::date=%(today)s),
              week_ev AS (SELECT COUNT(*) c FROM calendar_event ce JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id WHERE r.res_partner_id=%(pid)s AND ce.active=true AND ce.start::date>=%(today)s AND ce.start::date<=%(we)s),
              external AS (SELECT COUNT(*) c FROM calendar_event ce JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id WHERE r.res_partner_id=%(pid)s AND ce.active=true AND ce.start::date>=%(today)s AND ce.start::date<=%(we)s AND EXISTS(SELECT 1 FROM calendar_event_res_partner_rel r2 JOIN res_partner rp2 ON rp2.id=r2.res_partner_id WHERE r2.calendar_event_id=ce.id AND rp2.email NOT LIKE '%%casafolino.com' AND rp2.email NOT LIKE '%%caffelove%%' AND rp2.email IS NOT NULL)),
              buyer_ev AS (SELECT COUNT(*) c FROM calendar_event ce WHERE ce.active=true AND ce.start::date>=%(today)s AND ce.start::date<=%(d7)s AND (ce.name ILIKE '%%buyer%%' OR ce.name ILIKE '%%listino%%' OR ce.name ILIKE '%%sample%%')),
              investor_ev AS (SELECT COUNT(*) c FROM calendar_event ce WHERE ce.active=true AND ce.start::date>=%(today)s AND ce.start::date<=%(d7)s AND (ce.name ILIKE '%%investor%%' OR ce.name ILIKE '%%cda%%' OR ce.name ILIKE '%%crowdfund%%' OR ce.name ILIKE '%%board%%')),
              team_ev AS (SELECT COUNT(*) c FROM calendar_event ce JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id WHERE r.res_partner_id=%(pid)s AND ce.active=true AND ce.start::date=%(today)s AND NOT EXISTS(SELECT 1 FROM calendar_event_res_partner_rel r2 JOIN res_partner rp2 ON rp2.id=r2.res_partner_id WHERE r2.calendar_event_id=ce.id AND rp2.email NOT LIKE '%%casafolino.com' AND rp2.email NOT LIKE '%%caffelove%%' AND rp2.email IS NOT NULL)),
              allday_ev AS (SELECT COUNT(*) c FROM calendar_event ce JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id WHERE r.res_partner_id=%(pid)s AND ce.active=true AND ce.allday=true AND ce.start::date>=%(today)s AND ce.start::date<=%(d7)s),
              next_7d AS (SELECT COUNT(*) c FROM calendar_event ce JOIN calendar_event_res_partner_rel r ON r.calendar_event_id=ce.id WHERE r.res_partner_id=%(pid)s AND ce.active=true AND ce.start::date>%(today)s AND ce.start::date<=%(d7)s)
            SELECT today_ev.c, week_ev.c, external.c, buyer_ev.c, investor_ev.c, team_ev.c, allday_ev.c, next_7d.c
            FROM today_ev, week_ev, external, buyer_ev, investor_ev, team_ev, allday_ev, next_7d
        """, {"pid": pid, "today": today, "we": we, "d7": d7})
        row = cr.fetchone()
        counts = [row[i] or 0 for i in range(8)]
        results = []
        for i, area in enumerate(_CAL_MACRO):
            results.append({"id": area["id"], "label": area["label"], "icon": area["icon"], "color": area["color"], "count": counts[i], "visible": True})
        return results

    # ─── Feed ──────────────────────────────────────────
    @api.model
    def _feed(self, cr):
        cr.execute("""
            SELECT mm.id, mm.body, mm.date, rp.name AS author_name
            FROM mail_message mm
            LEFT JOIN res_partner rp ON rp.id=mm.author_id
            WHERE mm.model='calendar.event'
              AND mm.message_type IN ('comment','notification')
              AND mm.body IS NOT NULL AND mm.body != ''
              AND mm.date > NOW() - INTERVAL '30 days'
            ORDER BY mm.date DESC LIMIT 10
        """)
        import re
        _HTML = re.compile(r'<[^>]+>')
        feed = []
        for row in cr.fetchall():
            body = _HTML.sub('', row[1] or '').strip()
            if len(body) > 120:
                body = body[:117] + "..."
            if not body:
                continue
            author = row[3] or "Sistema"
            if isinstance(author, dict):
                author = author.get("it_IT") or author.get("en_US") or "Sistema"
            parts = str(author).split()
            ini = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else parts[0][:2].upper() if parts else "??"
            feed.append({"id": row[0], "body": body, "date": row[2].isoformat() if row[2] else "", "author": str(author), "initials": ini})
        return feed
