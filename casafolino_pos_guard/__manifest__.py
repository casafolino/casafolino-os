# -*- coding: utf-8 -*-
{
    "name": "CasaFolino POS Guard",
    "version": "18.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Protegge l'apertura del POS da errori temporanei della stampante fiscale",
    "author": "CasaFolino Srls",
    "depends": ["point_of_sale", "l10n_it_pos"],
    "post_init_hook": "_post_init_hook",
    "assets": {
        "point_of_sale._assets_pos": [
            "casafolino_pos_guard/static/src/js/fiscal_printer_guard.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
