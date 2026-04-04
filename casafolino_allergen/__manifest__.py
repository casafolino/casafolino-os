# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Allergeni",
    "version": "18.0.3.0.0",
    "category": "Manufacturing",
    "summary": "Allergeni da distinta base — 14 EU + USA/Canada/AUS, match automatico, testo etichetta",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_allergen_14eu.xml",
        "data/cf_allergen_keywords.xml",
        "data/cf_allergen_extra.xml",
        "data/cf_allergen_categories.xml",
        "data/cf_allergen_world.xml",
        "views/cf_allergen_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "casafolino_allergen/static/description/icon.png",
}
