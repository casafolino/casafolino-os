import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

# Riusa il pattern S5 (gate console + audit + attribution) e la logica rotting reale.
from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager, _activity_state

_logger = logging.getLogger(__name__)

# Ordinamento semaforo pipeline (Brief: rossi → gialli per giorni desc → verdi per attività recente).
_STATE_RANK = {'danger': 0, 'warning': 1, 'fresh': 2, 'neutral': 3}

# Stati sale.order da escludere ovunque (bozze/annullati non sono storia reale).
_ORDER_EXCLUDE = ('draft', 'sent', 'cancel')

# cf.task ancora aperti = pool/lavorazione in corso.
_TASK_OPEN = ('bozza', 'in_corso')


def _relid(v):
    return v[0] if isinstance(v, (list, tuple)) and v else None


def _relname(v):
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ''


def _initials(name):
    parts = [p for p in (name or '').replace('.', ' ').split() if p]
    if not parts:
        return '·'
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


class CrmLeadConsoleRegia(models.Model):
    """Regia — dashboard unica (Brief Regia+Dossier). SOLO letture aggregate, gated
    _is_console + _require_manager, audited. Nessun modello/campo nuovo: lente sui
    modelli nativi (crm.lead, mail.activity, sale.order, ...)."""
    _inherit = 'crm.lead'

    # ── helpers condivisi ─────────────────────────────────────────────
    def _regia_open_stage_ids(self):
        return self.env['crm.stage'].sudo().search([('fold', '=', False)], order='sequence, id').ids

    def _regia_chatter_map(self, lead_ids):
        """MAX data ultima nota chatter per lead (batch, no N+1) — base del rotting reale."""
        chatter = {}
        if not lead_ids:
            return chatter
        for g in self.env['mail.message'].sudo().read_group(
                [('model', '=', 'crm.lead'), ('res_id', 'in', lead_ids),
                 ('message_type', 'in', ['comment', 'notification'])],
                ['res_id', 'date:max'], ['res_id']):
            rid = g['res_id'] if isinstance(g['res_id'], int) else (g['res_id'][0] if g['res_id'] else None)
            if rid and g.get('date'):
                chatter[rid] = g['date']
        return chatter

    # ── KPI Regia ─────────────────────────────────────────────────────
    @api.model
    def console_regia_kpis(self, payload=None):
        """4 KPI (Brief): Attivi (opp. stage aperto), Fermi +3gg (attività reale > 3gg),
        In scadenza oggi (mail.activity date_deadline = oggi), Nuovi lead 7gg.
        payload: {operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        today = fields.Date.context_today(self)
        stage_ids = self._regia_open_stage_ids()
        base = [('type', '=', 'opportunity'), ('active', '=', True), ('stage_id', 'in', stage_ids)]

        attivi = self.sudo().search_count(base)
        nuovi7 = self.sudo().search_count(base + [('create_date', '>=', fields.Datetime.subtract(
            fields.Datetime.now(), days=7))])
        scadenza_oggi = self.env['mail.activity'].sudo().search_count(
            [('res_model', '=', 'crm.lead'), ('date_deadline', '=', today)])

        # Fermi +3gg — attività reale (MAX stage-update / ultima nota) oltre 3 giorni.
        rows = self.sudo().search_read(base, ['id', 'date_last_stage_update'])
        lead_ids = [r['id'] for r in rows]
        chatter = self._regia_chatter_map(lead_ids)
        fermi3 = 0
        for r in rows:
            _state, days = _activity_state(today, r.get('date_last_stage_update'), chatter.get(r['id']))
            if days is not None and days > 3:
                fermi3 += 1

        _audit(self.env, 'crm.lead', [], 'regia_kpis', None, operator)
        return {'attivi': attivi, 'fermi3': fermi3,
                'scadenzaOggi': scadenza_oggi, 'nuovi7': nuovi7}

    # ── Lista pipeline Regia (flat, ordinata semaforo) ────────────────
    @api.model
    def console_regia_pipeline(self, payload=None):
        """Lista piatta (non kanban) delle opportunità attive, un cliente per riga:
        pallino semaforo, cliente, stage, fermo da N gg, owner (iniziali).
        Ordine: rossi → gialli per giorni desc → verdi per attività più recente → neutri.
        payload: {operator_uid, limit, offset}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        payload = payload or {}
        limit = min(int(payload.get('limit') or 100), 300)
        offset = max(int(payload.get('offset') or 0), 0)

        today = fields.Date.context_today(self)
        stage_ids = self._regia_open_stage_ids()
        rows = self.sudo().search_read(
            [('type', '=', 'opportunity'), ('active', '=', True), ('stage_id', 'in', stage_ids)],
            ['name', 'partner_id', 'user_id', 'stage_id', 'date_last_stage_update', 'expected_revenue'],
            order='create_date desc', limit=800)
        chatter = self._regia_chatter_map([r['id'] for r in rows])

        items = []
        for r in rows:
            state, days = _activity_state(today, r.get('date_last_stage_update'), chatter.get(r['id']))
            owner = _relname(r['user_id'])
            items.append({
                'leadId': r['id'],
                'partnerId': _relid(r['partner_id']),
                'company': _relname(r['partner_id']) or (r['name'] or 'Lead'),
                'stage': _relname(r['stage_id']),
                'owner': owner,
                'ownerInitials': _initials(owner),
                'activityState': state,
                'daysInactive': days,
                'value': r.get('expected_revenue') or 0.0,
            })

        # Ordine Brief: rank stato; dentro danger/warning giorni desc; fresh giorni asc (recente prima).
        def _sort_key(it):
            rank = _STATE_RANK.get(it['activityState'], 3)
            d = it['daysInactive']
            if rank in (0, 1):  # danger/warning → più fermi in cima
                return (rank, -(d if d is not None else 0))
            return (rank, d if d is not None else 10 ** 6)  # fresh/neutral → più recenti in cima

        items.sort(key=_sort_key)
        total = len(items)
        page = items[offset:offset + limit]
        _audit(self.env, 'crm.lead', [], 'regia_pipeline', None, operator)
        return {'items': page, 'total': total, 'hasMore': offset + limit < total}


class ResPartnerConsoleDossier(models.Model):
    """Dossier cliente — vista unica per partner (Brief). Header + 4 metric card +
    timeline cronologica unica (ordini, mail, task, campioni, note). SOLO letture
    aggregate, gated + audited. Nessun campo nuovo."""
    _inherit = 'res.partner'

    def _dossier_partner(self, partner_id):
        p = self.sudo().browse(int(partner_id or 0))
        if not p.exists():
            raise UserError(_("Cliente non trovato."))
        return p

    def _dossier_open_leads(self, partner):
        stage_ids = self.env['crm.stage'].sudo().search([('fold', '=', False)]).ids
        return self.env['crm.lead'].sudo().search(
            [('partner_id', 'child_of', partner.id), ('type', '=', 'opportunity'),
             ('active', '=', True), ('stage_id', 'in', stage_ids)],
            order='expected_revenue desc, id desc')

    @api.model
    def console_partner_dossier(self, payload=None):
        """Header + 4 metric card + semaforo + tag. payload: {partnerId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        partner = self._dossier_partner((payload or {}).get('partnerId'))
        today = fields.Date.context_today(self)

        # Metric 1 — Ultimo ordine (reale, no bozze).
        last_order = self.env['sale.order'].sudo().search(
            [('partner_id', 'child_of', partner.id), ('state', 'not in', _ORDER_EXCLUDE)],
            order='date_order desc, id desc', limit=1)
        ultimo_ordine = None
        if last_order:
            ultimo_ordine = {'name': last_order.name, 'amount': last_order.amount_total,
                             'date': fields.Date.to_string(last_order.date_order.date())
                             if last_order.date_order else None}

        # Metric 2 — Fatturato 12 mesi (ordini reali, esclusi campioni).
        since = fields.Datetime.subtract(fields.Datetime.now(), days=365)
        rev_orders = self.env['sale.order'].sudo().search_read(
            [('partner_id', 'child_of', partner.id), ('state', 'not in', _ORDER_EXCLUDE),
             ('is_campione', '=', False), ('date_order', '>=', since)],
            ['amount_total'])
        fatturato12m = sum(o['amount_total'] or 0.0 for o in rev_orders)

        # Metric 3 — Stage (opportunità aperta principale) + semaforo peggiore.
        open_leads = self._dossier_open_leads(partner)
        stage = open_leads[0].stage_id.name if open_leads else None
        chatter = self.env['crm.lead']._regia_chatter_map(open_leads.ids)
        worst_rank, worst_state, worst_days = -1, 'neutral', None
        for l in open_leads:
            state, days = _activity_state(today, l.date_last_stage_update, chatter.get(l.id))
            rank = _STATE_RANK.get(state, 3)
            # peggiore = danger(0) prevale; ma neutral(3) è "nessuna attività", non allarme.
            weight = {'danger': 3, 'warning': 2, 'fresh': 1, 'neutral': 0}.get(state, 0)
            if weight > worst_rank:
                worst_rank, worst_state, worst_days = weight, state, days
        semaforo = worst_state if open_leads else 'neutral'

        # Metric 4 — Task aperti (cf.task del partner, stato aperto).
        task_aperti = self.env['cf.task'].sudo().search_count(
            [('partner_id', 'child_of', partner.id), ('state', 'in', _TASK_OPEN)])

        # Tag (best-effort): ruolo CasaFolino + area geo + categorie partner.
        tags = []
        role = partner.cf_partner_role if 'cf_partner_role' in partner._fields else None
        if role and role not in ('other', False):
            tags.append(dict(partner._fields['cf_partner_role'].selection).get(role, role))
        if partner.country_id:
            tags.append(partner.country_id.name)
        if partner.city:
            tags.append(partner.city)
        for c in partner.category_id[:3]:
            tags.append(c.name)

        _audit(self.env, 'res.partner', [partner.id], 'partner_dossier', None, operator)
        return {
            'partner': {
                'id': partner.id, 'name': partner.name or '',
                'isCompany': bool(partner.is_company),
                'email': partner.email or '', 'city': partner.city or '',
                'country': partner.country_id.name if partner.country_id else '',
                'ownerInitials': _initials(open_leads[0].user_id.name) if open_leads and open_leads[0].user_id else '',
                'owner': open_leads[0].user_id.name if open_leads and open_leads[0].user_id else '',
            },
            'semaforo': semaforo, 'semaforoDays': worst_days, 'tags': tags,
            'metrics': {
                'ultimoOrdine': ultimo_ordine,
                'fatturato12m': fatturato12m,
                'stage': stage,
                'taskAperti': task_aperti,
            },
        }

    @api.model
    def console_partner_timeline(self, payload=None):
        """Timeline unica cronologica (Brief): ordini, mail, task, campioni, note —
        mescolati per data desc, paginati. payload: {partnerId, limit, offset, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        partner = self._dossier_partner((payload or {}).get('partnerId'))
        payload = payload or {}
        limit = min(int(payload.get('limit') or 25), 100)
        offset = max(int(payload.get('offset') or 0), 0)
        pid = partner.id

        events = []

        def _dt(v):
            return fields.Datetime.to_datetime(v) if v else None

        # Ordini reali (campioni esclusi: arrivano come evento 'campione' da cf.shipment).
        for o in self.env['sale.order'].sudo().search_read(
                [('partner_id', 'child_of', pid), ('state', 'not in', _ORDER_EXCLUDE),
                 ('is_campione', '=', False)],
                ['name', 'amount_total', 'state', 'date_order'], order='date_order desc', limit=200):
            d = _dt(o.get('date_order'))
            if not d:
                continue
            events.append({'type': 'order', 'icon': 'order', 'date': d,
                           'title': _('Ordine %s') % (o['name'] or ''),
                           'subtitle': '€ %s · %s' % ('{:,.0f}'.format(o['amount_total'] or 0.0).replace(',', '.'),
                                                       o.get('state') or ''),
                           'author': ''})

        # Mail cliente (oggetto, non corpo).
        for m in self.env['casafolino.mail.message'].sudo().search_read(
                [('partner_id', '=', pid), ('state', 'not in', ['auto_discard', 'discard'])],
                ['subject', 'sender_name', 'sender_email', 'email_date', 'direction'],
                order='email_date desc', limit=200):
            d = _dt(m.get('email_date'))
            if not d:
                continue
            verso = _('Inviata') if m.get('direction') == 'outbound' else _('Ricevuta')
            events.append({'type': 'mail', 'icon': 'mail', 'date': d,
                           'title': _('Mail %s: %s') % (verso, m.get('subject') or _('(senza oggetto)')),
                           'subtitle': m.get('sender_name') or m.get('sender_email') or '',
                           'author': m.get('sender_name') or ''})

        # Task (cf.task) del partner.
        for t in self.env['cf.task'].sudo().search_read(
                [('partner_id', 'child_of', pid)],
                ['name', 'state', 'create_date', 'user_assigned_id'], order='create_date desc', limit=200):
            d = _dt(t.get('create_date'))
            if not d:
                continue
            aperto = t.get('state') in _TASK_OPEN
            events.append({'type': 'task', 'icon': 'task', 'date': d,
                           'title': _('Task: %s') % (t.get('name') or ''),
                           'subtitle': _('aperto') if aperto else _('chiuso'),
                           'author': _relname(t.get('user_assigned_id'))})

        # Campioni (cf.shipment) — evento spedizione/stato.
        for s in self.env['cf.shipment'].sudo().search_read(
                [('partner_id', 'child_of', pid)],
                ['name', 'state', 'date_spedito', 'date_creato', 'create_date'],
                order='create_date desc', limit=200):
            d = _dt(s.get('date_spedito') or s.get('date_creato') or s.get('create_date'))
            if not d:
                continue
            events.append({'type': 'sample', 'icon': 'sample', 'date': d,
                           'title': _('Campione %s') % (s.get('name') or ''),
                           'subtitle': s.get('state') or '', 'author': ''})

        # Note interne (mail.message mt_note sul partner) — escludi le copie mail ingest (message_type email).
        note_subtype = self.env.ref('mail.mt_note', raise_if_not_found=False)
        note_domain = [('model', '=', 'res.partner'), ('res_id', '=', pid),
                       ('message_type', 'in', ['comment', 'notification'])]
        if note_subtype:
            note_domain.append(('subtype_id', '=', note_subtype.id))
        for n in self.env['mail.message'].sudo().search_read(
                note_domain, ['subject', 'body', 'date', 'author_id'],
                order='date desc', limit=100):
            d = _dt(n.get('date'))
            if not d:
                continue
            body = (n.get('subject') or n.get('body') or '')
            # strip HTML minimale per la nota
            import re as _re
            body = _re.sub('<[^<]+?>', '', body).strip()
            if not body:
                continue
            events.append({'type': 'note', 'icon': 'note', 'date': d,
                           'title': _('Nota'), 'subtitle': body[:140],
                           'author': _relname(n.get('author_id'))})

        events.sort(key=lambda e: e['date'], reverse=True)
        total = len(events)
        page = events[offset:offset + limit]
        # serializza le date (ISO) solo sulla pagina restituita
        for e in page:
            e['date'] = fields.Datetime.to_string(e['date'])

        _audit(self.env, 'res.partner', [pid], 'partner_timeline', None, operator)
        return {'items': page, 'total': total, 'hasMore': offset + limit < total}
