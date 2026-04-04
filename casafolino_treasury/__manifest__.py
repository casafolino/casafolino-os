# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Treasury",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Tesoreria e Cash Flow",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "account", "sale_management", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/cf_treasury_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_treasury/static/src/xml/cf_treasury_dashboard.xml",
            "casafolino_treasury/static/src/js/cf_treasury_dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "casafolino_treasury/static/description/icon.png",
}
