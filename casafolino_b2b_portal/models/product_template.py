# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    cf_b2b_case_size = fields.Integer(
        string="B2B pezzi per collo",
        default=6,
        help="Quantita minima e multiplo usato dal portale B2B CasaFolino.",
    )
