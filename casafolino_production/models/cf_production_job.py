# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

PRODUCTION_LINES = [
    ("miele","Miele"),("creme","Creme Spalmabili"),("cantucci","Cantucci GF"),
    ("cioccolato","Cioccolato"),("crispy","Crispy Chili"),
    ("risotti","Risotti"),("confezionamento","Confezionamento"),
]

LINE_COLORS = {
    "miele":"#F59E0B","creme":"#8B5CF6","cantucci":"#10B981",
    "cioccolato":"#92400E","crispy":"#EF4444","risotti":"#3B82F6","confezionamento":"#6B7280",
}

class CfProductionJob(models.Model):
    _name = "cf.production.job"
    _description = "Commessa Produzione"
    _inherit = ["mail.thread","mail.activity.mixin"]
    _order = "date_start asc"
    _rec_name = "reference"

    reference = fields.Char(required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.production.job") or "PROD-NUOVO")
    state = fields.Selection([
        ("draft","Bozza"),("confirmed","Confermata"),("in_progress","In Produzione"),
        ("done","Completata"),("cancelled","Annullata"),
    ], default="draft", tracking=True)
    production_line = fields.Selection(PRODUCTION_LINES, required=True, tracking=True)
    line_color = fields.Char(compute="_compute_line_color", store=False)
    product_id = fields.Many2one("product.template", required=True)
    quantity_planned = fields.Float(string="Quantita Pianificata", required=True)
    quantity_done = fields.Float(string="Quantita Prodotta")
    date_start = fields.Datetime(string="Inizio", required=True)
    date_end = fields.Datetime(string="Fine", required=True)
    operator_ids = fields.Many2many("res.users", string="Operatori")
    production_id = fields.Many2one("mrp.production", string="Ordine Produzione")
    notes = fields.Text()

    @api.depends("production_line")
    def _compute_line_color(self):
        for rec in self:
            rec.line_color = LINE_COLORS.get(rec.production_line, "#6B7280")

    @api.constrains("date_start","date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start >= rec.date_end:
                raise ValidationError("La data di fine deve essere successiva alla data di inizio.")

    def action_confirm(self):
        self.write({"state":"confirmed"})
    def action_start(self):
        self.write({"state":"in_progress"})
    def action_done(self):
        self.write({"state":"done"})
    def action_cancel(self):
        self.write({"state":"cancelled"})

    def action_create_mo(self):
        self.ensure_one()
        mo = self.env["mrp.production"].create({
            "product_id": self.product_id.product_variant_id.id if self.product_id.product_variant_id else False,
            "product_qty": self.quantity_planned,
            "date_start": self.date_start,
        })
        self.production_id = mo
        return {"type":"ir.actions.act_window","name":"Ordine Produzione","res_model":"mrp.production","res_id":mo.id,"view_mode":"form"}
