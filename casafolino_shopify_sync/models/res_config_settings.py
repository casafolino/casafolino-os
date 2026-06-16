from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    shopify_shop_domain = fields.Char(
        string="Shopify Shop Domain",
        config_parameter="casafolino_shopify_sync.shop_domain",
        help="Esempio: nome-store.myshopify.com",
    )
    shopify_access_token = fields.Char(
        string="Shopify Admin API Token",
        config_parameter="casafolino_shopify_sync.access_token",
    )
    shopify_api_version = fields.Char(
        string="Shopify API Version",
        default="2026-04",
        config_parameter="casafolino_shopify_sync.api_version",
    )
    shopify_location_gid = fields.Char(
        string="Shopify Location GID",
        config_parameter="casafolino_shopify_sync.location_gid",
        help="Esempio: gid://shopify/Location/123456789",
    )
    shopify_webhook_secret = fields.Char(
        string="Shopify Webhook Secret",
        config_parameter="casafolino_shopify_sync.webhook_secret",
    )
    shopify_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Magazzino stock eCommerce",
        config_parameter="casafolino_shopify_sync.warehouse_id",
    )

