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
        ('external', 'Esterno'),
        ('other', 'Altro'),
    ], string='Qualifica', required=True, default='commercial')

    is_external = fields.Boolean(string='Esterno')
    is_primary = fields.Boolean(string='Primary')
    mail_sync_enabled = fields.Boolean(string='Sincronizza mail', default=True)
    mail_message_count = fields.Integer(
        string='Mail',
        compute='_compute_mail_message_count',
    )
    mail_last_sync = fields.Datetime(string='Ultima sync mail', readonly=True)
    note = fields.Char(string='Note')

    @api.depends('email')
    def _compute_email_norm(self):
        for c in self:
            c.email_normalized = (c.email or '').strip().lower()

    @api.depends('email_normalized', 'project_id')
    def _compute_mail_message_count(self):
        Mail = self.env.get('casafolino.mail.message')
        for contact in self:
            if not Mail:
                contact.mail_message_count = 0
                continue
            email = contact.email_normalized
            domain = [('cf_project_id', '=', contact.project_id.id)] if contact.project_id else []
            if email:
                email_domain = [
                    '|', '|',
                    ('sender_email', '=ilike', email),
                    ('recipient_emails', 'ilike', email),
                    ('cc_emails', 'ilike', email),
                ]
                domain = ['&'] + domain + email_domain if domain else email_domain
            contact.mail_message_count = Mail.search_count(domain) if domain else 0

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.email = self.partner_id.email
            self.phone = self.partner_id.phone or self.partner_id.mobile

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

    def _ensure_partner(self, parent_partner=False):
        self.ensure_one()
        if self.partner_id:
            return self.partner_id
        partner = self.env['res.partner'].search([
            ('email', '=ilike', self.email or ''),
        ], limit=1) if self.email else self.env['res.partner']
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.name,
                'email': self.email or False,
                'phone': self.phone or False,
                'parent_id': parent_partner.id if parent_partner else False,
                'type': 'contact',
            })
        self.partner_id = partner.id
        return partner
