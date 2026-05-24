# -*- coding: utf-8 -*-


def _post_init_hook(env):
    menu = env.ref("point_of_sale.menu_point_root", raise_if_not_found=False)
    if menu and not menu.active:
        menu.sudo().write({"active": True})
