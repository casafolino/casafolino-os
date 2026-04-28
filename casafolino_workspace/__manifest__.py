# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Workspace",
    "version": "18.0.0.1.0",
    "category": "Productivity",
    "summary": "Scrivania operativa CasaFolino",
    "author": "CasaFolino Srls",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_workspace/static/src/css/cf_workspace_client.css",
            "casafolino_workspace/static/src/xml/cf_workspace_client.xml",
            "casafolino_workspace/static/src/js/cf_workspace_client.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "casafolino_workspace/static/description/icon.png",
}
