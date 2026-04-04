# -*- coding: utf-8 -*-
from odoo import models, fields


class CfNutritionRegulation(models.Model):
    _name = "cf.nutrition.regulation"
    _description = "Normativa Nutrizionale"
    _rec_name = "name"
    _order = "sequence, name"

    name = fields.Char(string="Nome Normativa", required=True)
    market = fields.Selection([
        ('eu', 'Unione Europea (Reg. UE 1169/2011)'),
        ('usa', 'USA (FDA 21 CFR 101.9)'),
        ('canada', 'Canada (SOR/2003-11)'),
        ('australia', 'Australia / N. Zelanda (FSANZ 1.2.8)'),
        ('uk', 'Regno Unito (UK FIR 2014)'),
    ], string="Mercato", required=True, index=True)
    reference_url = fields.Char(string="Link Ufficiale")
    notes = fields.Text(string="Note Tecniche")
    mandatory_nutrients = fields.Text(string="Nutrienti Obbligatori")
    last_updated = fields.Date(string="Aggiornamento Normativa")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
