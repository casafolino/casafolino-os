import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CfProjectContact(models.Model):
    _name = 'cf.project.contact'
    _description = 'Contatto progetto commerciale'
    _order = 'sequence, id'

    project_id = fields.Many2one(
        'project.project', string='Progetto',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)

    partner_id = fields.Many2one(
        'res.partner', string='Contatto Odoo',
    )
    name = fields.Char(string='Nome', required=True)
    email = fields.Char(string='Email')
    email_normalized = fields.Char(
        compute='_compute_email_norm', store=True, index=True,
    )
    phone = fields.Char(string='Telefono')

    role = fields.Selection([
        ('commercial', 'Commerciale'),
        ('admin', 'Amministrativo'),
        ('operations', 'Operativo'),
        ('logistics', 'Logistica'),
        ('quality', 'Qualità'),
        ('management', 'Direzione'),
        ('broker', 'Broker'),
        ('internal', 'Team interno'),
        ('external', 'Esterno'),
        ('other', 'Altro'),
    ], string='Qualifica', required=True, default='commercial')

    is_external = fields.Boolean(string='Esterno')
    is_primary = fields.Boolean(string='Primary')
    mail_sync_enabled = fields.Boolean(string='Sync mail', default=True)
    mail_last_sync = fields.Datetime(string='Ultimo sync mail', readonly=True)
    mail_message_count = fields.Integer(
        string='Mail', compute='_compute_mail_message_count')
    note = fields.Char(string='Note')

    @api.depends('email')
    def _compute_email_norm(self):
        for c in self:
            c.email_normalized = (c.email or '').strip().lower()

    @api.depends('email_normalized')
    def _compute_mail_message_count(self):
        try:
            MailMsg = self.env['casafolino.mail.message'].sudo()
        except KeyError:
            MailMsg = False
        for contact in self:
            if MailMsg is False or not contact.email_normalized:
                contact.mail_message_count = 0
                continue
            contact.mail_message_count = MailMsg.search_count([
                '|', '|',
                ('sender_email', '=ilike', contact.email_normalized),
                ('recipient_emails', 'ilike', contact.email_normalized),
                ('cc_emails', 'ilike', contact.email_normalized),
            ])

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.email = self.partner_id.email
            self.phone = self.partner_id.phone or self.partner_id.mobile

    def _ensure_partner(self, parent_partner=False):
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        vals = {
            'name': self.name,
            'email': self.email or False,
            'phone': self.phone or False,
            'company_type': 'person',
            'parent_id': parent_partner.id if parent_partner else False,
        }
        partner = self.env['res.partner'].sudo().create(vals)
        self.partner_id = partner.id
        return partner

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for r in records:
            if r.is_primary:
                r._enforce_single_primary()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_primary'):
            for r in self:
                r._enforce_single_primary()
        return res

    def _enforce_single_primary(self):
        self.ensure_one()
        if self.is_primary:
            others = self.search([
                ('project_id', '=', self.project_id.id),
                ('id', '!=', self.id),
                ('is_primary', '=', True),
            ])
            if others:
                others.write({'is_primary': False})
