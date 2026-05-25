# -*- coding: utf-8 -*-

from . import models


def _post_init_hook(env):
    menu = env.ref("point_of_sale.menu_point_root", raise_if_not_found=False)
    if menu and not menu.active:
        menu.sudo().write({"active": True})
    env["pos.config"].cf_ensure_bank_transfer_payment_method()
