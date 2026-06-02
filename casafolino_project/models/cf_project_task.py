from odoo import models, fields, api
from odoo.exceptions import UserError


class CfProjectTask(models.Model):
    _inherit = 'project.task'

    # === TASK OPERATIVA CASAFOLINO ===
    cf_task_origin = fields.Selection([
        ('manual', 'Manuale'),
        ('call', 'Chiamata'),
        ('mail', 'Email'),
        ('voice_ai', 'Voice AI'),
        ('system', 'Sistema'),
    ], string="Origine richiesta", default='manual', tracking=True)
    cf_task_type = fields.Selection([
        ('todo', 'To-do operativo'),
        ('catalog_page', 'Pagina catalogo'),
        ('sample_shipment', 'Campionatura / spedizione'),
        ('quote', 'Preventivo'),
        ('followup', 'Follow-up cliente'),
        ('data_update', 'Aggiornamento anagrafica'),
        ('issue', 'Problema / blocco'),
    ], string="Tipo richiesta", default='todo', tracking=True)
    cf_department = fields.Selection([
        ('sales', 'Commerciale'),
        ('graphics', 'Grafica'),
        ('production', 'Produzione'),
        ('logistics', 'Logistica'),
        ('admin', 'Amministrazione'),
        ('management', 'Direzione'),
    ], string="Reparto owner", tracking=True)
    cf_customer_id = fields.Many2one(
        'res.partner', string="Cliente", tracking=True)
    cf_is_mini_project = fields.Boolean(
        string="Mini-progetto",
        help="Attiva quando la task richiede piu passaggi, reparti o checklist.")
    cf_source_note = fields.Text(string="Nota origine")
    cf_ai_suggested_next_step = fields.Text(string="Prossima azione suggerita AI")

    # === IN ATTESA DI ===
    cf_waiting_for = fields.Selection([
        ('none', 'Nessuno'),
        ('client', 'Cliente'),
        ('graphic', 'Grafico'),
        ('printer', 'Tipografia'),
        ('production', 'Produzione'),
        ('internal', 'Interno'),
        ('supplier', 'Fornitore'),
    ], string="In Attesa Di", default='none', tracking=True)

    # === CONTATORE GIORNI ===
    cf_days_in_stage = fields.Integer(
        compute='_compute_days_in_stage', string="Giorni in Stage")
    cf_stage_changed_date = fields.Datetime(string="Ultimo Cambio Stage")

    # === CHECKLIST ===
    cf_checklist_ids = fields.One2many(
        'cf.project.checklist.item', 'task_id', string="Checklist")
    cf_checklist_progress = fields.Float(
        compute='_compute_checklist_progress', string="Checklist %")
    cf_checklist_required = fields.Boolean(
        string="Checklist Obbligatoria",
        help="Se attivo, la task non puo essere completata senza completare la checklist")

    # === SPEDIZIONE ===
    cf_shipment_id = fields.Many2one(
        'cf.project.shipment', string="Spedizione Collegata")
    cf_trackbot_enabled = fields.Boolean(
        string="TrackBot attivo",
        related='cf_shipment_id.trackbot_enabled',
        readonly=False)
    cf_tracking_number = fields.Char(
        string="Tracking",
        related='cf_shipment_id.tracking_number',
        readonly=False)

    # === SEQUENZA NEL TEMPLATE ===
    cf_template_sequence = fields.Integer(string="Ordine nel Template", default=10)
    cf_relative_days = fields.Integer(string="Giorni Relativi")
    cf_auto_activate_next = fields.Boolean(string="Attiva Task Successiva")

    # ── Compute ──────────────────────────────────────────────────────

    def _compute_days_in_stage(self):
        now = fields.Datetime.now()
        for task in self:
            if task.cf_stage_changed_date:
                delta = now - task.cf_stage_changed_date
                task.cf_days_in_stage = delta.days
            else:
                task.cf_days_in_stage = 0

    @api.depends('cf_checklist_ids.is_done')
    def _compute_checklist_progress(self):
        for task in self:
            items = task.cf_checklist_ids
            total = len(items)
            done = len(items.filtered('is_done'))
            task.cf_checklist_progress = (done / total * 100) if total else 0

    # ── Write override ───────────────────────────────────────────────

    def write(self, vals):
        # Track stage change
        if 'stage_id' in vals:
            vals['cf_stage_changed_date'] = fields.Datetime.now()

            # Checklist validation on completion
            for task in self:
                new_stage = self.env['project.task.type'].browse(vals['stage_id'])
                if new_stage.fold and task.cf_checklist_required:
                    undone = task.cf_checklist_ids.filtered(lambda c: not c.is_done)
                    if undone:
                        raise UserError(
                            "La task '%s' ha una checklist obbligatoria non completata. "
                            "Completa tutti gli item prima di chiudere." % task.name)

        result = super().write(vals)

        # Auto-activate next task
        if 'stage_id' in vals:
            for task in self:
                new_stage = self.env['project.task.type'].browse(vals['stage_id'])
                if new_stage.fold and task.cf_auto_activate_next and task.project_id:
                    next_task = self.search([
                        ('project_id', '=', task.project_id.id),
                        ('cf_template_sequence', '>', task.cf_template_sequence),
                    ], order='cf_template_sequence', limit=1)
                    if next_task:
                        todo_stage = self.env['project.task.type'].search(
                            [('name', 'ilike', 'Da Fare')], limit=1)
                        if not todo_stage:
                            todo_stage = self.env['project.task.type'].search(
                                [('fold', '=', False)], limit=1)
                        if todo_stage:
                            next_task.write({'stage_id': todo_stage.id})

        return result

    # ── Actions ─────────────────────────────────────────────────────

    def action_cf_create_sample_shipment(self):
        self.ensure_one()
        if not self.project_id:
            raise UserError("Assegna la task a un progetto prima di creare la spedizione.")
        shipment = self.cf_shipment_id
        if not shipment:
            shipment = self.env['cf.project.shipment'].create({
                'project_id': self.project_id.id,
                'state': 'draft',
                'notes': self.cf_source_note or self.description or '',
                'trackbot_enabled': True,
            })
            self.cf_shipment_id = shipment.id
        self.write({
            'cf_task_type': 'sample_shipment',
            'cf_department': self.cf_department or 'logistics',
            'cf_is_mini_project': True,
            'cf_waiting_for': 'internal',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Spedizione campionatura',
            'res_model': 'cf.project.shipment',
            'res_id': shipment.id,
            'views': [(False, 'form')],
            'target': 'current',
        }
