import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

# Riusa il pattern S5: gate console + audit + attribution (operator dalla sessione).
from .console_gateway import _is_console, _audit
from .console_campionatura import _operator

_logger = logging.getLogger(__name__)


class CrmLeadConsoleRead(models.Model):
    """Gateway READ per la scheda lead ricca (Brief 4). Solo letture, audited, gated.
    Scope: lo legge come console_api (search applica le record-rule → niente leak);
    i dati correlati che console_api non vede via ACL (dossier project.project, chatter,
    shipment) sono letti in sudo DENTRO il metodo già autorizzato."""
    _inherit = 'crm.lead'

    def _console_scoped_lead(self, lead_id):
        """Browse rispettando lo scope di console_api (record-rule). Fuori scope → vuoto → errore."""
        lead = self.search([('id', '=', int(lead_id))], limit=1)
        if not lead:
            raise UserError(_("Lead non trovato o fuori dal tuo scope."))
        return lead

    @api.model
    def console_get_lead(self, payload):
        """Record lead completo: campi+metriche, partner/azienda, dossier, stage stepper,
        prossima azione. payload: {leadId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        lead = self._console_scoped_lead((payload or {}).get('leadId'))

        # stage stepper: fasi reali da Odoo (non inventate)
        stages = self.env['crm.stage'].sudo().search([], order='sequence, id')
        def is_lost(name):
            return bool(name) and ('pers' in name.lower())
        stage_list = [{
            'id': s.id, 'name': s.name, 'sequence': s.sequence,
            'isWon': bool(s.is_won), 'isLost': is_lost(s.name),
        } for s in stages]

        partner = lead.partner_id
        company = lead.partner_id.commercial_partner_id if lead.partner_id else self.env['res.partner']

        # dossier (project.project) via sudo: console_api non ha ACL sul modello
        dossier = False
        proj_id = lead.cf_project_id.id if 'cf_project_id' in lead._fields and lead.cf_project_id else False
        if proj_id:
            proj = self.env['project.project'].sudo().browse(proj_id)
            if proj.exists():
                dossier = {
                    'id': proj.id, 'name': proj.name or '',
                    'status': proj.cf_status_dossier if 'cf_status_dossier' in proj._fields else '',
                    'valueEstimate': proj.cf_dossier_value_estimate if 'cf_dossier_value_estimate' in proj._fields else None,
                }

        # prossima azione: prossima mail.activity, fallback al follow-up
        next_action = None
        act = self.env['mail.activity'].sudo().search(
            [('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id)],
            order='date_deadline asc', limit=1)
        if act:
            next_action = {'date': fields.Date.to_string(act.date_deadline),
                           'summary': act.summary or (act.activity_type_id.name or _("Attività"))}
        elif 'cf_date_next_followup' in lead._fields and lead.cf_date_next_followup:
            next_action = {'date': fields.Date.to_string(lead.cf_date_next_followup),
                           'summary': _("Follow-up")}

        create_dt = lead.create_date
        days_open = (fields.Datetime.now() - create_dt).days if create_dt else None

        _audit(self.env, 'crm.lead', [lead.id], 'get_lead', None, operator)
        return {
            'id': lead.id,
            'name': lead.name or '',
            'stageId': lead.stage_id.id,
            'stageName': lead.stage_id.name or '',
            'stages': stage_list,
            'ownerUid': lead.user_id.id,
            'owner': lead.user_id.name or '',
            'expectedRevenue': lead.expected_revenue,
            'probability': lead.probability,
            'score': lead.cf_lead_score if 'cf_lead_score' in lead._fields else None,
            'rottingState': lead.cf_rotting_state if 'cf_rotting_state' in lead._fields else None,
            'createDate': fields.Datetime.to_string(create_dt) if create_dt else None,
            'daysOpen': days_open,
            'nextAction': next_action,
            'partner': {
                'id': partner.id, 'name': partner.name or '',
                'email': partner.email or '', 'phone': partner.phone or '',
                'city': partner.city or '', 'country': partner.country_id.name or '',
                'isCompany': partner.is_company,
                'role': partner.cf_partner_role if (partner and 'cf_partner_role' in partner._fields) else '',
            } if partner else False,
            'company': {'id': company.id, 'name': company.name or ''} if (company and company != partner) else False,
            'dossier': dossier,
            'emailFrom': lead.email_from or (partner.email if partner else '') or '',
        }

    @api.model
    def console_get_lead_timeline(self, payload):
        """Timeline cronologica tipizzata: mail console + eventi campionatura/cf.task + attività/note.
        Sorgente: lead.partner_id (+sender_domain) UNION lead_id diretto (il link diretto è
        quasi vuoto in prod → il partner è la fonte reale). payload: {leadId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        lead = self._console_scoped_lead((payload or {}).get('leadId'))
        partner = lead.partner_id
        items = []

        # 1) MAIL del console (per lead_id diretto OR partner OR dominio mittente)
        Msg = self.env['casafolino.mail.message'].sudo()
        mail_domain = ['&', ('state', 'not in', ['auto_discard', 'discard']),
                       '|', '|', ('lead_id', '=', lead.id)]
        if partner:
            mail_domain += [('partner_id', '=', partner.id)]
            dom = (partner.email or '').split('@')[1].lower() if (partner.email and '@' in partner.email) else False
            mail_domain += [('sender_domain', '=', dom)] if dom else [('id', '=', -1)]
        else:
            mail_domain += [('id', '=', -1), ('id', '=', -1)]
        for m in Msg.search(mail_domain, order='email_date desc', limit=80):
            items.append({
                'type': 'mail',
                'date': fields.Datetime.to_string(m.email_date) if m.email_date else None,
                'title': m.subject or _("(senza oggetto)"),
                'subtitle': (m.sender_name or m.sender_email or ''),
                'direction': 'outbound' if m.direction == 'outbound' else 'inbound',
            })

        # 2) CAMPIONATURA / cf.task (per lead_id diretto OR partner)
        Ship = self.env['cf.shipment'].sudo()
        ship_domain = ['|', ('lead_id', '=', lead.id)]
        ship_domain += [('partner_id', '=', partner.id)] if partner else [('id', '=', -1)]
        for sh in Ship.search(ship_domain, order='create_date desc', limit=20):
            if sh.date_creato:
                items.append({'type': 'campionatura', 'date': fields.Datetime.to_string(sh.date_creato),
                              'title': _("Campionatura %s creata") % sh.name, 'subtitle': sh.partner_id.name or '',
                              'shipmentId': sh.id})
            if sh.date_spedito:
                items.append({'type': 'campionatura', 'date': fields.Datetime.to_string(sh.date_spedito),
                              'title': _("Spedito %s") % sh.name,
                              'subtitle': _("Corriere %s · %s") % (sh.carrier or '-', sh.tracking_code or '-'),
                              'shipmentId': sh.id})
            if sh.date_consegnato:
                items.append({'type': 'campionatura', 'date': fields.Datetime.to_string(sh.date_consegnato),
                              'title': _("Consegnato %s") % sh.name, 'subtitle': '', 'shipmentId': sh.id})

        # 3) ATTIVITÀ / NOTE (chatter del lead)
        Note = self.env['mail.message'].sudo()
        for msg in Note.search([('model', '=', 'crm.lead'), ('res_id', '=', lead.id),
                                ('message_type', 'in', ['comment', 'notification'])],
                               order='date desc', limit=30):
            body = (msg.body or '').replace('<p>', '').replace('</p>', ' ')
            import re
            body = re.sub(r'<[^>]+>', '', body).strip()
            if not body:
                continue
            items.append({
                'type': 'note',
                'date': fields.Datetime.to_string(msg.date) if msg.date else None,
                'title': body[:120],
                'subtitle': msg.author_id.name or '',
            })

        # ordina per data desc (None in fondo)
        items.sort(key=lambda i: i['date'] or '', reverse=True)
        _audit(self.env, 'crm.lead', [lead.id], 'get_lead_timeline', None, operator)
        return {'leadId': lead.id, 'items': items[:120]}
