import logging

from odoo import api, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_lead import _require_manager
from .console_enrich import _clean_str

_logger = logging.getLogger(__name__)


class ResPartnerConsoleDocs(models.Model):
    """Brief 10 — Invia documenti (libreria curata via outbound) + Ricetta (cf.task R&D).
    Manager-only + audit. Additivo: riusa il core outbound e il pattern crea-task."""
    _inherit = 'res.partner'

    def _console_recipient(self, lead_id, partner_id):
        """Email destinatario + partner dal contesto lead/partner."""
        if lead_id:
            lead = self.env['crm.lead'].sudo().browse(int(lead_id))
            if lead.exists():
                to = (lead.email_from or (lead.partner_id.email if lead.partner_id else '') or '').strip().lower()
                return to, lead.partner_id
        if partner_id:
            p = self.env['res.partner'].sudo().browse(int(partner_id))
            if p.exists():
                return (p.email or '').strip().lower(), p
        return '', self.env['res.partner']

    def _console_operator_account(self, operator):
        """Casella dell'operatore (responsible_user_id), fallback account 1 (antonio@)."""
        Acc = self.env['casafolino.mail.account'].sudo()
        acc = Acc.search([('responsible_user_id', '=', operator.id)], limit=1)
        return acc or Acc.browse(1)

    @api.model
    def console_send_documents(self, payload):
        """Invia documenti SOLO dalla libreria curata via outbound (rail+kill-switch+audit,
        safe-attach anti-exfiltration). payload: {leadId?, partnerId?, materialIds:[...],
        subject?, body?, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        material_ids = (payload or {}).get('materialIds') or []
        if not material_ids:
            raise UserError(_("Seleziona almeno un documento dalla libreria."))
        to, _partner = self._console_recipient((payload or {}).get('leadId'), (payload or {}).get('partnerId'))
        if not to or '@' not in to:
            raise UserError(_("Destinatario senza email valida."))
        account = self._console_operator_account(operator)
        if not account.exists() or not account.responsible_user_id:
            raise UserError(_("Casella mittente non risolta."))

        subject = _clean_str((payload or {}).get('subject')) or _("Documenti CasaFolino")
        body = (payload or {}).get('body') or _("<p>In allegato i documenti richiesti.</p>")

        # Brief 12 — split attach-vs-link per dimensione. Item <= soglia → allegato 3-tuple
        # (path esistente). Item > soglia → URL tokenizzato (access_token, per-file, non
        # enumerabile) nel body. SOLO libreria curata (ogni id validato approved+file).
        ICP = self.env['ir.config_parameter'].sudo()
        max_mb = float(ICP.get_param('casafolino.console_doc_attach_max_mb', 20) or 20)
        threshold = int(max_mb * 1024 * 1024)
        base_url = ICP.get_param('web.base.url') or ''
        Mat = self.env['casafolino.mail.material'].sudo()
        Att = self.env['ir.attachment'].sudo()

        attach_ids, links, total_attach = [], [], 0
        for mid in material_ids:
            m = Mat.browse(int(mid))
            # anti-exfiltration: SOLO materiali di libreria approvati (anche per il path link)
            if not m.exists() or m.state != 'approved' or not m.active or not m.file_data:
                raise UserError(_("Materiale %s non in libreria invii (approvato).") % mid)
            att = Att.search([('res_model', '=', 'casafolino.mail.material'),
                              ('res_field', '=', 'file_data'), ('res_id', '=', m.id)], limit=1)
            size = att.file_size if att else 0
            if att and size and size > threshold:
                if not att.access_token:
                    att.generate_access_token()
                url = '%s/web/content/%s?access_token=%s&download=true' % (base_url, att.id, att.access_token)
                links.append((m.file_name or m.name, url))
            else:
                attach_ids.append(m.id)
                total_attach += size

        if total_attach > 25 * 1024 * 1024:
            raise UserError(_("Allegati troppo grandi (%.1f MB > 25MB Gmail). Riduci la selezione.")
                            % (total_attach / 1024 / 1024))

        if links:
            body += '<p><b>Scarica:</b></p><ul>'
            for name, url in links:
                body += '<li><a href="%s">%s</a></li>' % (url, name)
            body += '</ul>'

        # core outbound condiviso: material_ids (attach) = SOLO libreria curata (safe-attach).
        res = self.env['casafolino.mail.message']._console_outbound(
            account, to, subject, body, False, 'documents',
            operator=operator, material_ids=attach_ids)
        _audit(self.env, 'casafolino.mail.material', [int(m) for m in material_ids],
               'send_documents:%s:attach%d:link%d' % (res.get('state', '?'), len(attach_ids), len(links)),
               None, operator)
        res['attached'] = len(attach_ids)
        res['linked'] = len(links)
        return res

    @api.model
    def console_crea_ricetta(self, payload):
        """Crea cf.task template_key='ricetta' (R&D): step Formulazione (default da
        ir.config_parameter casafolino_ricetta.user_formulazione, override). NIENTE ordine/
        spedizione. originatore = operatore. payload: {leadId?, partnerId?, recipeSpec,
        productType?, assignees?:{formulazione}, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo console_api."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        _require_manager(self.env, operator)

        _to, partner = self._console_recipient((payload or {}).get('leadId'), (payload or {}).get('partnerId'))
        lead_id = int((payload or {}).get('leadId') or 0) or False
        spec = _clean_str((payload or {}).get('recipeSpec')) or (payload or {}).get('recipeSpec') or ''
        product_type = _clean_str((payload or {}).get('productType'))

        ICP = self.env['ir.config_parameter'].sudo()
        assignees = (payload or {}).get('assignees') or {}
        uid_form = int(assignees.get('formulazione') or 0) or int(
            ICP.get_param('casafolino_ricetta.user_formulazione', 9) or 9) or operator.id

        title = _("Ricetta %s") % (product_type or (partner.name if partner else '') or operator.name)
        task = self.env['cf.task'].sudo().create({
            'name': title,
            'template_key': 'ricetta',
            'partner_id': partner.id if partner else False,
            'lead_id': lead_id,
            'step_ids': [(0, 0, {
                'sequence': 10, 'role': 'creazione',
                'user_id': uid_form, 'name': _("Formulazione ricetta"),
            })],
        })
        # originatore = operatore (default cf.task = env.user = console_api)
        task.write({'originator_id': operator.id})
        # la spec ricetta va nel chatter del task (R&D), niente ordine/spedizione
        if spec:
            task.message_post(body=_("<b>Spec ricetta:</b><br/>%s") % spec)
        task.action_start()

        steps = [{
            'stepId': s.id, 'role': s.role, 'name': s.name or '',
            'assignee': s.user_id.name or '', 'state': s.state, 'trafficLight': s.traffic_light,
        } for s in task.step_ids.sorted('sequence')]
        _audit(self.env, 'cf.task', [task.id], 'crea_ricetta', None, operator)
        return {'ok': True, 'taskId': task.id, 'name': task.name,
                'taskState': task.state, 'trafficLight': task.traffic_light, 'steps': steps}
