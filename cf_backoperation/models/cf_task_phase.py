from odoo import api, fields, models


class CfTaskPhase(models.Model):
    """Fase esecutiva di una produzione (Livello A).

    Snapshot delle operazioni della MO, materializzato al primo check-in.
    Registra eventi di esecuzione (chi/quando) che NON esistono nativamente.
    NON scrive su mrp.workorder (nessun write-back MRP — round 2).
    """
    _name = 'cf.task.phase'
    _description = 'CasaFolino Task Phase'
    _order = 'seq, id'

    task_id = fields.Many2one(
        'cf.task', string="Task", required=True, ondelete='cascade', index=True)
    seq = fields.Integer(string="Sequenza", default=10)
    name = fields.Char(string="Fase", required=True)
    operatore_id = fields.Many2one('hr.employee', string="Operatore")
    started_at = fields.Datetime(string="Inizio")
    ended_at = fields.Datetime(string="Fine")
    state = fields.Selection([
        ('da_fare', 'Da fare'),
        ('in_corso', 'In corso'),
        ('fatta', 'Fatta'),
    ], string="Stato", default='da_fare', required=True)

    def _bo_serialize(self):
        out = []
        for p in self:
            out.append({
                'id': p.id,
                'seq': p.seq,
                'name': p.name,
                'state': p.state,
                'operatore_id': p.operatore_id.id or False,
                'operatore_name': p.operatore_id.name or False,
                'started_at': p.started_at and fields.Datetime.to_string(p.started_at) or False,
                'ended_at': p.ended_at and fields.Datetime.to_string(p.ended_at) or False,
            })
        return out
