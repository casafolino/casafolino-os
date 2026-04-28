# -*- coding: utf-8 -*-
from odoo import fields, models


class CfWorkspaceConfig(models.Model):
    _name = "cf.workspace.config"
    _description = "Workspace Configuration"

    name = fields.Char(default="Workspace Config", required=True)
    active = fields.Boolean(default=True)
