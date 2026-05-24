# -*- coding: utf-8 -*-
{
    "name": "CasaFolino B2B Website Template",
    "version": "18.0.1.0.0",
    "category": "Website",
    "summary": "Template Website Odoo per il portale B2B CasaFolino.",
    "author": "CasaFolino S.r.l.",
    "depends": [
        "website_sale",
        "portal",
        "casafolino_b2b_portal",
    ],
    "data": [
        "views/website_layout.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "casafolino_b2b_theme/static/src/scss/theme.scss",
        ],
    },
    "post_init_hook": "_post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
