import json
import uuid

import requests

from odoo import _, models
from odoo.exceptions import UserError


class CasaFolinoShopifyClient(models.AbstractModel):
    _name = "casafolino.shopify.client"
    _description = "CasaFolino Shopify GraphQL Client"

    def _param(self, key, default=False):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _shop_domain(self):
        shop = (self._param("casafolino_shopify_sync.shop_domain") or "").strip()
        if shop.startswith("https://"):
            shop = shop[8:]
        if shop.startswith("http://"):
            shop = shop[7:]
        return shop.rstrip("/")

    def _api_version(self):
        return self._param("casafolino_shopify_sync.api_version", "2026-04")

    def _token(self):
        return (self._param("casafolino_shopify_sync.access_token") or "").strip()

    def _endpoint(self):
        shop = self._shop_domain()
        token = self._token()
        if not shop or not token:
            raise UserError(_("Configura dominio Shopify e Admin API access token."))
        return "https://%s/admin/api/%s/graphql.json" % (shop, self._api_version())

    def graphql(self, query, variables=None):
        response = requests.post(
            self._endpoint(),
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self._token(),
            },
            data=json.dumps({"query": query, "variables": variables or {}}),
            timeout=30,
        )
        if response.status_code >= 400:
            raise UserError(_("Errore Shopify HTTP %(code)s: %(body)s") % {
                "code": response.status_code,
                "body": response.text[:1000],
            })

        result = response.json()
        if result.get("errors"):
            raise UserError(_("Errore Shopify GraphQL: %s") % result["errors"])
        return result.get("data") or {}

    def find_variant_by_sku(self, sku):
        query = """
            query ProductVariantBySku($query: String!) {
              productVariants(first: 5, query: $query) {
                edges {
                  node {
                    id
                    sku
                    title
                    inventoryItem { id tracked }
                  }
                }
              }
            }
        """
        data = self.graphql(query, {"query": 'sku:"%s"' % sku.replace('"', '\\"')})
        variants = [
            edge["node"]
            for edge in data.get("productVariants", {}).get("edges", [])
            if edge.get("node")
        ]
        exact = [variant for variant in variants if variant.get("sku") == sku]
        return (exact or variants or [False])[0]

    def set_available_quantity(self, inventory_item_id, location_id, quantity, reference):
        mutation = """
            mutation InventorySet($input: InventorySetQuantitiesInput!, $idempotencyKey: String!) {
              inventorySetQuantities(input: $input) @idempotent(key: $idempotencyKey) {
                inventoryAdjustmentGroup {
                  reason
                  referenceDocumentUri
                  changes { name delta quantityAfterChange }
                }
                userErrors { code field message }
              }
            }
        """
        variables = {
            "idempotencyKey": str(uuid.uuid4()),
            "input": {
                "name": "available",
                "reason": "correction",
                "referenceDocumentUri": reference,
                "quantities": [{
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_id,
                    "quantity": int(quantity),
                    "ignoreCompareQuantity": True,
                }],
            },
        }
        data = self.graphql(mutation, variables)
        payload = data.get("inventorySetQuantities") or {}
        errors = payload.get("userErrors") or []
        if errors:
            raise UserError(_("Errore aggiornamento stock Shopify: %s") % errors)
        return payload

