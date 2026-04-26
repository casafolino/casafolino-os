from odoo import models, fields


class ResUsersMailV3(models.Model):
    _inherit = 'res.users'

    mail_v3_default_account_id = fields.Many2one('casafolino.mail.account',
                                                  string='Account Mail V3 default')
    mail_v3_reading_pane_position = fields.Selection([
        ('right', 'Destra'),
        ('bottom', 'Sotto'),
        ('off', 'Disattivato'),
    ], string='Reading pane', default='right')
    mail_v3_thread_list_density = fields.Selection([
        ('compact', 'Compatto'),
        ('comfortable', 'Comodo'),
        ('spacious', 'Spazioso'),
    ], string='Densità lista', default='comfortable')
    mail_v3_keyboard_shortcuts_enabled = fields.Boolean('Shortcut tastiera', default=True)
    mail_v3_dark_mode = fields.Boolean('Dark mode', default=False)
    mv3_font_size = fields.Selection([
        ('small', 'Piccolo'),
        ('medium', 'Medio'),
        ('large', 'Grande'),
    ], string='Dimensione font', default='medium')
    mv3_ai_reply_enabled = fields.Boolean('AI Reply attivo', default=True)
    mv3_ai_temperature = fields.Float('AI Temperature', default=0.5)
    mv3_ai_model = fields.Char('AI Model', default='llama-3.3-70b-versatile')
    mv3_undo_send_seconds = fields.Integer('Undo Send Timer (sec)', default=10)
    mv3_notifications_enabled = fields.Boolean('Notifiche browser Mail Hub', default=False)
