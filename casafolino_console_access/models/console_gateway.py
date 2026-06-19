from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError

CONSOLE_GROUP = 'casafolino_console_access.group_console_api'


def _is_console(env):
    """True se l'utente corrente è il service-user console (portal scoped)."""
    return env.user.has_group(CONSOLE_GROUP)


def _audit(env, model, res_ids, action, fields_touched=None):
    env['casafolino.console.audit'].sudo().create({
        'user_id': env.user.id,
        'login': env.user.login,
        'model': model,
        'res_ids': str(res_ids)[:255],
        'action': action,
        'fields_touched': (','.join(sorted(fields_touched))[:255]) if fields_touched else False,
    })


class CasafolinoMailMessageGateway(models.Model):
    """Gateway triage: l'unico modo per console_api di scrivere su una mail.
    Scrive SOLO il campo `state` (mai body/contenuto), valida lo stato, logga l'audit.
    L'ACL di console_api su casafolino.mail.message è READ-ONLY → niente write diretta."""
    _inherit = 'casafolino.mail.message'

    # stati triage ammessi (allineati alla selection del modello)
    _CONSOLE_TRIAGE_STATES = ('new', 'review', 'keep', 'auto_keep', 'discard', 'auto_discard')

    def console_triage(self, state):
        """Chiamato via JSON-RPC dall'utente portal: browse(ids).console_triage(state).
        Scrive solo state via sudo. Mai un write(model, vals) generico."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console può usare console_triage."))
        if state not in self._CONSOLE_TRIAGE_STATES:
            raise UserError(_("Stato triage non valido: %s") % state)
        if not self.ids:
            return {'ok': False, 'error': 'no records'}
        # self è già filtrato dalle record-rule di lettura dell'utente
        ids = self.ids
        self.sudo().write({'state': state})  # SOLO state — body invariato
        _audit(self.env, 'casafolino.mail.message', ids, 'triage:%s' % state, {'state'})
        return {'ok': True, 'count': len(ids), 'state': state}


class CrmLeadConsoleAudit(models.Model):
    """crm.lead: console_api scrive via ACL diretta scoped → qui logghiamo l'audit."""
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.su and _is_console(self.env):
            _audit(self.env, 'crm.lead', records.ids, 'create')
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.su and self.ids and _is_console(self.env):
            _audit(self.env, 'crm.lead', self.ids, 'write', set(vals.keys()))
        return res


class ResPartnerConsoleAudit(models.Model):
    """res.partner: idem crm.lead."""
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.su and _is_console(self.env):
            _audit(self.env, 'res.partner', records.ids, 'create')
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.su and self.ids and _is_console(self.env):
            _audit(self.env, 'res.partner', self.ids, 'write', set(vals.keys()))
        return res
