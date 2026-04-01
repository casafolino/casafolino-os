# -*- coding: utf-8 -*-
{
    "name": "CasaFolino KPI Dashboard",
    "version": "18.0.1.0.0",
    "category": "Reporting",
    "summary": "Dashboard KPI unificata",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "purchase", "account", "mrp", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/cf_kpi_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_kpi/static/src/xml/cf_kpi_dashboard.xml",
            "casafolino_kpi/static/src/js/cf_kpi_dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "casafolino_kpi/static/description/icon.png",
}
