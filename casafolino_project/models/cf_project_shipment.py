from datetime import timedelta

from odoo import models, fields, api


class CfProjectShipment(models.Model):
    _name = 'cf.project.shipment'
    _description = 'Spedizione Campioni'
    _inherit = ['mail.thread', 'mail.activity.mixin']
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
    trackbot_enabled = fields.Boolean(string="TrackBot attivo", tracking=True)
    trackbot_chat_ref = fields.Char(string="Chat/Canale TrackBot")
    trackbot_last_event = fields.Text(string="Ultimo evento TrackBot")
    trackbot_last_sync = fields.Datetime(string="Ultimo sync TrackBot")
    feedback_reminder_date = fields.Date(string="Reminder feedback")
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

    def action_mark_shipped(self):
        for shipment in self:
            vals = {
                'state': 'shipped',
                'ship_date': shipment.ship_date or fields.Date.context_today(shipment),
                'trackbot_enabled': True,
            }
            if not shipment.estimated_delivery:
                vals['estimated_delivery'] = fields.Date.context_today(shipment) + timedelta(days=3)
            shipment.write(vals)
            shipment.message_post(body="Spedizione campionatura segnata come spedita. Tracking: %s" % (shipment.tracking_number or "da inserire"))
        return True

    def action_mark_delivered(self):
        for shipment in self:
            today = fields.Date.context_today(shipment)
            shipment.write({
                'state': 'delivered',
                'actual_delivery': shipment.actual_delivery or today,
                'feedback_reminder_date': shipment.feedback_reminder_date or today + timedelta(days=7),
            })
            shipment._schedule_feedback_activity()
            shipment.message_post(body="Campionatura consegnata. Reminder feedback: %s" % (shipment.feedback_reminder_date or "da programmare"))
        return True

    def action_feedback_received(self):
        for shipment in self:
            shipment.write({'state': 'feedback'})
            shipment.message_post(body="Feedback campionatura ricevuto.")
        return True

    def _schedule_feedback_activity(self):
        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not todo_type:
            return
        for shipment in self:
            shipment.activity_schedule(
                todo_type.id,
                date_deadline=shipment.feedback_reminder_date or fields.Date.context_today(shipment),
                user_id=shipment.project_id.user_id.id or self.env.user.id,
                summary='Richiedere feedback campionatura',
                note=shipment.tracking_number or shipment.project_id.display_name,
            )
