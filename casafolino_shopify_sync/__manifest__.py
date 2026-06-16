{
    "name": "CasaFolino Shopify Sync",
    "version": "18.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Sincronizza giacenze Odoo verso Shopify e ordini Shopify verso Odoo via SKU.",
    "author": "CasaFolino",
    "license": "LGPL-3",
    "depends": ["sale_management", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/shopify_log_views.xml",
        "views/product_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

