from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class CfMailAccount(models.Model):
    _name = 'cf.mail.account'
    _description = 'Account Email CasaFolino'
    _order = 'sequence, id'

    name = fields.Char('Nome account', required=True)
    email = fields.Char('Indirizzo email', required=True)
    user_id = fields.Many2one('res.users', string='Utente', default=lambda self: self.env.uid)
    is_team = fields.Boolean('Team Inbox', default=False)
    color = fields.Char('Colore', default='#5A6E3A')
    signature = fields.Text('Firma')
    sequence = fields.Integer('Sequenza', default=10)
    active = fields.Boolean(default=True)
    message_ids = fields.One2many('cf.mail.message', 'account_id', string='Messaggi')

    @api.model
    def get_accounts(self, *args, **kw):
        accounts = self.search([('active', '=', True)], order='sequence, is_team, id')
        result = []
        for a in accounts:
            unread = self.env['cf.mail.message'].search_count([
                ('account_id', '=', a.id),
                ('is_read', '=', False),
                ('is_archived', '=', False),
                ('folder', '=', 'INBOX'),
            ])
            result.append({
                'id': a.id,
                'name': a.name,
                'email': a.email,
                'color': a.color or '#5A6E3A',
                'is_team': a.is_team,
                'unread': unread,
                'signature': a.signature or '',
            })
        return result
