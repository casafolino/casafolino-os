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
        "data/cf_supplier_qual_cron.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
