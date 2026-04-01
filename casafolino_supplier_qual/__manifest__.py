# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Supplier Qualification",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "summary": "Qualifica fornitori BRC/IFS",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "purchase", "stock"],
    "data": [
        "security/cf_supplier_qual_security.xml",
        "security/ir.model.access.csv",
        "views/cf_supplier_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_supplier_qual/static/src/xml/cf_supplier_dashboard.xml",
            "casafolino_supplier_qual/static/src/js/cf_supplier_dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
