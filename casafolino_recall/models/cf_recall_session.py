# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime

class CfRecallSession(models.Model):
    _name = "cf.recall.session"
    _description = "Sessione Mock Recall"
    _inherit = ["mail.thread"]
    _order = "date_start desc"
    _rec_name = "reference"

    reference = fields.Char(required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.recall.session") or "RECALL-NUOVO")
    session_type = fields.Selection([("mock","Mock Recall"),("real","Recall Reale"),("audit","Verifica Audit")], required=True, default="mock")
    lot_id = fields.Many2one("stock.lot", string="Lotto di Partenza", required=True)
    direction = fields.Selection([("forward","Avanti"),("backward","Indietro"),("both","Entrambe")], required=True, default="both")
    date_start = fields.Datetime(default=fields.Datetime.now)
    date_end = fields.Datetime(readonly=True)
    duration_seconds = fields.Float(readonly=True)
    state = fields.Selection([("draft","Bozza"),("running","In Corso"),("done","Completata")], default="draft", tracking=True)
    operator_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    result_summary = fields.Text(readonly=True)
    production_ids = fields.Many2many("mrp.production", string="MO Coinvolti")
    lot_ids = fields.Many2many("stock.lot", "cf_recall_lot_rel", "session_id", "lot_id", string="Lotti Tracciati")
    picking_ids = fields.Many2many("stock.picking", string="Spedizioni")
    partner_ids = fields.Many2many("res.partner", string="Partner Coinvolti")
    nodes_count = fields.Integer(readonly=True)
    notes = fields.Text()

    def action_run(self):
        self.ensure_one()
        self.state = "running"
        start = datetime.now()
        lot = self.lot_id
        productions, lots, pickings, partners = set(), set(), set(), set()
        lots.add(lot.id)
        if self.direction in ("forward","both"):
            self._trace_forward(lot, productions, lots, pickings, partners)
        if self.direction in ("backward","both"):
            self._trace_backward(lot, productions, lots, pickings, partners)
        end = datetime.now()
        duration = (end - start).total_seconds()
        self.write({
            "state": "done",
            "date_end": end,
            "duration_seconds": duration,
            "production_ids": [(6,0,list(productions))],
            "lot_ids": [(6,0,list(lots))],
            "picking_ids": [(6,0,list(pickings))],
            "partner_ids": [(6,0,list(partners))],
            "nodes_count": len(productions) + len(lots) + len(pickings),
            "result_summary": f"Completato in {duration:.1f}s. MO: {len(productions)}, Lotti: {len(lots)}, Spedizioni: {len(pickings)}, Partner: {len(partners)}",
        })

    def _trace_forward(self, lot, productions, lots, pickings, partners):
        mos = self.env["mrp.production"].search([("lot_producing_id","=",lot.id)])
        for mo in mos:
            productions.add(mo.id)
            for move_line in mo.move_finished_ids.mapped("move_line_ids"):
                if move_line.lot_id:
                    lots.add(move_line.lot_id.id)
        outgoing = self.env["stock.picking"].search([
            ("state","=","done"),("picking_type_code","=","outgoing"),
            ("move_line_ids.lot_id","=",lot.id)])
        for pick in outgoing:
            pickings.add(pick.id)
            if pick.partner_id: partners.add(pick.partner_id.id)

    def _trace_backward(self, lot, productions, lots, pickings, partners):
        move_lines = self.env["stock.move.line"].search([("lot_id","=",lot.id)])
        for ml in move_lines:
            if ml.production_id:
                productions.add(ml.production_id.id)
                for comp_line in ml.production_id.move_raw_ids.mapped("move_line_ids"):
                    if comp_line.lot_id: lots.add(comp_line.lot_id.id)
        incoming = self.env["stock.picking"].search([
            ("state","=","done"),("picking_type_code","=","incoming"),
            ("move_line_ids.lot_id","=",lot.id)])
        for pick in incoming:
            pickings.add(pick.id)
            if pick.partner_id: partners.add(pick.partner_id.id)
