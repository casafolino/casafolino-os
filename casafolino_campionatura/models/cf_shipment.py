import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CfShipment(models.Model):
    _name = 'cf.shipment'
    _description = 'CasaFolino Shipment'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string="Riferimento", default='Nuovo', copy=False, readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Destinatario", tracking=True)
    lead_id = fields.Many2one('crm.lead', string="Lead")
    sale_order_id = fields.Many2one('sale.order', string="Ordine")
    task_id = fields.Many2one('cf.task', string="Task")
    carrier = fields.Char(string="Corriere", tracking=True)
    tracking_code = fields.Char(string="Tracking", tracking=True)

    state = fields.Selection([
        ('creato', 'Creato'),
        ('preparazione', 'In preparazione'),
        ('etichetta', 'Etichetta'),
        ('spedito', 'Spedito'),
        ('consegnato', 'Consegnato'),
    ], string="Stato", default='creato', required=True, tracking=True)

    date_creato = fields.Datetime(string="Creato il", readonly=True)
    date_preparazione = fields.Datetime(string="Preparazione il", readonly=True)
    date_spedito = fields.Datetime(string="Spedito il", readonly=True)
    date_consegnato = fields.Datetime(string="Consegnato il", readonly=True)
    company_id = fields.Many2one(
        'res.company', string="Azienda", default=lambda self: self.env.company)

    # --------------------------------------------------------------- create/seq
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Nuovo':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'casafolino.shipment') or 'Nuovo'
            if not vals.get('date_creato'):
                vals['date_creato'] = fields.Datetime.now()
        return super().create(vals_list)

    # ------------------------------------------------------------- transizioni
    def action_set_preparazione(self):
        for sh in self:
            sh.write({'state': 'preparazione',
                      'date_preparazione': fields.Datetime.now()})
        return True

    def action_set_etichetta(self):
        for sh in self:
            sh.write({'state': 'etichetta'})
        return True

    def action_set_spedito(self):
        for sh in self:
            if not sh.tracking_code or not sh.carrier:
                raise UserError(_(
                    "Inserire corriere e tracking prima di spedire (%s).") % sh.name)
            sh.write({'state': 'spedito', 'date_spedito': fields.Datetime.now()})
            sh._notify_customer('spedito')
            sh._notify_team('spedito')
        return True

    def action_set_consegnato(self):
        for sh in self:
            sh.write({'state': 'consegnato',
                      'date_consegnato': fields.Datetime.now()})
            sh._notify_customer('consegnato')
            sh._notify_team('consegnato')
        return True

    # ---------------------------------------------------------------- notifiche
    def _notify_customer(self, event):
        """Mail al cliente nella lingua del partner, via mail.template (in coda)."""
        self.ensure_one()
        if not self.partner_id or not self.partner_id.email:
            return
        xmlid = {
            'spedito': 'casafolino_campionatura.mail_template_shipment_spedito',
            'consegnato': 'casafolino_campionatura.mail_template_shipment_consegnato',
        }.get(event)
        if not xmlid:
            return
        tmpl = self.env.ref(xmlid, raise_if_not_found=False)
        if tmpl:
            # force_send=False -> resta in coda, dispatch via cron coda mail Odoo
            tmpl.send_mail(self.id, force_send=False)

    def _notify_team(self, event):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        esc = int(ICP.get_param('casafolino_task.escalation_user_id', 2) or 2)
        users = self.env['res.users']
        if self.task_id.originator_id:
            users |= self.task_id.originator_id
        antonio = self.env['res.users'].browse(esc)
        if antonio.exists():
            users |= antonio
        label = dict(self._fields['state'].selection).get(event, event)
        body = _("Spedizione %s — stato: %s. Corriere: %s. Tracking: %s.") % (
            self.name, label, self.carrier or '-', self.tracking_code or '-')
        for u in users:
            if u.email:
                self.env['mail.mail'].sudo().create({
                    'subject': '[Campionatura] %s — %s' % (self.name, label),
                    'body_html': body,
                    'email_to': u.email,
                    'auto_delete': True,
                })
        self.message_post(body=body)

    # ------------------------------------------------------------ orchestrazione
    @api.model
    def crea_campionatura(self, partner_id=None, lead_id=None, lines=None,
                          assignees=None, carrier=None):
        """Crea atomicamente ordine campione + cf.task (3 ruoli) + cf.shipment.

        Args:
            partner_id: res.partner.id (o derivato dal lead)
            lead_id: crm.lead.id (opzionale)
            lines: [{'product_id': id, 'product_uom_qty': n}, ...]
            assignees: {'coordinazione': uid, 'creazione': uid, 'logistica': uid}
            carrier: corriere (opzionale)

        Returns: dict con order_id / sample_code / task_id / shipment_id.
        Rollback totale su qualsiasi errore (savepoint).
        """
        lines = lines or []
        if not lines:
            raise UserError(_("Nessuna riga prodotto per la campionatura."))
        lead = self.env['crm.lead'].browse(lead_id) if lead_id else self.env['crm.lead']
        if not partner_id and lead:
            partner_id = lead.partner_id.id
        if not partner_id:
            raise UserError(_("Serve un partner (o un lead con partner)."))
        partner = self.env['res.partner'].browse(partner_id)
        ICP = self.env['ir.config_parameter'].sudo()

        def role_uid(role):
            if assignees and assignees.get(role):
                return assignees[role]
            v = int(ICP.get_param('casafolino_campionatura.user_%s' % role, 0) or 0)
            return v or self.env.uid

        with self.env.cr.savepoint():
            order = self.env['sale.order'].create({
                'partner_id': partner_id,
                'is_campione': True,
                'sample_code': self.env['ir.sequence'].next_by_code('casafolino.campionatura'),
                'campione_lead_id': lead.id if lead else False,
                'order_line': [(0, 0, {
                    'product_id': l['product_id'],
                    'product_uom_qty': l.get('product_uom_qty', 1),
                }) for l in lines],
            })
            task = self.env['cf.task'].create({
                'name': _("Campionatura %s") % (partner.name or order.sample_code),
                'template_key': 'campionatura',
                'partner_id': partner_id,
                'lead_id': lead.id if lead else False,
                'step_ids': [
                    (0, 0, {'sequence': 10, 'role': 'coordinazione',
                            'user_id': role_uid('coordinazione'), 'name': _("Coordinazione")}),
                    (0, 0, {'sequence': 20, 'role': 'creazione',
                            'user_id': role_uid('creazione'), 'name': _("Creazione campione")}),
                    (0, 0, {'sequence': 30, 'role': 'logistica',
                            'user_id': role_uid('logistica'), 'name': _("Spedizione")}),
                ],
            })
            shipment = self.create({
                'partner_id': partner_id,
                'lead_id': lead.id if lead else False,
                'sale_order_id': order.id,
                'task_id': task.id,
                'carrier': carrier or False,
                'state': 'creato',
            })
            order.write({
                'campione_task_id': task.id,
                'campione_shipment_id': shipment.id,
            })
            # avvia il task: attiva 1° step + notifica handoff via _cf_notify
            task.action_start()
        return {
            'order_id': order.id,
            'sample_code': order.sample_code,
            'task_id': task.id,
            'shipment_id': shipment.id,
        }
