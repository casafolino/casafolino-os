import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    shopify_inventory_item_gid = fields.Char(
        string="Shopify Inventory Item GID",
        copy=False,
        readonly=True,
    )
    shopify_last_stock_sync = fields.Datetime(copy=False, readonly=True)

    def _shopify_location_gid(self):
        location = self.env["ir.config_parameter"].sudo().get_param(
            "casafolino_shopify_sync.location_gid"
        )
        if not location:
            raise UserError(_("Configura lo Shopify Location GID."))
        return location

    def _shopify_stock_quantity(self):
        warehouse_id = self.env["ir.config_parameter"].sudo().get_param(
            "casafolino_shopify_sync.warehouse_id"
        )
        product = self
        if warehouse_id:
            warehouse = self.env["stock.warehouse"].browse(int(warehouse_id))
            product = product.with_context(location=warehouse.lot_stock_id.id)
        return max(0, int(product.free_qty))

    def action_shopify_sync_stock(self):
        logs = self._shopify_sync_stock_quantity()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Shopify"),
                "message": _("%s prodotti sincronizzati.") % len(logs),
                "type": "success",
                "sticky": False,
            },
        }

    def _shopify_sync_stock_quantity(self):
        client = self.env["casafolino.shopify.client"]
        location_gid = self._shopify_location_gid()
        log_model = self.env["casafolino.shopify.sync.log"].sudo()
        synced_logs = self.env["casafolino.shopify.sync.log"]

        for product in self:
            sku = product.default_code
            if not sku:
                synced_logs |= log_model.create({
                    "name": _("Stock non sincronizzato"),
                    "direction": "odoo_to_shopify",
                    "status": "warning",
                    "odoo_model": product._name,
                    "odoo_res_id": product.id,
                    "message": _("Prodotto senza SKU/default_code."),
                })
                continue

            try:
                inventory_item_gid = product.shopify_inventory_item_gid
                if not inventory_item_gid:
                    variant = client.find_variant_by_sku(sku)
                    inventory_item_gid = variant and variant.get("inventoryItem", {}).get("id")
                    if not inventory_item_gid:
                        raise UserError(_("Nessuna variante Shopify trovata per SKU %s.") % sku)
                    product.sudo().shopify_inventory_item_gid = inventory_item_gid

                quantity = product._shopify_stock_quantity()
                payload = client.set_available_quantity(
                    inventory_item_gid,
                    location_gid,
                    quantity,
                    "odoo://product.product/%s/stock" % product.id,
                )
                product.sudo().shopify_last_stock_sync = fields.Datetime.now()
                synced_logs |= log_model.create({
                    "name": _("Stock sincronizzato"),
                    "direction": "odoo_to_shopify",
                    "status": "success",
                    "sku": sku,
                    "shopify_id": inventory_item_gid,
                    "odoo_model": product._name,
                    "odoo_res_id": product.id,
                    "message": _("Quantità disponibile inviata a Shopify: %s") % quantity,
                    "payload": json.dumps(payload, indent=2),
                })
            except Exception as exc:
                synced_logs |= log_model.create({
                    "name": _("Errore sync stock"),
                    "direction": "odoo_to_shopify",
                    "status": "error",
                    "sku": sku,
                    "shopify_id": product.shopify_inventory_item_gid,
                    "odoo_model": product._name,
                    "odoo_res_id": product.id,
                    "message": str(exc),
                })
        return synced_logs

    def _cron_shopify_sync_stock(self):
        now = fields.Datetime.now()
        sync_cutoff = fields.Datetime.subtract(now, hours=1)
        error_cutoff = fields.Datetime.subtract(now, hours=24)
        recent_error_product_ids = self.env["casafolino.shopify.sync.log"].sudo().search([
            ("direction", "=", "odoo_to_shopify"),
            ("status", "=", "error"),
            ("odoo_model", "=", "product.product"),
            ("odoo_res_id", "!=", False),
            ("create_date", ">=", error_cutoff),
            ("message", "ilike", "Nessuna variante Shopify"),
        ]).mapped("odoo_res_id")
        products = self.search([
            ("active", "=", True),
            ("type", "=", "consu"),
            ("default_code", "!=", False),
            ("id", "not in", recent_error_product_ids),
            "|",
            ("shopify_last_stock_sync", "=", False),
            ("shopify_last_stock_sync", "<", sync_cutoff),
        ], limit=50)
        products._shopify_sync_stock_quantity()
