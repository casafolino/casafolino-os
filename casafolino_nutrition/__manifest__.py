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
        "wizard/cf_nutrition_wizard_views.xml",
        "report/cf_nutrition_report.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "assets": {
        "web.assets_backend": [
            "casafolino_nutrition/static/src/xml/nutrition_chart.xml",
            "casafolino_nutrition/static/src/js/nutrition_chart.js",
        ],
    },
}
