from odoo import fields, models


class CasaFolinoShopifySyncLog(models.Model):
    _name = "casafolino.shopify.sync.log"
    _description = "CasaFolino Shopify Sync Log"
    _order = "create_date desc"

    name = fields.Char(required=True)
    direction = fields.Selection(
        [
            ("odoo_to_shopify", "Odoo -> Shopify"),
            ("shopify_to_odoo", "Shopify -> Odoo"),
        ],
        required=True,
    )
    status = fields.Selection(
        [("success", "Success"), ("warning", "Warning"), ("error", "Error")],
        required=True,
        default="success",
    )
    sku = fields.Char()
    shopify_id = fields.Char()
    odoo_model = fields.Char()
    odoo_res_id = fields.Integer()
    message = fields.Text()
    payload = fields.Text()

