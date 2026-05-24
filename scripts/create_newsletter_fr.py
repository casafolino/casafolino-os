#!/usr/bin/env python3
"""
Create a mailing.mailing draft targeting French contacts.
Does NOT send — leaves in state='draft'.
"""
import xmlrpc.client
import os

# --- Config ---
URL = os.environ.get("ODOO_URL", "https://erp.casafolino.com")
DB = os.environ.get("ODOO_DB", "folinofood")
USER = os.environ.get("ODOO_USER", "antonio@casafolino.com")
PASSWORD = os.environ.get("ODOO_PASSWORD", "")

if not PASSWORD:
    raise SystemExit("Set ODOO_PASSWORD env var")

# --- Connect ---
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PASSWORD, {})
if not uid:
    raise SystemExit("Authentication failed")

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def execute(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs)


# --- Domain: FR contacts, valid email, not blacklisted, active ---
# Odoo 18 mailing_domain is stored as string repr of domain list
FRANCE_ID = 75
domain_str = str([
    ("country_id", "=", FRANCE_ID),
    ("email", "!=", False),
    ("is_blacklisted", "=", False),
])

# Count recipients via res.partner
partner_count = execute(
    "res.partner", "search_count",
    [
        ("country_id", "=", FRANCE_ID),
        ("email", "!=", False),
        ("is_blacklisted", "=", False),
    ],
)
print(f"Target recipients (res.partner, FR): {partner_count}")

# --- Create mailing draft ---
mailing_id = execute(
    "mailing.mailing", "create",
    [{
        "subject": "Newsletter Casa Folino — Francia",
        "mailing_model_id": execute(
            "ir.model", "search",
            [("model", "=", "res.partner")],
            limit=1,
        )[0],
        "mailing_domain": domain_str,
        "body_html": """
<div style="max-width:600px;margin:0 auto;font-family:Arial,sans-serif;">
    <h2>Bonjour!</h2>
    <p>Bienvenue dans la newsletter de <strong>Casa Folino</strong>.</p>
    <p>Contenu à personnaliser avant l'envoi.</p>
    <br/>
    <p>Cordialement,<br/>L'équipe Casa Folino</p>
</div>
""",
        "reply_to_mode": "update",
    }],
)

print(f"\nMailing created!")
print(f"  ID:    {mailing_id}")
print(f"  URL:   {URL}/odoo/mass-mailing/{mailing_id}")
print(f"  State: draft")
print(f"  Recipients: {partner_count}")
