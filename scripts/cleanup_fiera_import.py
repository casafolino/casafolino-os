#!/usr/bin/env python3
"""
Cleanup fiera import — rimuove lead creati con un tag specifico.
Archivia prima, poi unlink, con conferma interattiva.

Usage:
  python3 scripts/cleanup_fiera_import.py --tag "__FIERA_IMPORT_20260510__"
"""
import argparse
import json
import os
import sys
import time

import requests

ODOO_URL = "https://erp.casafolino.com"
JSONRPC_URL = f"{ODOO_URL}/jsonrpc"
DB_NAME = "folinofood"
RPC_DELAY = 0.1

_rpc_id = 0
_uid = None
_api_key = None
_session_id = None


def _jsonrpc(url, method, params, session_id=None):
    global _rpc_id
    _rpc_id += 1
    headers = {"Content-Type": "application/json"}
    if session_id:
        headers["Cookie"] = f"session_id={session_id}"
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": _rpc_id}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if result.get("error"):
        err = result["error"]
        msg = err.get("data", {}).get("message", "") or err.get("message", str(err))
        raise Exception(f"JSON-RPC error: {msg}")
    return result.get("result")


def authenticate(db, login, api_key):
    result = _jsonrpc(
        f"{ODOO_URL}/web/session/authenticate", "call",
        {"db": db, "login": login, "password": api_key},
    )
    uid = result.get("uid")
    if not uid:
        raise Exception("Authentication failed")
    return uid, result.get("session_id", "")


def call_kw(model, method, args=None, kwargs=None):
    time.sleep(RPC_DELAY)
    return _jsonrpc(
        JSONRPC_URL, "call",
        {
            "service": "object", "method": "execute_kw",
            "args": [DB_NAME, _uid, _api_key, model, method, args or [], kwargs or {}],
        },
        session_id=_session_id,
    )


def main():
    global _uid, _api_key, _session_id

    parser = argparse.ArgumentParser(description="Cleanup lead importati per tag")
    parser.add_argument("--tag", required=True, help="Nome tag batch (es. __FIERA_IMPORT_20260510__)")
    parser.add_argument("--force", action="store_true", help="Skip conferma interattiva")
    args = parser.parse_args()

    _api_key = os.environ.get("ODOO_API_TOKEN", "")
    if not _api_key:
        print("ERRORE: env var ODOO_API_TOKEN non impostata")
        sys.exit(1)

    # Auth
    _uid, _session_id = authenticate(DB_NAME, "antonio@casafolino.com", _api_key)
    print(f"Autenticato: uid={_uid}")

    # Find tag
    tags = call_kw("crm.tag", "search_read", [[("name", "=", args.tag)]], {"fields": ["id", "name"]})
    if not tags:
        print(f"Tag '{args.tag}' non trovato. Nessun lead da rimuovere.")
        sys.exit(0)

    tag_id = tags[0]["id"]
    print(f"Tag trovato: id={tag_id}")

    # Find leads with this tag (active + archived)
    lead_ids_active = call_kw("crm.lead", "search", [[("tag_ids", "in", [tag_id]), ("active", "=", True)]])
    lead_ids_archived = call_kw("crm.lead", "search", [[("tag_ids", "in", [tag_id]), ("active", "=", False)]])
    all_lead_ids = (lead_ids_active or []) + (lead_ids_archived or [])

    if not all_lead_ids:
        print(f"Nessun lead trovato con tag '{args.tag}'.")
        sys.exit(0)

    print(f"\nTrovati {len(all_lead_ids)} lead con tag '{args.tag}':")
    print(f"  - Attivi:    {len(lead_ids_active or [])}")
    print(f"  - Archiviati: {len(lead_ids_archived or [])}")

    # Show first few
    sample = call_kw("crm.lead", "read", [all_lead_ids[:5]], {"fields": ["id", "name", "active"]})
    for s in sample:
        print(f"  #{s['id']} — {s['name']} (active={s['active']})")
    if len(all_lead_ids) > 5:
        print(f"  ... e altri {len(all_lead_ids) - 5}")

    # Confirm
    if not args.force:
        answer = input(f"\nCancellare TUTTI i {len(all_lead_ids)} lead? (digita 'SI' per confermare): ")
        if answer.strip() != "SI":
            print("Annullato.")
            sys.exit(0)

    # Archive active leads first
    if lead_ids_active:
        print(f"Archiviazione {len(lead_ids_active)} lead attivi...")
        call_kw("crm.lead", "write", [lead_ids_active, {"active": False}])

    # Unlink all
    print(f"Eliminazione {len(all_lead_ids)} lead...")
    # Unlink in batches of 50
    for i in range(0, len(all_lead_ids), 50):
        batch = all_lead_ids[i:i+50]
        call_kw("crm.lead", "unlink", [batch])
        print(f"  Eliminati {min(i+50, len(all_lead_ids))}/{len(all_lead_ids)}")

    # Cleanup tag
    remaining = call_kw("crm.lead", "search_count", [[("tag_ids", "in", [tag_id])]])
    if remaining == 0:
        call_kw("crm.tag", "unlink", [[tag_id]])
        print(f"Tag '{args.tag}' rimosso (nessun lead residuo).")

    print(f"\nCleanup completato. {len(all_lead_ids)} lead eliminati.")


if __name__ == "__main__":
    main()
