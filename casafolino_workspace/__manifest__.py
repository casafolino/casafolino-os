# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Workspace",
    "version": "18.0.0.3.0",
    "category": "Productivity",
    "summary": "Scrivania operativa CasaFolino",
    "author": "CasaFolino Srls",
    "depends": ["base", "web", "mail", "calendar", "crm", "project", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_workspace/static/src/css/cf_workspace_client.css",
            "casafolino_workspace/static/src/xml/cf_workspace_client.xml",
            "casafolino_workspace/static/src/js/components/workspace_hero.js",
            "casafolino_workspace/static/src/js/components/workspace_kpis.js",
            "casafolino_workspace/static/src/js/components/workspace_macro.js",
            "casafolino_workspace/static/src/js/components/workspace_work.js",
            "casafolino_workspace/static/src/js/components/workspace_detail.js",
            "casafolino_workspace/static/src/js/components/workspace_feed.js",
            "casafolino_workspace/static/src/css/workspace_lead.css",
            "casafolino_workspace/static/src/js/lead/workspace_lead.js",
            "casafolino_workspace/static/src/xml/workspace_lead.xml",
            "casafolino_workspace/static/src/js/cf_workspace_client.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "casafolino_workspace/static/description/icon.png",
}
