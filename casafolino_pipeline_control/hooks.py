from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    if not hasattr(env, 'cr'):
        env = api.Environment(env, SUPERUSER_ID, {})
    env['cf.pipeline.control'].cleanup_legacy_entrypoints()
