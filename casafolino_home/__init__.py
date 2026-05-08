# -*- coding: utf-8 -*-
from . import models


def _post_init_hook(env):
    """Post-install: set home action + remap menus that may not exist in all DBs."""
    # Set Scrivania Commerciale as default home action for key users
    try:
        action = env.ref('casafolino_home.action_scrivania_commerciale')
        users = env['res.users'].sudo().browse([2, 6, 8])
        existing = users.filtered(lambda u: u.exists())
        if existing:
            existing.write({'action_id': action.id})
    except Exception:
        pass

    # Remap menus that exist only in some DBs (e.g. eventi_root in prod only)
    _remap_optional_menus(env)


def _remap_optional_menus(env):
    """Remap menus that may not exist in all environments."""
    optional_remaps = [
        # (xml_id_to_remap, new_parent_xml_id, sequence)
        ('casafolino_commercial.menu_cf_eventi_root', 'casafolino_home.menu_ws_crm', 70),
    ]
    for menu_xmlid, parent_xmlid, seq in optional_remaps:
        try:
            menu = env.ref(menu_xmlid, raise_if_not_found=False)
            parent = env.ref(parent_xmlid, raise_if_not_found=False)
            if menu and parent:
                menu.write({'parent_id': parent.id, 'sequence': seq})
        except Exception:
            pass
