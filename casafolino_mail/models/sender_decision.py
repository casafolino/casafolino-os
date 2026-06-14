import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'googlemail.com',
    'yahoo.com', 'yahoo.it', 'yahoo.fr', 'yahoo.de', 'yahoo.es', 'yahoo.co.uk',
    'hotmail.com', 'hotmail.it', 'hotmail.fr', 'hotmail.de', 'hotmail.es',
    'outlook.com', 'outlook.it', 'outlook.fr', 'outlook.de',
    'live.com', 'live.it', 'msn.com',
    'libero.it', 'tiscali.it', 'virgilio.it', 'alice.it', 'tin.it',
    'icloud.com', 'me.com', 'mac.com',
    'aol.com',
    'gmx.de', 'gmx.at', 'gmx.com', 'gmx.net',
    'web.de', 't-online.de',
    'protonmail.com', 'proton.me',
    'pec.it',
}


class CasafolinoMailSenderDecision(models.Model):
    _name = 'casafolino.mail.sender.decision'
    _description = 'Decisione triage partner orfano'
    _order = 'triaged_at desc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True,
                                  ondelete='cascade')
    sender_email = fields.Char('Email mittente')
    sender_domain = fields.Char('Dominio', compute='_compute_sender_domain', store=True)
    decision = fields.Selection([
        ('lead_created', 'Lead creato'),
        ('assigned', 'Assegnato'),
        ('replied', 'Risposto con snippet'),
        ('kept', 'Tenuto (valido)'),
        ('ignored_sender', 'Ignorato mittente'),
        ('ignored_domain', 'Ignorato dominio'),
    ], string='Decisione', required=True)
    triaged_by = fields.Many2one('res.users', string='Triaged da',
                                  default=lambda self: self.env.uid)
    triaged_at = fields.Datetime('Data triage', default=fields.Datetime.now)
    notes = fields.Text('Note')
    lead_id = fields.Many2one('crm.lead', string='Lead creato', ondelete='set null')
    activity_id = fields.Many2one('mail.activity', string='Activity creata', ondelete='set null')
    sender_policy_id = fields.Many2one('casafolino.mail.sender_policy',
                                        string='Policy creata', ondelete='set null')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('partner_active_unique',
         'UNIQUE(partner_id) WHERE active = TRUE',
         'Questo partner ha già una decisione attiva.'),
    ]

    @api.depends('sender_email')
    def _compute_sender_domain(self):
        for rec in self:
            if rec.sender_email and '@' in rec.sender_email:
                rec.sender_domain = rec.sender_email.split('@')[1].lower().strip()
            else:
                rec.sender_domain = ''

    def action_undo(self):
        """Annulla decisione: disattiva decision + sender_policy associata."""
        self.ensure_one()
        if self.sender_policy_id:
            self.sender_policy_id.active = False
        self.active = False

    # ── Helper: get last inbound email for a partner ─────────────────

    @api.model
    def _get_last_email(self, partner_id):
        """Ritorna ultima email inbound keep/auto_keep per partner."""
        return self.env['casafolino.mail.message'].search([
            ('partner_id', '=', partner_id),
            ('direction', '=', 'inbound'),
            ('state', 'in', ['keep', 'auto_keep']),
        ], order='email_date desc', limit=1)

    @api.model
    def _get_last_email_preview(self, partner_id):
        """Ritorna (subject, body_preview) dell'ultima email inbound."""
        last = self._get_last_email(partner_id)
        subject = last.subject if last else ''
        body = ''
        if last and last.body_html:
            body = re.sub(r'<[^>]+>', ' ', last.body_html)
            body = re.sub(r'\s+', ' ', body).strip()[:500]
        elif last and last.snippet:
            body = last.snippet[:500]
        return subject, body
