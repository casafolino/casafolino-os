from datetime import timedelta
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

CF_PROJECT_TYPES = [
    ('sample_fair', 'Campionatura Fiera'),
    ('sample_client', 'Campionatura Cliente'),
    ('custom_label', 'Etichetta Personalizzata'),
    ('new_product', 'Lancio Nuovo Prodotto'),
    ('fair_prep', 'Preparazione Fiera'),
    ('strategic', 'Progetto Strategico'),
]

CF_WAITING_FOR = [
    ('none', 'Nessuno'),
    ('client', 'Cliente'),
    ('graphic', 'Grafico'),
    ('printer', 'Tipografia'),
    ('production', 'Produzione'),
    ('internal', 'Interno'),
    ('supplier', 'Fornitore'),
]


class CfProject(models.Model):
    _inherit = 'project.project'

    # === TIPO PROGETTO ===
    cf_project_type = fields.Selection(
        CF_PROJECT_TYPES, string="Tipo Progetto", tracking=True)

    # === PARTNER COLLEGATO ===
    cf_partner_id = fields.Many2one(
        'res.partner', string="Cliente/Partner", tracking=True, index=True)
    cf_partner_country_id = fields.Many2one(
        related='cf_partner_id.country_id', string="Paese", store=True)
    cf_partner_email = fields.Char(
        related='cf_partner_id.email', string="Email Partner")

    # === DEADLINE E SEMAFORO ===
    cf_target_date = fields.Date(
        string="Data Target", tracking=True,
        help="Deadline finale del progetto (es. data fiera, data consegna)")
    cf_traffic_light = fields.Selection([
        ('green', 'In Linea'),
        ('yellow', 'Attenzione'),
        ('red', 'Critico'),
    ], string="Stato", compute='_compute_traffic_light', store=True)

    # === AVANZAMENTO ===
    cf_progress = fields.Float(
        string="Avanzamento %", compute='_compute_progress', store=True)
    cf_tasks_total = fields.Integer(compute='_compute_progress', store=True)
    cf_tasks_done = fields.Integer(compute='_compute_progress', store=True)
    cf_tasks_blocked = fields.Integer(compute='_compute_progress', store=True)

    # === WAITING FOR (aggregato) ===
    cf_main_blocker = fields.Selection(
        CF_WAITING_FOR, string="Bloccato da",
        compute='_compute_main_blocker', store=True)

    # === FIERA PARENT ===
    cf_parent_project_id = fields.Many2one(
        'project.project', string="Progetto Padre (Fiera)",
        domain="[('cf_project_type', '=', 'fair_prep')]")
    cf_child_project_ids = fields.One2many(
        'project.project', 'cf_parent_project_id', string="Sotto-progetti")
    cf_child_count = fields.Integer(
        compute='_compute_child_count', string="N. Sotto-progetti")

    # === FAIR DASHBOARD ===
    cf_fair_start_date = fields.Date(string="Inizio Fiera", tracking=True)
    cf_fair_end_date = fields.Date(string="Fine Fiera", tracking=True)
    cf_fair_location = fields.Char(string="Sede / Padiglione", tracking=True)
    cf_fair_booth = fields.Char(string="N. Stand / Booth")

    cf_alert_90_sent = fields.Boolean(string="Alert -90gg inviato", default=False)
    cf_alert_60_sent = fields.Boolean(string="Alert -60gg inviato", default=False)
    cf_alert_30_sent = fields.Boolean(string="Alert -30gg inviato", default=False)
    cf_alert_7_sent = fields.Boolean(string="Alert -7gg inviato", default=False)

    cf_buyer_program_contacted = fields.Boolean(string="Ente fiera contattato per Buyer Program")
    cf_matchmaking_open = fields.Boolean(string="Piattaforma matchmaking aperta")
    cf_matchmaking_url = fields.Char(string="URL piattaforma appuntamenti")
    cf_matchmaking_notes = fields.Text(string="Note agenda appuntamenti")

    cf_contest_checked = fields.Boolean(string="Date iscrizione verificate")
    cf_contest_deadline = fields.Date(string="Deadline iscrizione concorso")
    cf_contest_requirements = fields.Text(string="Requisiti concorso")
    cf_contest_samples_sent = fields.Boolean(string="Campioni giuria spediti")
    cf_contest_samples_tracking = fields.Char(string="Tracking spedizione campioni giuria")

    cf_stand_samples_ordered = fields.Boolean(string="Ordine campionatura stand inviato")
    cf_stand_samples_date = fields.Date(string="Data invio ordine")
    cf_stand_samples_notes = fields.Text(string="Note prodotti / quantita stand")

    cf_graphics_reviewed = fields.Boolean(string="Grafiche stand verificate")
    cf_catalogue_digital = fields.Boolean(string="Catalogo digitale caricato")
    cf_catalogue_print_qty = fields.Integer(string="Copie catalogo cartaceo")
    cf_catalogue_print_done = fields.Boolean(string="Stampa catalogo completata")

    cf_linkedin_savedate = fields.Boolean(string="Post Save the Date pubblicato")
    cf_linkedin_stand = fields.Boolean(string="Post Ti aspettiamo allo stand pubblicato")
    cf_linkedin_notes = fields.Text(string="Piano editoriale LinkedIn")

    cf_badges_downloaded = fields.Boolean(string="Badge scaricati e distribuiti al team")
    cf_delivery_confirmed = fields.Boolean(string="Orari scarico merce confermati")
    cf_delivery_notes = fields.Char(string="Note logistica scarico")

    cf_fair_contacts = fields.Text(string="Contatti utili")
    cf_post_fair_notes = fields.Text(string="Note post-fiera / follow-up")

    cf_fair_completion = fields.Float(
        string="Completamento Dashboard Fiera %",
        compute='_compute_fair_completion', store=True)

    # === CONTATORE GIORNI ===
    cf_days_open = fields.Integer(
        compute='_compute_days_open', string="Giorni Aperti")

    # === TEMPLATE ===
    cf_template_id = fields.Many2one(
        'cf.project.template', string="Creato da Template")

    # === SPEDIZIONI ===
    cf_shipment_ids = fields.One2many(
        'cf.project.shipment', 'project_id', string="Spedizioni")

    # ── Fair dashboard compute ───────────────────────────────────────

    _FAIR_CHECKBOXES = [
        'cf_buyer_program_contacted', 'cf_matchmaking_open',
        'cf_contest_checked', 'cf_contest_samples_sent',
        'cf_stand_samples_ordered',
        'cf_graphics_reviewed', 'cf_catalogue_digital', 'cf_catalogue_print_done',
        'cf_linkedin_savedate', 'cf_linkedin_stand',
        'cf_badges_downloaded', 'cf_delivery_confirmed',
    ]

    @api.depends(
        'cf_buyer_program_contacted', 'cf_matchmaking_open',
        'cf_contest_checked', 'cf_contest_samples_sent',
        'cf_stand_samples_ordered',
        'cf_graphics_reviewed', 'cf_catalogue_digital', 'cf_catalogue_print_done',
        'cf_linkedin_savedate', 'cf_linkedin_stand',
        'cf_badges_downloaded', 'cf_delivery_confirmed',
    )
    def _compute_fair_completion(self):
        for project in self:
            total = len(self._FAIR_CHECKBOXES)
            done = sum(1 for f in self._FAIR_CHECKBOXES if project[f])
            project.cf_fair_completion = (done / total * 100) if total else 0

    # ── Onchange ──────────────────────────────────────────────────────

    @api.onchange('cf_template_id')
    def _onchange_cf_template_id(self):
        if self.cf_template_id and self.cf_template_id.cf_project_type:
            self.cf_project_type = self.cf_template_id.cf_project_type

    # ── Compute methods ──────────────────────────────────────────────

    @api.depends('task_ids.stage_id', 'task_ids.date_deadline', 'cf_target_date')
    def _compute_traffic_light(self):
        today = fields.Date.today()
        for proj in self:
            if not proj.cf_target_date:
                proj.cf_traffic_light = 'green'
                continue
            if proj.cf_target_date < today:
                proj.cf_traffic_light = 'red'
                continue
            # Check task deadlines (date_deadline is Datetime in Odoo 18)
            has_red = False
            has_yellow = False
            for task in proj.task_ids.filtered(lambda t: not t.stage_id.fold):
                if task.date_deadline:
                    dl = task.date_deadline.date()
                    if dl < today:
                        has_red = True
                    elif dl <= today + timedelta(days=3):
                        has_yellow = True
            if has_red:
                proj.cf_traffic_light = 'red'
            elif has_yellow:
                proj.cf_traffic_light = 'yellow'
            else:
                proj.cf_traffic_light = 'green'

    @api.depends('task_ids.stage_id', 'task_ids.cf_waiting_for')
    def _compute_progress(self):
        for proj in self:
            tasks = proj.task_ids.filtered(lambda t: not t.parent_id)
            total = len(tasks)
            done = len(tasks.filtered(lambda t: t.stage_id.fold))
            blocked = len(tasks.filtered(
                lambda t: t.cf_waiting_for and t.cf_waiting_for != 'none' and not t.stage_id.fold))
            proj.cf_tasks_total = total
            proj.cf_tasks_done = done
            proj.cf_tasks_blocked = blocked
            proj.cf_progress = (done / total * 100) if total else 0

    @api.depends('task_ids.cf_waiting_for', 'task_ids.stage_id')
    def _compute_main_blocker(self):
        for proj in self:
            active_tasks = proj.task_ids.filtered(
                lambda t: not t.stage_id.fold and t.cf_waiting_for and t.cf_waiting_for != 'none')
            if not active_tasks:
                proj.cf_main_blocker = 'none'
                continue
            # Most frequent blocker
            counts = {}
            for t in active_tasks:
                counts[t.cf_waiting_for] = counts.get(t.cf_waiting_for, 0) + 1
            proj.cf_main_blocker = max(counts, key=counts.get)

    @api.depends('cf_child_project_ids')
    def _compute_child_count(self):
        for proj in self:
            proj.cf_child_count = len(proj.cf_child_project_ids)

    def _compute_days_open(self):
        today = fields.Date.context_today(self)
        for proj in self:
            if proj.create_date:
                proj.cf_days_open = (today - proj.create_date.date()).days
            else:
                proj.cf_days_open = 0

    # ── Create from template ─────────���───────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        for project in projects:
            if project.cf_template_id:
                project._generate_tasks_from_template()
        return projects

    def _generate_tasks_from_template(self):
        """Genera task dal template con date relative a cf_target_date."""
        self.ensure_one()
        template = self.cf_template_id
        if not template:
            return

        if template.cf_project_type and not self.cf_project_type:
            self.cf_project_type = template.cf_project_type

        task_templates = template.task_template_ids.sorted('sequence')

        # Find or create stages
        stage_todo = self.env['project.task.type'].search(
            [('name', 'ilike', 'Da Fare')], limit=1)
        stage_waiting = self.env['project.task.type'].search(
            [('name', 'ilike', 'In Attesa')], limit=1)
        if not stage_todo:
            stage_todo = self.env['project.task.type'].search([], limit=1)
        if not stage_waiting:
            stage_waiting = stage_todo

        for idx, tt in enumerate(task_templates):
            # Calculate deadline
            deadline = False
            if self.cf_target_date and tt.relative_days:
                deadline = self.cf_target_date + timedelta(days=tt.relative_days)

            stage = stage_todo if idx == 0 else stage_waiting

            task = self.env['project.task'].create({
                'name': tt.name,
                'project_id': self.id,
                'user_ids': [(4, tt.default_user_id.id)] if tt.default_user_id else [],
                'date_deadline': deadline,
                'description': tt.description or '',
                'stage_id': stage.id if stage else False,
                'cf_waiting_for': tt.cf_waiting_for or 'none',
                'cf_template_sequence': tt.sequence,
                'cf_relative_days': tt.relative_days,
                'cf_auto_activate_next': tt.auto_activate_next,
                'cf_checklist_required': tt.checklist_required,
            })

            # Create checklist items from template
            for cl in tt.checklist_template_ids.sorted('sequence'):
                self.env['cf.project.checklist.item'].create({
                    'task_id': task.id,
                    'name': cl.name,
                    'sequence': cl.sequence,
                })

    # ── Fair Alerts Cron ─────────────────────────────────────────────

    @api.model
    def _cron_fair_alerts(self):
        """Invia alert automatici per fiere imminenti (-90, -60, -30, -7 giorni)."""
        today = fields.Date.today()
        thresholds = [
            (90, 'cf_alert_90_sent', '-90 giorni'),
            (60, 'cf_alert_60_sent', '-60 giorni'),
            (30, 'cf_alert_30_sent', '-30 giorni'),
            (7,  'cf_alert_7_sent',  '-7 giorni (Check-in finale)'),
        ]

        fair_projects = self.search([
            ('cf_project_type', '=', 'fair_prep'),
            ('cf_fair_start_date', '!=', False),
            ('active', '=', True),
        ])

        for project in fair_projects:
            delta = (project.cf_fair_start_date - today).days
            for days, flag_field, label in thresholds:
                if delta <= days and not project[flag_field]:
                    project[flag_field] = True
                    project.message_post(
                        body="<b>Alert Fiera %s</b>: mancano <b>%d giorni</b> "
                             "all'inizio di <b>%s</b> (%s). "
                             "Verifica il tab Fiera per i punti in sospeso." % (
                                 label, delta, project.name,
                                 project.cf_fair_start_date.strftime('%d/%m/%Y')),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
                    _logger.info(
                        "Fair alert %s sent for project %s (delta=%d days)",
                        label, project.name, delta
                    )
