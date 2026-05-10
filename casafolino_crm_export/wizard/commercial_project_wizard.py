import logging

from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CfCommercialProjectWizard(models.TransientModel):
    _name = 'cf.commercial.project.wizard'
    _description = 'Wizard nuovo progetto commerciale'

    # === CLIENTE ===
    partner_id = fields.Many2one(
        'res.partner', string='Cliente esistente',
        domain=[('is_company', '=', True)],
    )
    is_new_partner = fields.Boolean(string='Cliente nuovo')
    new_partner_name = fields.Char(string='Nome nuovo cliente')
    buyer_name = fields.Char(string='Buyer')
    country_id = fields.Many2one('res.country', string='Paese')
    lang = fields.Selection(
        selection='_get_lang_selection',
        string='Lingua', default='en_US',
    )

    # === ORIGINE ===
    origin_type = fields.Selection([
        ('fair', 'Fiera'),
        ('mail', 'Mail'),
        ('agent', 'Agente'),
        ('web', 'Web/SEO'),
        ('reorder', 'Riordino'),
    ], string='Origine', required=True, default='fair')
    origin_fair_tag_id = fields.Many2one(
        'crm.tag', string='Fiera',
        domain=[('cf_category', '=', 'fair')],
    )
    origin_note = fields.Char(string='Dettaglio origine')

    # === BRIEF COMMERCIALE ===
    product_category = fields.Selection([
        ('miele', 'Mieli aromatizzati'),
        ('crema', 'Creme spalmabili'),
        ('crispy', 'Crispy chili'),
        ('risotto', 'Risotti'),
        ('mousse', 'Mousse di miele'),
        ('cantucci', 'Cantucci / biscotti'),
        ('cioccolato', 'Cioccolato'),
        ('mix_spezie', 'Mix spezie'),
        ('altro', 'Altro / multi-categoria'),
    ], string='Categoria prodotto')
    volume_target = fields.Char(string='Volume target')
    margin_target = fields.Float(string='Margine target %')
    priority = fields.Selection([
        ('low', 'Bassa'),
        ('medium', 'Media'),
        ('high', 'Alta'),
    ], string='Priorità', default='medium')

    # === OWNER ===
    user_id = fields.Many2one(
        'res.users', string='Responsabile',
        default=lambda self: self.env.user, required=True,
    )
    agent_name = fields.Char(string='Agente / referente esterno')

    # === PROSSIMA AZIONE ===
    next_action = fields.Char(string='Prossima azione')
    next_action_date = fields.Date(string='Data prossima azione')

    # === COMPUTED ===
    ai_suggestion = fields.Html(
        compute='_compute_ai_suggestion', sanitize=False,
    )
    existing_projects_count = fields.Integer(
        compute='_compute_ai_suggestion',
    )
    preview_html = fields.Html(
        compute='_compute_preview', sanitize=False,
    )

    def _get_lang_selection(self):
        return self.env['res.lang'].get_installed()

    @api.depends('partner_id')
    def _compute_ai_suggestion(self):
        for w in self:
            count = 0
            html = False
            if w.partner_id:
                count = self.env['project.project'].search_count([
                    ('partner_id', '=', w.partner_id.id),
                    ('cf_status_dossier', 'in',
                     ['exploration', 'active', 'on_hold']),
                ])
                if count > 0:
                    html = Markup(
                        '<div class="alert alert-info" role="alert" '
                        'style="margin:0">'
                        '<strong>AI</strong> &middot; '
                        'Hai già <b>%d progett%s apert%s</b> con %s. '
                        'Verifica prima di duplicare.'
                        '</div>'
                    ) % (
                        count,
                        'o' if count == 1 else 'i',
                        'o' if count == 1 else 'i',
                        w.partner_id.name,
                    )
            w.existing_projects_count = count
            w.ai_suggestion = html

    @api.depends(
        'partner_id', 'new_partner_name', 'origin_fair_tag_id',
        'priority', 'volume_target', 'margin_target',
        'product_category', 'next_action_date',
    )
    def _compute_preview(self):
        priority_map = {
            'high': ('#FCEBEB', '#791F1F', 'Alta'),
            'medium': ('#FAEEDA', '#633806', 'Media'),
            'low': ('#E1F5EE', '#085041', 'Bassa'),
        }
        cat_map = dict(self._fields['product_category'].selection or [])
        for w in self:
            name = (
                w.partner_id.name if w.partner_id
                else w.new_partner_name or '— Cliente —'
            )
            cat = cat_map.get(w.product_category, '')
            badges = []
            if w.origin_fair_tag_id:
                badges.append(
                    '<span style="background:#FAEEDA;color:#633806;'
                    'font-size:10px;padding:2px 7px;border-radius:4px;">'
                    '%s</span>' % w.origin_fair_tag_id.name
                )
            if w.priority:
                bg, fg, lbl = priority_map.get(
                    w.priority, ('#FAEEDA', '#633806', 'Media'))
                badges.append(
                    '<span style="background:%s;color:%s;'
                    'font-size:10px;padding:2px 7px;border-radius:4px;">'
                    '%s</span>' % (bg, fg, lbl)
                )
            badges_html = ' '.join(badges)
            margin_str = (
                '%d%%' % int(w.margin_target) if w.margin_target else '—'
            )
            volume_str = w.volume_target or '—'
            date_str = (
                w.next_action_date.strftime('%d %b')
                if w.next_action_date else ''
            )
            w.preview_html = Markup(
                '<div style="background:white;border:0.5px solid '
                'rgba(0,0,0,0.1);border-radius:8px;padding:12px;">'
                '<div style="margin-bottom:8px;">%s</div>'
                '<div style="font-size:13px;font-weight:500;'
                'margin-bottom:4px;">%s%s</div>'
                '<div style="display:flex;justify-content:space-between;'
                'font-size:11px;color:#888;padding-top:8px;'
                'border-top:0.5px solid rgba(0,0,0,0.05);">'
                '<span>%s &middot; %s</span>'
                '<span>%s</span></div></div>'
            ) % (
                badges_html,
                name,
                (' — ' + cat) if cat else '',
                volume_str, margin_str, date_str,
            )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.country_id = self.partner_id.country_id
            self.lang = self.partner_id.lang or 'en_US'
            self.is_new_partner = False

    def action_create_project(self):
        self.ensure_one()
        # 1. Resolve partner
        partner = self.partner_id
        if not partner:
            if not self.new_partner_name:
                raise UserError(
                    _("Inserisci un cliente esistente o un nuovo nome."))
            partner = self.env['res.partner'].create({
                'name': self.new_partner_name,
                'company_type': 'company',
                'country_id': (
                    self.country_id.id if self.country_id else False
                ),
                'lang': self.lang,
            })

        # 2. Build project name
        cat_map = dict(self._fields['product_category'].selection or [])
        cat_label = cat_map.get(self.product_category, '')
        project_name = (
            '%s — %s' % (partner.name, cat_label)
            if cat_label else partner.name
        )

        # 3. Create project.project
        vals = {
            'name': project_name,
            'partner_id': partner.id,
            'user_id': self.user_id.id,
            'cf_status_dossier': 'active',
            'cf_dossier_priority': self.priority or 'medium',
            'cf_next_action': self.next_action or False,
            'cf_next_action_date': self.next_action_date or False,
        }
        # Buyer as Many2one (cf_buyer_id) — create child contact if name given
        if self.buyer_name:
            buyer = self.env['res.partner'].search([
                ('name', 'ilike', self.buyer_name),
                ('parent_id', '=', partner.id),
            ], limit=1)
            if not buyer:
                buyer = self.env['res.partner'].create({
                    'name': self.buyer_name,
                    'parent_id': partner.id,
                    'company_type': 'person',
                    'function': 'Buyer',
                })
            vals['cf_buyer_id'] = buyer.id

        # Volume / margin — store in cf_volume_target (Float) if parseable
        if self.volume_target:
            vals['cf_next_action'] = vals.get('cf_next_action') or ''
            # Store raw text in description for now
        if self.margin_target:
            vals['cf_margin_target'] = self.margin_target

        project = self.env['project.project'].create(vals)

        # 4. Create primary contact
        self.env['cf.project.contact'].create({
            'project_id': project.id,
            'partner_id': partner.id,
            'name': self.buyer_name or partner.name,
            'email': partner.email or '',
            'phone': partner.phone or partner.mobile or '',
            'role': 'commercial',
            'is_primary': True,
        })

        # 5. Origin info — chatter log
        origin_map = dict(self._fields['origin_type'].selection or [])
        origin_label = origin_map.get(self.origin_type, '')
        origin_parts = [origin_label]
        if self.origin_fair_tag_id:
            origin_parts.append(self.origin_fair_tag_id.name)
        if self.origin_note:
            origin_parts.append(self.origin_note)
        if self.agent_name:
            origin_parts.append('Agente: %s' % self.agent_name)

        project.message_post(
            body=_("Progetto creato dal wizard Scrivania Commerciale. "
                   "Origine: %s") % ' — '.join(origin_parts),
        )

        # 5. Activity if next_action provided
        if self.next_action and self.next_action_date:
            todo_type = self.env.ref(
                'mail.mail_activity_data_todo',
                raise_if_not_found=False,
            )
            self.env['mail.activity'].create({
                'res_model_id': self.env['ir.model']._get(
                    'project.project').id,
                'res_id': project.id,
                'summary': self.next_action,
                'date_deadline': self.next_action_date,
                'user_id': self.user_id.id,
                'activity_type_id': (
                    todo_type.id if todo_type else False
                ),
            })

        # 6. Open created project
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': project.id,
            'views': [[False, 'form']],
            'target': 'current',
        }
