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

    # === CONTATORE GIORNI ===
    cf_days_open = fields.Integer(
        compute='_compute_days_open', string="Giorni Aperti")

    # === TEMPLATE ===
    cf_template_id = fields.Many2one(
        'cf.project.template', string="Creato da Template")

    # === SPEDIZIONI ===
    cf_shipment_ids = fields.One2many(
        'cf.project.shipment', 'project_id', string="Spedizioni")

    # ── Compute methods ───���──────────────────────────────────────────

    @api.depends('task_ids.stage_id', 'task_ids.date_deadline', 'cf_target_date')
    def _compute_traffic_light(self):
        today = fields.Date.context_today(self)
        for proj in self:
            if not proj.cf_target_date:
                proj.cf_traffic_light = 'green'
                continue
            if proj.cf_target_date < today:
                proj.cf_traffic_light = 'red'
                continue
            # Check task deadlines
            has_red = False
            has_yellow = False
            for task in proj.task_ids.filtered(lambda t: not t.stage_id.fold):
                if task.date_deadline:
                    if task.date_deadline < today:
                        has_red = True
                    elif task.date_deadline <= today + timedelta(days=3):
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
