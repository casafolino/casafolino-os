from odoo import models, fields, api


class CfDossierTemplate(models.Model):
    _name = 'cf.dossier.template'
    _description = 'Template Dossier Commerciale'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    category = fields.Selection([
        ('commercial', 'Commerciale'),
        ('operational', 'Operativo'),
    ], string='Categoria', required=True)
    icon = fields.Char(default='fa-folder')
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    default_lang = fields.Selection([
        ('it', 'Italiano'), ('en', 'English'), ('es', 'Espanol'),
        ('fr', 'Francais'), ('de', 'Deutsch'), ('pt', 'Portugues'),
        ('ar', 'Arabo'), ('zh', 'Cinese'),
    ], string='Lingua default')
    default_certification_ids = fields.Many2many(
        'cf.export.certification',
        'cf_dossier_template_cert_rel',
        string='Certificazioni default',
    )
    default_volume_unit = fields.Selection([
        ('unit', 'Unita (pezzi)'), ('cartoni', 'Cartoni'),
        ('pallet', 'Pallet'), ('kg', 'Kg'), ('tonnellate', 'Tonnellate'),
    ], string='Unita volume default')
    default_incoterms = fields.Selection([
        ('exw', 'EXW'), ('fca', 'FCA'), ('fob', 'FOB'),
        ('cif', 'CIF'), ('ddp', 'DDP'),
    ], string='Incoterms default')
    default_payment_term = fields.Selection([
        ('advance', 'Anticipo 100%'),
        ('30_70', '30% advance / 70% balance'),
        ('50_50', '50/50'),
        ('lc', 'LC at sight'),
        ('30_days', '30 giorni FM'),
        ('60_days', '60 giorni FM'),
        ('open_account', 'Open account'),
    ], string='Pagamento default')

    checkpoint_ids = fields.One2many(
        'cf.dossier.template.checkpoint', 'template_id',
        string='Checkpoint',
    )

    def action_create_dossier(self):
        """Open wizard to create a dossier from this template."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Crea Dossier da Template',
            'res_model': 'cf.dossier.create.from.template',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_template_id': self.id},
        }


class CfDossierTemplateCheckpoint(models.Model):
    _name = 'cf.dossier.template.checkpoint'
    _description = 'Checkpoint Template Dossier'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'cf.dossier.template', string='Template',
        ondelete='cascade', required=True,
    )
    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    expected_duration_days = fields.Integer(default=7)
