import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BoPrepLine(models.Model):
    """Riga di preparazione per campionature (sale.order senza picking).
    Per gli ordini con picking si usa il nativo stock.move.line.quantity."""
    _name = 'bo.prep.line'
    _description = 'BackOperation Prep Line (campionature)'

    task_id = fields.Many2one('cf.task', required=True, ondelete='cascade', index=True)
    sale_line_id = fields.Many2one('sale.order.line', ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    qty_req = fields.Float(string="Richiesto")
    qty_done = fields.Float(string="Preparato", default=0.0)


class BoWorkday(models.Model):
    """Giornata operativa (fallback finché hr_attendance non è installato)."""
    _name = 'bo.workday'
    _description = 'BackOperation Workday'
    _order = 'check_in desc'

    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    check_in = fields.Datetime(string="Inizio", required=True)
    check_out = fields.Datetime(string="Fine")
    worked_hours = fields.Float(compute='_compute_hours', store=True)

    @api.depends('check_in', 'check_out')
    def _compute_hours(self):
        for w in self:
            if w.check_in and w.check_out:
                w.worked_hours = (w.check_out - w.check_in).total_seconds() / 3600.0
            else:
                w.worked_hours = 0.0


class CfTaskOrders(models.Model):
    _inherit = 'cf.task'

    # ----------------------------------------------------- pool sale.order
    @api.model
    def _bo_order_pool(self):
        """Ordini e campionature da lavorare, non ancora trasformati in task."""
        SO = self.env['sale.order']
        linked = self.search([('bo_sale_order_id', '!=', False)]).mapped('bo_sale_order_id').ids
        # ordini: stato sale con picking outgoing da preparare
        odom = [('state', '=', 'sale')]
        if 'is_campione' in SO._fields:
            odom.append(('is_campione', '=', False))
        if linked:
            odom.append(('id', 'not in', linked))
        orders = SO.search(odom, order='date_order desc', limit=60)
        orders = orders.filtered(lambda o: o.picking_ids.filtered(
            lambda p: p.picking_type_id.code == 'outgoing' and p.state not in ('done', 'cancel')))
        # campionature
        camps = SO.browse()
        if 'is_campione' in SO._fields:
            cdom = [('is_campione', '=', True), ('state', 'in', ['draft', 'sent', 'sale'])]
            if linked:
                cdom.append(('id', 'not in', linked))
            camps = SO.search(cdom, order='date_order desc', limit=60)
        return orders, camps

    def _bo_serialize_so(self, sos, kind):
        out = []
        for so in sos:
            righe = [{'product': l.product_id.display_name, 'qty': l.product_uom_qty}
                     for l in so.order_line if l.product_id and not l.display_type]
            out.append({
                'is_so': True,
                'so_id': so.id,
                'kind': kind,
                'name': _("%s — %s") % (kind.capitalize(), so.partner_id.name or so.name),
                'so_ref': so.name,
                'partner': so.partner_id.name or '',
                'date_order': so.date_order and fields.Datetime.to_string(so.date_order) or False,
                'commitment': so.commitment_date and fields.Datetime.to_string(so.commitment_date) or False,
                'lines': righe,
                'product': (righe[0]['product'] if righe else False),
            })
        return out

    @api.model
    def bo_claim_sale_order(self, so_id, employee_id, kind):
        emp = self._bo_check_employee(employee_id)
        so = self.env['sale.order'].browse(int(so_id))
        if not so.exists():
            raise UserError(_("Ordine %s inesistente.") % so_id)
        existing = self.search([('bo_sale_order_id', '=', so.id)], limit=1)
        if existing:
            existing.bo_titolare_id = emp.id
            return self._bo_serialize(existing.ids)[0]
        task = self.with_context(
            mail_create_nolog=True, mail_create_nosubscribe=True,
        ).create({
            'name': _("%s %s — %s") % (kind.capitalize(), so.name, so.partner_id.name or ''),
            'bo_kind': 'campionatura' if kind == 'campionatura' else 'ordine',
            'bo_sale_order_id': so.id,
            'bo_titolare_id': emp.id,
            'state': 'bozza',
        })
        task._message_log(body=_("Creata da %s %s, presa da %s.") % (kind, so.name, emp.name))
        return self._bo_serialize(task.ids)[0]

    # ----------------------------------------------------- preparazione/scan
    def _bo_outgoing_picking(self, so):
        return so.picking_ids.filtered(
            lambda p: p.picking_type_id.code == 'outgoing'
            and p.state not in ('done', 'cancel'))[:1]

    @api.model
    def bo_get_order_prep(self, task_id):
        """Righe da preparare con preparato/richiesto. Ordini→picking, campionature→bo.prep.line."""
        task = self.browse(int(task_id))
        if not task.exists() or not task.bo_sale_order_id:
            return {'applies': False}
        so = task.bo_sale_order_id
        pk = self._bo_outgoing_picking(so)
        lines = []
        if pk:
            for m in pk.move_ids.filtered(lambda x: x.state not in ('done', 'cancel')):
                done = sum(m.move_line_ids.mapped('quantity'))
                lines.append({
                    'line_id': m.id, 'kind': 'move',
                    'product': m.product_id.display_name,
                    'product_id': m.product_id.id,
                    'req': m.product_uom_qty, 'done': done,
                    'uom': m.product_uom.name or '',
                })
            target = 'picking'
        else:
            # campionatura: bo.prep.line materializzata da order_line
            PL = self.env['bo.prep.line']
            if not task.with_context(active_test=False) and False:
                pass
            existing = PL.search([('task_id', '=', task.id)])
            if not existing:
                for ol in so.order_line.filtered(lambda l: l.product_id and not l.display_type):
                    PL.create({'task_id': task.id, 'sale_line_id': ol.id,
                               'product_id': ol.product_id.id, 'qty_req': ol.product_uom_qty})
                existing = PL.search([('task_id', '=', task.id)])
            for pl in existing:
                lines.append({
                    'line_id': pl.id, 'kind': 'prep',
                    'product': pl.product_id.display_name,
                    'product_id': pl.product_id.id,
                    'req': pl.qty_req, 'done': pl.qty_done, 'uom': '',
                })
            target = 'prep'
        missing = sum(1 for l in lines if l['done'] < l['req'])
        return {'applies': True, 'target': target, 'so_ref': so.name,
                'partner': so.partner_id.name or '', 'lines': lines, 'missing': missing,
                'tracking': (pk.carrier_tracking_ref if pk else False) or False,
                'has_picking': bool(pk)}

    def _bo_prep_apply(self, task, product, qty):
        """Incrementa la preparazione del prodotto. Ritorna esito (estraneo se non in ordine)."""
        so = task.bo_sale_order_id
        pk = self._bo_outgoing_picking(so)
        if pk:
            move = pk.move_ids.filtered(
                lambda m: m.product_id.id == product.id and m.state not in ('done', 'cancel'))[:1]
            if not move:
                return {'ok': False, 'reason': 'estraneo', 'product': product.display_name}
            ml = move.move_line_ids[:1]
            if ml:
                ml.quantity = ml.quantity + qty
            else:
                self.env['stock.move.line'].create({
                    'move_id': move.id, 'picking_id': pk.id,
                    'product_id': product.id, 'quantity': qty,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                })
            done = sum(move.move_line_ids.mapped('quantity'))
            return {'ok': True, 'product': product.display_name, 'done': done,
                    'req': move.product_uom_qty}
        # campionatura
        PL = self.env['bo.prep.line']
        pl = PL.search([('task_id', '=', task.id), ('product_id', '=', product.id)], limit=1)
        if not pl:
            return {'ok': False, 'reason': 'estraneo', 'product': product.display_name}
        pl.qty_done = pl.qty_done + qty
        return {'ok': True, 'product': product.display_name, 'done': pl.qty_done, 'req': pl.qty_req}

    @api.model
    def bo_scan(self, task_id, barcode):
        task = self.browse(int(task_id))
        if not task.exists() or not task.bo_sale_order_id:
            raise UserError(_("Task ordine inesistente."))
        code = (barcode or '').strip()
        if not code:
            return {'ok': False, 'reason': 'vuoto'}
        pack = self.env['product.packaging'].search([('barcode', '=', code)], limit=1)
        if pack:
            return self._bo_prep_apply(task, pack.product_id, pack.qty or 1)
        product = self.env['product.product'].search([('barcode', '=', code)], limit=1)
        if not product:
            return {'ok': False, 'reason': 'not_found', 'barcode': code}
        return self._bo_prep_apply(task, product, 1)

    @api.model
    def bo_set_prep_qty(self, task_id, line_id, kind, qty):
        """Imposta a mano la qty preparata di una riga (10 pezzi senza 10 scan)."""
        task = self.browse(int(task_id))
        qty = max(0.0, float(qty))
        if kind == 'move':
            move = self.env['stock.move'].browse(int(line_id))
            ml = move.move_line_ids[:1]
            if ml:
                ml.quantity = qty
                # azzera eventuali righe extra
                (move.move_line_ids - ml).write({'quantity': 0})
            else:
                self.env['stock.move.line'].create({
                    'move_id': move.id, 'picking_id': move.picking_id.id,
                    'product_id': move.product_id.id, 'quantity': qty,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id})
        else:
            self.env['bo.prep.line'].browse(int(line_id)).qty_done = qty
        return self.bo_get_order_prep(task.id)

    # --------------------------------------------------------------- foto
    @api.model
    def bo_add_photo(self, task_id, kind, image_b64):
        """Foto obbligatoria -> ir.attachment su sale.order (dossier nativo)."""
        task = self.browse(int(task_id))
        if not task.exists() or not task.bo_sale_order_id:
            raise UserError(_("Task ordine inesistente."))
        raw = image_b64.split(',', 1)[-1] if ',' in (image_b64 or '') else image_b64
        op = task.bo_operatore_id.name or task.bo_titolare_id.name or ''
        name = _("BO %s — %s — %s") % (
            'contenuto' if kind == 'contenuto' else 'pacco_finito', op,
            fields.Datetime.to_string(fields.Datetime.now()))
        att = self.env['ir.attachment'].create({
            'name': name, 'datas': raw, 'res_model': 'sale.order',
            'res_id': task.bo_sale_order_id.id, 'mimetype': 'image/jpeg',
        })
        task._message_log(body=_("Foto %s caricata (%s).") % (kind, op))
        return {'ok': True, 'attachment_id': att.id, 'kind': kind}

    @api.model
    def bo_photo_status(self, task_id):
        task = self.browse(int(task_id))
        if not task.bo_sale_order_id:
            return {'contenuto': False, 'pacco_finito': False}
        atts = self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'), ('res_id', '=', task.bo_sale_order_id.id),
            ('name', 'like', 'BO %')])
        return {
            'contenuto': any('contenuto' in a.name for a in atts),
            'pacco_finito': any('pacco_finito' in a.name for a in atts),
        }

    # ------------------------------------------------------------ tracking
    @api.model
    def bo_set_tracking(self, task_id, tracking_code):
        task = self.browse(int(task_id))
        so = task.bo_sale_order_id
        pk = self._bo_outgoing_picking(so) if so else False
        if not pk:
            return {'ok': False, 'reason': 'no_picking'}
        pk.carrier_tracking_ref = (tracking_code or '').strip()
        task._message_log(body=_("Tracking: %s") % pk.carrier_tracking_ref)
        return {'ok': True, 'tracking': pk.carrier_tracking_ref}

    # ------------------------------------------------------ inizio/fine giornata
    @api.model
    def bo_day_start(self, employee_id):
        emp = self._bo_check_employee(employee_id)
        WD = self.env['bo.workday']
        openw = WD.search([('employee_id', '=', emp.id), ('check_out', '=', False)], limit=1)
        if openw:
            return {'ok': True, 'already_open': True, 'workday_id': openw.id}
        wd = WD.create({'employee_id': emp.id, 'check_in': fields.Datetime.now()})
        return {'ok': True, 'workday_id': wd.id, 'check_in': fields.Datetime.to_string(wd.check_in)}

    @api.model
    def bo_day_end(self, employee_id):
        emp = self._bo_check_employee(employee_id)
        WD = self.env['bo.workday']
        openw = WD.search([('employee_id', '=', emp.id), ('check_out', '=', False)],
                          order='check_in desc', limit=1)
        if not openw:
            return {'ok': False, 'reason': 'no_open_day'}
        openw.check_out = fields.Datetime.now()
        return {'ok': True, 'worked_hours': round(openw.worked_hours, 2)}

    @api.model
    def bo_day_status(self, employee_id):
        emp = self._bo_check_employee(int(employee_id))
        WD = self.env['bo.workday']
        openw = WD.search([('employee_id', '=', emp.id), ('check_out', '=', False)], limit=1)
        return {'open': bool(openw),
                'check_in': openw.check_in and fields.Datetime.to_string(openw.check_in) or False}
