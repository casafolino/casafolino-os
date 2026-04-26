import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class CasafolinoFiera(models.Model):
    _name = 'casafolino.fiera'
    _description = 'Fiera CasaFolino'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Nome Fiera',
        required=True,
        translate=True,
        tracking=True,
    )
    date_start = fields.Date(string='Data Inizio', required=True, tracking=True)
    date_end = fields.Date(string='Data Fine', required=True, tracking=True)
    location = fields.Char(string='Luogo')
    expected_visitors = fields.Integer(string='Visitatori Previsti')
    tag_id = fields.Many2one(
        'crm.tag',
        string='Tag CRM Lead',
        readonly=True,
        copy=False,
    )
    category_id = fields.Many2one(
        'res.partner.category',
        string='Tag Contatti',
        readonly=True,
        copy=False,
    )
    attendees = fields.Many2many(
        'res.users',
        relation='casafolino_fiera_users_rel',
        string='Partecipanti',
    )
    status = fields.Selection(
        [
            ('planned', 'Pianificata'),
            ('active', 'Attiva'),
            ('closed', 'Chiusa'),
        ],
        string='Stato',
        default='planned',
        required=True,
        tracking=True,
    )
    lead_count = fields.Integer(
        string='Lead',
        compute='_compute_lead_count',
    )
    partner_count = fields.Integer(
        string='Partner',
        compute='_compute_partner_count',
    )
    description = fields.Html(string='Note')

    # --- Computed fields ---

    def _compute_lead_count(self):
        for fiera in self:
            if fiera.tag_id:
                fiera.lead_count = self.env['crm.lead'].search_count(
                    [('tag_ids', 'in', fiera.tag_id.id)]
                )
            else:
                fiera.lead_count = 0

    def _compute_partner_count(self):
        for fiera in self:
            if fiera.category_id:
                fiera.partner_count = self.env['res.partner'].search_count(
                    [('category_id', 'in', fiera.category_id.id)]
                )
            else:
                fiera.partner_count = 0

    # --- CRUD overrides ---

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._ensure_tags()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for rec in self:
                if rec.tag_id:
                    rec.tag_id.name = rec.name
                if rec.category_id:
                    rec.category_id.name = rec.name
        return res

    def unlink(self):
        tags_to_delete = self.env['crm.tag']
        cats_to_delete = self.env['res.partner.category']
        for fiera in self:
            if not fiera.tag_id and not fiera.category_id:
                continue
            lead_count = self.env['crm.lead'].search_count(
                [('tag_ids', 'in', fiera.tag_id.id)]
            ) if fiera.tag_id else 0
            partner_count = self.env['res.partner'].search_count(
                [('category_id', 'in', fiera.category_id.id)]
            ) if fiera.category_id else 0
            if lead_count == 0 and partner_count == 0:
                if fiera.tag_id:
                    tags_to_delete |= fiera.tag_id
                if fiera.category_id:
                    cats_to_delete |= fiera.category_id
            else:
                _logger.warning(
                    "Fiera '%s': tag non cancellati (%d lead, %d partner associati)",
                    fiera.name, lead_count, partner_count,
                )
        res = super().unlink()
        if tags_to_delete:
            tags_to_delete.unlink()
        if cats_to_delete:
            cats_to_delete.unlink()
        return res

    # --- Helpers ---

    def _ensure_tags(self):
        """Create crm.tag and res.partner.category with fiera name if not exist."""
        self.ensure_one()
        CrmTag = self.env['crm.tag']
        PartnerCat = self.env['res.partner.category']

        if not self.tag_id:
            existing_tag = CrmTag.search([('name', '=', self.name)], limit=1)
            self.tag_id = existing_tag or CrmTag.create({'name': self.name})

        if not self.category_id:
            existing_cat = PartnerCat.search([('name', '=', self.name)], limit=1)
            self.category_id = existing_cat or PartnerCat.create({'name': self.name})

    # --- Actions ---

    def action_view_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lead — %s', self.name),
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('tag_ids', 'in', self.tag_id.id)] if self.tag_id else [('id', '=', 0)],
            'context': {'default_tag_ids': [self.tag_id.id]} if self.tag_id else {},
        }

    def action_view_partners(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contatti — %s', self.name),
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('category_id', 'in', self.category_id.id)] if self.category_id else [('id', '=', 0)],
        }

    def action_set_active(self):
        self.write({'status': 'active'})

    def action_set_closed(self):
        self.write({'status': 'closed'})

    def action_set_planned(self):
        self.write({'status': 'planned'})

    # --- GDPR Cron ---

    @api.model
    def _cron_cleanup_old_business_cards(self):
        """
        GDPR retention: cancella allegati biglietti da visita >24 mesi.

        Da configurare via UI Odoo:
        - Settings → Technical → Automation → Scheduled Actions → New
        - Name: CasaFolino: GDPR retention biglietti 24 mesi
        - Model: casafolino.fiera
        - Execute Every: 1 Months
        - Execute: Code
        - Code: model._cron_cleanup_old_business_cards()
        - Active: True
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=730)

        old_attachments = self.env['ir.attachment'].search([
            ('res_model', 'in', ['crm.lead', 'res.partner']),
            ('name', 'ilike', 'biglietto_originale%'),
            ('create_date', '<', cutoff_date),
        ])

        count = len(old_attachments)
        if count:
            old_attachments.unlink()
            _logger.info(
                "GDPR retention: rimossi %d allegati biglietti vecchi >24 mesi",
                count,
            )
        else:
            _logger.info("GDPR retention: nessun allegato da rimuovere")
