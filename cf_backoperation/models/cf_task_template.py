"""cf.task.template — routine ricorrenti che generano istanze cf.task.

generate_today() è idempotente (chiave: template_id + task_date=oggi) ed è
chiamato dal cron cf_task_routine_generate (creato via ORM, MAI XML).
"""
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# riusa le stesse Selection della lente ops
from .cf_task_ops import OPS_CATEGORIES, OPS_PRIORITIES, OPS_NEW

WEEKDAY_FIELDS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


class CfTaskTemplate(models.Model):
    _name = 'cf.task.template'
    _description = 'CasaFolino — Template task ricorrente'
    _order = 'name'

    name = fields.Char(string="Nome routine", required=True)
    description = fields.Text(string="Descrizione")
    user_assigned_id = fields.Many2one(
        'res.users', string="Responsabile", required=True,
        help="Responsabile della routine (assegnatario delle istanze).")
    category = fields.Selection(OPS_CATEGORIES, string="Categoria")
    priority = fields.Selection(OPS_PRIORITIES, string="Priorità", default='1')

    recurrence_type = fields.Selection([
        ('daily', 'Ogni giorno'),
        ('weekdays', 'Lun–Ven'),
        ('weekly', 'Settimanale (giorni scelti)'),
        ('monthly', 'Mensile (giorno del mese)'),
    ], string="Ricorrenza", default='daily', required=True)

    mon = fields.Boolean(string="Lun")
    tue = fields.Boolean(string="Mar")
    wed = fields.Boolean(string="Mer")
    thu = fields.Boolean(string="Gio")
    fri = fields.Boolean(string="Ven")
    sat = fields.Boolean(string="Sab")
    sun = fields.Boolean(string="Dom")

    day_of_month = fields.Integer(string="Giorno del mese", help="1–31 (se mensile).")
    time_due = fields.Char(string="Orario", help="Es. '11:00'.")
    active = fields.Boolean(string="Attivo", default=True)

    task_count = fields.Integer(string="Istanze generate", compute='_compute_task_count')

    def _compute_task_count(self):
        data = self.env['cf.task'].read_group(
            [('template_id', 'in', self.ids)], ['template_id'], ['template_id'])
        counts = {d['template_id'][0]: d['template_id_count'] for d in data}
        for tpl in self:
            tpl.task_count = counts.get(tpl.id, 0)

    # ------------------------------------------------------------ matching
    def _matches_today(self, today):
        """True se la routine deve generare un'istanza oggi (Europe/Rome)."""
        self.ensure_one()
        rt = self.recurrence_type
        weekday = today.weekday()  # 0=lun .. 6=dom
        if rt == 'daily':
            return True
        if rt == 'weekdays':
            return weekday < 5
        if rt == 'weekly':
            return bool(getattr(self, WEEKDAY_FIELDS[weekday]))
        if rt == 'monthly':
            dom = self.day_of_month or 1
            # clamp a fine mese (es. 31 su febbraio = ultimo giorno)
            import calendar
            last = calendar.monthrange(today.year, today.month)[1]
            return today.day == min(dom, last)
        return False

    # ------------------------------------------------------------- generate
    @api.model
    def generate_today(self):
        """Genera le istanze cf.task del giorno per i template attivi che
        matchano oggi. Idempotente: salta se esiste già (template_id+task_date).
        Chiamato dal cron cf_task_routine_generate."""
        Task = self.env['cf.task']
        today = fields.Date.context_today(self)
        created = 0
        for tpl in self.search([('active', '=', True)]):
            if not tpl._matches_today(today):
                continue
            exists = Task.search_count([
                ('template_id', '=', tpl.id), ('task_date', '=', today)])
            if exists:
                continue
            Task.with_context(
                mail_create_nolog=True, mail_create_nosubscribe=True,
                mail_notify_force_send=False,
            ).create({
                'name': tpl.name,
                'description': tpl.description or False,
                'user_assigned_id': tpl.user_assigned_id.id,
                'category': tpl.category or False,
                'priority': tpl.priority or '1',
                'time_due': tpl.time_due or False,
                'is_routine': True,
                'template_id': tpl.id,
                'task_date': today,
                'state': OPS_NEW,
            })
            created += 1
        if created:
            _logger.info("cf.task.template: generate %d istanze routine per %s", created, today)
        return created
