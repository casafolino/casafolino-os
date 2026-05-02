import logging
from datetime import date, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

USER_COLOR_MAP = {
    'antonio@casafolino.com': '#3F8A4F',
    'josefina.lazzaro@casafolino.com': '#8B5CF6',
    'martina.sinopoli@casafolino.com': '#6B4A1E',
}
DEFAULT_USER_COLOR = '#D1D5DB'


class CrmLead(models.Model):
    _inherit = 'crm.lead'

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

    # --- Colore operatore (bordo kanban) ---
    cf_user_color = fields.Char(
        string='Colore Operatore',
        compute='_compute_cf_user_color',
        store=False,
    )

    # ------------------------------------------------------------------
    # Write override — probability from stage + standby exit
    # ------------------------------------------------------------------

    def write(self, vals):
        # Detect stage change for standby exit logic
        old_stage_ids = {}
        if 'stage_id' in vals:
            standby_stage = self.env['crm.stage'].search([('name', '=', 'Standby')], limit=1)
            if standby_stage:
                for lead in self:
                    old_stage_ids[lead.id] = lead.stage_id.id

        res = super().write(vals)

        if 'stage_id' in vals:
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])
            if new_stage.exists():
                standby_stage = self.env['crm.stage'].search([('name', '=', 'Standby')], limit=1)
                for lead in self:
                    # Auto-set probability from stage (skip Standby = keep current)
                    if new_stage.name == 'Standby':
                        pass  # mantiene probabilità attuale
                    elif new_stage.cf_probability_default is not False:
                        lead.probability = new_stage.cf_probability_default

                    # Exit from Standby → reset last contact date
                    if standby_stage and old_stage_ids.get(lead.id) == standby_stage.id and new_stage.id != standby_stage.id:
                        lead.cf_date_last_contact = fields.Date.context_today(self)

        return res

    # ------------------------------------------------------------------
    # message_post override — update cf_date_last_contact on email
    # ------------------------------------------------------------------

    def message_post(self, **kwargs):
        res = super().message_post(**kwargs)
        message_type = kwargs.get('message_type', '')
        if message_type in ('email', 'email_outgoing'):
            self.sudo().write({'cf_date_last_contact': fields.Date.context_today(self)})
        return res

    # ------------------------------------------------------------------
    # Cron: Auto-Standby lead inattivi
    # ------------------------------------------------------------------

    @api.model
    def _cron_move_to_standby(self):
        standby_stage = self.env['crm.stage'].search([('name', '=', 'Standby')], limit=1)
        if not standby_stage:
            _logger.warning('CasaFolino: stage Standby non trovato, cron skip.')
            return

        won_stage = self.env['crm.stage'].search([('name', '=', 'Vinta')], limit=1)
        lost_stage = self.env['crm.stage'].search([('name', '=', 'Persa')], limit=1)
        excluded_ids = [s.id for s in (won_stage, lost_stage, standby_stage) if s]

        cutoff = fields.Date.context_today(self) - timedelta(days=30)

        leads = self.search([
            ('type', '=', 'opportunity'),
            ('active', '=', True),
            ('stage_id', 'not in', excluded_ids),
            '|',
            '&', ('cf_date_last_contact', '!=', False), ('cf_date_last_contact', '<', cutoff),
            '&', ('cf_date_last_contact', '=', False), ('create_date', '<', cutoff),
        ])

        if leads:
            _logger.info('CasaFolino: spostamento %d lead in Standby.', len(leads))
            for lead in leads:
                lead.stage_id = standby_stage.id
                lead.message_post(
                    body='Lead spostato automaticamente in Standby: nessun contatto da oltre 30 giorni.',
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

    # ------------------------------------------------------------------
    # Compute — user color
    # ------------------------------------------------------------------

    @api.depends('user_id')
    def _compute_cf_user_color(self):
        for lead in self:
            login = lead.user_id.login if lead.user_id else None
            lead.cf_user_color = USER_COLOR_MAP.get(login, DEFAULT_USER_COLOR)

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

    @api.depends('partner_id', 'message_ids')
    def _compute_cf_email_count(self):
        MailMessage = self.env['mail.message']
        for lead in self:
            if lead.partner_id:
                lead.cf_email_count = MailMessage.search_count([
                    '|',
                    '&', ('partner_ids', 'in', lead.partner_id.id),
                         ('message_type', 'in', ['email', 'email_outgoing']),
                    '&', ('res_id', '=', lead.id),
                    '&', ('model', '=', 'crm.lead'),
                         ('message_type', 'in', ['email', 'email_outgoing']),
                ])
            else:
                lead.cf_email_count = MailMessage.search_count([
                    ('res_id', '=', lead.id),
                    ('model', '=', 'crm.lead'),
                    ('message_type', '!=', 'notification'),
                ])

    @api.depends('partner_id', 'message_ids')
    def _compute_cf_partner_emails(self):
        MailMessage = self.env['mail.message']
        for lead in self:
            if lead.partner_id:
                lead.cf_partner_email_ids = MailMessage.search([
                    '|',
                    '&', ('partner_ids', 'in', lead.partner_id.id),
                         ('message_type', 'in', ['email', 'email_outgoing']),
                    '&', ('res_id', '=', lead.id),
                    '&', ('model', '=', 'crm.lead'),
                         ('message_type', 'in', ['email', 'email_outgoing']),
                ], order='date desc', limit=100)
            else:
                lead.cf_partner_email_ids = MailMessage.search([
                    ('res_id', '=', lead.id),
                    ('model', '=', 'crm.lead'),
                    ('message_type', '!=', 'notification'),
                ], order='date desc', limit=100)

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

            if lead.cf_date_last_contact:
                days_since = (today - lead.cf_date_last_contact).days
                if days_since <= 7:
                    score += 20
                elif days_since > 14:
                    score -= 20

            sample_states = lead.cf_sample_ids.mapped('state')
            if any(s in ('sent', 'received', 'feedback_ok') for s in sample_states):
                score += 15
            if 'feedback_ok' in sample_states:
                score += 20

            if hasattr(lead, "order_ids") and lead.order_ids:
                score += 25

            if lead.stage_id and lead.stage_id.sequence and lead.stage_id.sequence >= 4:
                score += 10

            if lead.priority == '1':
                score += 5
            elif lead.priority in ('2', '3'):
                score += 10

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

    def action_send_email(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Scrivi Email',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'crm.lead',
                'default_res_ids': [self.id],
                'default_partner_ids': [self.partner_id.id] if self.partner_id else [],
                'default_composition_mode': 'comment',
                'default_email_from': self.env.user.email,
            },
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
        }


class CfExportCertification(models.Model):
    _name = 'cf.export.certification'
    _description = 'Certificazione Export'

    name = fields.Char(required=True)
    code = fields.Char()
    color = fields.Integer(default=0)
