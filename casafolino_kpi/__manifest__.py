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
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
