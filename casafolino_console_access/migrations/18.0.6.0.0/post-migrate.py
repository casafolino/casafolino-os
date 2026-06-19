# Crea il cron digest invii su -u (post_init_hook gira solo su install). Idempotente.
from odoo import api, SUPERUSER_ID, fields


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron']
    if Cron.search([('cron_name', '=', 'CasaFolino Console: digest invii')], limit=1):
        return
    model = env['ir.model'].search([('model', '=', 'casafolino.mail.message')], limit=1)
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
