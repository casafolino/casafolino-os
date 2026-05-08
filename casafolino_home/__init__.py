# -*- coding: utf-8 -*-
from . import models


def _post_init_hook(env):
    """Set Scrivania Commerciale as default home action for Antonio/Josefina/Martina."""
    try:
        action = env.ref('casafolino_home.action_scrivania_commerciale')
        users = env['res.users'].sudo().browse([2, 6, 8])
        existing = users.filtered(lambda u: u.exists())
        if existing:
            existing.write({'action_id': action.id})
    except Exception:
        pass
