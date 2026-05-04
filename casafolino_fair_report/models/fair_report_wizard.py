from odoo import models, fields, _


class FairReportWizard(models.TransientModel):
    _name = 'casafolino.fair.report.wizard'
    _description = 'Wizard Report Fiera'

    fiera_id = fields.Many2one(
        'casafolino.fiera',
        string='Fiera',
        required=True,
    )
    close_fair = fields.Boolean(
        string='Chiudi fiera dopo invio',
        default=False,
    )
    include_contacts = fields.Boolean(
        string='Includi lista completa contatti',
        default=True,
    )

    def action_generate_report(self):
        self.ensure_one()
        fiera = self.fiera_id
        if self.close_fair:
            return fiera.action_close_fair()
        return fiera.action_send_report_only()
