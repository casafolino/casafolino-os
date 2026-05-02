from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fair_attachment_catalog = fields.Many2one(
        'documents.document',
        string='Catalogue (EN)',
        config_parameter='casafolino.crm_export.fair_attachment_catalog',
    )
    fair_attachment_company_profile = fields.Many2one(
        'documents.document',
        string='Company Profile (EN)',
        config_parameter='casafolino.crm_export.fair_attachment_company_profile',
    )
    fair_cc_email = fields.Char(
        string='Fair CC Email',
        config_parameter='casafolino.crm_export.fair_cc_email',
    )
