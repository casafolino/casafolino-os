import logging
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

OWNER_LOGIN_COLOR = {
    'antonio@casafolino.com': 'green',
    'josefina.lazzaro@casafolino.com': 'purple',
    'martina.sinopoli@casafolino.com': 'gray',
}


class ProjectProject(models.Model):
    _inherit = 'project.project'

    cf_managed_by_id = fields.Many2one(
        comodel_name='res.partner',
        domain="[('cf_partner_role', '=', 'agent')]",
        string='Agente',
        index=True,
        tracking=True,
    )

    cf_status_dossier = fields.Selection(
        selection=[
            ('exploration', 'Esplorativo'),
            ('active', 'Attivo'),
            ('on_hold', 'In pausa'),
            ('won', 'Vinto / ricorrente'),
            ('closed', 'Chiuso'),
        ],
        string='Status dossier',
        default='exploration',
        index=True,
        tracking=True,
    )

    cf_is_won = fields.Boolean(string='Vinto', default=False, tracking=True)
    cf_won_date = fields.Date(string='Data vinto')
    cf_recurring = fields.Boolean(string='Ricorrente')

    cf_dossier_priority = fields.Selection(
        selection=[
            ('low', 'Bassa'),
            ('medium', 'Media'),
            ('high', 'Alta'),
        ],
        string='Priorità dossier',
        default='medium',
    )

    cf_dossier_value_estimate = fields.Float(
        string='Valore stimato dossier',
    )

    cf_open_issues_count = fields.Integer(
        compute='_compute_cf_dossier_stats',
        string='Reclami aperti',
    )

    cf_last_activity_date = fields.Datetime(
        compute='_compute_cf_dossier_stats',
        string='Ultima attività',
    )

    cf_lead_count = fields.Integer(
        compute='_compute_cf_dossier_stats',
        string='Lead/quotazioni',
    )

    # Reverse relation from crm.lead.cf_project_id
    cf_lead_ids = fields.One2many(
        'crm.lead', 'cf_project_id',
        string='Lead CRM collegati',
    )

    # ------------------------------------------------------------------
    # Brief Commerciale fields
    # ------------------------------------------------------------------

    cf_buyer_id = fields.Many2one(
        'res.partner', string='Buyer',
        ondelete='set null', index=True,
    )
    cf_dossier_lang = fields.Selection([
        ('it', 'Italiano'), ('en', 'English'), ('es', 'Español'),
        ('fr', 'Français'), ('de', 'Deutsch'), ('pt', 'Português'),
        ('ar', 'العربية'), ('zh', '中文'),
    ], string='Lingua', default='en')
    cf_volume_target = fields.Float('Volume Target')
    cf_volume_unit = fields.Selection([
        ('unit', 'Unità (pezzi)'), ('cartoni', 'Cartoni'),
        ('pallet', 'Pallet'), ('kg', 'Kg'), ('tonnellate', 'Tonnellate'),
    ], string='Unità', default='unit')
    cf_margin_target = fields.Float(
        'Margine Target %',
        help='Margine in percentuale (es. 32 per 32%)',
    )
    cf_certification_ids = fields.Many2many(
        'cf.export.certification', string='Certificazioni',
    )
    cf_next_action = fields.Char('Prossima Azione', size=256)
    cf_next_action_date = fields.Date('Data Prossima Azione')
    cf_internal_notes = fields.Text('Note Interne')

    # ------------------------------------------------------------------
    # Dettagli Commerciali
    # ------------------------------------------------------------------

    cf_incoterms = fields.Selection([
        ('exw', 'EXW'), ('fca', 'FCA'), ('fob', 'FOB'),
        ('cif', 'CIF'), ('ddp', 'DDP'),
    ], string='Incoterms')
    cf_payment_term = fields.Selection([
        ('advance', 'Anticipo 100%'),
        ('30_70', '30% advance / 70% balance'),
        ('50_50', '50/50'),
        ('lc', 'LC at sight'),
        ('30_days', '30 giorni FM'),
        ('60_days', '60 giorni FM'),
        ('open_account', 'Open account'),
    ], string='Pagamento')
    cf_moq = fields.Char('MOQ', size=128)
    cf_lead_time = fields.Integer('Lead Time (gg)')
    cf_shelf_life = fields.Integer('Shelf Life (mesi)')

    # ------------------------------------------------------------------
    # Multi-operatore
    # ------------------------------------------------------------------

    cf_co_user_ids = fields.Many2many(
        'res.users', 'project_co_user_rel',
        string='Co-responsabili',
        help='Operatori interni che possono visualizzare e modificare il dossier',
    )

    # ------------------------------------------------------------------
    # Template origin
    # ------------------------------------------------------------------

    cf_template_origin_id = fields.Many2one(
        'cf.dossier.template', string='Da template',
        ondelete='set null', readonly=True,
    )

    # ------------------------------------------------------------------
    # Network & Commissioni
    # ------------------------------------------------------------------

    cf_actor_ids = fields.One2many(
        'cf.dossier.actor', 'project_id', string='Network e Commissioni',
    )
    cf_actor_count = fields.Integer(
        compute='_compute_cf_actor_count', string='Network',
    )

    # ------------------------------------------------------------------
    # Multi-contatti per dossier
    # ------------------------------------------------------------------

    cf_contact_ids = fields.One2many(
        'cf.project.contact', 'project_id',
        string='Contatti progetto',
    )

    # ------------------------------------------------------------------
    # Related inline lists (read-only computed Many2many)
    # ------------------------------------------------------------------

    cf_dossier_mail_ids = fields.Many2many(
        'casafolino.mail.message', compute='_compute_cf_dossier_mail_ids',
        string='Mail dossier',
    )
    cf_dossier_sample_ids = fields.Many2many(
        'cf.export.sample', compute='_compute_cf_dossier_sample_ids',
        string='Campionature dossier',
    )
    cf_dossier_attachment_ids = fields.Many2many(
        'ir.attachment', compute='_compute_cf_dossier_attachment_ids',
        string='Documenti dossier',
    )

    # ------------------------------------------------------------------
    # Stat button counts (mail, sample, order — lead/issues in existing)
    # ------------------------------------------------------------------

    cf_mail_count = fields.Integer(
        compute='_compute_cf_mail_count', string='Mail',
    )
    cf_sample_count = fields.Integer(
        compute='_compute_cf_sample_count', string='Campionature',
    )
    cf_order_count = fields.Integer(
        compute='_compute_cf_order_count', string='Ordini',
    )

    # ------------------------------------------------------------------
    # Client-aware: storico partner (ordini, fatture, DDT, lead, mail)
    # ------------------------------------------------------------------

    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
        string='Valuta', readonly=True,
    )

    cf_partner_orders_count = fields.Integer(
        compute='_compute_partner_orders', string='Ordini partner',
    )
    cf_partner_orders_amount = fields.Monetary(
        compute='_compute_partner_orders', string='Fatturato ordini',
        currency_field='company_currency_id',
    )
    cf_partner_invoices_count = fields.Integer(
        compute='_compute_partner_invoices', string='Fatture partner',
    )
    cf_partner_ddt_count = fields.Integer(
        compute='_compute_partner_ddt', string='DDT partner',
    )
    cf_partner_leads_count = fields.Integer(
        compute='_compute_partner_leads', string='Lead partner',
    )
    cf_partner_mails_count = fields.Integer(
        compute='_compute_partner_mails', string='Mail partner',
    )
    cf_sibling_dossiers_ids = fields.Many2many(
        'project.project', compute='_compute_sibling_dossiers',
        string='Altri dossier stesso cliente',
    )
    cf_sibling_dossiers_count = fields.Integer(
        compute='_compute_sibling_dossiers', string='Altri dossier',
    )

    @api.depends('partner_id', 'cf_contact_ids', 'cf_contact_ids.email_normalized')
    def _compute_cf_mail_count(self):
        for rec in self:
            try:
                MailMsg = self.env.get('casafolino.mail.message')
                if not MailMsg:
                    rec.cf_mail_count = 0
                    continue
                domain = rec._cf_mail_domain()
                if domain:
                    rec.cf_mail_count = MailMsg.search_count(domain)
                else:
                    rec.cf_mail_count = 0
            except Exception:
                rec.cf_mail_count = 0

    @api.depends('partner_id')
    def _compute_cf_sample_count(self):
        for rec in self:
            try:
                Sample = self.env.get('cf.export.sample')
                if Sample and rec.partner_id:
                    rec.cf_sample_count = Sample.search_count([
                        ('partner_id', '=', rec.partner_id.id),
                    ])
                else:
                    rec.cf_sample_count = 0
            except Exception:
                rec.cf_sample_count = 0

    @api.depends('partner_id')
    def _compute_cf_order_count(self):
        for rec in self:
            try:
                SO = self.env.get('sale.order')
                if SO and rec.partner_id:
                    rec.cf_order_count = SO.search_count([
                        ('partner_id', '=', rec.partner_id.id),
                        ('state', 'not in', ('draft', 'cancel')),
                    ])
                else:
                    rec.cf_order_count = 0
            except Exception:
                rec.cf_order_count = 0

    # ------------------------------------------------------------------
    # Client-aware compute methods
    # ------------------------------------------------------------------

    def _get_partner_related_ids(self):
        """Return list of partner IDs related to this dossier's partner:
        the partner itself, children, and siblings under same commercial_partner."""
        self.ensure_one()
        if not self.partner_id:
            return []
        commercial = self.partner_id.commercial_partner_id or self.partner_id
        return self.env['res.partner'].search([
            '|',
            ('id', '=', self.partner_id.id),
            '|',
            ('parent_id', '=', commercial.id),
            ('commercial_partner_id', '=', commercial.id),
        ]).ids

    # ------------------------------------------------------------------
    # Domain-based email matching (for mail only)
    # ------------------------------------------------------------------

    _GENERIC_EMAIL_DOMAINS = {
        'gmail.com', 'googlemail.com', 'outlook.com', 'hotmail.com',
        'yahoo.com', 'yahoo.it', 'live.com', 'icloud.com', 'me.com',
        'libero.it', 'virgilio.it', 'tiscali.it', 'tin.it', 'alice.it',
        'aol.com', 'protonmail.com', 'pec.it',
    }

    def _get_email_domains(self):
        """Extract non-generic email domains from partner_id + cf_contact_ids."""
        self.ensure_one()
        domains = set()

        def _extract(email):
            if not email or '@' not in email:
                return None
            d = email.split('@')[-1].strip().lower()
            return None if d in self._GENERIC_EMAIL_DOMAINS else d

        if self.partner_id and self.partner_id.email:
            d = _extract(self.partner_id.email)
            if d:
                domains.add(d)
        for c in self.cf_contact_ids:
            d = _extract(c.email)
            if d:
                domains.add(d)
        return domains

    def _get_partner_ids_by_domain(self):
        """Find res.partner whose email matches dossier email domains."""
        self.ensure_one()
        domains = self._get_email_domains()
        if not domains:
            return []
        domain = []
        for d in domains:
            if domain:
                domain.insert(0, '|')
            domain.append(('email', '=ilike', '%%@%s' % d))
        return self.env['res.partner'].search(domain).ids

    def _get_all_related_partner_ids(self):
        """Union: partner_id tree + partners matching email domains."""
        self.ensure_one()
        ids = set(self._get_partner_related_ids())
        ids.update(self._get_partner_ids_by_domain())
        return list(ids)

    @api.depends('partner_id')
    def _compute_partner_orders(self):
        SO = self.env['sale.order']
        for p in self:
            if not p.partner_id:
                p.cf_partner_orders_count = 0
                p.cf_partner_orders_amount = 0
                continue
            related_ids = p._get_partner_related_ids()
            orders = SO.search([
                ('partner_id', 'in', related_ids),
                ('state', 'in', ['sale', 'done']),
            ])
            p.cf_partner_orders_count = len(orders)
            p.cf_partner_orders_amount = sum(orders.mapped('amount_total'))

    def action_view_partner_orders(self):
        self.ensure_one()
        related_ids = self._get_partner_related_ids()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ordini di %s') % (self.partner_id.name or ''),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', 'in', related_ids),
                ('state', 'in', ['sale', 'done']),
            ],
        }

    @api.depends('partner_id')
    def _compute_partner_invoices(self):
        AM = self.env['account.move']
        for p in self:
            if not p.partner_id:
                p.cf_partner_invoices_count = 0
                continue
            related_ids = p._get_partner_related_ids()
            p.cf_partner_invoices_count = AM.search_count([
                ('partner_id', 'in', related_ids),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '!=', 'cancel'),
            ])

    def action_view_partner_invoices(self):
        self.ensure_one()
        related_ids = self._get_partner_related_ids()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fatture di %s') % (self.partner_id.name or ''),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', 'in', related_ids),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '!=', 'cancel'),
            ],
        }

    @api.depends('partner_id')
    def _compute_partner_ddt(self):
        SP = self.env['stock.picking']
        for p in self:
            if not p.partner_id:
                p.cf_partner_ddt_count = 0
                continue
            related_ids = p._get_partner_related_ids()
            p.cf_partner_ddt_count = SP.search_count([
                ('partner_id', 'in', related_ids),
                ('state', '=', 'done'),
                ('picking_type_id.code', '=', 'outgoing'),
            ])

    def action_view_partner_ddt(self):
        self.ensure_one()
        related_ids = self._get_partner_related_ids()
        return {
            'type': 'ir.actions.act_window',
            'name': _('DDT di %s') % (self.partner_id.name or ''),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', 'in', related_ids),
                ('state', '=', 'done'),
                ('picking_type_id.code', '=', 'outgoing'),
            ],
        }

    @api.depends('partner_id')
    def _compute_partner_leads(self):
        Lead = self.env['crm.lead']
        for p in self:
            if not p.partner_id:
                p.cf_partner_leads_count = 0
                continue
            related_ids = p._get_partner_related_ids()
            p.cf_partner_leads_count = Lead.search_count([
                ('partner_id', 'in', related_ids),
            ])

    def action_view_partner_leads(self):
        self.ensure_one()
        related_ids = self._get_partner_related_ids()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lead di %s') % (self.partner_id.name or ''),
            'res_model': 'crm.lead',
            'view_mode': 'list,kanban,form',
            'domain': [('partner_id', 'in', related_ids)],
        }

    @api.depends('partner_id', 'cf_contact_ids.email')
    def _compute_partner_mails(self):
        MM = self.env['mail.message']
        for p in self:
            related_ids = p._get_all_related_partner_ids()
            if not related_ids:
                p.cf_partner_mails_count = 0
                continue
            p.cf_partner_mails_count = MM.search_count([
                '|',
                ('author_id', 'in', related_ids),
                ('partner_ids', 'in', related_ids),
            ])

    def action_view_partner_mails(self):
        self.ensure_one()
        related_ids = self._get_all_related_partner_ids()
        if not related_ids:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mail di %s') % (self.partner_id.name or 'cliente'),
            'res_model': 'mail.message',
            'view_mode': 'list,form',
            'domain': [
                '|',
                ('author_id', 'in', related_ids),
                ('partner_ids', 'in', related_ids),
            ],
        }

    @api.depends('partner_id')
    def _compute_sibling_dossiers(self):
        Project = self.env['project.project']
        for p in self:
            if not p.partner_id:
                p.cf_sibling_dossiers_ids = False
                p.cf_sibling_dossiers_count = 0
                continue
            commercial = p.partner_id.commercial_partner_id or p.partner_id
            siblings = Project.search([
                ('id', '!=', p.id),
                '|',
                ('partner_id.commercial_partner_id', '=', commercial.id),
                ('partner_id', '=', commercial.id),
            ])
            p.cf_sibling_dossiers_ids = siblings
            p.cf_sibling_dossiers_count = len(siblings)

    def action_view_sibling_dossiers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Altri dossier %s') % (self.partner_id.name if self.partner_id else ''),
            'res_model': 'project.project',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', self.cf_sibling_dossiers_ids.ids)],
        }

    @api.depends('cf_actor_ids')
    def _compute_cf_actor_count(self):
        for rec in self:
            rec.cf_actor_count = len(rec.cf_actor_ids)

    @api.depends('partner_id', 'cf_contact_ids', 'cf_contact_ids.email_normalized')
    def _compute_cf_dossier_mail_ids(self):
        for rec in self:
            try:
                MailMsg = self.env.get('casafolino.mail.message')
                if not MailMsg:
                    rec.cf_dossier_mail_ids = False
                    continue
                domain = rec._cf_mail_domain()
                if domain:
                    rec.cf_dossier_mail_ids = MailMsg.search(
                        domain, order='email_date desc', limit=200)
                else:
                    rec.cf_dossier_mail_ids = False
            except Exception:
                rec.cf_dossier_mail_ids = False

    def _cf_mail_domain(self):
        """Build search domain for casafolino.mail.message matching
        partner_id OR any contact email."""
        self.ensure_one()
        emails = list(filter(
            None, self.cf_contact_ids.mapped('email_normalized')))
        partner_ids = []
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        partner_ids += self.cf_contact_ids.mapped('partner_id').ids
        partner_ids = list(set(filter(None, partner_ids)))

        if not emails and not partner_ids:
            return None

        parts = []
        if partner_ids:
            parts.append(('partner_id', 'in', partner_ids))
        if emails:
            parts.append(('sender_email', 'in', emails))

        if len(parts) == 2:
            return ['|'] + parts
        return parts

    def action_cf_compose_mail(self):
        """Open standard Odoo mail composer pre-populated."""
        self.ensure_one()
        primary = self.cf_contact_ids.filtered('is_primary')[:1]
        partner = (
            primary.partner_id or self.partner_id
            if primary else self.partner_id
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scrivi mail'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_composition_mode': 'comment',
                'default_model': 'project.project',
                'default_res_ids': [self.id],
                'default_partner_ids': (
                    [partner.id] if partner else []
                ),
                'default_subject': '[%s] ' % (self.name or ''),
            },
        }

    def action_compose_email_f8(self):
        """Open F8 Outlook-style composer via client action."""
        self.ensure_one()
        primary = self.cf_contact_ids.filtered('is_primary')[:1]
        partner = primary.partner_id or self.partner_id if primary else self.partner_id
        email = partner.email if partner else ''
        return {
            'type': 'ir.actions.client',
            'tag': 'casafolino_mail.compose_f8',
            'context': {
                'default_partner_email': email,
                'default_subject': '[%s] ' % (self.name or ''),
                'default_partner_id': partner.id if partner else False,
                'default_thread_id': self.id,
                'default_thread_model': 'project.project',
            },
        }

    @api.depends('partner_id')
    def _compute_cf_dossier_sample_ids(self):
        for rec in self:
            try:
                Sample = self.env.get('cf.export.sample')
                if Sample and rec.partner_id:
                    rec.cf_dossier_sample_ids = Sample.search([
                        ('partner_id', '=', rec.partner_id.id),
                    ], order='create_date desc', limit=50)
                else:
                    rec.cf_dossier_sample_ids = False
            except Exception:
                rec.cf_dossier_sample_ids = False

    @api.depends('partner_id')
    def _compute_cf_dossier_attachment_ids(self):
        for rec in self:
            try:
                Att = self.env['ir.attachment']
                domain = ['|',
                    '&', ('res_model', '=', 'project.project'), ('res_id', '=', rec.id),
                    '&', ('res_model', '=', 'res.partner'),
                          ('res_id', '=', rec.partner_id.id if rec.partner_id else 0),
                ]
                rec.cf_dossier_attachment_ids = Att.search(domain, order='create_date desc', limit=50)
            except Exception:
                rec.cf_dossier_attachment_ids = False

    # ------------------------------------------------------------------
    # Write override: auto-add co-responsabili as followers
    # ------------------------------------------------------------------

    def write(self, vals):
        res = super().write(vals)
        if 'cf_co_user_ids' in vals:
            for rec in self:
                partner_ids = rec.cf_co_user_ids.mapped('partner_id').ids
                existing = rec.message_partner_ids.ids
                to_add = [pid for pid in partner_ids if pid and pid not in existing]
                if to_add:
                    rec.message_subscribe(partner_ids=to_add)
        return res

    # ------------------------------------------------------------------
    # Stat button actions
    # ------------------------------------------------------------------

    def action_open_dossier_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead — %s' % self.name,
            'res_model': 'crm.lead',
            'view_mode': 'list,kanban,form',
            'domain': [('cf_project_id', '=', self.id)],
            'context': {
                'default_cf_project_id': self.id,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
            },
        }

    def action_open_dossier_mails(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mail — %s' % self.name,
            'res_model': 'casafolino.mail.message',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id if self.partner_id else 0),
                ('state', 'in', ('keep', 'auto_keep')),
            ],
        }

    def action_open_dossier_samples(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Campionature — %s' % self.name,
            'res_model': 'cf.export.sample',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id if self.partner_id else 0),
            ],
        }

    def action_open_dossier_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ordini — %s' % self.name,
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.partner_id.id if self.partner_id else 0),
                ('state', 'not in', ('draft', 'cancel')),
            ],
        }

    def action_open_dossier_actors(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Network — %s' % self.name,
            'res_model': 'cf.dossier.actor',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_project_dashboard_360(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'casafolino_crm_export.project_dashboard',
            'name': 'Vista 360° — %s' % self.name,
            'context': {
                'default_project_id': self.id,
                'active_id': self.id,
                'active_model': 'project.project',
            },
            'target': 'main',
        }

    @api.depends('partner_id')
    def _compute_cf_dossier_stats(self):
        if not self.ids:
            for p in self:
                p.cf_open_issues_count = 0
                p.cf_last_activity_date = False
                p.cf_lead_count = 0
            return

        # Lead counts
        self.env.cr.execute("""
            SELECT cf_project_id, COUNT(*)
            FROM crm_lead
            WHERE cf_project_id IN %s AND active = true
            GROUP BY cf_project_id
        """, (tuple(self.ids),))
        lead_counts = dict(self.env.cr.fetchall())

        # Last activity
        self.env.cr.execute("""
            SELECT cf_project_id, MAX(write_date)
            FROM crm_lead
            WHERE cf_project_id IN %s AND active = true
            GROUP BY cf_project_id
        """, (tuple(self.ids),))
        last_dates = dict(self.env.cr.fetchall())

        # Open issues
        self.env.cr.execute("""
            SELECT l.cf_project_id, COUNT(*)
            FROM crm_lead l
            JOIN crm_tag_rel ctr ON ctr.lead_id = l.id
            JOIN crm_tag t ON t.id = ctr.tag_id
            WHERE l.cf_project_id IN %s
              AND l.active = true
              AND t.cf_category = 'issue'
            GROUP BY l.cf_project_id
        """, (tuple(self.ids),))
        issue_counts = dict(self.env.cr.fetchall())

        for project in self:
            project.cf_lead_count = lead_counts.get(project.id, 0)
            project.cf_last_activity_date = last_dates.get(project.id) or project.write_date
            project.cf_open_issues_count = issue_counts.get(project.id, 0)

    # ------------------------------------------------------------------
    # Dashboard 360° aggregator — Brief #5.0
    # ------------------------------------------------------------------

    def cf_get_dashboard_data(self):
        """Single aggregator for the 360° OWL dashboard.
        Returns a JSON-serializable dict with all data the frontend needs."""
        self.ensure_one()

        # Find main lead (highest expected_revenue)
        leads = self.env['crm.lead'].search(
            [('cf_project_id', '=', self.id), ('active', '=', True)],
            order='expected_revenue desc',
            limit=10,
        )
        lead = leads[:1] if leads else self.env['crm.lead']
        partner = lead.partner_id if lead else self.partner_id

        return {
            'project': self._cf_serialize_project(),
            'lead': self._cf_serialize_lead(lead) if lead else None,
            'partner': self._cf_serialize_partner(partner) if partner else None,
            'kpi': self._cf_compute_kpi(leads, partner),
            'timeline': self._cf_get_timeline(limit=20),
            'contacts': self._cf_get_contacts(partner) if partner else [],
            'owner': self._cf_serialize_owner(),
            # Brief #B6
            'mail': self._cf_get_mail_timeline(limit=20),
            'mail_count': self._cf_get_mail_count(),
            # Brief #FINAL
            'commerciale': self._cf_get_commerciale(partner),
            'campionature': self._cf_get_campionature(leads),
            'documenti': self._cf_get_documenti(),
            'note': self._cf_get_note(),
        }

    def _cf_serialize_project(self):
        return {
            'id': self.id,
            'name': self.name or '',
            'status_dossier': self.cf_status_dossier or 'exploration',
            'dossier_priority': self.cf_dossier_priority or 'medium',
            'create_date': fields.Datetime.to_string(self.create_date) if self.create_date else '',
        }

    def _cf_serialize_lead(self, lead):
        if not lead:
            return None
        stage_name = lead.stage_id.name if lead.stage_id else ''
        stage_seq = lead.stage_id.sequence if lead.stage_id else 0
        return {
            'id': lead.id,
            'name': lead.name or '',
            'stage_name': stage_name,
            'stage_sequence': stage_seq,
            'stage_position': max(1, min(9, stage_seq // 10)) if stage_seq else 0,
            'expected_revenue': lead.expected_revenue or 0,
            'probability': lead.probability or 0,
            'priority': lead.priority or '0',
            'score': lead.cf_lead_score or 0,
            'rotting_state': lead.cf_rotting_state or 'ok',
            'days_in_stage': lead.cf_days_in_stage or 0,
            'forecast_value': lead.cf_forecast_value or 0,
        }

    def _cf_serialize_partner(self, partner):
        if not partner:
            return None
        country = partner.country_id
        return {
            'id': partner.id,
            'name': partner.name or '',
            'city': partner.city or '',
            'country_name': country.name if country else '',
            'country_code': (country.code or '').upper() if country else '',
            'phone': partner.phone or '',
            'mobile': partner.mobile or '',
            'email': partner.email or '',
            'website': partner.website or '',
            'lang': partner.lang or '',
        }

    def _cf_serialize_owner(self):
        user = self.user_id or self.env.user
        login = (user.login or '').lower().strip()
        color_class = OWNER_LOGIN_COLOR.get(login, 'gray')
        name = user.name or ''
        parts = name.split()
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[-1][0]).upper()
        elif name:
            initials = name[:2].upper()
        else:
            initials = '?'
        return {
            'id': user.id,
            'name': name,
            'initials': initials,
            'color_class': color_class,
            'login': login,
        }

    def _cf_compute_kpi(self, leads, partner):
        # Revenue forecast
        total_revenue = sum(leads.mapped('expected_revenue'))
        total_forecast = sum(leads.mapped('cf_forecast_value'))

        # Sample count
        sample_count = 0
        if leads:
            sample_count = sum(leads.mapped('cf_sample_count'))

        # Email count
        email_count = 0
        if partner:
            email_count = self.env['mail.message'].search_count([
                ('partner_ids', 'in', partner.id),
                ('message_type', 'in', ['email', 'email_outgoing']),
            ])

        # Next activity
        next_activity = None
        activities = self.env['mail.activity'].search([
            '|',
            '&', ('res_model', '=', 'project.project'), ('res_id', '=', self.id),
            '&', ('res_model', '=', 'crm.lead'), ('res_id', 'in', leads.ids),
        ], order='date_deadline asc', limit=1)
        if activities:
            act = activities[0]
            next_activity = {
                'summary': act.summary or (act.activity_type_id.name if act.activity_type_id else ''),
                'date': fields.Date.to_string(act.date_deadline) if act.date_deadline else '',
                'type': act.activity_type_id.name if act.activity_type_id else '',
            }

        return {
            'revenue': total_revenue,
            'forecast': total_forecast,
            'sample_count': sample_count,
            'email_count': email_count,
            'next_activity': next_activity,
            'lead_count': len(leads),
        }

    def _cf_get_timeline(self, limit=20):
        """Unified timeline: mail.message + mail.activity for project and its leads."""
        events = []

        lead_ids = self.env['crm.lead'].search(
            [('cf_project_id', '=', self.id), ('active', '=', True)],
        ).ids

        # Mail messages on project
        messages = self.env['mail.message'].search([
            '|',
            '&', ('model', '=', 'project.project'), ('res_id', '=', self.id),
            '&', ('model', '=', 'crm.lead'), ('res_id', 'in', lead_ids),
        ], order='date desc', limit=limit)

        now = datetime.utcnow()
        for msg in messages:
            msg_type = msg.message_type or 'notification'
            if msg_type == 'notification' and msg.subtype_id and msg.subtype_id.internal:
                icon = 'note'
                color = 'gray'
                type_label = 'Nota'
            elif msg_type in ('email', 'email_outgoing'):
                icon = 'mail'
                color = 'blue'
                type_label = 'Email'
            elif msg_type == 'comment':
                icon = 'message'
                color = 'green'
                type_label = 'Commento'
            else:
                icon = 'bell'
                color = 'gray'
                type_label = 'Notifica'

            date_str = fields.Datetime.to_string(msg.date) if msg.date else ''
            events.append({
                'type': icon,
                'color': color,
                'type_label': type_label,
                'title': msg.subject or type_label,
                'subtitle': (msg.body or '')[:120] if msg.body else '',
                'date': date_str,
                'date_label': self._cf_relative_date(msg.date, now) if msg.date else '',
                'author': msg.author_id.name if msg.author_id else '',
                'model': msg.model or '',
            })

        # Activities (upcoming)
        activities = self.env['mail.activity'].search([
            '|',
            '&', ('res_model', '=', 'project.project'), ('res_id', '=', self.id),
            '&', ('res_model', '=', 'crm.lead'), ('res_id', 'in', lead_ids),
        ], order='date_deadline asc', limit=5)

        for act in activities:
            dl = act.date_deadline
            events.append({
                'type': 'activity',
                'color': 'orange',
                'type_label': 'Attività',
                'title': act.summary or (act.activity_type_id.name if act.activity_type_id else 'Attività'),
                'subtitle': act.note[:120] if act.note else '',
                'date': fields.Date.to_string(dl) if dl else '',
                'date_label': self._cf_relative_date(
                    datetime.combine(dl, datetime.min.time()), now
                ) if dl else '',
                'author': act.user_id.name if act.user_id else '',
                'model': act.res_model or '',
            })

        # Sort by date desc, limit
        events.sort(key=lambda e: e.get('date', ''), reverse=True)
        return events[:limit]

    def _cf_relative_date(self, dt, now):
        if not dt:
            return ''
        if isinstance(dt, str):
            return dt
        delta = now - dt
        minutes = int(delta.total_seconds() / 60)
        if minutes < 0:
            # Future (activities)
            abs_min = abs(minutes)
            if abs_min < 60:
                return 'tra %dm' % abs_min
            if abs_min < 1440:
                return 'tra %dh' % (abs_min // 60)
            return 'tra %dgg' % (abs_min // 1440)
        if minutes < 5:
            return 'ora'
        if minutes < 60:
            return '%dm fa' % minutes
        if minutes < 1440:
            return '%dh fa' % (minutes // 60)
        if minutes < 10080:
            return '%dgg fa' % (minutes // 1440)
        return '%d sett fa' % (minutes // 10080)

    def _cf_get_contacts(self, partner):
        if not partner:
            return []
        # Company + child contacts
        contacts = []
        # Primary partner first
        contacts.append(self._cf_contact_dict(partner, is_primary=True))

        children = self.env['res.partner'].search([
            ('parent_id', '=', partner.id),
            ('active', '=', True),
        ], limit=9, order='name')
        for child in children:
            contacts.append(self._cf_contact_dict(child, is_primary=False))

        return contacts[:10]

    def _cf_contact_dict(self, partner, is_primary=False):
        return {
            'id': partner.id,
            'name': partner.name or '',
            'email': partner.email or '',
            'phone': partner.phone or partner.mobile or '',
            'function': partner.function or '',
            'is_primary': is_primary,
        }

    # ── Brief #FINAL — Commerciale ────────────────────────────────

    def _cf_get_commerciale(self, partner):
        """Sale orders del partner + pricelist + MOQ notes."""
        if not partner:
            return {
                'orders': [], 'orders_count': 0,
                'orders_total_amount': 0.0, 'pricelist_id': None,
                'last_quote_date': None, 'moq_notes': None,
            }
        now = datetime.utcnow()
        SaleOrder = self.env['sale.order']
        orders = SaleOrder.search([
            ('partner_id', '=', partner.id),
        ], order='date_order desc', limit=10)
        state_labels = dict(SaleOrder._fields['state'].selection) if 'state' in SaleOrder._fields else {}
        return {
            'orders': [
                {
                    'id': o.id,
                    'name': o.name or '',
                    'state': o.state or '',
                    'state_label': state_labels.get(o.state, o.state or ''),
                    'amount_total': o.amount_total or 0,
                    'currency': o.currency_id.name if o.currency_id else 'EUR',
                    'date_order': fields.Datetime.to_string(o.date_order) if o.date_order else None,
                    'date_label': self._cf_relative_date(o.date_order, now) if o.date_order else '',
                }
                for o in orders
            ],
            'orders_count': SaleOrder.search_count([('partner_id', '=', partner.id)]),
            'orders_total_amount': sum(o.amount_total for o in orders),
            'pricelist_id': [partner.property_product_pricelist.id, partner.property_product_pricelist.name]
                if partner.property_product_pricelist else None,
            'last_quote_date': fields.Datetime.to_string(orders[0].date_order) if orders and orders[0].date_order else None,
            'moq_notes': (partner.comment or '')[:500] or None,
        }

    # ── Brief #FINAL — Campionature ────────────────────────────────

    def _cf_get_campionature(self, leads):
        """cf.export.sample dei lead collegati al progetto."""
        if not leads:
            return {'samples': [], 'samples_count': 0, 'samples_by_state': {}}
        now = datetime.utcnow()
        Sample = self.env['cf.export.sample']
        samples = Sample.search([
            ('lead_id', 'in', leads.ids),
        ], order='create_date desc', limit=15)
        state_labels = dict(Sample._fields['state'].selection) if 'state' in Sample._fields else {}
        by_state = {}
        for s in samples:
            st = s.state or 'draft'
            by_state[st] = by_state.get(st, 0) + 1
        return {
            'samples': [
                {
                    'id': s.id,
                    'name': s.reference or f"CAMP-{s.id}",
                    'state': s.state or 'draft',
                    'state_label': state_labels.get(s.state, s.state or ''),
                    'create_date': fields.Datetime.to_string(s.create_date) if s.create_date else None,
                    'date_label': self._cf_relative_date(s.create_date, now) if s.create_date else '',
                    'lead_name': s.lead_id.name or '',
                    'partner_name': s.partner_id.name or '',
                    'product_count': len(s.product_ids),
                    'feedback_score': s.feedback_score or '',
                }
                for s in samples
            ],
            'samples_count': Sample.search_count([('lead_id', 'in', leads.ids)]),
            'samples_by_state': {state_labels.get(k, k): v for k, v in by_state.items()},
        }

    # ── Brief #FINAL — Documenti ───────────────────────────────────

    def _cf_get_documenti(self, limit=20):
        """ir.attachment del progetto + del partner."""
        self.ensure_one()
        partner_id = self.partner_id.id if self.partner_id else None
        Attachment = self.env['ir.attachment']
        domain = ['|',
            '&', ('res_model', '=', 'project.project'), ('res_id', '=', self.id),
            '&', ('res_model', '=', 'res.partner'), ('res_id', '=', partner_id or 0),
        ]
        atts = Attachment.search(domain, order='create_date desc', limit=limit)
        now = datetime.utcnow()
        return {
            'attachments': [
                {
                    'id': a.id,
                    'name': a.name or '',
                    'size': a.file_size or 0,
                    'size_label': self._cf_format_size(a.file_size),
                    'mimetype': a.mimetype or 'application/octet-stream',
                    'icon_class': self._cf_mimetype_icon(a.mimetype),
                    'create_date': fields.Datetime.to_string(a.create_date),
                    'date_label': self._cf_relative_date(a.create_date, now) if a.create_date else '',
                    'source': 'project' if a.res_model == 'project.project' else 'partner',
                    'url': '/web/content/%d?download=true' % a.id,
                }
                for a in atts
            ],
            'attachments_count': Attachment.search_count(domain),
        }

    # ── Brief #FINAL — Note ────────────────────────────────────────

    def _cf_get_note(self):
        """Chatter internal notes del progetto."""
        self.ensure_one()
        now = datetime.utcnow()
        mt_note = self.env.ref('mail.mt_note', raise_if_not_found=False)
        notes = self.env['mail.message'].search([
            ('model', '=', 'project.project'),
            ('res_id', '=', self.id),
            ('subtype_id', '=', mt_note.id if mt_note else 0),
            ('message_type', '=', 'comment'),
        ], order='date desc', limit=15) if mt_note else self.env['mail.message']
        return {
            'notes': [
                {
                    'id': n.id,
                    'body': n.body or '',
                    'author_name': n.author_id.name if n.author_id else 'Sistema',
                    'author_id': n.author_id.id if n.author_id else None,
                    'date': fields.Datetime.to_string(n.date),
                    'date_label': self._cf_relative_date(n.date, now) if n.date else '',
                }
                for n in notes
            ],
            'description': self.description or '',
        }

    # ── Brief #FINAL — Helpers ─────────────────────────────────────

    def _cf_format_size(self, size_bytes):
        if not size_bytes:
            return '0 B'
        if size_bytes < 1024:
            return '%d B' % size_bytes
        if size_bytes < 1024 * 1024:
            return '%d KB' % (size_bytes // 1024)
        return '%d MB' % (size_bytes // (1024 * 1024))

    def _cf_mimetype_icon(self, mimetype):
        if not mimetype:
            return 'fa-file-o'
        m = mimetype.lower()
        if 'pdf' in m:
            return 'fa-file-pdf-o'
        if 'image' in m:
            return 'fa-file-image-o'
        if 'word' in m or 'document' in m:
            return 'fa-file-word-o'
        if 'excel' in m or 'spreadsheet' in m:
            return 'fa-file-excel-o'
        if 'zip' in m or 'compressed' in m:
            return 'fa-file-archive-o'
        return 'fa-file-o'

    # ── Brief #B6 — Mail timeline for dashboard ──────────────────

    def _cf_get_mail_timeline(self, limit=20):
        """Mail positioned on this project, ordered by date desc."""
        self.ensure_one()
        try:
            Message = self.env['casafolino.mail.message']
        except KeyError:
            return []  # casafolino_mail not installed
        messages = Message.search([
            ('cf_project_id', '=', self.id),
        ], limit=limit, order='email_date desc')
        now = datetime.utcnow()
        result = []
        for msg in messages:
            partner = msg.partner_id
            if msg.body_downloaded and (msg.body_html or msg.body_plain):
                import re as _re
                body_text = _re.sub(r'<[^>]+>', ' ', msg.body_html or msg.body_plain or '')
                body_text = _re.sub(r'\s+', ' ', body_text).strip()
                preview = body_text[:150] + ('...' if len(body_text) > 150 else '')
            else:
                preview = '(corpo non scaricato)'
            is_outbound = bool(
                msg.account_id and msg.account_id.email_address
                and msg.sender_email
                and msg.account_id.email_address.lower() == (msg.sender_email or '').lower()
            )
            result.append({
                'casafolino_id': msg.id,
                'subject': msg.subject or '(no subject)',
                'sender_email': msg.sender_email or '',
                'sender_name': partner.name if partner else (msg.sender_email or '?'),
                'partner_id': partner.id if partner else None,
                'partner_name': partner.name if partner else '',
                'email_date': fields.Datetime.to_string(msg.email_date) if msg.email_date else '',
                'date_label': self._cf_relative_date(msg.email_date, now) if msg.email_date else '',
                'preview_text': preview,
                'is_outbound': is_outbound,
                'mail_message_id': msg.mail_message_id.id if msg.mail_message_id else None,
            })
        return result

    def _cf_get_mail_count(self):
        """Count mail positioned on this project."""
        self.ensure_one()
        try:
            return self.env['casafolino.mail.message'].search_count([
                ('cf_project_id', '=', self.id)
            ])
        except KeyError:
            return 0
