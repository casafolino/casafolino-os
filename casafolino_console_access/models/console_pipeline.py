import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager  # Brief 5 — manager-only

_logger = logging.getLogger(__name__)


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
        leads = self.sudo().search([
            ('type', '=', 'opportunity'), ('active', '=', True),
            ('stage_id', 'in', stage_ids),
        ], order='expected_revenue desc', limit=1000)

        today = fields.Date.context_today(self)
        by_stage = {sid: [] for sid in stage_ids}
        CAP = 60
        for l in leads:
            sid = l.stage_id.id
            if sid not in by_stage or len(by_stage[sid]) >= CAP:
                continue
            dls = l.date_last_stage_update
            days = (today - dls.date()).days if dls else None
            by_stage[sid].append({
                'id': l.id,
                'name': l.name or 'Lead',
                'partnerId': l.partner_id.id if l.partner_id else None,
                'company': l.partner_id.commercial_partner_id.name if l.partner_id else '',
                'value': l.expected_revenue,
                'owner': l.user_id.name or '',
                'score': l.cf_lead_score if 'cf_lead_score' in l._fields else None,
                'rottingState': l.cf_rotting_state if 'cf_rotting_state' in l._fields else None,
                'daysInStage': days,
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
