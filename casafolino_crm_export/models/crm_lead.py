from datetime import date, timedelta

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # --- Mercato / Canale ---
    cf_market = fields.Selection([
        ('america', 'America'),
        ('europa', 'Europa'),
        ('italia', 'Italia'),
        ('medio_oriente', 'Medio Oriente'),
        ('australia', 'Australia'),
        ('altri', 'Altri'),
    ], string='Mercato', tracking=True)

    cf_channel = fields.Selection([
        ('gdo', 'GDO'),
        ('importatore', 'Importatore'),
        ('distributore', 'Distributore'),
        ('horeca', 'Ho.Re.Ca.'),
        ('ecommerce', 'E-commerce'),
        ('private_label', 'Private Label'),
        ('foodservice', 'Foodservice'),
    ], string='Canale', tracking=True)

    # --- Scoring ---
    cf_lead_score = fields.Integer(
        string='Lead Score',
        compute='_compute_cf_lead_score',
        store=True,
    )

    # --- Rotting ---
    cf_rotting_days = fields.Integer(
        string='Giorni Inattività',
        compute='_compute_cf_rotting',
        store=True,
    )
    cf_rotting_state = fields.Selection([
        ('ok', 'OK'),
        ('warning', 'Attenzione'),
        ('danger', 'Critico'),
        ('dead', 'Morto'),
    ], string='Stato Rotting', compute='_compute_cf_rotting', store=True)

    # --- Campionature ---
    cf_sample_ids = fields.One2many('cf.export.sample', 'lead_id', string='Campionature')
    cf_sample_count = fields.Integer(
        string='N. Campionature',
        compute='_compute_cf_sample_count',
    )

    # --- Fiera ---
    cf_fair_id = fields.Many2one('cf.export.fair', string='Fiera Origine', tracking=True)

    # --- Sequenze ---
    cf_sequence_log_ids = fields.One2many('cf.export.sequence.log', 'lead_id', string='Log Sequenze')

    # --- Comunicazione ---
    cf_language = fields.Selection([
        ('it', 'Italiano'),
        ('en', 'English'),
        ('de', 'Deutsch'),
        ('fr', 'Français'),
        ('es', 'Español'),
        ('ar', 'العربية'),
    ], string='Lingua Comunicazione')

    # --- Certificazioni ---
    cf_certifications_required = fields.Many2many(
        'cf.export.certification',
        string='Certificazioni Richieste',
    )

    # --- Follow-up ---
    cf_date_last_contact = fields.Date(string='Ultimo Contatto', tracking=True)
    cf_date_next_followup = fields.Date(string='Prossimo Follow-up', tracking=True)

    # --- Email partner ---
    cf_email_count = fields.Integer(string='N. Email', compute='_compute_cf_email_count')
    cf_partner_email_ids = fields.Many2many(
        'mail.message', string='Email Partner',
        compute='_compute_cf_partner_emails',
    )

    # --- Contact details (related from partner) ---
    cf_partner_phone = fields.Char(related='partner_id.phone', string='Telefono Partner')
    cf_partner_mobile = fields.Char(related='partner_id.mobile', string='Cellulare Partner')
    cf_partner_country = fields.Many2one(related='partner_id.country_id', string='Paese Partner')
    cf_partner_city = fields.Char(related='partner_id.city', string='Città Partner')
    cf_partner_image = fields.Binary(related='partner_id.image_128', string='Foto Partner')

    # --- Premium form computed ---
    cf_rotting_days_display = fields.Char(
        string='Ultimo Aggiornamento', compute='_compute_cf_rotting_days_display',
    )
    cf_forecast_value = fields.Float(
        string='Forecast', compute='_compute_cf_forecast_value', store=True,
    )
    cf_days_in_stage = fields.Integer(
        string='Giorni in Fase', compute='_compute_cf_days_in_stage',
    )
    cf_next_activity_summary = fields.Char(
        string='Prossima Attività', compute='_compute_cf_next_activity',
    )
    cf_next_activity_date = fields.Date(
        string='Data Prossima Attività', compute='_compute_cf_next_activity',
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    def _compute_cf_rotting_days_display(self):
        for lead in self:
            days = lead.cf_rotting_days
            if days <= 0:
                lead.cf_rotting_days_display = 'Aggiornato oggi'
            elif days == 1:
                lead.cf_rotting_days_display = '1 giorno fa'
            else:
                lead.cf_rotting_days_display = f'{days} giorni fa'

    @api.depends('expected_revenue', 'probability')
    def _compute_cf_forecast_value(self):
        for lead in self:
            lead.cf_forecast_value = (lead.expected_revenue or 0) * (lead.probability or 0) / 100

    def _compute_cf_days_in_stage(self):
        today = fields.Date.today()
        for lead in self:
            if lead.date_last_stage_update:
                lead.cf_days_in_stage = (today - lead.date_last_stage_update.date()).days
            else:
                lead.cf_days_in_stage = 0

    def _compute_cf_next_activity(self):
        for lead in self:
            activity = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
            ], order='date_deadline asc', limit=1)
            if activity:
                lead.cf_next_activity_summary = activity.summary or activity.activity_type_id.name
                lead.cf_next_activity_date = activity.date_deadline
            else:
                lead.cf_next_activity_summary = False
                lead.cf_next_activity_date = False

    @api.depends('partner_id')
    def _compute_cf_email_count(self):
        for lead in self:
            if lead.partner_id:
                lead.cf_email_count = self.env['mail.message'].search_count([
                    ('partner_ids', 'in', lead.partner_id.id),
                    ('message_type', 'in', ['email', 'email_outgoing']),
                ])
            else:
                lead.cf_email_count = 0

    @api.depends('partner_id')
    def _compute_cf_partner_emails(self):
        for lead in self:
            if lead.partner_id:
                lead.cf_partner_email_ids = self.env['mail.message'].search([
                    ('partner_ids', 'in', lead.partner_id.id),
                    ('message_type', 'in', ['email', 'email_outgoing']),
                ], order='date desc', limit=50)
            else:
                lead.cf_partner_email_ids = False

    @api.depends('cf_sample_ids')
    def _compute_cf_sample_count(self):
        for lead in self:
            lead.cf_sample_count = len(lead.cf_sample_ids)

    @api.depends(
        'cf_date_last_contact', 'cf_date_next_followup',
        'cf_sample_ids', 'cf_sample_ids.state',
        'stage_id', 'priority', 'activity_ids',
    )
    def _compute_cf_lead_score(self):
        today = date.today()
        for lead in self:
            score = 0

            # Ultimo contatto recente
            if lead.cf_date_last_contact:
                days_since = (today - lead.cf_date_last_contact).days
                if days_since <= 7:
                    score += 20
                elif days_since > 14:
                    score -= 20

            # Campionature
            sample_states = lead.cf_sample_ids.mapped('state')
            if any(s in ('sent', 'received', 'feedback_ok') for s in sample_states):
                score += 15
            if 'feedback_ok' in sample_states:
                score += 20

            # Ordini collegati
            if hasattr(lead, "order_ids") and lead.order_ids:
                score += 25

            # Stage avanzato
            if lead.stage_id and lead.stage_id.sequence and lead.stage_id.sequence >= 4:
                score += 10

            # Priorità
            if lead.priority == '1':
                score += 5
            elif lead.priority in ('2', '3'):
                score += 10

            # Penalità
            if not lead.cf_date_next_followup:
                score -= 10
            if not lead.activity_ids:
                score -= 5

            lead.cf_lead_score = max(0, min(100, score))

    @api.depends('write_date', 'stage_id')
    def _compute_cf_rotting(self):
        today = date.today()
        for lead in self:
            if lead.stage_id and lead.stage_id.is_won:
                lead.cf_rotting_days = 0
                lead.cf_rotting_state = 'ok'
                continue

            if lead.write_date:
                delta = (today - lead.write_date.date()).days
            else:
                delta = 0

            lead.cf_rotting_days = delta

            if delta <= 7:
                lead.cf_rotting_state = 'ok'
            elif delta <= 14:
                lead.cf_rotting_state = 'warning'
            elif delta <= 30:
                lead.cf_rotting_state = 'danger'
            else:
                lead.cf_rotting_state = 'dead'

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_mark_contacted(self):
        self.write({
            'cf_date_last_contact': date.today(),
            'cf_date_next_followup': date.today() + timedelta(days=7),
        })

    def action_schedule_followup(self):
        self.write({
            'cf_date_next_followup': date.today() + timedelta(days=7),
        })

    def action_view_partner_emails(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Email Contatto',
            'res_model': 'mail.message',
            'view_mode': 'list,form',
            'domain': [
                ('partner_ids', 'in', self.partner_id.id),
                ('message_type', 'in', ['email', 'email_outgoing']),
            ],
            'context': {'default_partner_ids': [self.partner_id.id]},
        }

    def action_view_samples(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Campionature',
            'res_model': 'cf.export.sample',
            'view_mode': 'kanban,list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    def action_create_sample(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nuova Campionatura',
            'res_model': 'cf.export.sample',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_lead_id': self.id},
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    @api.model
    def get_cf_dashboard_data(self):
        leads = self.search([('type', '=', 'opportunity')])
        today = date.today()
        return {
            'total_revenue': sum(leads.mapped('expected_revenue')),
            'total_forecast': sum(leads.filtered(
                lambda l: l.stage_id and not l.stage_id.is_won
            ).mapped('expected_revenue')),
            'avg_score': (
                sum(leads.mapped('cf_lead_score')) / len(leads)
                if leads else 0
            ),
            'total_leads': len(leads),
            'rotting_count': len(leads.filtered(
                lambda l: l.cf_rotting_state in ('danger', 'dead')
            )),
            'followup_today': len(leads.filtered(
                lambda l: l.cf_date_next_followup == today
            )),
            'by_market': {
                market: len(leads.filtered(lambda l, m=market: l.cf_market == m))
                for market in ('america', 'europa', 'italia', 'medio_oriente', 'australia', 'altri')
            },
        }


class CfExportCertification(models.Model):
    _name = 'cf.export.certification'
    _description = 'Certificazione Export'

    name = fields.Char(required=True)
    code = fields.Char()
    color = fields.Integer(default=0)
