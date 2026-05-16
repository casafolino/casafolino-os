#!/usr/bin/env python3
"""
Import contatti agenda → crm.lead con arricchimento da Odoo.
Connessione JSON-RPC a erp.casafolino.com. Token da env var ODOO_API_TOKEN.

Usage:
  python3 scripts/import_fiera_contatti.py \
    --csv scripts/contatti_agenda_progetti.csv \
    --fiera "Agenda Antonio - Settembre 2025" \
    --salesperson Antonio \
    --dry-run
"""
import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from datetime import datetime

# ─── Config ────────────────────────────────────────────────────
ODOO_URL = "https://erp.casafolino.com"
JSONRPC_URL = f"{ODOO_URL}/jsonrpc"
DB_NAME = "folinofood"

SALESPERSON_LOGINS = {
    "antonio": "antonio@casafolino.com",
    "josefina": "josefina.lazzaro@casafolino.com",
    "martina": "martina.sinopoli@casafolino.com",
}

RPC_DELAY = 0.1  # 100ms between calls

# ─── JSON-RPC helpers ─────────────────────────────────────────
_rpc_id = 0


def _jsonrpc(url, method, params, session_id=None):
    """Low-level JSON-RPC call."""
    import requests
    global _rpc_id
    _rpc_id += 1
    headers = {"Content-Type": "application/json"}
    if session_id:
        headers["Cookie"] = f"session_id={session_id}"
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": _rpc_id,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if result.get("error"):
        err = result["error"]
        msg = err.get("data", {}).get("message", "") or err.get("message", str(err))
        raise Exception(f"JSON-RPC error: {msg}")
    return result.get("result")


def authenticate(db, login, api_key):
    """Authenticate via JSON-RPC and return (uid, session_id)."""
    result = _jsonrpc(
        f"{ODOO_URL}/web/session/authenticate",
        "call",
        {"db": db, "login": login, "password": api_key},
    )
    uid = result.get("uid")
    if not uid:
        raise Exception("Authentication failed — check ODOO_API_TOKEN and login")
    session_id = result.get("session_id", "")
    return uid, session_id


def call_kw(session_id, model, method, args=None, kwargs=None):
    """Call a model method via JSON-RPC."""
    time.sleep(RPC_DELAY)
    return _jsonrpc(
        JSONRPC_URL,
        "call",
        {
            "service": "object",
            "method": "execute_kw",
            "args": [DB_NAME, _uid, _api_key, model, method, args or [], kwargs or {}],
        },
        session_id=_session_id,
    )


def search_read(model, domain, fields, limit=0, order=""):
    """Convenience wrapper."""
    kwargs = {"fields": fields, "limit": limit}
    if order:
        kwargs["order"] = order
    return call_kw(_session_id, model, "search_read", [domain], kwargs)


def search_count(model, domain):
    return call_kw(_session_id, model, "search_count", [domain])


def create_record(model, vals):
    return call_kw(_session_id, model, "create", [vals])


# ─── Helpers ───────────────────────────────────────────────────

def mask_email(email):
    """a***o@dom.com"""
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked = local[0] + "*"
    else:
        masked = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked}@{domain}"


def build_description_html(row, partner_info, mail_info, candidates):
    """Build HTML description for the lead."""
    parts = []
    parts.append("<h3>Import Agenda</h3>")
    parts.append("<table style='border-collapse:collapse;'>")

    def tr(label, value):
        return (
            f"<tr><td style='padding:2px 8px;font-weight:bold;'>{label}</td>"
            f"<td style='padding:2px 8px;'>{value or '—'}</td></tr>"
        )

    parts.append(tr("Giorno agenda", row.get("giorno_agenda", "")))
    parts.append(tr("Fiera origine", row.get("fiera_origine", "")))
    parts.append(tr("Canale", row.get("canale", "")))
    parts.append(tr("Paese CSV", row.get("paese", "")))
    parts.append(tr("Assegnato a", row.get("assegnato_a", "")))
    parts.append(tr("Stato", row.get("stato", "")))
    parts.append(tr("Note", row.get("note", "")))
    parts.append("</table>")

    # Partner match info
    parts.append("<h4>Match Partner Odoo</h4>")
    if partner_info:
        parts.append(f"<p>Partner trovato: <b>{partner_info['name']}</b> (id={partner_info['id']})</p>")
        if partner_info.get("email"):
            parts.append(f"<p>Email: {partner_info['email']}</p>")
        if partner_info.get("phone"):
            parts.append(f"<p>Telefono: {partner_info['phone']}</p>")
        if partner_info.get("website"):
            parts.append(f"<p>Website: {partner_info['website']}</p>")
    elif candidates:
        parts.append(f"<p><b>Match multipli ({len(candidates)} candidati):</b></p><ul>")
        for c in candidates[:10]:
            email_display = mask_email(c.get("email", ""))
            parts.append(
                f"<li>{c['name']} (id={c['id']}) — {email_display}</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p><i>Nessun match partner trovato in Odoo.</i></p>")

    # Last email info
    if mail_info:
        parts.append("<h4>Ultimo contatto email</h4>")
        parts.append(f"<p>Data: {mail_info['date']}</p>")
        parts.append(f"<p>Oggetto: {mail_info['subject']}</p>")

    return "\n".join(parts)


# ─── Lookup helpers ────────────────────────────────────────────

def lookup_salesperson(name):
    """Resolve salesperson name → user_id."""
    login = SALESPERSON_LOGINS.get(name.lower())
    if not login:
        raise Exception(f"Salesperson '{name}' sconosciuto. Validi: {list(SALESPERSON_LOGINS.keys())}")
    users = search_read("res.users", [("login", "=", login)], ["id", "name"], limit=1)
    if not users:
        raise Exception(f"User con login '{login}' non trovato in Odoo")
    return users[0]["id"], users[0]["name"]


def lookup_team():
    """Find CRM Export team."""
    teams = search_read("crm.team", [("name", "ilike", "Export")], ["id", "name"], limit=1)
    if not teams:
        # fallback: first team
        teams = search_read("crm.team", [], ["id", "name"], limit=1)
        if not teams:
            raise Exception("Nessun crm.team trovato in Odoo")
        _logger.warning("Team 'Export' non trovato, uso: %s", teams[0]["name"])
    return teams[0]["id"], teams[0]["name"]


def lookup_stage():
    """Find first stage (Qualifica or lowest sequence)."""
    stages = search_read(
        "crm.stage",
        [("name", "ilike", "Qualifica")],
        ["id", "name"],
        limit=1,
    )
    if not stages:
        stages = search_read("crm.stage", [], ["id", "name"], limit=1, order="sequence asc")
        if not stages:
            raise Exception("Nessun crm.stage trovato in Odoo")
        _logger.warning("Stage 'Qualifica' non trovato, uso: %s", stages[0]["name"])
    return stages[0]["id"], stages[0]["name"]


def get_or_create_tag(tag_name):
    """Get or create a crm.tag by name."""
    tags = search_read("crm.tag", [("name", "=", tag_name)], ["id"], limit=1)
    if tags:
        return tags[0]["id"]
    return create_record("crm.tag", {"name": tag_name})


def lookup_country(country_name):
    """Try to match country from CSV value."""
    if not country_name or not country_name.strip():
        return None
    name = country_name.strip()
    # Try common mappings
    COUNTRY_MAP = {
        "italia": "IT", "italy": "IT", "it": "IT",
        "francia": "FR", "france": "FR", "fr": "FR",
        "germania": "DE", "germany": "DE", "de": "DE",
        "austria": "AT", "at": "AT",
        "spagna": "ES", "spain": "ES", "es": "ES",
        "svizzera": "CH", "switzerland": "CH", "ch": "CH",
        "uk": "GB", "regno unito": "GB", "inghilterra": "GB",
        "usa": "US", "stati uniti": "US", "us": "US",
        "marocco": "MA", "morocco": "MA", "ma": "MA",
        "arabia saudita": "SA", "saudi arabia": "SA", "sa": "SA",
        "brasile": "BR", "brazil": "BR", "br": "BR",
        "canada": "CA", "ca": "CA",
        "giappone": "JP", "japan": "JP", "jp": "JP",
        "cina": "CN", "china": "CN", "cn": "CN",
        "corea": "KR", "korea": "KR", "kr": "KR",
        "australia": "AU", "au": "AU",
        "portogallo": "PT", "portugal": "PT", "pt": "PT",
        "grecia": "GR", "greece": "GR", "gr": "GR",
        "polonia": "PL", "poland": "PL", "pl": "PL",
        "romania": "RO", "ro": "RO",
        "olanda": "NL", "paesi bassi": "NL", "netherlands": "NL", "nl": "NL",
        "belgio": "BE", "belgium": "BE", "be": "BE",
        "svezia": "SE", "sweden": "SE", "se": "SE",
        "norvegia": "NO", "norway": "NO",
        "danimarca": "DK", "denmark": "DK", "dk": "DK",
        "finlandia": "FI", "finland": "FI", "fi": "FI",
        "irlanda": "IE", "ireland": "IE", "ie": "IE",
        "turchia": "TR", "turkey": "TR", "tr": "TR",
        "emirati": "AE", "uae": "AE", "dubai": "AE",
        "egitto": "EG", "egypt": "EG", "eg": "EG",
        "sudafrica": "ZA", "south africa": "ZA", "za": "ZA",
        "messico": "MX", "mexico": "MX", "mx": "MX",
        "argentina": "AR", "ar": "AR",
        "cile": "CL", "chile": "CL", "cl": "CL",
        "colombia": "CO", "co": "CO",
        "peru": "PE", "perù": "PE",
        "india": "IN",
        "singapore": "SG",
        "hong kong": "HK",
        "taiwan": "TW",
        "malesia": "MY", "malaysia": "MY",
        "tailandia": "TH", "thailand": "TH",
        "vietnam": "VN",
        "indonesia": "ID",
        "filippine": "PH", "philippines": "PH",
        "nuova zelanda": "NZ", "new zealand": "NZ",
        "israele": "IL", "israel": "IL",
        "libano": "LB", "lebanon": "LB",
        "giordania": "JO", "jordan": "JO",
        "tunisia": "TN",
        "algeria": "DZ",
        "libia": "LY", "libya": "LY",
        "croazia": "HR", "croatia": "HR",
        "slovenia": "SI",
        "serbia": "RS",
        "ungheria": "HU", "hungary": "HU",
        "repubblica ceca": "CZ", "czech republic": "CZ", "czechia": "CZ",
        "slovacchia": "SK", "slovakia": "SK",
        "bulgaria": "BG",
        "lituania": "LT", "lithuania": "LT",
        "lettonia": "LV", "latvia": "LV",
        "estonia": "EE",
        "cipro": "CY", "cyprus": "CY",
        "malta": "MT",
        "lussemburgo": "LU", "luxembourg": "LU",
        "islanda": "IS", "iceland": "IS",
    }
    code = COUNTRY_MAP.get(name.lower())
    if not code:
        # Try direct 2-letter code
        if len(name) == 2:
            code = name.upper()
        else:
            return None
    countries = search_read("res.country", [("code", "=", code)], ["id"], limit=1)
    return countries[0]["id"] if countries else None


# ─── Match pipeline ────────────────────────────────────────────

def match_partner(nome):
    """Step A: match res.partner by name."""
    domain = [
        ("name", "ilike", nome),
        "|", ("is_company", "=", True), ("parent_id", "=", False),
    ]
    partners = search_read(
        "res.partner",
        domain,
        ["id", "name", "email", "phone", "mobile", "country_id", "website", "lang", "vat"],
        limit=20,
    )
    return partners


def match_last_emails(partner_id):
    """Step B: find last emails for partner."""
    messages = search_read(
        "mail.message",
        [("res_id", "=", partner_id), ("model", "=", "res.partner"), ("message_type", "in", ["email", "email_outgoing"])],
        ["date", "subject", "email_from"],
        limit=5,
        order="date desc",
    )
    return messages


def match_existing_leads(nome):
    """Step C: check existing crm.lead by name."""
    # Active leads
    active = search_read(
        "crm.lead",
        [("name", "ilike", nome), ("active", "=", True)],
        ["id", "name", "stage_id"],
        limit=5,
    )
    # Archived leads
    archived = search_read(
        "crm.lead",
        [("name", "ilike", nome), ("active", "=", False)],
        ["id", "name", "stage_id"],
        limit=5,
    )
    return active, archived


# ─── Main ──────────────────────────────────────────────────────

_uid = None
_api_key = None
_session_id = None
_logger = logging.getLogger("import_fiera")


def main():
    global _uid, _api_key, _session_id

    parser = argparse.ArgumentParser(description="Import contatti agenda → crm.lead con arricchimento Odoo")
    parser.add_argument("--csv", required=True, help="Path al file CSV")
    parser.add_argument("--fiera", default="Agenda Fiera", help="Nome fiera origine (default: Agenda Fiera)")
    parser.add_argument("--salesperson", default="Antonio", help="Nome salesperson: Antonio, Josefina, Martina")
    parser.add_argument("--tag", default="", help="Tag batch import (default: auto __FIERA_IMPORT_YYYYMMDD__)")
    parser.add_argument("--dry-run", action="store_true", help="Esegui matching senza creare record")
    parser.add_argument("--log-file", default="", help="Path log file (default: scripts/logs/import_fiera_YYYYMMDD_HHMM.log)")
    args = parser.parse_args()

    # Validate CSV
    if not os.path.isfile(args.csv):
        print(f"ERRORE: file CSV non trovato: {args.csv}")
        sys.exit(1)

    # API token
    _api_key = os.environ.get("ODOO_API_TOKEN", "")
    if not _api_key:
        print("ERRORE: env var ODOO_API_TOKEN non impostata. Esegui: export ODOO_API_TOKEN='...'")
        sys.exit(1)

    # Tag
    now = datetime.utcnow()
    tag_name = args.tag or f"__FIERA_IMPORT_{now.strftime('%Y%m%d')}__"

    # Log setup
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = args.log_file or os.path.join(log_dir, f"import_fiera_{now.strftime('%Y%m%d_%H%M')}.log")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.setLevel(logging.INFO)
    _logger.addHandler(file_handler)
    _logger.addHandler(console_handler)

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    _logger.info("=" * 60)
    _logger.info(f"IMPORT FIERA CONTATTI — {mode}")
    _logger.info(f"CSV: {args.csv}")
    _logger.info(f"Fiera: {args.fiera}")
    _logger.info(f"Salesperson: {args.salesperson}")
    _logger.info(f"Tag: {tag_name}")
    _logger.info("=" * 60)

    # ─── Authenticate ──────────────────────────────────────────
    _logger.info("Connessione a Odoo...")
    try:
        login = SALESPERSON_LOGINS.get(args.salesperson.lower(), "antonio@casafolino.com")
        _uid, _session_id = authenticate(DB_NAME, login, _api_key)
        _logger.info(f"Autenticato: uid={_uid}")
    except Exception as e:
        _logger.error(f"BLOCKER: autenticazione fallita — {e}")
        sys.exit(1)

    # ─── Verify connectivity ───────────────────────────────────
    try:
        test = search_read("crm.lead", [], ["id", "name"], limit=1)
        _logger.info(f"Connessione OK — test lead: {test[0]['name'] if test else 'empty'}")
    except Exception as e:
        _logger.error(f"BLOCKER: query crm.lead fallita — {e}")
        sys.exit(1)

    # ─── Lookups ───────────────────────────────────────────────
    try:
        user_id, user_name = lookup_salesperson(args.salesperson)
        _logger.info(f"Salesperson: {user_name} (id={user_id})")
    except Exception as e:
        _logger.error(f"BLOCKER: {e}")
        sys.exit(1)

    try:
        team_id, team_name = lookup_team()
        _logger.info(f"Team: {team_name} (id={team_id})")
    except Exception as e:
        _logger.error(f"BLOCKER: {e}")
        sys.exit(1)

    try:
        stage_id, stage_name = lookup_stage()
        _logger.info(f"Stage: {stage_name} (id={stage_id})")
    except Exception as e:
        _logger.error(f"BLOCKER: {e}")
        sys.exit(1)

    # ─── Tags ──────────────────────────────────────────────────
    if not args.dry_run:
        tag_fiera_id = get_or_create_tag(args.fiera)
        tag_batch_id = get_or_create_tag(tag_name)
        _logger.info(f"Tag fiera: id={tag_fiera_id}")
        _logger.info(f"Tag batch: id={tag_batch_id}")
    else:
        tag_fiera_id = None
        tag_batch_id = None
        _logger.info("DRY-RUN: tag non creati")

    _logger.info("-" * 60)

    # ─── Read CSV ──────────────────────────────────────────────
    with open(args.csv, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    _logger.info(f"Righe CSV: {len(rows)}")
    _logger.info("-" * 60)

    # ─── Process rows ─────────────────────────────────────────
    stats = {"created": 0, "created_no_match": 0, "created_multi": 0, "skipped": 0, "error": 0}
    country_cache = {}

    for i, row in enumerate(rows, 1):
        nome = (row.get("nome") or "").strip()
        if not nome:
            _logger.warning(f"[{i}] SKIP — riga senza nome")
            continue

        try:
            # Step A: match partner
            partners = match_partner(nome)
            partner_info = None
            candidates = []

            if len(partners) == 1:
                partner_info = partners[0]
                match_status = "unique"
            elif len(partners) > 1:
                candidates = partners
                match_status = "multiple"
            else:
                match_status = "none"

            # Step B: last emails (only if unique partner)
            mail_info = None
            if partner_info:
                messages = match_last_emails(partner_info["id"])
                if messages:
                    mail_info = {
                        "date": messages[0]["date"],
                        "subject": messages[0].get("subject", ""),
                    }

            # Step C: existing leads
            active_leads, archived_leads = match_existing_leads(nome)

            if active_leads:
                existing_id = active_leads[0]["id"]
                _logger.info(
                    f"[SKIPPED_DUPLICATE] {nome} | existing_lead_id={existing_id} | "
                    f"partner_match={partner_info['id'] if partner_info else 'none'}"
                )
                stats["skipped"] += 1
                continue

            # ─── Build lead vals ───────────────────────────────
            partner_id = partner_info["id"] if partner_info else False
            email_from = (partner_info or {}).get("email", "") or ""
            phone = (partner_info or {}).get("phone", "") or ""
            mobile = (partner_info or {}).get("mobile", "") or ""

            # Country: from partner, else from CSV
            country_id = False
            if partner_info and partner_info.get("country_id"):
                country_id = partner_info["country_id"][0] if isinstance(partner_info["country_id"], list) else partner_info["country_id"]
            else:
                csv_country = (row.get("paese") or "").strip()
                if csv_country:
                    if csv_country not in country_cache:
                        country_cache[csv_country] = lookup_country(csv_country)
                    country_id = country_cache[csv_country] or False

            description = build_description_html(row, partner_info, mail_info, candidates)

            # Salesperson override from CSV if present
            row_salesperson = (row.get("assegnato_a") or "").strip().lower()
            lead_user_id = user_id
            if row_salesperson and row_salesperson in SALESPERSON_LOGINS:
                try:
                    lead_user_id, _ = lookup_salesperson(row_salesperson)
                except Exception:
                    lead_user_id = user_id

            vals = {
                "name": nome,
                "partner_id": partner_id,
                "email_from": email_from,
                "phone": phone,
                "mobile": mobile,
                "country_id": country_id,
                "user_id": lead_user_id,
                "team_id": team_id,
                "stage_id": stage_id,
                "description": description,
                "referred": "Agenda Antonio - import automatico",
                "type": "lead",
            }

            if not args.dry_run:
                vals["tag_ids"] = [(4, tag_fiera_id), (4, tag_batch_id)]

            # Log line
            status = {
                "unique": "CREATED",
                "none": "CREATED_NO_MATCH",
                "multiple": "CREATED_MULTI_MATCH",
            }[match_status]

            log_line = (
                f"[{status}] {nome} | "
                f"partner_match={'id=' + str(partner_info['id']) if partner_info else match_status} | "
                f"email={mask_email(email_from)} | "
                f"last_contact={mail_info['date'] if mail_info else 'none'} | "
            )

            if args.dry_run:
                _logger.info(f"{log_line}lead_id=DRY_RUN | note=would create")
            else:
                lead_id = create_record("crm.lead", vals)
                _logger.info(f"{log_line}lead_id={lead_id}")

                # Add chatter note if archived leads exist
                if archived_leads:
                    archived_note = "Lead archiviati esistenti: " + ", ".join(
                        f"#{a['id']} ({a['name']})" for a in archived_leads[:5]
                    )
                    try:
                        call_kw(_session_id, "crm.lead", "message_post", [lead_id], {
                            "body": archived_note,
                            "message_type": "comment",
                            "subtype_xmlid": "mail.mt_note",
                        })
                    except Exception:
                        pass  # non-critical

            stats[{
                "CREATED": "created",
                "CREATED_NO_MATCH": "created_no_match",
                "CREATED_MULTI_MATCH": "created_multi",
            }[status]] += 1

        except Exception as e:
            _logger.error(f"[ERROR] {nome} | {e}")
            stats["error"] += 1

    # ─── Summary ───────────────────────────────────────────────
    total = sum(stats.values())
    _logger.info("=" * 60)
    _logger.info(f"RIEPILOGO {'(DRY-RUN)' if args.dry_run else ''}")
    _logger.info(f"  Totale righe:        {len(rows)}")
    _logger.info(f"  Processate:          {total}")
    _logger.info(f"  Creati (match):      {stats['created']}")
    _logger.info(f"  Creati (no match):   {stats['created_no_match']}")
    _logger.info(f"  Creati (multi):      {stats['created_multi']}")
    _logger.info(f"  Skipped duplicati:   {stats['skipped']}")
    _logger.info(f"  Errori:              {stats['error']}")
    _logger.info(f"  Tag batch:           {tag_name}")
    _logger.info(f"  Log file:            {log_path}")
    _logger.info("=" * 60)

    if stats["error"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
