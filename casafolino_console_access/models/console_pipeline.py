import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager, _activity_state  # Brief 5/20

_logger = logging.getLogger(__name__)

# Brief 20 — campi modificabili inline dalla scheda lead (whitelist: niente scrittura fuori da qui).
_LEAD_EDITABLE = {'name', 'expected_revenue', 'probability', 'stage_id', 'email_from', 'cf_date_next_followup'}


class CrmLeadConsolePipeline(models.Model):
    """Brief 6 — kanban pipeline + ricerca universale. Manager-only (difesa in profondità
    oltre al gate UI). Letture+set stage; lo scoring/rotting resta a crm_export (solo set)."""
    _inherit = 'crm.lead'

    @api.model
    def console_pipeline_board(self, payload=None):
        """Board: colonne = stage NON terminali (fold=false), card con valore/owner/rotting/
        giorni-in-fase. payload: {operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        stages = self.env['crm.stage'].sudo().search([('fold', '=', False)], order='sequence, id')
        stage_ids = stages.ids

        # PERF (Brief 20): search_read in UNA query con campi scalari + m2o display → niente N+1
        # (prima: browse 1000 lead + walk partner_id.commercial_partner_id.name = ~1700ms).
        # A: ordina per create_date desc (ultimi creati in cima).
        has_score = 'cf_lead_score' in self._fields
        flds = ['name', 'partner_id', 'expected_revenue', 'user_id', 'stage_id',
                'date_last_stage_update', 'create_date', 'tag_ids']
        if has_score:
            flds.append('cf_lead_score')
        rows = self.sudo().search_read(
            [('type', '=', 'opportunity'), ('active', '=', True), ('stage_id', 'in', stage_ids)],
            flds, order='create_date desc', limit=800)
        lead_ids = [r['id'] for r in rows]

        # M6 — tag (nomi) + flag campionatura attiva (lead con cf.shipment in transito). Batch, no N+1.
        tag_names = {}
        all_tag_ids = {t for r in rows for t in (r.get('tag_ids') or [])}
        if all_tag_ids:
            for t in self.env['crm.tag'].sudo().browse(list(all_tag_ids)):
                if t.exists():
                    tag_names[t.id] = t.name
        campione_leads = set()
        if lead_ids:
            for sh in self.env['cf.shipment'].sudo().search_read(
                    [('lead_id', 'in', lead_ids),
                     ('state', 'in', ['creato', 'preparazione', 'etichetta', 'spedito'])],
                    ['lead_id']):
                lid = sh['lead_id'][0] if sh.get('lead_id') else None
                if lid:
                    campione_leads.add(lid)

        # B: ATTIVITÀ REALE (batch, no N+1) = MAX(date_last_stage_update, ultima nota chatter).
        # Il rosso non deve più venire da cf_rotting_state (stale, basato su create_date).
        chatter = {}
        if lead_ids:
            for g in self.env['mail.message'].sudo().read_group(
                    [('model', '=', 'crm.lead'), ('res_id', 'in', lead_ids),
                     ('message_type', 'in', ['comment', 'notification'])],
                    ['res_id', 'date:max'], ['res_id']):
                rid = g['res_id'] if isinstance(g['res_id'], int) else (g['res_id'][0] if g['res_id'] else None)
                if rid and g.get('date'):
                    chatter[rid] = g['date']

        today = fields.Date.context_today(self)

        def _relid(v):
            return v[0] if isinstance(v, (list, tuple)) and v else None

        def _relname(v):
            return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ''

        by_stage = {sid: [] for sid in stage_ids}
        CAP = 60
        for r in rows:
            sid = _relid(r['stage_id'])
            if sid not in by_stage or len(by_stage[sid]) >= CAP:
                continue
            state, days = _activity_state(today, r.get('date_last_stage_update'), chatter.get(r['id']))
            by_stage[sid].append({
                'id': r['id'],
                'name': r['name'] or 'Lead',
                'partnerId': _relid(r['partner_id']),
                'company': _relname(r['partner_id']),
                'value': r['expected_revenue'],
                'owner': _relname(r['user_id']),
                'score': r.get('cf_lead_score') if has_score else None,
                'activityState': state,
                'daysInactive': days,
                'tags': [tag_names[t] for t in (r.get('tag_ids') or []) if t in tag_names],
                'hasCampione': r['id'] in campione_leads,
            })

        columns = [{
            'stageId': s.id, 'name': s.name, 'sequence': s.sequence,
            'count': len(by_stage.get(s.id, [])),
            'cards': by_stage.get(s.id, []),
        } for s in stages]
        # stage terminali (fold=true) per il menu "Segna Vinta/Persa/Standby" (no colonne)
        terms = self.env['crm.stage'].sudo().search([('fold', '=', True)], order='sequence, id')
        terminal_stages = [{'stageId': t.id, 'name': t.name, 'isWon': bool(t.is_won)} for t in terms]
        _audit(self.env, 'crm.lead', stage_ids, 'pipeline_board', None, operator)
        return {'columns': columns, 'terminalStages': terminal_stages}

    @api.model
    def console_set_lead_stage(self, payload):
        """Sposta il lead di fase. Scrive SOLO stage_id (scoring/rotting ricalcolano da soli
        via date_last_stage_update). Gestisce anche i terminali Vinta/Persa/Standby.
        payload: {leadId, stageId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        stage = self.env['crm.stage'].sudo().browse(int((payload or {}).get('stageId') or 0))
        if not stage.exists():
            raise UserError(_("Stage inesistente."))
        lead = self.search([('id', '=', int((payload or {}).get('leadId') or 0))], limit=1)
        if not lead:
            raise UserError(_("Lead non trovato o fuori scope."))

        lead.sudo().write({'stage_id': stage.id})  # SOLO stage — niente duplicazione scoring
        _audit(self.env, 'crm.lead', [lead.id], 'set_stage:%s' % stage.id, {'stage_id'}, operator)
        return {'ok': True, 'leadId': lead.id, 'stageId': stage.id,
                'stageName': stage.name, 'terminal': bool(stage.fold)}

    @api.model
    def console_universal_search(self, payload):
        """Ricerca universale tipizzata e raggruppata: lead (nome), partner (nome/email),
        mail (oggetto/mittente — NO full body, perf), dossier (project.project nome).
        Limite ~10/tipo. payload: {query, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        q = ((payload or {}).get('query') or '').strip()
        if len(q) < 2:
            return {'query': q, 'groups': []}
        LIM = 10

        leads = self.sudo().search(['|', ('name', 'ilike', q),
                                    ('partner_id.name', 'ilike', q),
                                    ('type', '=', 'opportunity')], limit=LIM)
        # nota: '|' copre name/partner; type filtra opportunity (AND implicito finale)
        lead_items = [{'id': l.id, 'title': l.name or 'Lead',
                       'subtitle': (l.stage_id.name or '') + (' · ' + l.partner_id.name if l.partner_id else '')}
                      for l in leads]

        partners = self.env['res.partner'].sudo().search(
            ['|', ('name', 'ilike', q), ('email', 'ilike', q)], limit=LIM)
        partner_items = [{'id': p.id, 'title': p.name or '',
                          'subtitle': (p.email or '') + ((' · ' + p.city) if p.city else '')}
                         for p in partners]

        mails = self.env['casafolino.mail.message'].sudo().search(
            ['&', ('state', 'not in', ['auto_discard', 'discard']),
             '|', ('subject', 'ilike', q), ('sender_email', 'ilike', q)],
            order='email_date desc', limit=LIM)
        mail_items = [{'id': m.id, 'title': m.subject or '(senza oggetto)',
                       'subtitle': (m.sender_name or m.sender_email or '')}
                      for m in mails]

        dossiers = self.env['project.project'].sudo().search(
            ['&', ('cf_status_dossier', '!=', False), ('name', 'ilike', q)], limit=LIM)
        dossier_items = [{'id': d.id, 'title': d.name or 'Dossier',
                          'subtitle': (d.partner_id.name if d.partner_id else '')}
                         for d in dossiers]

        groups = []
        if lead_items:
            groups.append({'type': 'lead', 'label': 'Lead', 'items': lead_items})
        if partner_items:
            groups.append({'type': 'partner', 'label': 'Contatti', 'items': partner_items})
        if mail_items:
            groups.append({'type': 'mail', 'label': 'Mail', 'items': mail_items})
        if dossier_items:
            groups.append({'type': 'dossier', 'label': 'Dossier', 'items': dossier_items})

        _audit(self.env, 'crm.lead', [], 'universal_search', None, operator)
        return {'query': q, 'groups': groups}

    @api.model
    def console_update_lead(self, payload):
        """Brief 20 P2 — modifica inline dei campi della scheda lead. SOLO whitelist (_LEAD_EDITABLE),
        mai campi fuori. Lascia ricalcolare scoring/rotting a Odoo. payload: {leadId, values:{...}}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        lead = self.search([('id', '=', int((payload or {}).get('leadId') or 0))], limit=1)
        if not lead:
            raise UserError(_("Lead non trovato o fuori scope."))

        raw = (payload or {}).get('values') or {}
        vals = {}
        for k, v in raw.items():
            if k not in _LEAD_EDITABLE:
                continue  # mai scrivere fuori dalla whitelist
            if k == 'stage_id':
                sid = int(v or 0)
                if sid and self.env['crm.stage'].sudo().browse(sid).exists():
                    vals['stage_id'] = sid
            elif k in ('expected_revenue', 'probability'):
                try:
                    vals[k] = float(v) if v not in (None, '') else 0.0
                except (TypeError, ValueError):
                    raise UserError(_("Valore numerico non valido per %s.") % k)
            elif k == 'cf_date_next_followup':
                vals[k] = v or False
            else:  # name, email_from
                s = (v or '').strip() if isinstance(v, str) else v
                if k == 'name' and not s:
                    raise UserError(_("Il titolo non può essere vuoto."))
                vals[k] = s or False
        if not vals:
            raise UserError(_("Nessun campo modificabile fornito."))
        # cf_date_next_followup potrebbe non esistere su tutte le installazioni
        if 'cf_date_next_followup' in vals and 'cf_date_next_followup' not in lead._fields:
            vals.pop('cf_date_next_followup')

        lead.sudo().write(vals)
        _audit(self.env, 'crm.lead', [lead.id], 'update_lead', set(vals.keys()), operator)
        return {'ok': True, 'leadId': lead.id,
                'stageId': lead.stage_id.id, 'stageName': lead.stage_id.name or '',
                'expectedRevenue': lead.expected_revenue, 'probability': lead.probability,
                'name': lead.name, 'emailFrom': lead.email_from or ''}
