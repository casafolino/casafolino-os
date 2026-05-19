from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Create cron in Python to avoid Odoo 18 ir.cron XML model_id issues."""
    if not hasattr(env, 'registry'):
        env = api.Environment(env, SUPERUSER_ID, {})

    model = env['ir.model']._get('casafolino.voice.outbound.queue')
    server_action = env['ir.actions.server'].search([
        ('name', '=', 'CasaFolino Voice AI: process outbound queue'),
        ('model_id', '=', model.id),
    ], limit=1)
    if not server_action:
        server_action = env['ir.actions.server'].create({
            'name': 'CasaFolino Voice AI: process outbound queue',
            'model_id': model.id,
            'state': 'code',
            'code': "model.cron_process_outbound_queue()",
        })

    cron = env['ir.cron'].search([
        ('cron_name', '=', 'CasaFolino Voice AI: outbound queue'),
    ], limit=1)
    if not cron:
        env['ir.cron'].create({
            'cron_name': 'CasaFolino Voice AI: outbound queue',
            'ir_actions_server_id': server_action.id,
            'interval_number': 5,
            'interval_type': 'minutes',
            'active': True,
        })

