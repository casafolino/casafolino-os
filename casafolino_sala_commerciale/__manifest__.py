# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Sala Commerciale",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Sala Controllo Commerciale v8 affiancata a Odoo",
    "author": "CasaFolino Srls",
    "depends": [
        "base",
        "web",
        "crm",
        "mail",
        "contacts",
        "project",
        "casafolino_home",
        "casafolino_mail",
        "casafolino_crm_export",
    ],
    "data": [
        "views/sala_commerciale_actions.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "casafolino_sala_commerciale/static/src/sala_commerciale_v8/sala_commerciale_v8.scss",
            "casafolino_sala_commerciale/static/src/sala_commerciale_v8/sala_commerciale_v8.xml",
            "casafolino_sala_commerciale/static/src/sala_commerciale_v8/sala_commerciale_v8.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}

