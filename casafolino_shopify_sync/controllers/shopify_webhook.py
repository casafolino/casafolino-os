import base64
import hashlib
import hmac
import json

from odoo import http
from odoo.http import request


class ShopifyWebhookController(http.Controller):
    @http.route(
        "/shopify/webhook/orders/create",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def orders_create(self, **kwargs):
        raw_body = request.httprequest.get_data()
        if not self._valid_hmac(raw_body):
            return request.make_response("invalid signature", status=401)

        payload = json.loads(raw_body.decode("utf-8") or "{}")
        request.env["sale.order"].sudo()._shopify_import_order_payload(payload)
        return request.make_response("ok", status=200)

    def _valid_hmac(self, raw_body):
        secret = request.env["ir.config_parameter"].sudo().get_param(
            "casafolino_shopify_sync.webhook_secret"
        )
        if not secret:
            return True

        header = request.httprequest.headers.get("X-Shopify-Hmac-Sha256", "")
        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
        calculated = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(calculated, header)

