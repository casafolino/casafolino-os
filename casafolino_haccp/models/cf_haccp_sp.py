# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class CfHaccpSp(models.Model):
    _name = "cf.haccp.sp"
    _description = "Scheda di Produzione HACCP"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(string="N° Scheda", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.sp") or "SP-NUOVO")
    state = fields.Selection([
        ("draft","Bozza"),("in_progress","In Produzione"),
        ("completed","Completata"),("released","Rilasciata"),("blocked","Bloccata"),
    ], string="Stato", default="draft", tracking=True, required=True)
    production_id = fields.Many2one("mrp.production", string="Ordine di Produzione")
    product_id = fields.Many2one("product.template", string="Prodotto", required=True)
    lot_id = fields.Many2one("stock.lot", string="Lotto PF")
    date = fields.Datetime(string="Data Inizio", default=fields.Datetime.now, required=True)
    date_end = fields.Datetime(string="Data Fine")
    operator_id = fields.Many2one("res.users", string="Operatore", default=lambda self: self.env.user)
    quantity_produced = fields.Float(string="Quantita Prodotta")
    step1_ok = fields.Boolean(string="Step 1 OK")
    step2_ok = fields.Boolean(string="Step 2 OK")
    step3_ok = fields.Boolean(string="Step 3 OK")
    step4_ok = fields.Boolean(string="Step 4 OK")
    step5_ok = fields.Boolean(string="Step 5 OK")
    step6_ok = fields.Boolean(string="Step 6 OK")
    step7_ok = fields.Boolean(string="Step 7 OK")
    step8_ok = fields.Boolean(string="Step 8 OK")
    step9_ok = fields.Boolean(string="Step 9 OK")
    step10_ok = fields.Boolean(string="Step 10 OK")
    notes = fields.Text(string="Note")
    ccp_ids = fields.One2many("cf.haccp.ccp", "sp_id", string="CCP")
    nc_ids = fields.One2many("cf.haccp.nc", "sp_id", string="Non Conformita")

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_complete(self):
        for rec in self:
            open_nc = rec.nc_ids.filtered(lambda n: n.state not in ("closed","cancelled"))
            rec.state = "blocked" if open_nc else "completed"

    def action_release(self):
        for rec in self:
            open_nc = rec.nc_ids.filtered(lambda n: n.state not in ("closed","cancelled"))
            if open_nc:
                raise UserError("Impossibile rilasciare: NC aperte.")
            rec.state = "released"

class MrpProductionHaccp(models.Model):
    _inherit = "mrp.production"
    haccp_sp_ids = fields.One2many("cf.haccp.sp", "production_id", string="Schede HACCP")
    haccp_sp_count = fields.Integer(compute="_compute_haccp_sp_count")

    def _compute_haccp_sp_count(self):
        for rec in self:
            rec.haccp_sp_count = len(rec.haccp_sp_ids)
