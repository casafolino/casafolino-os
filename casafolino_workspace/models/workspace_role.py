# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

# Hardcoded role mapping
_ROLE_MAP_EMAIL = {
    "antonio@casafolino.com": "antonio",
    "josefina.lazzaro@casafolino.com": "josefina",
    "martina.sinopoli@casafolino.com": "martina",
}

_ROLE_MAP_NAME = {
    "lazzaro": "josefina",
    "sinopoli": "martina",
    "mirabelli": "maria",
    "folino": "antonio",
}

_ROLE_COLORS = {
    "antonio": "#7C3AED",
    "josefina": "#0D9488",
    "martina": "#E11D48",
    "maria": "#2563EB",
}

_ROLE_GREET = {
    "antonio": "CEO & Founder",
    "josefina": "Export Manager",
    "martina": "Back Office",
    "maria": "Quality Manager",
}


class ResUsersWorkspace(models.Model):
    _inherit = "res.users"

    @api.model
    def _get_workspace_role(self, user=None):
        user = user or self.env.user
        login = (user.login or "").lower().strip()
        if login in _ROLE_MAP_EMAIL:
            return _ROLE_MAP_EMAIL[login]
        name = (user.name or "").lower()
        for fragment, role in _ROLE_MAP_NAME.items():
            if fragment in name:
                return role
        return "antonio"

    @api.model
    def _get_workspace_profile(self, user=None):
        user = user or self.env.user
        role = self._get_workspace_role(user)
        first_name = (user.name or "").split()[0] if user.name else "Utente"
        initials = ""
        parts = (user.name or "").split()
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[-1][0]).upper()
        elif parts:
            initials = parts[0][:2].upper()
        return {
            "name": first_name,
            "full_name": user.name or "",
            "initials": initials,
            "role": role,
            "role_label": _ROLE_GREET.get(role, "Team"),
            "color": _ROLE_COLORS.get(role, "#7C3AED"),
            "user_id": user.id,
            "partner_id": user.partner_id.id,
        }
