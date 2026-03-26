# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Mail",
    "version": "18.0.1.0.0",
    "category": "Discuss",
    "summary": "Client email integrato — inbox personali e condivise con Gmail OAuth2",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "google_gmail"],
    "data": [
        "security/ir.model.access.csv",
        "views/cf_mail_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_mail/static/src/js/cf_mail_client.js",
            "casafolino_mail/static/src/css/cf_mail_client.css",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
