# -*- coding: utf-8 -*-
from odoo import models, fields

class CfRecallWizard(models.TransientModel):
    _name = "cf.recall.wizard"
    _description = "Wizard Avvio Mock Recall"
    lot_id = fields.Many2one("stock.lot", required=True)
    direction = fields.Selection([("forward","Avanti"),("backward","Indietro"),("both","Entrambe")], required=True, default="both")
    session_type = fields.Selection([("mock","Mock"),("real","Reale"),("audit","Audit")], required=True, default="mock")
    notes = fields.Text()

    def action_run_recall(self):
        session = self.env["cf.recall.session"].create({
            "lot_id": self.lot_id.id,
            "direction": self.direction,
            "session_type": self.session_type,
            "notes": self.notes,
        })
        session.action_run()
        return {"type":"ir.actions.act_window","name":"Risultato Recall","res_model":"cf.recall.session","res_id":session.id,"view_mode":"form","target":"current"}
