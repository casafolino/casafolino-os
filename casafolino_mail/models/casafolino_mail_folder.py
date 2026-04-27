import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SYSTEM_FOLDERS = [
    ('inbox', 'Inbox', 1, '\U0001f4e5'),
    ('unsorted', 'Da smistare', 2, '\u26a0\ufe0f'),
    ('sent', 'Inviate', 3, '\U0001f4e4'),
    ('archive', 'Archivio', 4, '\U0001f5c4'),
    ('trash', 'Cestino', 5, '\U0001f5d1'),
    ('spam', 'Spam', 6, '\U0001f6ab'),
]


class CasafolinoMailFolder(models.Model):
    _name = 'casafolino.mail.folder'
    _description = 'Cartella email — Mail Hub'
    _order = 'sequence, id'

    name = fields.Char('Nome', required=True)
    account_id = fields.Many2one(
        'casafolino.mail.account', string='Account',
        required=True, ondelete='cascade', index=True)
    color = fields.Integer('Colore', default=0)
    icon = fields.Char('Icona', default='\U0001f4c1')
    parent_folder_id = fields.Many2one(
        'casafolino.mail.folder', string='Cartella padre',
        ondelete='cascade', index=True)
    child_folder_ids = fields.One2many(
        'casafolino.mail.folder', 'parent_folder_id', string='Sotto-cartelle')
    sequence = fields.Integer('Sequenza', default=10)
    is_system = fields.Boolean('Sistema', default=False)
    system_code = fields.Selection([
        ('inbox', 'Inbox'),
        ('sent', 'Inviate'),
        ('archive', 'Archivio'),
        ('trash', 'Cestino'),
        ('unsorted', 'Da smistare'),
        ('spam', 'Spam'),
    ], string='Codice sistema')
    folder_path = fields.Char(
        'Percorso', compute='_compute_folder_path', store=True)
    message_count = fields.Integer(
        'Messaggi', compute='_compute_message_count')
    unread_count = fields.Integer(
        'Non letti', compute='_compute_unread_count')

    _sql_constraints = [
        ('system_code_account_uniq',
         'UNIQUE(account_id, system_code)',
         'Codice sistema univoco per account'),
        ('name_parent_account_uniq',
         'UNIQUE(account_id, parent_folder_id, name)',
         'Nome cartella univoco tra fratelli'),
    ]

    def init(self):
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS casafolino_mail_folder_account_idx
            ON casafolino_mail_folder (account_id)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS casafolino_mail_folder_system_code_idx
            ON casafolino_mail_folder (system_code)
        """)

    @api.depends('name', 'parent_folder_id', 'parent_folder_id.name')
    def _compute_folder_path(self):
        for folder in self:
            if folder.parent_folder_id:
                folder.folder_path = '%s / %s' % (
                    folder.parent_folder_id.name, folder.name)
            else:
                folder.folder_path = folder.name

    def _compute_message_count(self):
        for folder in self:
            folder.message_count = self.env['casafolino.mail.message'].search_count([
                ('folder_id', '=', folder.id),
                ('is_deleted', '=', False),
            ])

    def _compute_unread_count(self):
        for folder in self:
            folder.unread_count = self.env['casafolino.mail.message'].search_count([
                ('folder_id', '=', folder.id),
                ('is_deleted', '=', False),
                ('is_read', '=', False),
            ])

    @api.model
    def _create_system_folders(self, account_id):
        """Create 6 system folders for an account. Idempotent."""
        existing = self.search([
            ('account_id', '=', account_id),
            ('is_system', '=', True),
        ])
        existing_codes = set(existing.mapped('system_code'))

        created = 0
        for code, name, seq, icon in SYSTEM_FOLDERS:
            if code not in existing_codes:
                self.create({
                    'name': name,
                    'account_id': account_id,
                    'sequence': seq,
                    'icon': icon,
                    'is_system': True,
                    'system_code': code,
                })
                created += 1

        if created:
            _logger.info(
                "[folder] Created %d system folders for account %d",
                created, account_id)
        return created

    def action_rename_folder(self):
        self.ensure_one()
        if self.is_system:
            raise UserError("Le cartelle di sistema non possono essere rinominate.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rinomina cartella',
            'res_model': 'casafolino.mail.folder',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_delete_folder(self):
        self.ensure_one()
        if self.is_system:
            raise UserError("Le cartelle di sistema non possono essere eliminate.")
        # Move messages to parent folder or inbox
        messages = self.env['casafolino.mail.message'].search([
            ('folder_id', '=', self.id),
        ])
        if messages:
            target = self.parent_folder_id
            if not target:
                target = self.search([
                    ('account_id', '=', self.account_id.id),
                    ('system_code', '=', 'inbox'),
                ], limit=1)
            messages.write({'folder_id': target.id})
            _logger.info(
                "[folder] Moved %d messages from folder %d to %d",
                len(messages), self.id, target.id)
        # Move child folders to parent
        for child in self.child_folder_ids:
            child.parent_folder_id = self.parent_folder_id
        self.unlink()
