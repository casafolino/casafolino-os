# -*- coding: utf-8 -*-
{
    "name": "CasaFolino CRM Export",
    "version": "18.0.3.2.0",
    "category": "Sales/CRM",
    "summary": "CRM Export B2B — Pipeline, Scoring, Sequenze, Fiere, Campionature",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_export_stages.xml",
        "data/cf_export_lost_reasons.xml",
        "views/cf_export_views.xml",
        "views/cf_export_lead_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_crm_export/static/src/css/cf_crm_style.css",
            "casafolino_crm_export/static/src/xml/cf_crm_dashboard.xml",
            "casafolino_crm_export/static/src/js/cf_crm_dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
