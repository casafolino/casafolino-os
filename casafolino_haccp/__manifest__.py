# -*- coding: utf-8 -*-
{
    "name": "CasaFolino HACCP",
    "version": "18.0.1.2.0",
    "category": "Manufacturing",
    "summary": "HACCP Manager — Schede Produzione, CCP, NC, Quarantena, Calibrazioni, Documenti",
    "author": "CasaFolino Srls",
    "website": "https://casafolino.com",
    "depends": ["base", "mail", "mrp", "stock", "purchase", "product"],
    "data": [
        "security/cf_haccp_security.xml",
        "security/ir.model.access.csv",
        "data/cf_haccp_sequences.xml",
        "data/cf_haccp_automation.xml",
        "views/cf_haccp_views_final.xml",
        "views/menus.xml",
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
