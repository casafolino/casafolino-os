import base64
import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Parametro che abilita la chiusura magazzino (B2) su questo DB. Default False:
# il flusso B2 NON tocca nulla finché Antonio non lo abilita (secondo gate).
B2_FLAG_PARAM = 'casafolino.bo_b2_enabled'

# Stati cf.task riusati (modulo casafolino_task): bozza / in_corso / chiuso / annullato.
# Mapping lifecycle BackOperation:
#   da_fare -> bozza | in_corso -> in_corso | fatta -> chiuso
BO_DONE_STATE = 'chiuso'
BO_TODO_STATE = 'bozza'
BO_WIP_STATE = 'in_corso'

# Stati MO "da produrre" esposti come card claimabili nel pool.
MRP_POOL_STATES = ('confirmed', 'progress')


class CfTaskBackOperation(models.Model):
    """Estensione di cf.task per la PWA BackOperation (Livello A).

    Aggiunge SOLO i campi mancanti: lo stato vive su cf.task.state. Le scritture
    arrivano dal service account Odoo, ma ogni record traccia l'hr.employee reale
    (bo_operatore_id / bo_titolare_id) per audit IFS/BRC.
    """
    _inherit = 'cf.task'

    bo_kind = fields.Selection([
        ('produzione', 'Produzione'),
        ('campionatura', 'Campionatura'),
        ('ordine', 'Ordine'),
        ('generico', 'Generico'),
    ], string="Tipo BackOp", default='generico', tracking=True, index=True)

    bo_production_id = fields.Many2one(
        'mrp.production', string="Ordine di produzione",
        ondelete='set null', index=True)
    bo_sale_order_id = fields.Many2one(
        'sale.order', string="Ordine di vendita", ondelete='set null')

    bo_titolare_id = fields.Many2one(
        'hr.employee', string="Titolare (claim)", index=True,
        help="Operativa che ha preso in carico la task dal pool.")
    bo_assegnata_da_id = fields.Many2one(
        'res.users', string="Assegnata da",
        help="Antonio/Martina che ha assegnato la task dentro Odoo.")
    bo_is_pool = fields.Boolean(
        string="In pool", compute='_compute_bo_is_pool', store=True,
        help="True se libera (nessun titolare e non assegnata).")

    bo_checkin_at = fields.Datetime(string="Check-in")
    bo_checkout_at = fields.Datetime(string="Check-out")
    bo_worked_seconds = fields.Integer(
        string="Secondi lavorati", default=0,
        help="Accumulatore: somma delle sessioni check-in/check-out.")

    bo_operatore_id = fields.Many2one(
        'hr.employee', string="Operatore (firma)", index=True,
        help="Chi ha eseguito materialmente = firma. Risposta all'audit.")
    bo_firmata = fields.Boolean(string="Firmata", default=False)
    bo_firma_at = fields.Datetime(string="Data firma")
    bo_firma_image = fields.Binary(string="Firma", attachment=True)

    bo_phase_ids = fields.One2many('cf.task.phase', 'task_id', string="Fasi")

    # ------------------------------------------------------------- computes
    @api.depends('bo_titolare_id', 'bo_assegnata_da_id')
    def _compute_bo_is_pool(self):
        for task in self:
            task.bo_is_pool = not task.bo_titolare_id and not task.bo_assegnata_da_id

    # --------------------------------------------------------- helper employee
    def _bo_check_employee(self, employee_id):
        emp = self.env['hr.employee'].browse(int(employee_id))
        if not emp.exists():
            raise UserError(_("Operatore (employee_id=%s) inesistente.") % employee_id)
        return emp

    # ------------------------------------------------------------- lifecycle
    def bo_action_claim(self, employee_id):
        """Prendi dal pool: imposta titolare. Stato resta da_fare (bozza)."""
        emp = self._bo_check_employee(employee_id)
        for task in self:
            task.bo_titolare_id = emp.id
            if task.state == BO_DONE_STATE:
                task.state = BO_TODO_STATE
            task._message_log(body=_("Presa in carico da %s.") % emp.name)
        return self._bo_serialize(self.ids)

    def bo_action_to_pool(self):
        """Rimetti la task nel pool (riassegnabile)."""
        for task in self:
            task.bo_titolare_id = False
            task.bo_assegnata_da_id = False
            task._message_log(body=_("Rimessa nel pool."))
        return self._bo_serialize(self.ids)

    def bo_action_checkin(self, employee_id):
        """Inizia: timer parte, operatore registrato, stato -> in_corso."""
        emp = self._bo_check_employee(employee_id)
        now = fields.Datetime.now()
        for task in self:
            if not task.bo_titolare_id:
                task.bo_titolare_id = emp.id
            task.bo_operatore_id = emp.id
            task.bo_checkin_at = now
            task.bo_checkout_at = False
            task.state = BO_WIP_STATE
            task._bo_materialize_phases()
            task._message_log(body=_("Check-in di %s.") % emp.name)
        return self._bo_serialize(self.ids)

    # --------------------------------------------------------------- fasi
    def _bo_materialize_phases(self):
        """Snapshot delle operazioni MO -> cf.task.phase al primo check-in.
        Idempotente: non ricrea se già presenti. Solo per produzioni."""
        self.ensure_one()
        if self.bo_kind != 'produzione' or not self.bo_production_id:
            return
        if self.bo_phase_ids:
            return
        Phase = self.env['cf.task.phase']
        seq = 10
        for wo in self.bo_production_id.workorder_ids:
            Phase.create({
                'task_id': self.id,
                'seq': seq,
                'name': wo.operation_id.name or wo.name or _("Fase"),
                'state': 'da_fare',
                'bo_workorder_id': wo.id,
            })
            seq += 10

    def _bo_resolve_workorder(self, phase):
        """WO collegato alla fase: id esplicito o fallback per nome nella MO."""
        if phase.bo_workorder_id:
            return phase.bo_workorder_id
        task = phase.task_id
        if not task.bo_production_id:
            return self.env['mrp.workorder']
        wo = task.bo_production_id.workorder_ids.filtered(
            lambda w: (w.operation_id.name or w.name) == phase.name)
        return wo[:1]

    @api.model
    def bo_phase_start(self, phase_id, employee_id):
        emp = self._bo_check_employee(employee_id)
        phase = self.env['cf.task.phase'].browse(int(phase_id))
        if not phase.exists():
            raise UserError(_("Fase %s inesistente.") % phase_id)
        phase.write({
            'state': 'in_corso',
            'operatore_id': emp.id,
            'started_at': phase.started_at or fields.Datetime.now(),
            'ended_at': False,
        })
        self._bo_sync_wo_start(phase)
        phase.task_id._message_log(
            body=_("Fase '%s' iniziata da %s.") % (phase.name, emp.name))
        return phase._bo_serialize()[0]

    # --------------------------------------------- Livello B: sync workorder
    def _bo_sync_wo_start(self, phase):
        """B1: avvia il WO reale. Idempotente, degrada senza rompere l'app."""
        wo = self._bo_resolve_workorder(phase)
        if not wo:
            return
        try:
            if wo.state not in ('progress', 'done'):
                wo.button_start()
        except Exception as e:
            _logger.warning("WO %s button_start fallito (%s): scrivo date_start soft.",
                            wo.id, e)
            try:
                if not wo.date_start:
                    wo.date_start = fields.Datetime.now()
            except Exception:
                _logger.exception("WO %s date_start soft fallito.", wo.id)

    def _bo_sync_wo_finish(self, phase):
        """B1: chiude il WO reale. Idempotente, degrada senza rompere l'app."""
        wo = self._bo_resolve_workorder(phase)
        if not wo:
            return
        try:
            if wo.state == 'done':
                return
            if wo.state != 'progress':
                # serve essere in progress per finire pulito
                wo.button_start()
            wo.button_finish()
        except Exception as e:
            _logger.warning("WO %s button_finish fallito (%s): scrivo date_finished soft.",
                            wo.id, e)
            try:
                if not wo.date_finished:
                    wo.date_finished = fields.Datetime.now()
            except Exception:
                _logger.exception("WO %s date_finished soft fallito.", wo.id)

    @api.model
    def bo_phase_end(self, phase_id, employee_id=False):
        phase = self.env['cf.task.phase'].browse(int(phase_id))
        if not phase.exists():
            raise UserError(_("Fase %s inesistente.") % phase_id)
        vals = {'state': 'fatta', 'ended_at': fields.Datetime.now()}
        if employee_id:
            emp = self._bo_check_employee(employee_id)
            vals['operatore_id'] = phase.operatore_id.id or emp.id
        phase.write(vals)
        self._bo_sync_wo_finish(phase)
        phase.task_id._message_log(body=_("Fase '%s' terminata.") % phase.name)
        return phase._bo_serialize()[0]

    @api.model
    def bo_get_phases(self, task_id):
        task = self.browse(int(task_id))
        if not task.exists():
            return []
        return task.bo_phase_ids._bo_serialize()

    def bo_action_checkout(self):
        """Ferma il timer, accumula i secondi della sessione."""
        now = fields.Datetime.now()
        for task in self:
            if task.bo_checkin_at and not task.bo_checkout_at:
                delta = (now - task.bo_checkin_at).total_seconds()
                task.bo_worked_seconds = (task.bo_worked_seconds or 0) + max(0, int(delta))
                task.bo_checkout_at = now
                task._message_log(body=_("Check-out (sessione %ds).") % int(delta))
        return self._bo_serialize(self.ids)

    def _bo_sign_one(self, task, emp, firma_b64):
        """Logica firma su una task (riusata da sign e close)."""
        now = fields.Datetime.now()
        if task.bo_checkin_at and not task.bo_checkout_at:
            delta = (now - task.bo_checkin_at).total_seconds()
            task.bo_worked_seconds = (task.bo_worked_seconds or 0) + max(0, int(delta))
            task.bo_checkout_at = now
        task.bo_operatore_id = emp.id
        task.bo_firmata = True
        task.bo_firma_at = now
        if firma_b64:
            raw = firma_b64.split(',', 1)[-1] if ',' in firma_b64 else firma_b64
            try:
                base64.b64decode(raw)
                task.bo_firma_image = raw
            except Exception:
                _logger.warning("Firma non valida per task %s, ignorata.", task.id)
        task.state = BO_DONE_STATE

    def bo_action_sign(self, employee_id, firma_b64=False):
        """Firma e chiudi (Livello A): operatore + timestamp + firma."""
        emp = self._bo_check_employee(employee_id)
        for task in self:
            self._bo_sign_one(task, emp, firma_b64)
            task._message_log(body=_("Firmata e chiusa da %s.") % emp.name)
        return self._bo_serialize(self.ids)

    # ============================================================ B2 (gated)
    @api.model
    def _bo_b2_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            B2_FLAG_PARAM, 'False') in ('True', 'true', '1')

    @api.model
    def _bo_lot_sku(self, mo):
        return (mo.product_id.default_code or mo.product_id.name or '').strip()

    @api.model
    def bo_get_lot_default(self, task_id):
        """Default lotto finito = {SKU}-{DDD}-{YY} (giorno dell'anno, anno 2 cifre).
        Ritorna anche regex SKU e se il lotto esiste già (avviso duplicato)."""
        task = self.browse(int(task_id))
        if not task.exists() or not task.bo_production_id:
            return {'applies': False}
        mo = task.bo_production_id
        finito_lot = mo.product_id.tracking == 'lot'
        sku = self._bo_lot_sku(mo)
        today = fields.Date.context_today(self)
        ddd = today.timetuple().tm_yday
        default = "%s-%03d-%02d" % (sku, ddd, today.year % 100)
        exists = bool(self.env['stock.lot'].search_count([
            ('name', '=', default), ('product_id', '=', mo.product_id.id)]))
        return {
            'applies': True,
            'b2_enabled': self._bo_b2_enabled(),
            'requires_lot': finito_lot,
            'sku': sku,
            'default': default,
            'pattern': '^%s-[0-9]{3}-[0-9]{2}$' % re.escape(sku),
            'default_exists': exists,
            'qty': mo.product_qty,
            'uom': mo.product_uom_id.name or '',
        }

    def _bo_validate_lot(self, mo, lot_name):
        sku = self._bo_lot_sku(mo)
        if not re.match(r'^%s-\d{3}-\d{2}$' % re.escape(sku), lot_name or ''):
            raise UserError(_("Lotto '%s' non valido: atteso %s-DDD-YY.") % (lot_name, sku))

    def _bo_force_mark_done(self, mo):
        """button_mark_done gestendo i wizard (consumption warning / immediate)."""
        res = mo.with_context(skip_redirection=True).button_mark_done()
        # Odoo può restituire un'azione-wizard: confermala.
        guard = 0
        while isinstance(res, dict) and res.get('res_model') and guard < 4:
            guard += 1
            model = res['res_model']
            ctx = dict(res.get('context') or {})
            Wiz = self.env[model].with_context(ctx)
            wiz = Wiz.create({})
            done = False
            for meth in ('action_confirm', 'process', 'action_done',
                         'action_generate_serial', 'do_produce'):
                if hasattr(wiz, meth):
                    res = getattr(wiz, meth)()
                    done = True
                    break
            if not done:
                break
        return res

    def _bo_b2_close_mo(self, task, lot_name, qty_done, qty_scrap):
        """Chiusura magazzino reale: lotto finito + qty + consumo + mark_done.
        Idempotente: se MO già done, no-op."""
        mo = task.bo_production_id
        if not mo or mo.state == 'done':
            return False
        qty = qty_done or mo.product_qty
        if mo.product_id.tracking != 'none':
            self._bo_validate_lot(mo, lot_name)
            Lot = self.env['stock.lot']
            lot = Lot.search([
                ('name', '=', lot_name), ('product_id', '=', mo.product_id.id),
                ('company_id', '=', mo.company_id.id)], limit=1)
            if not lot:
                lot = Lot.create({
                    'name': lot_name, 'product_id': mo.product_id.id,
                    'company_id': mo.company_id.id})
            mo.lot_producing_id = lot.id
        mo.qty_producing = qty
        if qty_scrap:
            task._message_log(body=_("Scarto dichiarato: %s") % qty_scrap)
        self._bo_force_mark_done(mo)
        return mo.state == 'done'

    def bo_action_close(self, employee_id, firma_b64=False,
                        lot_name=False, qty_done=False, qty_scrap=0.0):
        """Chiusura task produzione: firma (sempre) + B2 (se abilitato e produzione).
        Con flag B2 OFF: equivale alla firma Livello A (nessun movimento stock)."""
        emp = self._bo_check_employee(employee_id)
        for task in self:
            self._bo_sign_one(task, emp, firma_b64)
            did_b2 = False
            if (task.bo_kind == 'produzione' and task.bo_production_id
                    and self._bo_b2_enabled()):
                did_b2 = self._bo_b2_close_mo(task, lot_name, qty_done, qty_scrap)
            if did_b2:
                task._message_log(body=_(
                    "Chiusa da %s — magazzino allineato (lotto %s, MO done).")
                    % (emp.name, lot_name or ''))
            else:
                task._message_log(body=_("Firmata e chiusa da %s.") % emp.name)
        return self._bo_serialize(self.ids)

    # --------------------------------------------------- claim da MO produzione
    @api.model
    def bo_claim_production(self, production_id, employee_id):
        """Trasforma una card MO del pool in cf.task e la prende in carico."""
        emp = self._bo_check_employee(employee_id)
        mo = self.env['mrp.production'].browse(int(production_id))
        if not mo.exists():
            raise UserError(_("MO %s inesistente.") % production_id)
        existing = self.search([('bo_production_id', '=', mo.id)], limit=1)
        if existing:
            existing.bo_titolare_id = emp.id
            return self._bo_serialize(existing.ids)[0]
        task = self.with_context(
            mail_create_nolog=True, mail_create_nosubscribe=True,
            mail_notify_force_send=False,
        ).create({
            'name': _("Produzione %s — %s") % (mo.name, mo.product_id.display_name or ''),
            'bo_kind': 'produzione',
            'bo_production_id': mo.id,
            'bo_titolare_id': emp.id,
            'state': BO_TODO_STATE,
        })
        task._message_log(body=_("Creata da MO %s, presa in carico da %s.") % (mo.name, emp.name))
        return self._bo_serialize(task.ids)[0]

    # ----------------------------------------------------------- floor plan
    @api.model
    def bo_get_floorplan(self, task_id):
        """Scheda produzione (floor plan) della task: ricetta (distinta) + fasi.

        Restituita al check-in di una produzione. Le operative non hanno
        accesso Odoo: il contenuto viene renderizzato in-app.
        """
        task = self.browse(int(task_id))
        if not task.exists() or not task.bo_production_id:
            return {'has': False}
        mo = task.bo_production_id
        recipe = []
        for line in (mo.bom_id.bom_line_ids if mo.bom_id else []):
            recipe.append({
                'name': line.product_id.display_name or '',
                'qty': line.product_qty,
                'uom': line.product_uom_id.name or '',
            })
        # Fasi: se materializzate (post check-in) ritorna quelle eseguibili,
        # altrimenti anteprima sola-lettura dai nomi operazione MO.
        if task.bo_phase_ids:
            phases = task.bo_phase_ids._bo_serialize()
            materialized = True
        else:
            phases = []
            seq = 10
            for wo in mo.workorder_ids:
                phases.append({
                    'id': False, 'seq': seq,
                    'name': wo.operation_id.name or wo.name or '',
                    'state': 'da_fare', 'operatore_id': False,
                    'operatore_name': False, 'started_at': False, 'ended_at': False,
                })
                seq += 10
            materialized = False
        return {
            'has': True,
            'mo_ref': mo.name,
            'product': mo.product_id.display_name or '',
            'qty': mo.product_qty,
            'uom': mo.product_uom_id.name or '',
            'recipe': recipe,
            'phases': phases,
            'phases_materialized': materialized,
        }

    # ----------------------------------------------------------- serialization
    def _bo_serialize(self, ids):
        recs = self.browse(ids)
        out = []
        for t in recs:
            out.append({
                'id': t.id,
                'name': t.name,
                'kind': t.bo_kind,
                'state': t.state,
                'is_pool': t.bo_is_pool,
                'titolare_id': t.bo_titolare_id.id or False,
                'titolare_name': t.bo_titolare_id.name or False,
                'operatore_id': t.bo_operatore_id.id or False,
                'operatore_name': t.bo_operatore_id.name or False,
                'assegnata_da': t.bo_assegnata_da_id.name or False,
                'production_id': t.bo_production_id.id or False,
                'production_ref': t.bo_production_id.name or False,
                'product': t.bo_production_id.product_id.display_name or (t.bo_sale_order_id.name or False),
                'checkin_at': t.bo_checkin_at and fields.Datetime.to_string(t.bo_checkin_at) or False,
                'checkout_at': t.bo_checkout_at and fields.Datetime.to_string(t.bo_checkout_at) or False,
                'worked_seconds': t.bo_worked_seconds or 0,
                'firmata': t.bo_firmata,
                'firma_at': t.bo_firma_at and fields.Datetime.to_string(t.bo_firma_at) or False,
            })
        return out

    def _bo_serialize_mo(self, mos):
        out = []
        for mo in mos:
            out.append({
                'mo_id': mo.id,
                'kind': 'produzione',
                'is_mo': True,
                'name': _("Produzione %s") % mo.name,
                'production_ref': mo.name,
                'product': mo.product_id.display_name or '',
                'qty': mo.product_qty,
                'mo_state': mo.state,
                'date_start': mo.date_start and fields.Datetime.to_string(mo.date_start) or False,
            })
        return out

    # ------------------------------------------------------------------- board
    @api.model
    def bo_get_board(self, employee_id):
        """Bacheca 'Oggi' per un'operativa.

        pool = task libere (claimabili) + MO da produrre non ancora trasformate.
        assigned_to_me = titolare me, non ancora avviate.
        in_progress = stato in_corso che mi riguardano.
        done_today = chiuse oggi da me.
        """
        emp = self._bo_check_employee(employee_id)
        eid = emp.id

        pool_tasks = self.search([
            ('bo_is_pool', '=', True),
            ('state', '=', BO_TODO_STATE),
        ], order='create_date desc', limit=100)

        assigned = self.search([
            ('bo_titolare_id', '=', eid),
            ('state', '=', BO_TODO_STATE),
        ], order='create_date desc', limit=100)

        in_progress = self.search([
            '|', ('bo_operatore_id', '=', eid), ('bo_titolare_id', '=', eid),
            ('state', '=', BO_WIP_STATE),
        ], order='bo_checkin_at desc', limit=100)

        today_start = fields.Datetime.to_string(
            fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
        done_today = self.search([
            ('bo_operatore_id', '=', eid),
            ('state', '=', BO_DONE_STATE),
            ('bo_firma_at', '>=', today_start),
        ], order='bo_firma_at desc', limit=100)

        # MO da produrre senza cf.task collegata -> card sintetiche nel pool
        linked = self.search([('bo_production_id', '!=', False)]).mapped('bo_production_id').ids
        mo_domain = [('state', 'in', list(MRP_POOL_STATES))]
        if linked:
            mo_domain.append(('id', 'not in', linked))
        mos = self.env['mrp.production'].search(mo_domain, order='date_start asc', limit=100)

        return {
            'employee': {'id': eid, 'name': emp.name},
            'pool': self._bo_serialize(pool_tasks.ids) + self._bo_serialize_mo(mos),
            'assigned_to_me': self._bo_serialize(assigned.ids),
            'in_progress': self._bo_serialize(in_progress.ids),
            'done_today': self._bo_serialize(done_today.ids),
        }
