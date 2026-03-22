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
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
