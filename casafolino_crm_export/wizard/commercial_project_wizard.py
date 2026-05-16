import logging

from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CfCommercialProjectWizard(models.TransientModel):
    _name = 'cf.commercial.project.wizard'
    _description = 'Wizard nuovo progetto commerciale'

    wizard_step = fields.Selection([
        ('client', 'Cliente'),
        ('origin', 'Origine'),
        ('brief', 'Brief'),
        ('plan', 'Piano'),
        ('confirm', 'Conferma'),
    ], default='client', required=True)
    step_html = fields.Html(compute='_compute_step_html', sanitize=False)

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
    project_name = fields.Char(string='Nome dossier')
    project_type = fields.Selection([
        ('sample_fair', 'Campionatura Fiera'),
        ('sample_client', 'Campionatura Cliente'),
        ('custom_label', 'Etichetta Personalizzata'),
        ('new_product', 'Lancio Nuovo Prodotto'),
        ('fair_prep', 'Preparazione Fiera'),
        ('strategic', 'Progetto Strategico'),
    ], string='Tipo progetto', default='strategic')
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
    volume_target = fields.Char(string='Volume target libero')
    volume_qty = fields.Float(string='Volume target')
    volume_unit = fields.Selection([
        ('unit', 'Unità (pezzi)'),
        ('cartoni', 'Cartoni'),
        ('pallet', 'Pallet'),
        ('kg', 'Kg'),
        ('tonnellate', 'Tonnellate'),
    ], string='Unità', default='unit')
    margin_target = fields.Float(string='Margine target %')
    value_estimate = fields.Float(string='Valore stimato')
    certification_ids = fields.Many2many(
        'cf.export.certification', string='Certificazioni')
    incoterms = fields.Selection([
        ('exw', 'EXW'), ('fca', 'FCA'), ('fob', 'FOB'),
        ('cif', 'CIF'), ('ddp', 'DDP'),
    ], string='Incoterms')
    payment_term = fields.Selection([
        ('advance', 'Anticipo 100%'),
        ('30_70', '30% advance / 70% balance'),
        ('50_50', '50/50'),
        ('lc', 'LC at sight'),
        ('30_days', '30 giorni FM'),
        ('60_days', '60 giorni FM'),
        ('open_account', 'Open account'),
    ], string='Pagamento')
    moq = fields.Char(string='MOQ')
    lead_time = fields.Integer(string='Lead time (gg)')
    shelf_life = fields.Integer(string='Shelf life (mesi)')
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
    target_date = fields.Date(string='Data target dossier')
    create_lead = fields.Boolean(string='Crea lead collegato', default=True)
    lead_name = fields.Char(string='Nome lead')
    expected_revenue = fields.Float(string='Ricavo atteso')
    internal_notes = fields.Text(string='Note interne')

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

    def _step_order(self):
        return ['client', 'origin', 'brief', 'plan', 'confirm']

    @api.depends('wizard_step')
    def _compute_step_html(self):
        labels = dict(self._fields['wizard_step'].selection)
        order = self._step_order()
        for w in self:
            active_idx = order.index(w.wizard_step or 'client')
            chunks = []
            for idx, step in enumerate(order):
                bg = '#6B4A1E' if idx == active_idx else (
                    '#C8A43A' if idx < active_idx else '#E8E4DE')
                fg = '#F5E6C8' if idx == active_idx else (
                    '#3E2518' if idx < active_idx else '#8B7355')
                chunks.append(
                    '<span style="display:inline-flex;align-items:center;'
                    'gap:6px;margin-right:8px;margin-bottom:6px;'
                    'background:%s;color:%s;border-radius:999px;'
                    'padding:5px 10px;font-size:12px;">'
                    '<b>%d</b>%s</span>' % (
                        bg, fg, idx + 1, labels.get(step, step))
                )
            w.step_html = Markup('<div style="margin-bottom:8px">%s</div>') % (
                Markup(''.join(chunks)))

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
        'priority', 'volume_target', 'volume_qty', 'volume_unit',
        'margin_target', 'value_estimate', 'product_category',
        'project_name', 'next_action', 'next_action_date', 'target_date',
        'create_lead', 'expected_revenue',
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
                w.project_name or w._default_project_name()
                or '— Dossier commerciale —'
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
            if w.volume_qty:
                unit_label = dict(w._fields['volume_unit'].selection).get(
                    w.volume_unit, '')
                volume_str = '%s %s' % ('{:g}'.format(w.volume_qty), unit_label)
            else:
                volume_str = w.volume_target or '—'
            date_str = (
                w.next_action_date.strftime('%d %b')
                if w.next_action_date else ''
            )
            value_str = (
                '€ {:,.0f}'.format(w.value_estimate).replace(',', '.')
                if w.value_estimate else '—')
            lead_str = (
                'Lead € {:,.0f}'.format(w.expected_revenue).replace(',', '.')
                if w.create_lead and w.expected_revenue else
                ('Lead collegato' if w.create_lead else 'Solo dossier'))
            w.preview_html = Markup(
                '<div style="background:white;border:0.5px solid '
                'rgba(0,0,0,0.1);border-radius:8px;padding:12px;">'
                '<div style="margin-bottom:8px;">%s</div>'
                '<div style="font-size:13px;font-weight:500;'
                'margin-bottom:4px;">%s%s</div>'
                '<div style="font-size:11px;color:#666;margin-bottom:8px;">'
                'Valore dossier: <b>%s</b> &middot; %s</div>'
                '<div style="display:flex;justify-content:space-between;'
                'font-size:11px;color:#888;padding-top:8px;'
                'border-top:0.5px solid rgba(0,0,0,0.05);">'
                '<span>%s &middot; %s</span>'
                '<span>%s</span></div></div>'
            ) % (
                badges_html,
                name,
                (' — ' + cat) if cat else '',
                value_str, lead_str,
                volume_str, margin_str, date_str,
            )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.country_id = self.partner_id.country_id
            self.lang = self.partner_id.lang or 'en_US'
            self.is_new_partner = False
            if not self.project_name:
                self.project_name = self._default_project_name()

    @api.onchange('new_partner_name', 'product_category')
    def _onchange_project_name_parts(self):
        if not self.project_name:
            self.project_name = self._default_project_name()

    @api.onchange('product_category')
    def _onchange_product_category(self):
        mapping = {
            'crema': 'sample_client',
            'crispy': 'new_product',
            'cioccolato': 'new_product',
            'altro': 'strategic',
        }
        if self.product_category:
            self.project_type = mapping.get(self.product_category, 'sample_client')
        if not self.lead_name:
            self.lead_name = self._default_project_name(prefix='Lead')

    def _default_project_name(self, prefix=False):
        self.ensure_one()
        partner_name = (
            self.partner_id.name or self.new_partner_name or ''
        )
        cat_map = dict(self._fields['product_category'].selection or [])
        cat_label = cat_map.get(self.product_category, '')
        if not partner_name and not cat_label:
            return ''
        base = partner_name or _('Nuovo cliente')
        if cat_label:
            base = '%s — %s' % (base, cat_label)
        return '%s %s' % (prefix, base) if prefix else base

    def _validate_step(self, step):
        self.ensure_one()
        if step == 'client':
            if not self.partner_id and not self.new_partner_name:
                raise UserError(_("Scegli un cliente o inserisci un nuovo nome."))
        elif step == 'origin':
            if self.origin_type == 'fair' and not self.origin_fair_tag_id:
                raise UserError(_("Se l'origine è Fiera, indica quale fiera."))
        elif step == 'brief':
            if not self.product_category:
                raise UserError(_("Indica almeno la categoria prodotto."))
            if not self.project_name:
                self.project_name = self._default_project_name()
        elif step == 'plan':
            if bool(self.next_action) != bool(self.next_action_date):
                raise UserError(_(
                    "Compila sia prossima azione sia data, oppure lasciale vuote."))

    def action_next_step(self):
        self.ensure_one()
        order = self._step_order()
        step = self.wizard_step or order[0]
        self._validate_step(step)
        idx = order.index(step)
        self.wizard_step = order[min(idx + 1, len(order) - 1)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_prev_step(self):
        self.ensure_one()
        order = self._step_order()
        idx = order.index(self.wizard_step or order[0])
        self.wizard_step = order[max(idx - 1, 0)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_project(self):
        self.ensure_one()
        for step in self._step_order()[:-1]:
            self._validate_step(step)

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
        project_name = self.project_name or (
            '%s — %s' % (partner.name, cat_label)
            if cat_label else partner.name
        )

        # 3. Create project.project
        vals = {
            'name': project_name,
            'partner_id': partner.id,
            'cf_partner_id': partner.id,
            'user_id': self.user_id.id,
            'cf_status_dossier': 'active',
            'cf_dossier_priority': self.priority or 'medium',
            'cf_project_type': self.project_type or False,
            'cf_dossier_lang': (self.lang or 'en_US')[:2],
            'cf_dossier_value_estimate': self.value_estimate or 0.0,
            'cf_next_action': self.next_action or False,
            'cf_next_action_date': self.next_action_date or False,
            'date': self.target_date or self.next_action_date or False,
            'cf_volume_unit': self.volume_unit or 'unit',
            'cf_incoterms': self.incoterms or False,
            'cf_payment_term': self.payment_term or False,
            'cf_moq': self.moq or False,
            'cf_lead_time': self.lead_time or 0,
            'cf_shelf_life': self.shelf_life or 0,
            'cf_internal_notes': self.internal_notes or False,
        }
        if self.certification_ids:
            vals['cf_certification_ids'] = [
                (6, 0, self.certification_ids.ids)]

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

        if self.volume_qty:
            vals['cf_volume_target'] = self.volume_qty
        elif self.volume_target:
            vals['cf_internal_notes'] = '%s\nVolume target: %s' % (
                vals.get('cf_internal_notes') or '', self.volume_target)
        if self.margin_target:
            vals['cf_margin_target'] = self.margin_target

        project = self.env['project.project'].create(vals)

        lead = self.env['crm.lead']
        if self.create_lead:
            lead = self.env['crm.lead'].create({
                'name': self.lead_name or project_name,
                'type': 'lead',
                'partner_id': partner.id,
                'user_id': self.user_id.id,
                'expected_revenue': self.expected_revenue or self.value_estimate or 0.0,
                'cf_project_id': project.id,
                'description': self.internal_notes or False,
            })

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
        if lead:
            origin_parts.append('Lead collegato: %s' % lead.display_name)

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
