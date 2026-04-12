import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CasafolinoMailMessage(models.Model):
    _name = 'casafolino.mail.message'
    _description = 'Email Staging — Mail Hub Triage'
    _order = 'email_date desc, id desc'

    account_id = fields.Many2one('casafolino.mail.account', string='Account',
                                  required=True, ondelete='cascade')
    message_id_rfc = fields.Char('Message-ID RFC 2822', index=True)
    imap_uid = fields.Char('UID IMAP')
    imap_folder = fields.Char('Cartella IMAP')
    direction = fields.Selection([
        ('inbound', 'Ricevuta'),
        ('outbound', 'Inviata'),
    ], string='Direzione')
    sender_email = fields.Char('Email mittente')
    sender_name = fields.Char('Nome mittente')
    sender_domain = fields.Char('Dominio mittente', compute='_compute_sender_domain',
                                 store=True, index=True)
    recipient_emails = fields.Char('Destinatari')
    cc_emails = fields.Char('CC')
    subject = fields.Char('Oggetto')
    email_date = fields.Datetime('Data email')
    snippet = fields.Text('Anteprima')

    state = fields.Selection([
        ('new', 'Nuova'),
        ('keep', 'Tenuta'),
        ('discard', 'Scartata'),
    ], string='Stato', default='new', index=True)

    partner_id = fields.Many2one('res.partner', string='Contatto')
    match_type = fields.Selection([
        ('exact', 'Email esatta'),
        ('domain', 'Dominio'),
        ('manual', 'Manuale'),
        ('none', 'Nessuno'),
    ], string='Tipo match', default='none')

    body_html = fields.Html('Body HTML', sanitize=False)
    body_downloaded = fields.Boolean('Body scaricato', default=False)
    attachment_ids = fields.One2many('ir.attachment', 'res_id',
                                      string='Allegati',
                                      domain=[('res_model', '=', 'casafolino.mail.message')])
    triage_user_id = fields.Many2one('res.users', string='Triage da')
    triage_date = fields.Datetime('Data triage')

    _sql_constraints = [
        ('message_id_unique', 'unique(message_id_rfc)',
         'Email già presente (Message-ID duplicato).'),
    ]

    @api.depends('sender_email')
    def _compute_sender_domain(self):
        for rec in self:
            if rec.sender_email and '@' in rec.sender_email:
                rec.sender_domain = rec.sender_email.split('@')[1].lower().strip()
            else:
                rec.sender_domain = ''

    # ── Triage actions (placeholders — body download in Step 3) ───────

    def action_keep(self):
        """Marca come keep."""
        self.write({
            'state': 'keep',
            'triage_user_id': self.env.user.id,
            'triage_date': fields.Datetime.now(),
        })

    def action_discard(self):
        """Marca come discard."""
        self.write({
            'state': 'discard',
            'triage_user_id': self.env.user.id,
            'triage_date': fields.Datetime.now(),
        })
