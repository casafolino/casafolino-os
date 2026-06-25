"""CasaFolino Operations — lente 'task generico/personale' su cf.task.

Aggiunge SOLO i campi mancanti per il caso ad-hoc/routine a responsabile UNICO
(res.users), senza usare il motore step. Stato vive su cf.task.state: riusa i
valori esistenti (bozza/in_corso/chiuso/annullato) e aggiunge taken/blocked via
selection_add (non-breaking — vedi DISCOVERY.md §4). RPC op_* per la PWA.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

# Mappa lifecycle brief -> stati cf.task
OPS_NEW = 'bozza'          # new (assegnato)
OPS_TAKEN = 'taken'        # preso in carico
OPS_WIP = 'in_corso'       # in corso
OPS_BLOCKED = 'blocked'    # bloccato
OPS_DONE = 'chiuso'        # fatto
OPS_CANCELLED = 'annullato'

OPS_OPEN_STATES = (OPS_NEW, OPS_TAKEN, OPS_WIP, OPS_BLOCKED)
OPS_SETTABLE = (OPS_TAKEN, OPS_WIP, OPS_BLOCKED, OPS_DONE, OPS_CANCELLED, OPS_NEW)

# Categorie operative (brief §5.1)
OPS_CATEGORIES = [
    ('produzione', 'Produzione'),
    ('qualita', 'Qualità'),
    ('logistica', 'Logistica'),
    ('commerciale', 'Commerciale'),
    ('fiera', 'Fiera'),
    ('admin', 'Admin'),
    ('ecom', 'E-commerce'),
]

OPS_PRIORITIES = [
    ('0', 'Bassa'),
    ('1', 'Normale'),
    ('2', 'Alta'),
    ('3', 'Urgente'),
]


class CfTaskOps(models.Model):
    """Estensione cf.task per il sistema task unico (ad-hoc + routine)."""
    _inherit = 'cf.task'

    # nuovi stati, additivi: i record esistenti non vengono toccati
    state = fields.Selection(
        selection_add=[
            (OPS_TAKEN, 'Preso in carico'),
            (OPS_BLOCKED, 'Bloccato'),
        ],
        ondelete={OPS_TAKEN: 'set default', OPS_BLOCKED: 'set default'},
    )

    description = fields.Text(string="Descrizione")
    user_assigned_id = fields.Many2one(
        'res.users', string="Responsabile", index=True, tracking=True,
        help="Responsabile UNICO del task (assegnatario).")
    date_deadline = fields.Datetime(string="Scadenza", tracking=True)
    time_due = fields.Char(string="Orario", help="Orario indicativo, es. '11:00' (routine).")
    priority = fields.Selection(
        OPS_PRIORITIES, string="Priorità", default='1', index=True, tracking=True)
    acknowledged_date = fields.Datetime(string="Preso in carico il")
    category = fields.Selection(OPS_CATEGORIES, string="Categoria", index=True)

    is_routine = fields.Boolean(string="Routine", default=False, index=True)
    template_id = fields.Many2one(
        'cf.task.template', string="Template routine", ondelete='set null', index=True)
    task_date = fields.Date(
        string="Giorno", index=True,
        help="Giorno a cui appartiene l'istanza (chiave idempotenza routine).")

    ops_overdue = fields.Boolean(
        string="In ritardo", compute='_compute_ops_overdue',
        help="True se aperto e oltre la scadenza.")

    @api.depends('date_deadline', 'state')
    def _compute_ops_overdue(self):
        now = fields.Datetime.now()
        for t in self:
            t.ops_overdue = bool(
                t.date_deadline and t.state in OPS_OPEN_STATES and t.date_deadline < now)

    # --------------------------------------------------------------- helpers
    @api.model
    def _ops_user(self, user_id):
        user = self.env['res.users'].browse(int(user_id))
        if not user.exists():
            raise UserError(_("Utente (id=%s) inesistente.") % user_id)
        return user

    def _ops_is_manager(self, user):
        """Manager = ruolo che vede tutto (Antonio/capi-reparto)."""
        return user.has_group('base.group_system') or user.has_group(
            'cf_backoperation.group_ops_manager')

    def _ops_assert_can_touch(self, user):
        """Guardrail: l'utente tocca i propri task; il manager tutti."""
        if self._ops_is_manager(user):
            return
        for task in self:
            if task.user_assigned_id and task.user_assigned_id.id != user.id \
                    and task.create_uid.id != user.id:
                raise AccessError(_("Non puoi modificare un task non tuo."))

    # ------------------------------------------------------------ serialize
    def _ops_serialize(self):
        out = []
        for t in self:
            overdue = bool(
                t.date_deadline and t.state in OPS_OPEN_STATES
                and t.date_deadline < fields.Datetime.now())
            out.append({
                'id': t.id,
                'name': t.name,
                'description': t.description or '',
                'state': t.state,
                'priority': t.priority or '1',
                'category': t.category or False,
                'is_routine': t.is_routine,
                'time_due': t.time_due or '',
                'assigned_id': t.user_assigned_id.id or False,
                'assigned_name': t.user_assigned_id.name or False,
                'created_by': t.create_uid.name or False,
                'deadline': t.date_deadline and fields.Datetime.to_string(t.date_deadline) or False,
                'acknowledged': t.acknowledged_date and fields.Datetime.to_string(t.acknowledged_date) or False,
                'overdue': overdue,
            })
        return out

    # ----------------------------------------------------------------- RPC
    @api.model
    def op_get_my_day(self, user_id):
        """Task di OGGI dell'utente: routine + ad-hoc con scadenza oggi o
        scaduti aperti. Ordine: priorità desc, poi orario/scadenza."""
        user = self._ops_user(user_id)
        today = fields.Date.context_today(self)
        day_start = fields.Datetime.to_string(
            fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
        domain = [
            ('user_assigned_id', '=', user.id),
            '|', '|',
            ('task_date', '=', today),                       # routine di oggi
            ('date_deadline', '>=', day_start),              # ad-hoc con scadenza odierna/futura ravvicinata
            '&', ('state', 'in', list(OPS_OPEN_STATES)),     # scaduti ancora aperti
            ('date_deadline', '<', day_start),
        ]
        tasks = self.search(domain, limit=200)
        # esclude i chiusi/annullati vecchi non di oggi
        tasks = tasks.filtered(
            lambda t: t.state in OPS_OPEN_STATES
            or (t.task_date == today)
            or (t.date_deadline and t.date_deadline >= fields.Datetime.from_string(day_start)))
        tasks = tasks.sorted(
            key=lambda t: (-int(t.priority or '1'), t.time_due or '99:99',
                           t.date_deadline or fields.Datetime.now()))
        return tasks._ops_serialize()

    @api.model
    def op_create_task(self, vals):
        """Crea task ad-hoc. Ritorna l'id. Trigger notifica all'assegnatario."""
        clean = {
            'name': vals.get('name'),
            'description': vals.get('description') or False,
            'user_assigned_id': vals.get('user_assigned_id') or False,
            'date_deadline': vals.get('date_deadline') or False,
            'time_due': vals.get('time_due') or False,
            'priority': vals.get('priority') or '1',
            'category': vals.get('category') or False,
            'state': OPS_NEW,
        }
        if not clean['name']:
            raise UserError(_("Il task deve avere un titolo."))
        task = self.with_context(
            mail_create_nolog=True, mail_create_nosubscribe=True,
            mail_notify_force_send=False,
        ).create(clean)
        task._ops_notify_assigned()
        return task._ops_serialize()[0]

    def op_set_state(self, task_id, state, user_id=False):
        """Cambia stato: taken/in_progress/blocked/done/cancelled/new.
        Su 'taken' setta acknowledged_date."""
        task = self.browse(int(task_id))
        if not task.exists():
            raise UserError(_("Task %s inesistente.") % task_id)
        if state not in OPS_SETTABLE:
            raise UserError(_("Stato '%s' non valido.") % state)
        if user_id:
            task._ops_assert_can_touch(self._ops_user(user_id))
        if state == OPS_TAKEN and not task.acknowledged_date:
            task.acknowledged_date = fields.Datetime.now()
        task.state = state
        task._message_log(body=_("Stato → %s.") % dict(
            task._fields['state'].selection).get(state, state))
        return task._ops_serialize()[0]

    def op_ack(self, task_id, user_id=False):
        """Scorciatoia 'preso in carico'."""
        return self.op_set_state(task_id, OPS_TAKEN, user_id=user_id)

    @api.model
    def op_get_board(self, filters=None):
        """Console CEO: task aperti, in ritardo evidenziati, carico per persona."""
        filters = filters or {}
        domain = [('state', 'in', list(OPS_OPEN_STATES))]
        if filters.get('category'):
            domain.append(('category', '=', filters['category']))
        if filters.get('user_id'):
            domain.append(('user_assigned_id', '=', int(filters['user_id'])))
        tasks = self.search(domain, limit=500)
        rows = tasks._ops_serialize()
        # carico per persona (conteggio aperti per assegnatario)
        load = {}
        for t in tasks:
            uid = t.user_assigned_id.id or 0
            name = t.user_assigned_id.name or _("Non assegnato")
            entry = load.setdefault(uid, {'user_id': uid, 'name': name, 'open': 0, 'overdue': 0})
            entry['open'] += 1
        overdue_ids = {r['id'] for r in rows if r['overdue']}
        for t in tasks:
            if t.id in overdue_ids:
                load[t.user_assigned_id.id or 0]['overdue'] += 1
        return {
            'tasks': rows,
            'load': list(load.values()),
            'overdue_count': len(overdue_ids),
            'open_count': len(rows),
        }

    # ------------------------------------------------------------- notifica
    def _ops_notify_assigned(self):
        """Notifica 'nuovo task assegnato a me'. Riusa _cf_notify (mail+inapp);
        il canale push si aggancia in SLICE 4 via _cf_notify_push."""
        for task in self:
            if task.user_assigned_id:
                task._cf_notify(task.user_assigned_id, 'step_assigned',
                                {'role': task.category or _("task")})
