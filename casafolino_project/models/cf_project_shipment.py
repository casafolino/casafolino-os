from odoo import models, fields, api


class CfProjectShipment(models.Model):
    _name = 'cf.project.shipment'
    _description = 'Spedizione Campioni'
    _inherit = ['mail.thread']
    _order = 'ship_date desc'

    project_id = fields.Many2one('project.project', string="Progetto", required=True)
    partner_id = fields.Many2one(related='project_id.cf_partner_id', store=True, string="Partner")
    state = fields.Selection([
        ('draft', 'Da Preparare'),
        ('ready', 'Pronto'),
        ('shipped', 'Spedito'),
        ('delivered', 'Consegnato'),
        ('feedback', 'Feedback Ricevuto'),
    ], default='draft', tracking=True, string="Stato")
    carrier = fields.Char(string="Corriere")
    tracking_number = fields.Char(string="Tracking Number")
    tracking_url = fields.Char(compute='_compute_tracking_url', string="Link Tracking")
    ship_date = fields.Date(string="Data Spedizione")
    estimated_delivery = fields.Date(string="Consegna Stimata")
    actual_delivery = fields.Date(string="Consegna Effettiva")
    product_ids = fields.Many2many('product.product', string="Prodotti Campionati")
    notes = fields.Text(string="Note Spedizione")
    weight = fields.Float(string="Peso (kg)")
    shipping_cost = fields.Float(string="Costo Spedizione")

    @api.depends('carrier', 'tracking_number')
    def _compute_tracking_url(self):
        carriers = {
            'dhl': 'https://www.dhl.com/it-it/home/tracking.html?tracking-id=',
            'ups': 'https://www.ups.com/track?tracknum=',
            'fedex': 'https://www.fedex.com/fedextrack/?trknbr=',
            'gls': 'https://www.gls-italy.com/?option=com_gls&view=track&mode=search&numero_spedizione=',
            'brt': 'https://vas.brt.it/vas/sped/BRT-SEGUITURA.htm?Lession=',
            'sda': 'https://www.sda.it/wps/portal/Servizi_online/dettaglio-spedizione?locale=it&tression=',
        }
        for rec in self:
            if rec.tracking_number and rec.carrier:
                carrier_key = (rec.carrier or '').lower().strip()
                for key, base_url in carriers.items():
                    if key in carrier_key:
                        rec.tracking_url = base_url + rec.tracking_number
                        break
                else:
                    rec.tracking_url = ''
            else:
                rec.tracking_url = ''
