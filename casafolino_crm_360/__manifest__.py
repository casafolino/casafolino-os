{
    "name": "CasaFolino CRM 360",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Dossier commerciale 360 nativo Odoo, senza dashboard JS custom",
    "author": "CasaFolino S.R.L.",
    "depends": [
        "crm",
        "project",
        "sale",
        "mail",
        "contacts",
        "documents",
        "casafolino_project",
        "casafolino_mail",
        "casafolino_crm_export",
        "casafolino_initiative_dashboard",
    ],
    "data": [
        "views/project_project_views.xml",
        "views/crm_lead_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_crm_360/static/src/scss/crm360_cockpit.scss",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
