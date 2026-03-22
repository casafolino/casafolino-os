# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Mock Recall",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Mock Recall BRC/IFS",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "stock", "purchase", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/cf_recall_views.xml",
        "views/menus.xml",
        "wizard/cf_recall_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
