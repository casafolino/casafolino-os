import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError


class CasafolinoMailMaterial(models.Model):
    _name = 'casafolino.mail.material'
    _description = 'Materiale commerciale email'
    _order = 'category, sequence, name'

    name = fields.Char('Nome materiale', required=True)
    code = fields.Char('Codice')
    sequence = fields.Integer(default=10)
    category = fields.Selection([
        ('catalog', 'Catalogo'),
        ('price_list', 'Listino'),
        ('technical_sheet', 'Scheda tecnica'),
        ('marketing', 'Materiale marketing'),
        ('presentation', 'Presentazione'),
        ('certification', 'Certificazione'),
        ('terms', 'Condizioni commerciali'),
        ('other', 'Altro'),
    ], string='Categoria', required=True, default='catalog', index=True)
    language = fields.Selection([
        ('it', 'Italiano'),
        ('en', 'English'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
        ('es', 'Español'),
        ('multi', 'Multilingua'),
    ], string='Lingua', required=True, default='it', index=True)
    version = fields.Char('Versione')
    state = fields.Selection([
        ('draft', 'Bozza'),
        ('approved', 'Approvato'),
        ('obsolete', 'Obsoleto'),
    ], string='Stato', default='draft', required=True, index=True)
    active = fields.Boolean(default=True)
    delivery_type = fields.Selection([
        ('file', 'File scaricabile'),
        ('url', 'Link esterno'),
    ], string='Tipo materiale', required=True, default='file')
    file_data = fields.Binary('File', attachment=True)
    file_name = fields.Char('Nome file')
    external_url = fields.Char('URL esterno')
    description = fields.Text('Descrizione interna')
    notes = fields.Text('Note operative')
    tag_ids = fields.Many2many('cf.contact.tag', string='Tag')
    link_ids = fields.One2many('casafolino.mail.material.link', 'material_id', string='Link tracciati')
    link_count = fields.Integer('Link creati', compute='_compute_link_stats')
    access_count = fields.Integer('Accessi', compute='_compute_link_stats')
    last_access_date = fields.Datetime('Ultimo accesso', compute='_compute_link_stats')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Esiste gia un materiale con questo codice.'),
    ]

    @api.depends('link_ids.access_count', 'link_ids.last_access_date')
    def _compute_link_stats(self):
        for material in self:
            material.link_count = len(material.link_ids)
            material.access_count = sum(material.link_ids.mapped('access_count'))
            dates = material.link_ids.mapped('last_access_date')
            material.last_access_date = max(dates) if dates else False

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_obsolete(self):
        self.write({'state': 'obsolete', 'active': False})

    def action_create_tracking_link(self):
        self.ensure_one()
        link = self.env['casafolino.mail.material.link'].create({
            'material_id': self.id,
            'user_id': self.env.user.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Link materiale tracciabile',
            'res_model': 'casafolino.mail.material.link',
            'res_id': link.id,
            'view_mode': 'form',
            'target': 'current',
        }


class CasafolinoMailMaterialLink(models.Model):
    _name = 'casafolino.mail.material.link'
    _description = 'Link tracciabile materiale commerciale'
    _order = 'create_date desc'

    name = fields.Char('Descrizione', compute='_compute_name', store=True)
    material_id = fields.Many2one(
        'casafolino.mail.material', string='Materiale', required=True,
        ondelete='cascade', index=True)
    message_id = fields.Many2one(
        'casafolino.mail.message', string='Email collegata',
        ondelete='set null', index=True)
    partner_id = fields.Many2one('res.partner', string='Contatto', index=True)
    lead_id = fields.Many2one('crm.lead', string='Trattativa', index=True)
    user_id = fields.Many2one('res.users', string='Creato da', default=lambda self: self.env.user)
    token = fields.Char('Token', required=True, default=lambda self: uuid.uuid4().hex, index=True)
    access_url = fields.Char('URL tracciabile', compute='_compute_access_url')
    active = fields.Boolean(default=True)
    expires_at = fields.Datetime('Scade il')
    access_count = fields.Integer('Accessi', default=0, readonly=True)
    download_count = fields.Integer('Download', default=0, readonly=True)
    last_access_date = fields.Datetime('Ultimo accesso', readonly=True)
    last_ip = fields.Char('Ultimo IP', readonly=True)
    last_user_agent = fields.Char('Ultimo User-Agent', readonly=True)

    _sql_constraints = [
        ('token_unique', 'UNIQUE(token)', 'Token link gia esistente.'),
    ]

    @api.depends('material_id', 'partner_id', 'lead_id')
    def _compute_name(self):
        for link in self:
            pieces = [link.material_id.name or 'Materiale']
            if link.partner_id:
                pieces.append(link.partner_id.display_name)
            elif link.lead_id:
                pieces.append(link.lead_id.display_name)
            link.name = ' - '.join(pieces)

    def _compute_access_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        base_url = (base_url or '').rstrip('/')
        for link in self:
            link.access_url = '%s/cf/material/%s' % (base_url, link.token) if base_url and link.token else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('message_id'):
                msg = self.env['casafolino.mail.message'].browse(vals['message_id']).exists()
                if msg:
                    vals.setdefault('partner_id', msg.partner_id.id if msg.partner_id else False)
                    vals.setdefault('lead_id', msg.lead_id.id if msg.lead_id else False)
        return super().create(vals_list)

    def action_open_material(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Materiale',
            'res_model': 'casafolino.mail.material',
            'res_id': self.material_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _record_public_access(self, ip_address='', user_agent=''):
        self.ensure_one()
        if self.expires_at and self.expires_at < fields.Datetime.now():
            raise UserError('Link scaduto.')
        event_type = 'clicked' if self.material_id.delivery_type == 'url' else 'downloaded'
        values = {
            'access_count': self.access_count + 1,
            'last_access_date': fields.Datetime.now(),
            'last_ip': (ip_address or '')[:120],
            'last_user_agent': (user_agent or '')[:500],
        }
        if event_type == 'downloaded':
            values['download_count'] = self.download_count + 1
        self.sudo().write(values)
        if self.message_id:
            self.env['casafolino.mail.tracking'].sudo().create({
                'message_id': self.message_id.id,
                'tracking_token': self.token,
                'event_type': event_type,
                'ip_address': (ip_address or '')[:120],
                'user_agent': (user_agent or '')[:500],
                'url_clicked': self.material_id.external_url or self.access_url or '',
                'attachment_name': self.material_id.file_name or self.material_id.name or '',
                'partner_id': self.partner_id.id if self.partner_id else False,
                'lead_id': self.lead_id.id if self.lead_id else False,
                'account_id': self.message_id.account_id.id if self.message_id.account_id else False,
            })
