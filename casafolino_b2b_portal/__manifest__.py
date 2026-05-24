# -*- coding: utf-8 -*-
{
    "name": "CasaFolino B2B Portal",
    "version": "18.0.1.0.0",
    "category": "Website/eCommerce",
    "summary": "Portale B2B CasaFolino con approvazione clienti, prezzi riservati e minimi ordine.",
    "author": "CasaFolino S.r.l.",
    "depends": ["website_sale", "sale_management", "contacts", "portal", "auth_signup", "casafolino_pipeline_control"],
    "data": [
        "data/website.xml",
        "data/mail_templates.xml",
        "views/res_partner_views.xml",
        "views/product_template_views.xml",
        "views/templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "casafolino_b2b_portal/static/src/css/b2b.css",
            "casafolino_b2b_portal/static/src/js/b2b.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
