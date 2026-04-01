# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Home Dashboard",
    "version": "18.0.1.0.0",
    "category": "Extra Tools",
    "summary": "Home page OWL con KPI consolidati di tutti i moduli CasaFolino",
    "author": "CasaFolino Srls",
    "depends": ["base", "web", "mail"],
    "data": [
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_home/static/src/css/cf_home.css",
            "casafolino_home/static/src/xml/cf_home_dashboard.xml",
            "casafolino_home/static/src/js/cf_home_dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
