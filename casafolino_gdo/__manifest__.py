# -*- coding: utf-8 -*-
{
    "name": "CasaFolino GDO",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Pipeline GDO",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/cf_gdo_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
