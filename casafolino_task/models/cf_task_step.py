from odoo import api, fields, models, _
from odoo.exceptions import UserError

ROLE_SELECTION = [
    ('coordinazione', 'Coordinazione'),
    ('creazione', 'Creazione'),
    ('produzione', 'Produzione'),
    ('logistica', 'Logistica'),
    ('commerciale', 'Commerciale'),
    ('amministrazione', 'Amministrazione'),
    ('altro', 'Altro'),
]


class CfTaskStep(models.Model):
    _name = 'cf.task.step'
    _description = 'CasaFolino Task Step'
    _order = 'task_id, sequence, id'

    task_id = fields.Many2one(
        'cf.task', string="Task", required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string="Ordine", default=10)
    name = fields.Char(string="Descrizione")
    role = fields.Selection(ROLE_SELECTION, string="Ruolo", required=True, default='coordinazione')
    user_id = fields.Many2one('res.users', string="Assegnatario", required=True)

    state = fields.Selection([
        ('da_fare', 'Da fare'),
        ('in_corso', 'In corso'),
        ('confermato', 'Confermato'),
        ('saltato', 'Saltato'),
    ], string="Stato", default='da_fare', required=True)

    activated_dt = fields.Datetime(
        string="Affidato il", readonly=True,
        help="Quando lo step è diventato attivo (avvio del cronometro semaforo).")
    checkin_dt = fields.Datetime(string="Check-in", readonly=True)
    checkout_dt = fields.Datetime(string="Check-out", readonly=True)

    elapsed_work_hours = fields.Float(
        string="Ore lavorative", compute='_compute_traffic_light', store=True,
        help="Ore lavorative (da calendario) trascorse da quando lo step è attivo.")
    traffic_light = fields.Selection([
        ('green', 'Verde'),
        ('yellow', 'Giallo'),
        ('red', 'Rosso'),
    ], string="Semaforo", compute='_compute_traffic_light', store=True, default='green')
    last_red_alert = fields.Datetime(string="Ultimo alert rosso", readonly=True)

    time_log_ids = fields.One2many('cf.task.time.log', 'step_id', string="Log tempo")
    company_id = fields.Many2one(related='task_id.company_id', store=True)

    # ----------------------------------------------------------- ore lavorative
    def _get_work_calendar(self):
        ICP = self.env['ir.config_parameter'].sudo()
        cal_id = int(ICP.get_param('casafolino_task.work_calendar_id', 0) or 0)
        cal = self.env['resource.calendar'].browse(cal_id) if cal_id else False
        if not cal or not cal.exists():
            cal = self.env.company.resource_calendar_id \
                or self.env['resource.calendar'].search([], limit=1)
        return cal

    def _work_hours_between(self, start, end):
        """Ore lavorative tra due datetime (naive UTC) via resource.calendar.
        Mai wall-clock: weekend e fuori-orario non contano."""
        if not start or not end or end <= start:
            return 0.0
        cal = self._get_work_calendar()
        if not cal:
            return 0.0
        data = cal.get_work_duration_data(start, end, compute_leaves=False)
        return data.get('hours', 0.0)

    @api.depends('state', 'activated_dt', 'checkout_dt')
    def _compute_traffic_light(self):
        ICP = self.env['ir.config_parameter'].sudo()
        soft = float(ICP.get_param('casafolino_task.soft_hours', 4) or 4)
        hard = float(ICP.get_param('casafolino_task.hard_hours', 8) or 8)
        now = fields.Datetime.now()
        for step in self:
            if step.state in ('confermato', 'saltato') or not step.activated_dt:
                step.elapsed_work_hours = step.elapsed_work_hours or 0.0
                step.traffic_light = 'green'
                continue
            end = step.checkout_dt or now
            hours = step._work_hours_between(step.activated_dt, end)
            step.elapsed_work_hours = hours
            if hours > hard:
                step.traffic_light = 'red'
            elif hours >= soft:
                step.traffic_light = 'yellow'
            else:
                step.traffic_light = 'green'

    # ------------------------------------------------------------- transizioni
    def _activate(self):
        """Rende lo step attivo: avvia il cronometro semaforo e notifica."""
        for step in self:
            if step.activated_dt:
                continue
            step.activated_dt = fields.Datetime.now()
            step.task_id._cf_notify(
                step.user_id, 'step_assigned',
                {'role': dict(ROLE_SELECTION).get(step.role, step.role)})

    def action_checkin(self):
        for step in self:
            if not step.activated_dt:
                raise UserError(_("Lo step non è ancora stato affidato."))
            if step.state != 'da_fare':
                raise UserError(_("Check-in possibile solo da 'Da fare'."))
            now = fields.Datetime.now()
            step.write({'state': 'in_corso', 'checkin_dt': now})
            self.env['cf.task.time.log'].create({
                'step_id': step.id,
                'user_id': step.user_id.id,
                'date_start': now,
            })
        return True

    def action_confirm(self):
        for step in self:
            if step.state not in ('da_fare', 'in_corso'):
                raise UserError(_("Step già chiuso."))
            now = fields.Datetime.now()
            vals = {'state': 'confermato', 'checkout_dt': now}
            if not step.checkin_dt:
                vals['checkin_dt'] = now
            step.write(vals)
            # chiudi l'ultimo log aperto
            open_log = step.time_log_ids.filtered(lambda l: not l.date_end)[:1]
            if open_log:
                open_log.date_end = now
            else:
                self.env['cf.task.time.log'].create({
                    'step_id': step.id,
                    'user_id': step.user_id.id,
                    'date_start': step.checkin_dt or now,
                    'date_end': now,
                })
            step.task_id._activate_next(step)
            step.task_id._check_completion()
        return True

    def action_skip(self):
        for step in self:
            if step.state in ('confermato', 'saltato'):
                continue
            step.state = 'saltato'
            step.task_id._activate_next(step)
            step.task_id._check_completion()
        return True

    def action_remind(self):
        """Sollecito manuale all'assegnatario."""
        for step in self:
            step.task_id._cf_notify(
                step.user_id, 'task_reminder',
                {'role': dict(ROLE_SELECTION).get(step.role, step.role)})
        return True

    def _escalate_red(self):
        """Notifica originatore + Antonio sui rossi, con anti-spam."""
        ICP = self.env['ir.config_parameter'].sudo()
        realert_h = float(ICP.get_param('casafolino_task.red_realert_hours', 24) or 24)
        esc_uid = int(ICP.get_param('casafolino_task.escalation_user_id', 2) or 2)
        now = fields.Datetime.now()
        for step in self:
            if step.last_red_alert:
                delta_h = (now - step.last_red_alert).total_seconds() / 3600.0
                if delta_h < realert_h:
                    continue
            ctx = {
                'role': dict(ROLE_SELECTION).get(step.role, step.role),
                'user': step.user_id.name or '',
                'hours': step.elapsed_work_hours,
            }
            recipients = step.task_id.originator_id
            antonio = self.env['res.users'].browse(esc_uid)
            if antonio.exists() and antonio not in recipients:
                recipients = recipients | antonio
            for user in recipients:
                step.task_id._cf_notify(user, 'step_red', ctx)
            step.last_red_alert = now
