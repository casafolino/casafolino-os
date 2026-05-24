from odoo import SUPERUSER_ID, api


def post_init_hook(env):
    if not hasattr(env, "ref"):
        env = api.Environment(env, SUPERUSER_ID, {})

    cron = env["ir.cron"].sudo()
    model = env["ir.model"].sudo().search([("model", "=", "product.product")], limit=1)
    if not model:
        return

    existing = cron.search([("cron_name", "=", "CasaFolino Shopify: sync stock")], limit=1)
    values = {
        "name": "CasaFolino Shopify: sync stock",
        "cron_name": "CasaFolino Shopify: sync stock",
        "model_id": model.id,
        "state": "code",
        "code": "model._cron_shopify_sync_stock()",
        "interval_number": 15,
        "interval_type": "minutes",
        "active": False,
    }
    if existing:
        existing.write(values)
    else:
        cron.create(values)
