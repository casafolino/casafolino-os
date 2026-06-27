import logging

from odoo import api, models, _
from odoo.exceptions import AccessError

from .console_gateway import _is_console

_logger = logging.getLogger(__name__)

# Sotto-albero "CasaFolino B2B" (parent id 44): le sue categorie figlie SONO le linee di prodotto.
# Lente pura: nessun dato duplicato — tutto calcolato live dai nativi (sale.order) per partner+linea.
# Campionature = sale.order con is_campione=True; preventivi = draft/sent; ordini = sale/done.
B2B_ROOT_XMLID_FALLBACK = 44


class ResPartnerLines(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _console_line_categories(self):
        """Le categorie-linea = figlie dirette del nodo 'CasaFolino B2B'. Robusto: trova il root
        per nome se l'id 44 cambiasse."""
        Cat = self.env['product.category'].sudo()
        root = Cat.browse(B2B_ROOT_XMLID_FALLBACK)
        if not root.exists() or 'B2B' not in (root.name or ''):
            root = Cat.search([('name', '=', 'CasaFolino B2B'), ('parent_id', '=', False)], limit=1) \
                or Cat.search([('name', 'ilike', 'CasaFolino B2B')], limit=1)
        if not root:
            return Cat.browse()
        return Cat.search([('parent_id', '=', root.id)])

    @api.model
    def console_partner_lines(self, payload=None):
        """Lente: linee di prodotto di un cliente con conteggi (campionature/preventivi/ordini/valore),
        calcolati live dai sale.order.line. payload: {partner_id}. Read-only gated."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console."))
        pid = int((payload or {}).get('partner_id') or 0)
        if not pid:
            return {'ok': False, 'message': 'partner_id mancante'}
        line_cats = self._console_line_categories()
        SOL = self.env['sale.order.line'].sudo()
        sols = SOL.search([
            ('order_partner_id', '=', pid),
            ('product_id.categ_id', 'in', line_cats.ids),
        ])
        agg = {}
        for l in sols:
            o = l.order_id
            cid = l.product_id.categ_id.id
            a = agg.setdefault(cid, {'camp': set(), 'prev': set(), 'ord': set(), 'value': 0.0})
            if o.is_campione:
                a['camp'].add(o.id)
            elif o.state in ('sale', 'done'):
                a['ord'].add(o.id)
                a['value'] += l.price_subtotal
            else:
                a['prev'].add(o.id)
        cat_name = {c.id: c.name for c in line_cats}
        lines = []
        for cid, a in agg.items():
            state = 'attivo' if a['ord'] else ('esplorazione' if (a['prev'] or a['camp']) else 'chiuso')
            lines.append({
                'category_id': cid, 'name': cat_name.get(cid, ''),
                'n_campionature': len(a['camp']), 'n_preventivi': len(a['prev']),
                'n_ordini': len(a['ord']), 'value': round(a['value'], 2), 'state': state,
            })
        lines.sort(key=lambda x: (-x['n_ordini'], -x['value'], x['name']))
        return {'ok': True, 'partner_id': pid, 'lines': lines}

    @api.model
    def console_line_history(self, payload=None):
        """Lente: storia di una linea per un cliente = sale.order (campionature/preventivi/ordini)
        che contengono prodotti di quella categoria, cronologico desc. payload: {partner_id, category_id}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console."))
        p = (payload or {})
        pid = int(p.get('partner_id') or 0)
        cid = int(p.get('category_id') or 0)
        if not pid or not cid:
            return {'ok': False, 'message': 'partner_id/category_id mancanti'}
        SO = self.env['sale.order'].sudo()
        orders = SO.search([
            ('partner_id', '=', pid),
            ('order_line.product_id.categ_id', '=', cid),
        ], order='date_order desc')
        items = []
        for o in orders:
            if o.is_campione:
                kind, label = 'campionatura', 'Campionatura'
            elif o.state in ('sale', 'done'):
                kind, label = 'ordine', 'Ordine'
            else:
                kind, label = 'preventivo', 'Preventivo'
            items.append({
                'kind': kind, 'kind_label': label, 'id': o.id, 'name': o.name or '',
                'date': str(o.date_order) if o.date_order else '',
                'amount': round(o.amount_total or 0.0, 2), 'state': o.state,
                'sample_code': o.sample_code or '', 'model': 'sale.order',
            })
        return {'ok': True, 'partner_id': pid, 'category_id': cid, 'count': len(items), 'items': items}
