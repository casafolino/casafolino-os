from odoo import api, fields, models


class CfSampleRequest(models.Model):
    _name = 'cf.sample.request'
    _description = 'Richiesta Campione'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(readonly=True, copy=False, default='New')
    initiative_id = fields.Many2one(
        'cf.initiative', required=True, ondelete='cascade', index=True,
        string='Iniziativa',
    )
    partner_id = fields.Many2one(
        'res.partner', required=True, string='Cliente / Buyer',
    )
    product_ids = fields.Many2many(
        'product.template', string='Prodotti Campione',
    )
    iteration = fields.Integer(default=1, string='N. Invio')
    parent_request_id = fields.Many2one(
        'cf.sample.request', string='Richiesta Originale',
        ondelete='set null',
    )
    send_date = fields.Date(string='Data Spedizione')
    shipping_address_id = fields.Many2one(
        'res.partner', string='Indirizzo Spedizione',
    )
    tracking_number = fields.Char(string='Tracking')
    notes_internal = fields.Text(string='Note Operative')
    notes_buyer_feedback = fields.Text(string='Feedback Buyer')
    state = fields.Selection([
        ('draft', 'Bozza'),
        ('sent', 'Inviato'),
        ('delivered', 'Consegnato'),
        ('feedback_received', 'Feedback Ricevuto'),
        ('modifications_requested', 'Modifiche Richieste'),
        ('completed', 'Completato'),
        ('cancelled', 'Annullato'),
    ], default='draft', tracking=True, string='Stato')

    _sql_constraints = [
        ('iteration_positive', 'CHECK(iteration > 0)',
         'Il numero di invio deve essere positivo.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'cf.sample.request') or 'New'
        return super().create(vals_list)

    def action_resend_with_modifications(self):
        self.ensure_one()
        new_request = self.copy({
            'parent_request_id': self.id,
            'iteration': self.iteration + 1,
            'state': 'draft',
            'send_date': False,
            'tracking_number': False,
            'notes_buyer_feedback': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cf.sample.request',
            'res_id': new_request.id,
            'view_mode': 'form',
            'target': 'current',
        }
