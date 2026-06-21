import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Eventi notifica -> (subject, body template). Body riceve .format(**ctx).
CF_EVENTS = {
    'step_assigned': (
        "[Task] {task} — tocca a te ({role})",
        "Ti è stato affidato lo step <b>{role}</b> del task <b>{task}</b>.<br/>"
        "Fai check-in quando inizi e conferma quando hai finito.",
    ),
    'step_red': (
        "[Task] ROSSO — {task} / {role}",
        "Lo step <b>{role}</b> del task <b>{task}</b> è in <b>ROSSO</b> "
        "({hours:.1f}h lavorative, oltre soglia). Assegnatario: {user}.",
    ),
    'task_closed': (
        "[Task] Chiuso — {task}",
        "Il task <b>{task}</b> è stato completato: tutti gli step sono confermati.",
    ),
    'task_reminder': (
        "[Task] Sollecito — {task} / {role}",
        "Sollecito sullo step <b>{role}</b> del task <b>{task}</b>.",
    ),
}


class CfTask(models.Model):
    _name = 'cf.task'
    _description = 'CasaFolino Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string="Titolo", required=True, tracking=True)
    template_key = fields.Char(
        string="Template key",
        help="Chiave usata dai wizard futuri per generare gli step.")

    originator_id = fields.Many2one(
        'res.users', string="Originatore",
        default=lambda self: self.env.user, required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Contatto", tracking=True)
    lead_id = fields.Many2one('crm.lead', string="Lead/Opportunità", tracking=True)
    company_id = fields.Many2one(
        'res.company', string="Azienda",
        default=lambda self: self.env.company)

    state = fields.Selection([
        ('bozza', 'Bozza'),
        ('in_corso', 'In corso'),
        ('chiuso', 'Chiuso'),
        ('annullato', 'Annullato'),
    ], string="Stato", default='bozza', required=True, tracking=True)

    parallel = fields.Boolean(
        string="Step paralleli",
        help="Se attivo tutti gli step partono insieme; altrimenti handoff sequenziale.")

    step_ids = fields.One2many('cf.task.step', 'task_id', string="Step")
    step_count = fields.Integer(compute='_compute_step_count')
    current_step_id = fields.Many2one(
        'cf.task.step', string="Step attivo",
        compute='_compute_current_step', store=True)
    traffic_light = fields.Selection([
        ('green', 'Verde'),
        ('yellow', 'Giallo'),
        ('red', 'Rosso'),
    ], string="Semaforo", compute='_compute_traffic_light', store=True, default='green')

    # ---------------------------------------------------------------- computes
    def _compute_step_count(self):
        for task in self:
            task.step_count = len(task.step_ids)

    @api.depends('step_ids.state', 'step_ids.sequence')
    def _compute_current_step(self):
        for task in self:
            active = task.step_ids.filtered(lambda s: s.state == 'in_corso')
            if active:
                task.current_step_id = active[0]
            else:
                todo = task.step_ids.filtered(
                    lambda s: s.state == 'da_fare' and s.activated_dt)
                task.current_step_id = todo[:1].id if todo else False

    @api.depends('step_ids.traffic_light', 'step_ids.state')
    def _compute_traffic_light(self):
        rank = {'green': 0, 'yellow': 1, 'red': 2}
        inv = {v: k for k, v in rank.items()}
        for task in self:
            open_steps = task.step_ids.filtered(
                lambda s: s.state in ('da_fare', 'in_corso'))
            if not open_steps:
                task.traffic_light = 'green'
            else:
                worst = max(rank.get(s.traffic_light, 0) for s in open_steps)
                task.traffic_light = inv[worst]

    # ------------------------------------------------------------- transitions
    def action_start(self):
        for task in self:
            if task.state != 'bozza':
                continue
            if not task.step_ids:
                continue
            task.state = 'in_corso'
            ordered = task.step_ids.sorted(lambda s: s.sequence)
            if task.parallel:
                for step in ordered:
                    step._activate()
            else:
                ordered[0]._activate()
        return True

    def action_cancel(self):
        self.write({'state': 'annullato'})
        return True

    def action_draft(self):
        self.write({'state': 'bozza'})
        return True

    def _check_completion(self):
        for task in self:
            if task.state != 'in_corso':
                continue
            if task.step_ids and all(
                    s.state in ('confermato', 'saltato') for s in task.step_ids):
                task.state = 'chiuso'
                task.message_post(body=_("Task completato: tutti gli step confermati."))
                task._cf_notify(task.originator_id, 'task_closed', {})

    def _activate_next(self, after_step):
        """Handoff sequenziale: attiva il prossimo step da_fare per sequence."""
        self.ensure_one()
        if self.parallel:
            return
        nexts = self.step_ids.filtered(
            lambda s: s.state == 'da_fare' and not s.activated_dt
            and s.sequence >= after_step.sequence).sorted(lambda s: s.sequence)
        if nexts:
            nexts[0]._activate()

    # ---------------------------------------------------------------- notifica
    def _cf_notify_channels(self):
        ICP = self.env['ir.config_parameter'].sudo()
        raw = ICP.get_param('casafolino_task.notify_channels', 'mail,inapp')
        return [c.strip() for c in raw.split(',') if c.strip()]

    def _cf_notify(self, user, event, context=None):
        """Punto unico di notifica. Instrada per canale.

        v1: 'mail' (mail.mail via ir.mail_server) + 'inapp' (message_post).
        Canali futuri (telegram/whatsapp/display) si aggiungono definendo
        _cf_notify_<canale> senza toccare la logica task.
        """
        self.ensure_one()
        if not user:
            return
        context = dict(context or {})
        for channel in self._cf_notify_channels():
            handler = getattr(self, '_cf_notify_%s' % channel, None)
            if handler:
                try:
                    handler(user, event, context)
                except Exception:
                    _logger.exception(
                        "cf.task notify channel %s failed (event=%s, task=%s)",
                        channel, event, self.id)

    def _cf_render_event(self, event, context):
        self.ensure_one()
        subject_t, body_t = CF_EVENTS.get(event, ("[Task] {task}", "{task}"))
        ctx = {
            'task': self.name or '',
            'role': context.get('role', ''),
            'user': context.get('user', ''),
            'hours': context.get('hours', 0.0),
        }
        return subject_t.format(**ctx), body_t.format(**ctx)

    def _cf_notify_mail(self, user, event, context):
        if not user.email:
            return
        subject, body = self._cf_render_event(event, context)
        self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body,
            'email_to': user.email,
            'auto_delete': True,
        }).send()

    def _cf_notify_inapp(self, user, event, context):
        if not user.partner_id:
            return
        subject, body = self._cf_render_event(event, context)
        self.message_post(
            body=body, subject=subject,
            partner_ids=[user.partner_id.id],
            message_type='notification',
            subtype_xmlid='mail.mt_comment')

    # --------------------------------------------------------------- escalation
    @api.model
    def _cron_escalation_check(self):
        """Scansiona step aperti, ricalcola semaforo su ore lavorative,
        notifica originatore + Antonio sui rossi. Pattern del cron 53218."""
        Step = self.env['cf.task.step']
        open_steps = Step.search([
            ('state', 'in', ['da_fare', 'in_corso']),
            ('task_id.state', '=', 'in_corso'),
        ])
        if not open_steps:
            return
        open_steps._compute_traffic_light()
        for step in open_steps.filtered(lambda s: s.traffic_light == 'red'):
            step._escalate_red()
