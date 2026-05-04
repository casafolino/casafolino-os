from odoo import api, fields, models


class CfExportSampleStage(models.Model):
    _name = 'cf.export.sample.stage'
    _description = 'Stage Campionatura'
    _order = 'sequence asc'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(default=False)
    is_closed = fields.Boolean(default=False)


class CfExportSample(models.Model):
    _name = 'cf.export.sample'
    _description = 'Campionatura Export'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Riferimento',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('cf.export.sample') or 'CAMP-NEW',
    )
    lead_id = fields.Many2one('crm.lead', string='Trattativa', required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='lead_id.partner_id', store=True, string='Cliente')
    stage_id = fields.Many2one(
        'cf.export.sample.stage',
        string='Stage',
        default=lambda self: self.env['cf.export.sample.stage'].search([], limit=1),
        tracking=True,
        group_expand='_read_group_stage_ids',
    )
    state = fields.Selection([
        ('draft', 'Da Preparare'),
        ('prepared', 'Preparata'),
        ('sent', 'Spedita'),
        ('received', 'Ricevuta'),
        ('feedback_ok', 'Feedback Positivo'),
        ('feedback_ko', 'Feedback Negativo'),
        ('no_feedback', 'Nessun Feedback'),
    ], string='Stato', default='draft', tracking=True)
    product_ids = fields.Many2many('product.template', string='Prodotti')
    date_sent = fields.Date(string='Data Spedizione', tracking=True)
    date_feedback_expected = fields.Date(string='Feedback Atteso')
    tracking_number = fields.Char(string='Tracking')
    feedback_notes = fields.Text(string='Note Feedback')
    feedback_score = fields.Selection([
        ('1', '⭐'),
        ('2', '⭐⭐'),
        ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'),
        ('5', '⭐⭐⭐⭐⭐'),
    ], string='Valutazione')
    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        return self.env['cf.export.sample.stage'].search([])
