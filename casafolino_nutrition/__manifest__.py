# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Nutrition",
    "version": "18.0.2.0.0",
    "category": "Manufacturing",
    "summary": "Etichette nutrizionali da distinta base — EU, USA, Canada, AUS, UK",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_nutrition_regulations.xml",
        "data/cf_nutrition_cron.xml",
        "views/cf_nutrition_views.xml",
        "views/cf_nutrition_inherit_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_nutrition/static/src/xml/cf_nutrition_chart.xml",
            "casafolino_nutrition/static/src/js/cf_nutrition_chart.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "icon": "casafolino_nutrition/static/description/icon.png",
}
