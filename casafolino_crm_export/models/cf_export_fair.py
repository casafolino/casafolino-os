from odoo import api, fields, models


class CfExportFair(models.Model):
    _name = 'cf.export.fair'
    _description = 'Fiera Export'
    _inherit = ['mail.thread']
    _order = 'date_start desc'

    name = fields.Char(string='Nome Fiera', required=True, tracking=True)
    date_start = fields.Date(string='Data Inizio', tracking=True)
    date_end = fields.Date(string='Data Fine')
    location = fields.Char(string='Luogo')
    country_id = fields.Many2one('res.country', string='Paese')
    state = fields.Selection([
        ('planned', 'Pianificata'),
        ('confirmed', 'Confermata'),
        ('active', 'In Corso'),
        ('done', 'Completata'),
        ('followup', 'Follow-up in Corso'),
        ('closed', 'Chiusa'),
    ], string='Stato', default='planned', tracking=True)
    budget = fields.Float(string='Budget €')
    notes = fields.Text(string='Note')
    lead_ids = fields.One2many('crm.lead', 'cf_fair_id', string='Trattative')
    lead_count = fields.Integer(string='N. Trattative', compute='_compute_lead_count', store=True)
    lead_count_won = fields.Integer(string='N. Vinti', compute='_compute_lead_count', store=True)
    revenue_generated = fields.Float(string='Ricavo Atteso (€)', compute='_compute_roi', store=True)
    revenue_won = fields.Float(string='Ricavo Vinto (€)', compute='_compute_roi', store=True)
    roi = fields.Float(string='ROI % (atteso)', compute='_compute_roi', store=True)
    roi_won = fields.Float(string='ROI % (vinto)', compute='_compute_roi', store=True)

    @api.depends('lead_ids', 'lead_ids.stage_id', 'lead_ids.stage_id.is_won')
    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = len(rec.lead_ids)
            rec.lead_count_won = len(rec.lead_ids.filtered(lambda l: l.stage_id.is_won))

    @api.depends('lead_ids.expected_revenue', 'lead_ids.stage_id.is_won', 'budget')
    def _compute_roi(self):
        for rec in self:
            revenue = sum(rec.lead_ids.mapped('expected_revenue'))
            revenue_won = sum(
                rec.lead_ids.filtered(lambda l: l.stage_id.is_won).mapped('expected_revenue'))
            rec.revenue_generated = revenue
            rec.revenue_won = revenue_won
            rec.roi = (revenue / rec.budget * 100) if rec.budget else 0.0
            rec.roi_won = (revenue_won / rec.budget * 100) if rec.budget else 0.0

    def action_view_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Trattative da Fiera',
            'res_model': 'crm.lead',
            'view_mode': 'kanban,list,form',
            'domain': [('cf_fair_id', '=', self.id)],
            'context': {'default_cf_fair_id': self.id},
        }
