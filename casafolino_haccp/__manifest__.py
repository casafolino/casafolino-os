# -*- coding: utf-8 -*-
{
    "name": "CasaFolino HACCP",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "HACCP Manager nativo Odoo 18",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "stock", "purchase", "product"],
    "data": [
        "security/cf_haccp_security.xml",
        "security/ir.model.access.csv",
        "data/cf_haccp_sequences.xml",
        "views/cf_haccp_receipt_views.xml",
        "views/cf_haccp_sp_views.xml",
        "views/cf_haccp_nc_views.xml",
        "views/cf_haccp_quarantine_views.xml",
        "views/cf_haccp_calibration_views.xml",
        "views/cf_haccp_document_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
