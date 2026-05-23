{
    "name": "CasaFolino Reverse Charge Safe",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations/EDI",
    "summary": "Procedura controllata per registrare e inviare integrazioni reverse charge",
    "author": "CasaFolino Srls",
    "depends": ["account", "l10n_it_edi"],
    "data": [
        "data/reverse_charge_server_action.xml",
    ],
    "post_init_hook": "_post_init_reverse_charge_action",
    "installable": True,
    "license": "LGPL-3",
}

