# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Allergeni",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Gestione 14 allergeni UE — Reg. 1169/2011",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_allergen_14eu.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
