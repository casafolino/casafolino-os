# -*- coding: utf-8 -*-
"""Workspace Mail — backend data provider for Mail Hub section.
Reads from casafolino_mail_message (primary) with fallback to mail.message.
NEVER modifies casafolino_mail tables — read-only integration.
"""
import logging
import re
from datetime import date, timedelta

from odoo import api, models

_logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r'<[^>]+>')

# Map casafolino_mail ai_category → UI tag
_CAT_MAP = {
    "commerciale": ("lead", "Lead", "#EEEDFE", "#3C3489"),
    "lead": ("lead", "Lead", "#EEEDFE", "#3C3489"),
    "buyer": ("lead", "Lead", "#EEEDFE", "#3C3489"),
    "fornitore": ("ops", "Operativo", "#E1F5EE", "#085041"),
    "operations": ("ops", "Operativo", "#E1F5EE", "#085041"),
    "interno": ("ops", "Operativo", "#E1F5EE", "#085041"),
    "admin": ("adm", "Admin", "#F1EFE8", "#444441"),
    "newsletter": ("adm", "Admin", "#F1EFE8", "#444441"),
    "personale": ("adm", "Admin", "#F1EFE8", "#444441"),
    "spam": ("adm", "Spam", "#F1EFE8", "#444441"),
    "quality": ("qa", "Qualità", "#FAECE7", "#712B13"),
    "finance": ("fin", "Finanza", "#FAEEDA", "#633806"),
    "decision": ("dec", "Decisione", "#FCEBEB", "#791F1F"),
}

_DEFAULT_TAG = ("adm", "Admin", "#F1EFE8", "#444441")

_MAIL_MACRO = [
    {"id": "unread", "label": "Non lette", "icon": "fa-envelope", "color": "#FAECE7"},
    {"id": "important", "label": "Importanti", "icon": "fa-star", "color": "#FAEEDA"},
    {"id": "lead_mail", "label": "Lead / Buyer", "icon": "fa-bullseye", "color": "#EEEDFE"},
    {"id": "ops_mail", "label": "Operativo", "icon": "fa-cog", "color": "#E1F5EE"},
    {"id": "threads", "label": "Thread attivi", "icon": "fa-comments", "color": "#FBEAF0"},
    {"id": "outbound", "label": "Inviate 7gg", "icon": "fa-paper-plane", "color": "#E6F1FB"},
    {"id": "action_req", "label": "Azione richiesta", "icon": "fa-bolt", "color": "#FCEBEB"},
    {"id": "archived", "label": "Archiviate", "icon": "fa-archive", "color": "#F1EFE8"},
]

_REPLY_TEMPLATES = {
    "lead": "Buongiorno {name}, grazie del messaggio. Ti aggiorno con i dettagli richiesti entro 48 ore. Cordiali saluti, Antonio",
    "dec": "Ho rivisto il documento. Ho 2 osservazioni minori, possiamo allinearci con una call breve? Antonio",
    "qa": "In riferimento alla richiesta, allego l'integrazione documentale. Per ulteriori chiarimenti resto a disposizione.",
    "ops": "Confermo la lavorazione, ti aggiorno appena disponibile il tracking. Cordiali saluti.",
    "fin": "Grazie per la nota. Allego la documentazione richiesta entro fine settimana.",
    "adm": "Confermo il ricevimento. Procedo con quanto richiesto. Cordiali saluti.",
}


def _jsonb_str(val):
    if not val:
        return ""
    if isinstance(val, dict):
        return val.get("it_IT") or val.get("en_US") or next(iter(val.values()), "")
    return str(val)


def _tag_for(ai_category, subject=""):
    """Map AI category to UI tag tuple (key, label, bg, fg)."""
    if ai_category:
        t = _CAT_MAP.get(ai_category.lower().strip())
        if t:
            return t
    # Keyword fallback on subject
    subj = (subject or "").lower()
    if any(k in subj for k in ("pagamento", "fattura", "saldo", "iva", "bonifico")):
        return ("fin", "Finanza", "#FAEEDA", "#633806")
    if any(k in subj for k in ("ordine", "sample", "campione", "quotation", "listino", "preventivo", "buyer")):
        return ("lead", "Lead", "#EEEDFE", "#3C3489")
    if any(k in subj for k in ("haccp", "certif", "halal", "kosher", "ifs", "brc", "allergeni")):
        return ("qa", "Qualità", "#FAECE7", "#712B13")
    if any(k in subj for k in ("spedizione", "ddt", "corriere", "customs", "dogana", "tracking")):
        return ("ops", "Operativo", "#E1F5EE", "#085041")
    if any(k in subj for k in ("firma", "approva", "loi", "contratto", "decisione")):
        return ("dec", "Decisione", "#FCEBEB", "#791F1F")
    return _DEFAULT_TAG


def _relative_time(dt_val):
    """Format datetime to relative Italian string."""
    if not dt_val:
        return ""
    from datetime import datetime
    now = datetime.now()
    if hasattr(dt_val, 'replace'):
        diff = now - dt_val
    else:
        return str(dt_val)
    days = diff.days
    if days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            mins = max(1, diff.seconds // 60)
            return f"{mins} min fa"
        return f"{hours} h fa"
    if days == 1:
        return "ieri"
    if days < 7:
        return f"{days} gg fa"
    return f"{days} gg fa"


class WorkspaceMail(models.AbstractModel):
    _name = "workspace.mail"
    _description = "Workspace Mail Hub Data Provider"

    # ─── /workspace/mail/data ──────────────────────────
    @api.model
    def get_mail_data(self):
        profile = self.env["res.users"]._get_workspace_profile(self.env.user)
        cr = self.env.cr

        kpis = self._kpis(cr)
        macro = self._macro_batch(cr)
        feed = self._feed(cr)

        hero = {
            "greet": "Mail hub",
            "sub": f"{kpis[0]['raw']} in sospeso · {kpis[1]['raw']} thread attivi · {kpis[3]['raw']} importanti",
            "tip": {
                "text": "Hai mail buyer non risposte da oltre 48h. Verifica triage.",
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
            "filters": ["Tutte", "Importanti", "Buyer", "Decisioni", "Archiviate"],
            "feed": feed,
        }

    # ─── /workspace/mail/inbox ─────────────────────────
    @api.model
    def get_inbox(self, filter_key="tutte"):
        cr = self.env.cr

        where_extra = ""
        if filter_key == "importanti":
            where_extra = "AND (m.ai_action_required = true OR m.ai_urgency = 'high')"
        elif filter_key == "buyer":
            where_extra = "AND (m.ai_category = 'commerciale' OR m.ai_category = 'lead')"
        elif filter_key == "decisioni":
            where_extra = "AND m.subject ILIKE '%%firma%%' OR m.subject ILIKE '%%loi%%' OR m.subject ILIKE '%%contratto%%' OR m.subject ILIKE '%%approv%%'"
        elif filter_key == "archiviate":
            where_extra = "AND m.is_archived = true"

        archive_filter = "AND m.is_archived = false" if filter_key != "archiviate" else ""

        cr.execute(f"""
            SELECT m.id, m.sender_name, m.sender_email, m.sender_domain,
                   m.subject, m.snippet, m.ai_category,
                   m.email_date, m.is_read, m.is_starred,
                   m.is_important, m.lead_id, m.thread_id,
                   m.ai_action_required, m.ai_urgency,
                   (SELECT COUNT(*) FROM casafolino_mail_message m2
                    WHERE m2.thread_id = m.thread_id AND m.thread_id IS NOT NULL) AS thread_count
            FROM casafolino_mail_message m
            WHERE m.direction = 'inbound'
              AND m.is_deleted = false
              AND m.state != 'auto_discard'
              {archive_filter}
              AND m.email_date >= NOW() - INTERVAL '30 days'
              {where_extra}
            ORDER BY m.is_read ASC, m.email_date DESC
            LIMIT 50
        """)

        mails = []
        for row in cr.fetchall():
            tag_key, tag_label, tag_bg, tag_fg = _tag_for(row[6], row[4])

            # Pill based on age
            age_days = (date.today() - row[7].date()).days if row[7] else 0
            if age_days > 3 and not row[8]:
                pill_status, pill_label = "red", f"-{age_days} gg"
            elif age_days > 1 and not row[8]:
                pill_status, pill_label = "amber", f"-{age_days} gg"
            elif not row[8]:
                pill_status, pill_label = "green", "nuovo"
            else:
                pill_status, pill_label = "gray", "letto"

            mails.append({
                "id": row[0],
                "source": "casafolino",
                "from_name": row[1] or "Sconosciuto",
                "from_email": row[2] or "",
                "from_company": (row[3] or "").replace(".", " ").title() if row[3] else "",
                "subject": row[4] or "(nessun oggetto)",
                "preview": (row[5] or "")[:120],
                "tag": tag_key,
                "tag_label": tag_label,
                "tag_bg": tag_bg,
                "tag_fg": tag_fg,
                "when_relative": _relative_time(row[7]),
                "when_iso": row[7].isoformat() if row[7] else "",
                "pill_status": pill_status,
                "pill_label": pill_label,
                "thread_count": row[15] or 0,
                "unread": not row[8],
                "starred": row[9] or False,
                "linked_lead_id": row[11],
            })

        return {"mails": mails}

    # ─── /workspace/mail/threads ───────────────────────
    @api.model
    def get_threads(self):
        cr = self.env.cr
        cr.execute("""
            SELECT t.id, t.partner_id,
                   rp.name AS contact_name, rp.email AS contact_email,
                   rp.company_name,
                   (SELECT COUNT(*) FROM casafolino_mail_message m WHERE m.thread_id = t.id) AS msg_count,
                   (SELECT MAX(m.email_date) FROM casafolino_mail_message m WHERE m.thread_id = t.id) AS last_date,
                   (SELECT COUNT(*) FROM casafolino_mail_message m
                    WHERE m.thread_id = t.id AND m.is_read = false) AS unread_count
            FROM casafolino_mail_thread t
            LEFT JOIN res_partner rp ON rp.id = t.partner_id
            WHERE EXISTS (
                SELECT 1 FROM casafolino_mail_message m
                WHERE m.thread_id = t.id AND m.email_date >= NOW() - INTERVAL '30 days'
            )
            ORDER BY last_date DESC NULLS LAST
            LIMIT 20
        """)

        threads = []
        for row in cr.fetchall():
            contact_name = _jsonb_str(row[2]) or "Sconosciuto"
            parts = str(contact_name).split()
            initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else (parts[0][:2].upper() if parts else "??")
            unread = row[7] or 0

            threads.append({
                "id": row[0],
                "contact_name": contact_name,
                "contact_email": row[3] or "",
                "company": _jsonb_str(row[4]) or "",
                "count": row[5] or 0,
                "last_message": _relative_time(row[6]),
                "status": "Attivo" if unread > 0 else "Letto",
                "status_color": "green" if unread > 0 else "gray",
                "avatar": initials,
                "unread": unread,
            })
        return {"threads": threads}

    # ─── /workspace/mail/triage ────────────────────────
    @api.model
    def get_triage(self):
        cr = self.env.cr
        cr.execute("""
            SELECT m.id, m.sender_name, m.sender_email, m.sender_domain,
                   m.subject, m.snippet, m.ai_category,
                   m.email_date, m.is_read, m.ai_action_required, m.ai_urgency,
                   m.lead_id
            FROM casafolino_mail_message m
            WHERE m.direction = 'inbound'
              AND m.is_deleted = false AND m.is_archived = false
              AND m.is_read = false
              AND m.state != 'auto_discard'
              AND m.email_date >= NOW() - INTERVAL '30 days'
            ORDER BY
              CASE WHEN m.ai_action_required = true THEN 0 ELSE 1 END,
              CASE WHEN m.ai_urgency = 'high' THEN 0 WHEN m.ai_urgency = 'medium' THEN 1 ELSE 2 END,
              m.email_date DESC
            LIMIT 10
        """)

        mails = []
        for row in cr.fetchall():
            tag_key, tag_label, tag_bg, tag_fg = _tag_for(row[6], row[4])
            age_days = (date.today() - row[7].date()).days if row[7] else 0

            mails.append({
                "id": row[0],
                "from_name": row[1] or "Sconosciuto",
                "from_email": row[2] or "",
                "subject": row[4] or "(nessun oggetto)",
                "preview": (row[5] or "")[:120],
                "tag": tag_key,
                "tag_label": tag_label,
                "tag_bg": tag_bg,
                "tag_fg": tag_fg,
                "when_relative": _relative_time(row[7]),
                "age_days": age_days,
                "action_required": row[9] or False,
                "urgency": row[10] or "normal",
                "linked_lead_id": row[11],
                "actions": ["reply", "to_lead", "to_task", "archive"],
            })
        return {"mails": mails}

    # ─── /workspace/mail/detail ────────────────────────
    @api.model
    def get_mail_detail(self, mail_id):
        cr = self.env.cr
        cr.execute("""
            SELECT m.id, m.sender_name, m.sender_email, m.sender_domain,
                   m.subject, m.body_html, m.body_plain, m.snippet,
                   m.ai_category, m.email_date, m.is_read,
                   m.thread_id, m.lead_id, m.partner_id,
                   m.ai_action_required, m.ai_urgency, m.ai_sentiment
            FROM casafolino_mail_message m
            WHERE m.id = %s
        """, [mail_id])
        row = cr.fetchone()
        if not row:
            return {"error": "Mail not found"}

        tag_key, tag_label, tag_bg, tag_fg = _tag_for(row[8], row[4])
        body = row[6] or _HTML_TAG_RE.sub('', row[5] or '').strip() or row[7] or ""

        # Thread history
        thread_history = []
        if row[11]:
            cr.execute("""
                SELECT m2.id, m2.sender_name, m2.subject, m2.snippet,
                       m2.email_date, m2.direction
                FROM casafolino_mail_message m2
                WHERE m2.thread_id = %s AND m2.id != %s
                ORDER BY m2.email_date DESC
                LIMIT 5
            """, [row[11], mail_id])
            for r2 in cr.fetchall():
                thread_history.append({
                    "id": r2[0],
                    "from_name": r2[1] or "—",
                    "subject": r2[2] or "",
                    "preview": (r2[3] or "")[:80],
                    "when": _relative_time(r2[4]),
                    "direction": r2[5] or "inbound",
                })

        # Suggested reply
        from_name = (row[1] or "").split()[0] if row[1] else ""
        template = _REPLY_TEMPLATES.get(tag_key, _REPLY_TEMPLATES["adm"])
        suggested = template.replace("{name}", from_name)

        # Chain
        chain = []
        if row[11]:
            cr.execute("SELECT COUNT(*) FROM casafolino_mail_message WHERE thread_id = %s", [row[11]])
            tc = cr.fetchone()[0] or 0
            chain.append({"label": f"Thread ({tc})", "icon": "fa-comments", "count": tc})
        if row[12]:
            chain.append({"label": "Lead collegato", "icon": "fa-bullseye", "count": 1})
        if row[13]:
            cr.execute("SELECT COUNT(*) FROM crm_lead WHERE partner_id = %s AND active = true", [row[13]])
            lc = cr.fetchone()[0] or 0
            if lc:
                chain.append({"label": f"Lead partner ({lc})", "icon": "fa-bullseye", "count": lc})

        return {
            "mail": {
                "id": row[0],
                "from_name": row[1] or "—",
                "from_email": row[2] or "",
                "from_company": (row[3] or "").replace(".", " ").title(),
                "subject": row[4] or "",
                "body": body[:2000],
                "tag": tag_key,
                "tag_label": tag_label,
                "tag_bg": tag_bg,
                "tag_fg": tag_fg,
                "when_relative": _relative_time(row[9]),
                "when_iso": row[9].isoformat() if row[9] else "",
                "unread": not row[10],
                "action_required": row[14] or False,
                "urgency": row[15] or "normal",
                "sentiment": row[16] or "",
            },
            "thread_history": thread_history,
            "suggested_reply": suggested,
            "chain": chain,
        }

    # ─── /workspace/mail/action ────────────────────────
    @api.model
    def execute_action(self, mail_id, action, params=None):
        params = params or {}
        cr = self.env.cr

        # Get mail info
        cr.execute("""
            SELECT sender_name, sender_email, subject, body_plain, snippet, partner_id
            FROM casafolino_mail_message WHERE id = %s
        """, [mail_id])
        row = cr.fetchone()
        if not row:
            return {"ok": False, "message": "Mail non trovata"}

        sender_name, sender_email, subject, body, snippet, partner_id = row

        if action == "to_lead":
            lead = self.env["crm.lead"].create({
                "name": subject or f"Lead da {sender_name}",
                "email_from": sender_email,
                "partner_name": sender_name or "",
                "description": body or snippet or "",
                "type": "opportunity",
            })
            return {"ok": True, "result_id": lead.id, "message": f"Lead #{lead.id} creato"}

        elif action == "to_task":
            # Find or create inbox project
            project = self.env["project.project"].search([("name", "ilike", "Inbox")], limit=1)
            if not project:
                project = self.env["project.project"].create({
                    "name": "Inbox",
                    "privacy_visibility": "employees",
                })
            task = self.env["project.task"].create({
                "name": subject or f"Task da {sender_name}",
                "project_id": project.id,
                "description": body or snippet or "",
            })
            return {"ok": True, "result_id": task.id, "message": f"Task #{task.id} creata"}

        elif action == "archive":
            cr.execute("UPDATE casafolino_mail_message SET is_archived = true WHERE id = %s", [mail_id])
            return {"ok": True, "message": "Mail archiviata"}

        elif action in ("schedule", "delegate"):
            return {"ok": False, "message": "Funzione in arrivo nelle prossime fasi"}

        return {"ok": False, "message": f"Azione '{action}' non riconosciuta"}

    # ─── KPIs ──────────────────────────────────────────
    @api.model
    def _kpis(self, cr):
        cr.execute("""
            SELECT
                (SELECT COUNT(*) FROM casafolino_mail_message
                 WHERE direction='inbound' AND is_read=false AND is_archived=false
                   AND is_deleted=false AND state!='auto_discard'
                   AND email_date >= NOW() - INTERVAL '30 days') AS pending,
                (SELECT COUNT(DISTINCT thread_id) FROM casafolino_mail_message
                 WHERE thread_id IS NOT NULL AND email_date >= NOW() - INTERVAL '30 days') AS threads,
                (SELECT COALESCE(ROUND(AVG(EXTRACT(EPOCH FROM (
                   (SELECT MIN(m2.email_date) FROM casafolino_mail_message m2
                    WHERE m2.thread_id=m.thread_id AND m2.direction='outbound'
                      AND m2.email_date > m.email_date)
                   - m.email_date)) / 3600), 1), 0)
                 FROM casafolino_mail_message m
                 WHERE m.direction='inbound'
                   AND m.email_date >= NOW() - INTERVAL '30 days'
                   AND EXISTS (SELECT 1 FROM casafolino_mail_message m2
                               WHERE m2.thread_id=m.thread_id AND m2.direction='outbound'
                                 AND m2.email_date > m.email_date)
                 ) AS avg_resp_hrs,
                (SELECT COUNT(*) FROM casafolino_mail_message
                 WHERE direction='inbound' AND email_date >= NOW() - INTERVAL '30 days'
                   AND (ai_action_required=true OR ai_urgency='high'
                        OR ai_category='commerciale')) AS important
        """)
        row = cr.fetchone()
        avg_h = float(row[2] or 0)
        if avg_h < 1:
            avg_str = f"{int(avg_h * 60)} min"
        elif avg_h < 24:
            avg_str = f"{avg_h:.1f} h"
        else:
            avg_str = f"{avg_h / 24:.1f} gg"

        return [
            {"id": "pending", "label": "Mail in sospeso", "value": str(row[0] or 0),
             "raw": int(row[0] or 0), "icon": "fa-envelope"},
            {"id": "threads", "label": "Thread attivi", "value": str(row[1] or 0),
             "raw": int(row[1] or 0), "icon": "fa-comments"},
            {"id": "avg_resp", "label": "Tempo medio risp.", "value": avg_str,
             "raw": float(avg_h), "icon": "fa-clock-o"},
            {"id": "important", "label": "Mail importanti", "value": str(row[3] or 0),
             "raw": int(row[3] or 0), "icon": "fa-star"},
        ]

    # ─── Macro ─────────────────────────────────────────
    @api.model
    def _macro_batch(self, cr):
        cr.execute("""
            WITH
              unread AS (
                SELECT COUNT(*) c FROM casafolino_mail_message
                WHERE direction='inbound' AND is_read=false AND is_archived=false
                  AND is_deleted=false AND email_date >= NOW() - INTERVAL '30 days'
              ),
              important AS (
                SELECT COUNT(*) c FROM casafolino_mail_message
                WHERE direction='inbound' AND email_date >= NOW() - INTERVAL '30 days'
                  AND (ai_action_required=true OR ai_urgency='high')
              ),
              lead_mail AS (
                SELECT COUNT(*) c FROM casafolino_mail_message
                WHERE direction='inbound' AND email_date >= NOW() - INTERVAL '30 days'
                  AND (ai_category='commerciale' OR ai_category='lead')
              ),
              ops_mail AS (
                SELECT COUNT(*) c FROM casafolino_mail_message
                WHERE direction='inbound' AND email_date >= NOW() - INTERVAL '30 days'
                  AND (ai_category='fornitore' OR ai_category='interno')
              ),
              threads AS (
                SELECT COUNT(DISTINCT thread_id) c FROM casafolino_mail_message
                WHERE thread_id IS NOT NULL AND email_date >= NOW() - INTERVAL '30 days'
              ),
              outbound AS (
                SELECT COUNT(*) c FROM casafolino_mail_message
                WHERE direction='outbound' AND email_date >= NOW() - INTERVAL '7 days'
              ),
              action_req AS (
                SELECT COUNT(*) c FROM casafolino_mail_message
                WHERE direction='inbound' AND ai_action_required=true
                  AND is_read=false AND email_date >= NOW() - INTERVAL '30 days'
              ),
              archived AS (
                SELECT COUNT(*) c FROM casafolino_mail_message
                WHERE is_archived=true AND email_date >= NOW() - INTERVAL '30 days'
              )
            SELECT unread.c, important.c, lead_mail.c, ops_mail.c,
                   threads.c, outbound.c, action_req.c, archived.c
            FROM unread, important, lead_mail, ops_mail,
                 threads, outbound, action_req, archived
        """)
        row = cr.fetchone()
        counts = [row[i] or 0 for i in range(8)]

        results = []
        for i, area in enumerate(_MAIL_MACRO):
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
            SELECT m.id, m.sender_name, m.subject, m.email_date, m.direction,
                   m.ai_category
            FROM casafolino_mail_message m
            WHERE m.email_date >= NOW() - INTERVAL '7 days'
              AND m.is_deleted = false
              AND m.state != 'auto_discard'
            ORDER BY m.email_date DESC
            LIMIT 10
        """)
        feed = []
        for row in cr.fetchall():
            direction = "ricevuta" if row[4] == "inbound" else "inviata"
            sender = row[1] or "Sconosciuto"
            subj = row[2] or ""
            if len(subj) > 60:
                subj = subj[:57] + "..."
            body = f"Mail {direction}: {subj}"

            parts = str(sender).split()
            initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else (parts[0][:2].upper() if parts else "??")

            feed.append({
                "id": row[0],
                "body": body,
                "date": row[3].isoformat() if row[3] else "",
                "author": sender,
                "initials": initials,
            })
        return feed
