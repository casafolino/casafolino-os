# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Home",
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "summary": "3 Scrivanie: Commerciale, Operativa, Admin",
    "author": "CasaFolino Srls",
    "depends": [
        "base", "web", "crm", "project", "account", "stock",
        "casafolino_mail", "casafolino_crm_export",
    ],
    "data": [
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_home/static/src/scrivania_commerciale/scrivania_commerciale.scss",
            "casafolino_home/static/src/scrivania_commerciale/scrivania_commerciale.xml",
            "casafolino_home/static/src/scrivania_commerciale/scrivania_commerciale.js",
            "casafolino_home/static/src/scrivania_operativa/scrivania_operativa.xml",
            "casafolino_home/static/src/scrivania_operativa/scrivania_operativa.js",
            "casafolino_home/static/src/scrivania_admin/scrivania_admin.xml",
            "casafolino_home/static/src/scrivania_admin/scrivania_admin.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "casafolino_home/static/description/icon.png",
}
