# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Private Label",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Gestione clienti Private Label",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/cf_pl_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
