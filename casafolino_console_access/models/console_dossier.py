import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .console_gateway import _is_console, _audit
from .console_campionatura import _operator
from .console_enrich import _clean_str

_logger = logging.getLogger(__name__)


class CfDossierFolder(models.Model):
    """Cartella/categoria per i dossier curati (USA, Private label, VIP…). Gestita da Antonio
    dal console. Poche righe, non hardcoded. Scritture sempre via metodi gated del console."""
    _name = 'cf.dossier.folder'
    _description = 'Cartella Dossier (console)'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    color = fields.Integer(default=0)
    sequence = fields.Integer(default=10)
    partner_ids = fields.One2many('res.partner', 'dossier_folder_id', string='Dossier')
    partner_count = fields.Integer(compute='_compute_partner_count')

    @api.depends('partner_ids', 'partner_ids.is_dossier')
    def _compute_partner_count(self):
        for f in self:
            f.partner_count = len(f.partner_ids.filtered('is_dossier'))


class ResPartnerDossier(models.Model):
    """Pin dossier + cartella su res.partner. La pagina Dossier mostra SOLO is_dossier=True.
    Nessuna migrazione: i dossier nascono vuoti, li popola Antonio pinnando dal fascicolo."""
    _inherit = 'res.partner'

    is_dossier = fields.Boolean('Dossier curato (console)', default=False, index=True)
    dossier_folder_id = fields.Many2one(
        'cf.dossier.folder', string='Cartella dossier', ondelete='set null', index=True)

    # ── metodi gated console (payload-style, anti-spoof operator_uid dalla sessione) ──

    @api.model
    def console_toggle_dossier(self, payload):
        """payload: {partner_id, is_dossier, folder_id?, new_folder_name?, operator_uid}.
        Pin/unpin del partner come dossier + cartella opzionale. Scrive SOLO i 2 campi dossier."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console."))
        p = (payload or {})
        partner = self.env['res.partner'].sudo().browse(int(p.get('partner_id') or 0))
        if not partner.exists():
            raise UserError(_("Partner inesistente."))
        operator = _operator(self.env, p.get('operator_uid'))
        is_dossier = bool(p.get('is_dossier'))
        vals = {'is_dossier': is_dossier}
        if is_dossier:
            fid = int(p.get('folder_id') or 0) or False
            nm = _clean_str(p.get('new_folder_name'))
            if nm:
                fid = self.env['cf.dossier.folder'].sudo().create({'name': nm}).id
            vals['dossier_folder_id'] = fid or False
        else:
            vals['dossier_folder_id'] = False
        partner.write(vals)
        _audit(self.env, 'res.partner', partner.ids, 'dossier_toggle:%s' % is_dossier,
               set(vals.keys()), operator)
        return {'ok': True, 'partner_id': partner.id, 'is_dossier': is_dossier,
                'folder_id': vals.get('dossier_folder_id') or False}

    @api.model
    def console_dossier_folders(self, payload=None):
        """Lista cartelle + conteggi dossier. Read-only gated."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console."))
        folders = self.env['cf.dossier.folder'].sudo().search([])
        return {'ok': True, 'folders': [{
            'id': f.id, 'name': f.name, 'color': f.color, 'count': f.partner_count,
        } for f in folders]}

    @api.model
    def console_create_folder(self, payload):
        """payload: {name, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console."))
        nm = _clean_str((payload or {}).get('name'))
        if not nm:
            raise UserError(_("Nome cartella obbligatorio."))
        operator = _operator(self.env, (payload or {}).get('operator_uid'))
        folder = self.env['cf.dossier.folder'].sudo().create({'name': nm})
        _audit(self.env, 'cf.dossier.folder', [folder.id], 'create_folder', None, operator)
        return {'ok': True, 'id': folder.id, 'name': folder.name}

    @api.model
    def console_rename_folder(self, payload):
        """payload: {folder_id, name, operator_uid}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console."))
        p = (payload or {})
        nm = _clean_str(p.get('name'))
        folder = self.env['cf.dossier.folder'].sudo().browse(int(p.get('folder_id') or 0))
        if not folder.exists() or not nm:
            raise UserError(_("Cartella o nome non validi."))
        operator = _operator(self.env, p.get('operator_uid'))
        folder.write({'name': nm})
        _audit(self.env, 'cf.dossier.folder', [folder.id], 'rename_folder', {'name'}, operator)
        return {'ok': True, 'id': folder.id, 'name': folder.name}

    @api.model
    def console_dossier_list(self, payload=None):
        """SOLO partner pinnati (is_dossier), raggruppati per cartella. Sezione 'Senza cartella'
        in coda. Read-only gated. Nessuna anagrafica non pinnata. payload: {query?}."""
        if not _is_console(self.env):
            raise AccessError(_("Solo l'utente Console."))
        Partner = self.env['res.partner'].sudo()
        domain = [('is_dossier', '=', True)]
        q = _clean_str((payload or {}).get('query'))
        if q:
            domain += ['|', ('name', 'ilike', q), ('email', 'ilike', q)]
        partners = Partner.search(domain, order='name')
        folders = self.env['cf.dossier.folder'].sudo().search([])
        groups = []
        for f in folders:
            members = partners.filtered(lambda p: p.dossier_folder_id.id == f.id)
            groups.append({'id': f.id, 'name': f.name, 'color': f.color,
                           'partners': [self._console_dossier_card(p) for p in members]})
        no_folder = partners.filtered(lambda p: not p.dossier_folder_id)
        groups.append({'id': False, 'name': 'Senza cartella', 'color': 0,
                       'partners': [self._console_dossier_card(p) for p in no_folder]})
        return {'ok': True, 'total': len(partners), 'groups': groups}

    def _console_dossier_card(self, p):
        return {'id': p.id, 'name': p.name or '', 'email': p.email or '',
                'city': p.city or '', 'country': p.country_id.name or '',
                'is_company': p.is_company, 'folder_id': p.dossier_folder_id.id or False}
