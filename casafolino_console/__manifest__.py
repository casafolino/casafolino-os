{
    "name": "CasaFolino Console (link)",
    "version": "18.0.1.0.0",
    "summary": "Voce di menu che apre la Console commerciale (Next.js, sola lettura).",
    "description": """
Aggiunge una app/menu in Odoo che apre la Console commerciale CasaFolino
servita dietro nginx su /console. Solo un'azione act_url + menuitem con icona:
nessun modello, nessuna scrittura. Pensato per STAGE.
""",
    "category": "Sales/CRM",
    "author": "CasaFolino",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [
        "views/console_menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
