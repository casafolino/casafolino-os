import logging

from odoo import api, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager, _is_free_domain
from .console_enrich import _clean_str

_logger = logging.getLogger(__name__)


class CrmLeadConsoleCockpit(models.Model):
    """Brief 15 — cruscotto mail: risolve il mittente → stato relazione (partner/lead/dossier)
    + create rapidi. Read-only (cockpit) + create azienda standalone. Manager-only + audit."""
    _inherit = 'crm.lead'

    @api.model
    def console_mail_cockpit(self, payload):
        """Risolve il mittente di una mail PER EMAIL (esatta → dominio+is_company, non solo
        mail.partner_id) → {partner, company, lead+fase, dossier} + leadStages per il create.
        Read-only. payload: {mailId, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        mail = self.env['casafolino.mail.message'].sudo().browse(int((payload or {}).get('mailId') or 0))
        if not mail.exists():
            raise UserError(_("Mail inesistente."))
        email = (mail.sender_email or '').strip().lower()
        domain = email.split('@')[1] if '@' in email else ''
        Partner = self.env['res.partner'].sudo()

        # 1) partner: mail.partner_id → email esatta → dominio+is_company
        partner = mail.partner_id
        if not partner and email:
            partner = Partner.search([('email', '=ilike', email)], limit=1)
        company = self.env['res.partner']
        if partner:
            company = partner.commercial_partner_id if partner.commercial_partner_id != partner else partner.parent_id
        if not partner and domain and not _is_free_domain(domain):
            # Brief 16 — mai risolvere l'azienda per dominio free (sennò ogni mittente gmail
            # finirebbe sotto la stessa "azienda" gmail).
            company = Partner.search([('email', '=ilike', '%@' + domain), ('is_company', '=', True)], limit=1)

        # 2) lead: opportunità del partner (più recente per valore)
        lead = self.env['crm.lead']
        if partner:
            lead = self.sudo().search([('partner_id', '=', partner.id), ('type', '=', 'opportunity')],
                                      order='expected_revenue desc', limit=1)

        # 3) dossier: project.project del partner (via sudo, console_api no ACL project)
        dossier = self.env['project.project']
        if partner:
            dossier = self.env['project.project'].sudo().search(
                ['&', ('cf_status_dossier', '!=', False),
                 '|', ('partner_id', '=', partner.id), ('cf_buyer_id', '=', partner.id)], limit=1)

        stages = self.env['crm.stage'].sudo().search([('fold', '=', False)], order='sequence, id')

        _audit(self.env, 'casafolino.mail.message', [mail.id], 'mail_cockpit', None, operator)
        return {
            'mailId': mail.id,
            'sender': {'email': email, 'name': mail.sender_name or ''},
            'partner': {'exists': bool(partner), 'id': partner.id if partner else False,
                        'name': partner.name if partner else '', 'isCompany': partner.is_company if partner else False},
            'company': {'exists': bool(company), 'id': company.id if company else False,
                        'name': company.name if company else ''},
            'lead': {'exists': bool(lead), 'id': lead.id if lead else False,
                     'name': lead.name if lead else '',
                     'stage': lead.stage_id.name if lead else '', 'stageId': lead.stage_id.id if lead else False},
            'dossier': {'exists': bool(dossier), 'id': dossier.id if dossier else False,
                        'name': dossier.name if dossier else ''},
            'leadStages': [{'id': s.id, 'name': s.name} for s in stages],
        }

    @api.model
    def console_create_company(self, payload):
        """Crea un'azienda (res.partner is_company) STANDALONE (non solo come parent del
        contatto). payload: {data:{nome, dominio?, citta?}, mailId?, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)
        data = (payload or {}).get('data') or {}
        name = _clean_str(data.get('nome')) or _clean_str(data.get('name'))
        if not name:
            raise UserError(_("Nome azienda obbligatorio."))
        dom = _clean_str(data.get('dominio'))
        company = self.env['res.partner'].sudo().create({
            'name': name, 'is_company': True,
            'website': ('https://' + dom) if dom else False,
            'city': _clean_str(data.get('citta')) or False,
        })
        mail_id = int((payload or {}).get('mailId') or 0)
        if mail_id:
            self.env['casafolino.mail.message'].sudo().browse(mail_id).write({'partner_id': company.id})
        _audit(self.env, 'res.partner', [company.id], 'create_company', None, operator)
        return {'ok': True, 'partnerId': company.id, 'name': company.name}
