# casafolino_console_access — ACL scoped per gli utenti di servizio della Console.
# S0: console_prod_rw (internal, dormiente). console_api (portal, no seat) con gateway
# triage/send/reply sudo + audit + sponde S4 (cap/dedup/burst/digest).
from . import models


def post_init_hook(env):
    """Crea il cron digest invii (idempotente). Evita model_id ref in XML (ParseError Odoo 18)."""
    from odoo import fields
    Cron = env['ir.cron'].sudo()
    if Cron.search([('cron_name', '=', 'CasaFolino Console: digest invii')], limit=1):
        return
    model = env['ir.model'].sudo().search([('model', '=', 'casafolino.mail.message')], limit=1)
    if not model:
        return
    Cron.create({
        'name': 'CasaFolino Console: digest invii',
        'model_id': model.id,
        'state': 'code',
        'code': 'model._cron_console_send_digest()',
        'interval_number': 1,
        'interval_type': 'days',
        'active': True,
        'nextcall': fields.Datetime.now(),
    })
