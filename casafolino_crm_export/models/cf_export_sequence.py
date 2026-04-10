from odoo import api, fields, models


class CfExportSequence(models.Model):
    _name = 'cf.export.sequence'
    _description = 'Sequenza Follow-up Export'

    name = fields.Char(string='Nome Sequenza', required=True)
    active = fields.Boolean(default=True)
    step_ids = fields.One2many('cf.export.sequence.step', 'sequence_id', string='Step')
    description = fields.Text(string='Descrizione')


class CfExportSequenceStep(models.Model):
    _name = 'cf.export.sequence.step'
    _description = 'Step Sequenza Export'
    _order = 'day_offset asc'

    sequence_id = fields.Many2one('cf.export.sequence', required=True, ondelete='cascade')
    day_offset = fields.Integer(string='Giorno (offset)', required=True, default=0)
    action_type = fields.Selection([
        ('email', 'Email'),
        ('call', 'Chiamata'),
        ('whatsapp', 'WhatsApp'),
        ('task', 'Attività'),
    ], string='Tipo Azione', required=True, default='email')
    note = fields.Text(string='Note / Template')
    name = fields.Char(string='Titolo Step')


class CfExportSequenceLog(models.Model):
    _name = 'cf.export.sequence.log'
    _description = 'Log Sequenza su Lead'
    _order = 'create_date desc'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade', string='Trattativa')
    sequence_id = fields.Many2one('cf.export.sequence', required=True, string='Sequenza')
    state = fields.Selection([
        ('running', 'In Corso'),
        ('paused', 'In Pausa'),
        ('done', 'Completata'),
        ('cancelled', 'Annullata'),
    ], string='Stato', default='running')
    line_ids = fields.One2many('cf.export.sequence.log.line', 'log_id', string='Step Eseguiti')
    date_start = fields.Date(string='Data Inizio', default=fields.Date.today)


class CfExportSequenceLogLine(models.Model):
    _name = 'cf.export.sequence.log.line'
    _description = 'Riga Log Sequenza'
    _order = 'date_executed asc'

    log_id = fields.Many2one('cf.export.sequence.log', required=True, ondelete='cascade')
    step_id = fields.Many2one('cf.export.sequence.step', string='Step')
    date_executed = fields.Datetime(string='Data Esecuzione')
    result = fields.Selection([
        ('done', 'Eseguito'),
        ('skipped', 'Saltato'),
        ('failed', 'Fallito'),
    ], string='Risultato')
    note = fields.Text(string='Note')
