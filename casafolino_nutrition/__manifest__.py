# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Nutrition",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Valori nutrizionali da BoM",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/cf_nutrition_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "casafolino_nutrition/static/description/icon.png",
}
