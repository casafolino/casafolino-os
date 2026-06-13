import json
import logging
from pprint import pformat

import requests

from odoo import models
from odoo.exceptions import ValidationError

from odoo.addons.sale_amazon import utils as amazon_utils


_logger = logging.getLogger(__name__)


class AmazonOffer(models.Model):
    _inherit = "amazon.offer"

    def _update_inventory_availability(self, account):
        """Update FBM inventory with Amazon's current JSON listings feed.

        Odoo 18.0.1.1 still submits the legacy XML
        POST_INVENTORY_AVAILABILITY_DATA feed. Amazon deprecated XML/flat
        listings feeds and now expects JSON_LISTINGS_FEED for listing
        inventory updates.
        """

        def _chunked(recordset, size):
            for index in range(0, len(recordset), size):
                yield recordset[index:index + size]

        def _build_payload(offers):
            messages = []
            for message_id, offer in enumerate(offers, start=1):
                available_qty = int(max(offer._get_available_product_qty(), 0))
                messages.append({
                    "messageId": message_id,
                    "sku": offer.sku,
                    "operationType": "PATCH",
                    "productType": "PRODUCT",
                    "patches": [{
                        "op": "replace",
                        "path": "/attributes/fulfillment_availability",
                        "value": [{
                            "fulfillment_channel_code": "DEFAULT",
                            "quantity": available_qty,
                        }],
                    }],
                })
            return {
                "header": {
                    "sellerId": account.seller_key,
                    "version": "2.0",
                    "issueLocale": "it_IT",
                },
                "messages": messages,
            }

        def _submit_json_feed(offers):
            content_type = "application/json; charset=UTF-8"
            feed = json.dumps(_build_payload(offers), separators=(",", ":")).encode()

            document = amazon_utils.make_sp_api_request(
                account,
                "createFeedDocument",
                payload={"contentType": content_type},
                method="POST",
            )
            try:
                response = requests.put(
                    document["url"],
                    data=feed,
                    headers={"content-Type": content_type},
                    timeout=60,
                )
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception("Invalid Amazon JSON inventory feed upload:\n%s", feed)
                raise ValidationError(self.env._("The communication with the API failed."))
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                _logger.exception("Could not establish the connection to the Amazon feed URL.")
                raise ValidationError(self.env._("Could not establish the connection to the feed URL."))

            marketplace_refs = account.active_marketplace_ids.mapped("api_ref")
            payload = {
                "feedType": "JSON_LISTINGS_FEED",
                "marketplaceIds": marketplace_refs,
                "inputFeedDocumentId": document["feedDocumentId"],
            }
            _logger.info("Submitting Amazon JSON inventory feed:\n%s", pformat(payload))
            response = amazon_utils.make_sp_api_request(
                account,
                "createFeed",
                payload=payload,
                method="POST",
            )
            return response["feedId"]

        offers_to_sync = self.filtered(lambda offer: offer.sku)
        if not offers_to_sync:
            return

        for offers_batch in _chunked(offers_to_sync, 500):
            try:
                feed_ref = _submit_json_feed(offers_batch)
            except amazon_utils.AmazonRateLimitError:
                _logger.info(
                    "Rate limit reached while sending JSON inventory feed for Amazon account %s.",
                    account.id,
                )
            else:
                _logger.info(
                    "Sent JSON inventory feed %s to Amazon for SKUs %s.",
                    feed_ref,
                    ", ".join(offers_batch.mapped("sku")),
                )
                offers_batch.write({
                    "amazon_sync_status": "processing",
                    "amazon_feed_ref": feed_ref,
                })
