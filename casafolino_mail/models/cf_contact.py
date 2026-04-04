from odoo import models, fields, api



class ResPartnerMailExt(models.Model):
    _inherit = 'res.partner'

    # Campi extra tipo HubSpot/Zoho
    cf_job_title = fields.Char('Ruolo / Posizione')
    cf_department = fields.Char('Reparto')
    cf_linkedin = fields.Char('LinkedIn')
    cf_instagram = fields.Char('Instagram')
    cf_whatsapp = fields.Char('WhatsApp')
    cf_language = fields.Char('Lingua')
    cf_country_origin = fields.Char('Paese di origine')
    cf_birthday = fields.Date('Data di nascita')
    cf_source = fields.Selection([
        ('fiera', 'Fiera'),
        ('email', 'Email'),
        ('referral', 'Referral'),
        ('web', 'Web'),
        ('cold', 'Cold outreach'),
        ('altro', 'Altro'),
    ], string='Fonte contatto')
    cf_fairs = fields.Char('Fiere frequentate')
    cf_notes = fields.Text('Note private')
    cf_rating = fields.Selection([
        ('1', '★'),
        ('2', '★★'),
        ('3', '★★★'),
        ('4', '★★★★'),
        ('5', '★★★★★'),
    ], string='Valutazione')
    cf_tag_ids = fields.Many2many(
        'cf.contact.tag',
        'cf_partner_tag_rel',
        'partner_id', 'tag_id',
        string='Tag CasaFolino'
    )
    cf_last_contact = fields.Datetime('Ultimo contatto', compute='_compute_last_contact', store=True)
    cf_email_count = fields.Integer('Email totali', compute='_compute_email_count')
    cf_opt_out = fields.Boolean('Opt-out email marketing', default=False)
    cf_gdpr_consent = fields.Boolean('Consenso GDPR', default=False)
    cf_gdpr_date = fields.Date('Data consenso GDPR')

    @api.depends('message_ids')
    def _compute_last_contact(self):
        for p in self:
            msgs = self.env['cf.mail.message'].search([
                ('partner_id', '=', p.id)
            ], order='date desc', limit=1)
            p.cf_last_contact = msgs.date if msgs else False

    def _compute_email_count(self):
        for p in self:
            p.cf_email_count = self.env['cf.mail.message'].search_count([
                ('partner_id', '=', p.id)
            ])

    @api.model
    def get_contact_detail(self, *args, **kw):
        partner_id = kw.get('partner_id')
        if not partner_id:
            return {}
        p = self.browse(int(partner_id))
        if not p.exists():
            return {}
        return {
            'id': p.id,
            'name': p.name or '',
            'email': p.email or '',
            'phone': p.phone or '',
            'mobile': p.mobile or '',
            'company': p.parent_id.name if p.parent_id else (p.company_name or ''),
            'job_title': p.cf_job_title or p.function or '',
            'department': p.cf_department or '',
            'country': p.country_id.name if p.country_id else '',
            'language': p.cf_language or '',
            'linkedin': p.cf_linkedin or '',
            'instagram': p.cf_instagram or '',
            'whatsapp': p.cf_whatsapp or '',
            'source': p.cf_source or '',
            'fairs': p.cf_fairs or '',
            'notes': p.cf_notes or '',
            'rating': p.cf_rating or '',
            'opt_out': p.cf_opt_out,
            'gdpr_consent': p.cf_gdpr_consent,
            'gdpr_date': p.cf_gdpr_date.strftime('%d/%m/%Y') if p.cf_gdpr_date else '',
            'tags': [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in p.cf_tag_ids],
            'email_count': p.cf_email_count,
            'last_contact': p.cf_last_contact.strftime('%d/%m/%Y %H:%M') if p.cf_last_contact else '',
        }

    @api.model
    def save_contact(self, *args, **kw):
        partner_id = kw.get('id')
        vals = {}
        fields_map = {
            'name': 'name', 'email': 'email', 'phone': 'phone', 'mobile': 'mobile',
            'job_title': 'cf_job_title', 'department': 'cf_department',
            'language': 'cf_language', 'linkedin': 'cf_linkedin',
            'instagram': 'cf_instagram', 'whatsapp': 'cf_whatsapp',
            'source': 'cf_source', 'fairs': 'cf_fairs', 'notes': 'cf_notes',
            'rating': 'cf_rating', 'opt_out': 'cf_opt_out',
            'gdpr_consent': 'cf_gdpr_consent',
        }
        for k, v in fields_map.items():
            if k in kw:
                vals[v] = kw[k]

        if kw.get('tag_ids'):
            vals['cf_tag_ids'] = [(6, 0, [int(t) for t in kw['tag_ids']])]

        if partner_id:
            p = self.browse(int(partner_id))
            p.write(vals)
        else:
            p = self.create(vals)
        return {'success': True, 'id': p.id}

    @api.model
    def search_contacts(self, *args, **kw):
        query = kw.get('query') or ''
        tag_ids = kw.get('tag_ids') or []
        limit = int(kw.get('limit') or 30)

        domain = []
        if query:
            domain += ['|', '|', '|',
                ('name', 'ilike', query),
                ('email', 'ilike', query),
                ('cf_job_title', 'ilike', query),
                ('company_name', 'ilike', query),
            ]
        if tag_ids:
            domain.append(('cf_tag_ids', 'in', [int(t) for t in tag_ids]))

        partners = self.search(domain, limit=limit, order='name')
        result = []
        for p in partners:
            result.append({
                'id': p.id,
                'name': p.name or '',
                'email': p.email or '',
                'company': p.parent_id.name if p.parent_id else (p.company_name or ''),
                'job_title': p.cf_job_title or p.function or '',
                'country': p.country_id.name if p.country_id else '',
                'tags': [{'id': t.id, 'name': t.name, 'color': t.color or '#5A6E3A'} for t in p.cf_tag_ids],
                'email_count': p.cf_email_count,
                'last_contact': p.cf_last_contact.strftime('%d/%m/%Y') if p.cf_last_contact else '',
                'rating': p.cf_rating or '',
            })
        return result


class CfContactTag(models.Model):
    _name = 'cf.contact.tag'
    _description = 'Tag Contatto CasaFolino'
    _order = 'name'

    name = fields.Char('Nome', required=True)
    color = fields.Char('Colore', default='#5A6E3A')
    category = fields.Selection([
        ('nazione', 'Nazione'),
        ('lingua', 'Lingua'),
        ('fiera', 'Fiera'),
        ('settore', 'Settore'),
        ('ruolo', 'Ruolo'),
        ('altro', 'Altro'),
    ], string='Categoria', default='altro')
    partner_count = fields.Integer('Contatti', compute='_compute_partner_count')

    def _compute_partner_count(self):
        for t in self:
            t.partner_count = self.env['res.partner'].search_count([('cf_tag_ids', 'in', [t.id])])

    @api.model
    def get_all_tags(self, *args, **kw):
        tags = self.search([], order='category, name')
        return [{'id': t.id, 'name': t.name, 'color': t.color, 'category': t.category, 'count': t.partner_count} for t in tags]

    @api.model
    def create_tag(self, *args, **kw):
        name = kw.get('name')
        color = kw.get('color') or '#5A6E3A'
        category = kw.get('category') or 'altro'
        if not name:
            return False
        tag = self.create({'name': name, 'color': color, 'category': category})
        return {'id': tag.id, 'name': tag.name, 'color': tag.color, 'category': tag.category}
