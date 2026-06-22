import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager
from .console_enrich import _console_groq_json, _clean_str

_logger = logging.getLogger(__name__)


class CrmLeadConsoleCreate(models.Model):
    """Brief 9 — crea lead + crea dossier dal console. Manager-only + audit. Scheletro Brief 8.
    project.project (dossier) creato in sudo DENTRO il metodo gated (console_api senza ACL project)."""
    _inherit = 'crm.lead'

    def _console_default_stage(self):
        """Primo stage non terminale (fold=false), come il kanban."""
        s = self.env['crm.stage'].sudo().search([('fold', '=', False)], order='sequence, id', limit=1)
        return s.id if s else False

    @api.model
    def console_suggest_lead(self, payload):
        """Suggerimento IA per il titolo del lead da una mail (revisione umana in UI, niente
        auto-save). Body assente → titolo = oggetto. payload: {mailId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        mail = self.env['casafolino.mail.message'].sudo().browse(int((payload or {}).get('mailId') or 0))
        if not mail.exists():
            raise UserError(_("Mail inesistente."))
        subject = mail.subject or ''
        title = subject
        body = mail.body_html or ''
        if body and len(body) > 40:
            text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body))[:3000]
            data = _console_groq_json(self.env, (
                "Proponi un titolo breve (max 8 parole) per un'opportunità commerciale a partire da "
                "questa email. Rispondi SOLO JSON: {\"titolo\":\"\"}. Niente testo.\n\nOggetto: %s\n\n%s"
                % (subject, text)))
            ai = _clean_str((data or {}).get('titolo'))
            if ai:
                title = ai
        return {
            'title': title,
            'emailFrom': (mail.sender_email or '').strip().lower(),
            'partnerId': mail.partner_id.id if mail.partner_id else None,
            'aiUsed': title != subject and bool(body and len(body) > 40),
        }

    @api.model
    def console_create_lead(self, payload):
        """Crea crm.lead. stage default = primo non terminale; owner = operatore (sessione).
        Solo dati revisionati. payload: {data:{name, emailFrom?}, partnerId?, stageId?, fromMailId?,
        operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        data = (payload or {}).get('data') or {}
        name = _clean_str(data.get('name'))
        if not name:
            raise UserError(_("Titolo lead obbligatorio."))
        stage_id = int((payload or {}).get('stageId') or 0) or self._console_default_stage()
        partner_id = int((payload or {}).get('partnerId') or 0) or False

        vals = {
            'name': name, 'type': 'opportunity',
            'user_id': operator.id,
            'stage_id': stage_id or False,
            'partner_id': partner_id,
            'email_from': _clean_str(data.get('emailFrom')) or False,
        }
        lead = self.sudo().create(vals)

        mail_id = int((payload or {}).get('fromMailId') or 0)
        if mail_id:
            self.env['casafolino.mail.message'].sudo().browse(mail_id).write({'lead_id': lead.id})

        _audit(self.env, 'crm.lead', [lead.id], 'create_lead', set(vals.keys()), operator)
        return {'ok': True, 'leadId': lead.id, 'name': lead.name,
                'stageId': lead.stage_id.id, 'stageName': lead.stage_id.name or ''}

    @api.model
    def console_create_dossier(self, payload):
        """Crea project.project (dossier) in SUDO dentro il metodo gated. Collega partner/lead.
        payload: {data:{name}, partnerId?, leadId?, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        data = (payload or {}).get('data') or {}
        name = _clean_str(data.get('name'))
        partner_id = int((payload or {}).get('partnerId') or 0) or False
        lead_id = int((payload or {}).get('leadId') or 0) or False

        # se manca il nome ma c'è un partner/lead, deriva un nome sensato
        if not name:
            if partner_id:
                name = _("Dossier %s") % (self.env['res.partner'].sudo().browse(partner_id).name or '')
            elif lead_id:
                name = _("Dossier %s") % (self.sudo().browse(lead_id).name or '')
        if not name:
            raise UserError(_("Nome dossier obbligatorio."))

        proj_vals = {'name': name, 'cf_status_dossier': 'exploration'}
        if partner_id:
            proj_vals['partner_id'] = partner_id
            proj_vals['cf_buyer_id'] = partner_id
        project = self.env['project.project'].sudo().create(proj_vals)

        if lead_id:
            lead = self.sudo().browse(lead_id)
            if lead.exists():
                lead.write({'cf_project_id': project.id})
                if not partner_id and lead.partner_id:
                    project.write({'partner_id': lead.partner_id.id, 'cf_buyer_id': lead.partner_id.id})

        _audit(self.env, 'project.project', [project.id], 'create_dossier', None, operator)
        return {'ok': True, 'dossierId': project.id, 'name': project.name}
