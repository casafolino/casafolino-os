from odoo import models, fields, api
from odoo.exceptions import UserError


class CfProjectTask(models.Model):
    _inherit = 'project.task'

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
