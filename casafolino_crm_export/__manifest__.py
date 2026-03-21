# -*- coding: utf-8 -*-
{
    "name": "CasaFolino CRM Export",
    "version": "18.0.2.0.0",
    "category": "Sales/CRM",
    "summary": "CRM Export B2B — Pipeline, Scoring, Sequenze, Fiere",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_export_stages.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
