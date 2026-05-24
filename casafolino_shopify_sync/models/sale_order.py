import json
from datetime import datetime, timezone

from odoo import _, fields, models


def _join_name(*parts):
    return " ".join([part for part in parts if part])


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shopify_order_gid = fields.Char(copy=False, readonly=True, index=True)
    shopify_order_name = fields.Char(copy=False, readonly=True, index=True)

    def _shopify_import_order_payload(self, payload):
        shopify_id = payload.get("admin_graphql_api_id") or payload.get("id")
        order_name = payload.get("name") or str(shopify_id or "")
        log_model = self.env["casafolino.shopify.sync.log"].sudo()

        if not shopify_id:
            return log_model.create({
                "name": _("Ordine Shopify ignorato"),
                "direction": "shopify_to_odoo",
                "status": "error",
                "message": _("Payload ordine senza id Shopify."),
                "payload": json.dumps(payload, indent=2),
            })

        existing = self.search([
            "|",
            ("shopify_order_gid", "=", str(shopify_id)),
            ("shopify_order_name", "=", order_name),
        ], limit=1)
        if existing:
            return log_model.create({
                "name": _("Ordine Shopify già importato"),
                "direction": "shopify_to_odoo",
                "status": "warning",
                "shopify_id": str(shopify_id),
                "odoo_model": existing._name,
                "odoo_res_id": existing.id,
                "message": _("Ordine %s già presente in Odoo.") % order_name,
                "payload": json.dumps(payload, indent=2),
            })

        lines, errors = self._shopify_prepare_order_lines(payload)
        if errors:
            return log_model.create({
                "name": _("Ordine Shopify non importato"),
                "direction": "shopify_to_odoo",
                "status": "error",
                "shopify_id": str(shopify_id),
                "message": "\n".join(errors),
                "payload": json.dumps(payload, indent=2),
            })

        partner = self._shopify_find_or_create_partner(payload)
        order = self.create({
            "partner_id": partner.id,
            "origin": "Shopify %s" % order_name,
            "client_order_ref": order_name,
            "shopify_order_gid": str(shopify_id),
            "shopify_order_name": order_name,
            "date_order": self._shopify_datetime(payload.get("created_at")),
            "order_line": lines,
        })

        return log_model.create({
            "name": _("Ordine Shopify importato"),
            "direction": "shopify_to_odoo",
            "status": "success",
            "shopify_id": str(shopify_id),
            "odoo_model": order._name,
            "odoo_res_id": order.id,
            "message": _("Creato ordine Odoo %s da Shopify %s.") % (order.name, order_name),
            "payload": json.dumps(payload, indent=2),
        })

    def _shopify_prepare_order_lines(self, payload):
        lines = []
        errors = []
        products = self.env["product.product"].sudo()

        for item in payload.get("line_items") or []:
            sku = (item.get("sku") or "").strip()
            if not sku:
                errors.append(_("Riga senza SKU: %s") % (item.get("name") or item.get("title")))
                continue

            product = products.search([("default_code", "=", sku)], limit=1)
            if not product:
                errors.append(_("SKU Shopify non trovato in Odoo: %s") % sku)
                continue

            lines.append((0, 0, {
                "product_id": product.id,
                "name": item.get("name") or product.display_name,
                "product_uom_qty": item.get("quantity") or 1,
                "price_unit": float(item.get("price") or 0.0),
            }))
        if not lines and not errors:
            errors.append(_("Ordine Shopify senza righe articolo."))
        return lines, errors

    def _shopify_find_or_create_partner(self, payload):
        partner_model = self.env["res.partner"].sudo()
        customer = payload.get("customer") or {}
        shipping = payload.get("shipping_address") or {}
        billing = payload.get("billing_address") or {}
        address = shipping or billing

        email = payload.get("email") or customer.get("email") or address.get("email")
        phone = payload.get("phone") or address.get("phone") or customer.get("phone")
        partner = email and partner_model.search([("email", "=", email)], limit=1)
        if not partner and phone:
            partner = partner_model.search([("phone", "=", phone)], limit=1)
        if partner:
            return partner

        name = _join_name(
            address.get("first_name") or customer.get("first_name"),
            address.get("last_name") or customer.get("last_name"),
        ) or payload.get("name") or _("Cliente Shopify")

        return partner_model.create({
            "name": name,
            "email": email,
            "phone": phone,
            "street": address.get("address1"),
            "street2": address.get("address2"),
            "city": address.get("city"),
            "zip": address.get("zip"),
            "country_id": self._shopify_country(address.get("country_code")).id,
            "customer_rank": 1,
        })

    def _shopify_country(self, country_code):
        if not country_code:
            return self.env["res.country"]
        return self.env["res.country"].sudo().search([("code", "=", country_code)], limit=1)

    def _shopify_datetime(self, value):
        if not value:
            return fields.Datetime.now()
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return fields.Datetime.to_string(parsed.astimezone(timezone.utc).replace(tzinfo=None))
        except ValueError:
            return fields.Datetime.now()
