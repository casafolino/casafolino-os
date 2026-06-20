from odoo import models, fields


class CasafolinoConsoleAudit(models.Model):
    """Traccia ogni scrittura della Console in prod: chi / cosa / quando.
    Popolato dal gateway triage e dagli override create/write di crm.lead/res.partner."""
    _name = 'casafolino.console.audit'
    _description = 'Console Write Audit Log'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='Utente', required=True, index=True)
    login = fields.Char('Login')
    model = fields.Char('Modello', required=True, index=True)
    res_ids = fields.Char('Record IDs')
    action = fields.Char('Azione', required=True)  # es. 'create', 'write', 'triage:keep'
    fields_touched = fields.Char('Campi')
    # S5 — attribution operatore umano (separato da user_id = console_api service-user).
    # Vuoto quando l'azione non porta un operatore (es. cron digest, triage senza operatore).
    operator_uid = fields.Many2one('res.users', string='Operatore (umano)', index=True)
    operator_login = fields.Char('Operatore login')
    # create_date / create_uid automatici
