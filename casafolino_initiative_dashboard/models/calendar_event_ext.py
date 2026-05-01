from odoo import fields, models


class CalendarEventExt(models.Model):
    _inherit = 'calendar.event'

    cf_initiative_ids = fields.Many2many(
        'cf.initiative',
        'calendar_event_cf_initiative_rel',
        string='Iniziative',
    )
