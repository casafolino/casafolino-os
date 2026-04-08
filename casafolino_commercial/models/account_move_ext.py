from odoo import models, fields


class AccountMoveExt(models.Model):
    _inherit = 'account.move'

    footer_block_ids = fields.Many2many(
        'cf.doc.footer.block',
        'account_move_footer_block_rel',
        'move_id',
        'block_id',
        string='Blocchi Documento',
    )
