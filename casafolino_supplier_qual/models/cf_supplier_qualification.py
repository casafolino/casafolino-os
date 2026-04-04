# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfSupplierQualification(models.Model):
    _name = "casafolino.supplier.qualification"
    _description = "Qualifica Fornitore"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id"
    _rec_name = "partner_id"
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade", domain="[('supplier_rank','>',0)]", tracking=True)
    partner_country_id = fields.Many2one(related="partner_id.country_id", store=True, readonly=True)
    status = fields.Selection([("approved","Approvato"),("evaluation","In Valutazione"),("suspended","Sospeso"),("excluded","Escluso")], default="evaluation", required=True, tracking=True)
    traffic_light = fields.Selection([("green","Verde"),("yellow","Giallo"),("red","Rosso")], compute="_compute_traffic_light", store=True)
    date_qualification = fields.Date(default=fields.Date.today)
    qualified_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    last_evaluation_date = fields.Date(readonly=True)
    next_evaluation_date = fields.Date(tracking=True)
    notes = fields.Text()
    document_ids = fields.One2many("casafolino.supplier.document", "partner_id", string="Documenti")
    evaluation_ids = fields.One2many("casafolino.supplier.evaluation", "partner_id", string="Valutazioni")
    document_count = fields.Integer(compute="_compute_stats")
    evaluation_count = fields.Integer(compute="_compute_stats")
    expired_doc_count = fields.Integer(compute="_compute_stats")
    expiring_doc_count = fields.Integer(compute="_compute_stats")
    last_score = fields.Float(compute="_compute_stats", store=True)

    @api.depends("document_ids","document_ids.doc_status","evaluation_ids","evaluation_ids.punteggio_totale")
    def _compute_stats(self):
        for rec in self:
            docs = rec.document_ids
            rec.document_count = len(docs)
            rec.evaluation_count = len(rec.evaluation_ids)
            rec.expired_doc_count = len(docs.filtered(lambda d: d.doc_status == "expired"))
            rec.expiring_doc_count = len(docs.filtered(lambda d: d.doc_status == "expiring"))
            last_eval = rec.evaluation_ids.sorted("date", reverse=True)[:1]
            rec.last_score = last_eval.punteggio_totale if last_eval else 0.0

    @api.depends("status","document_ids.doc_status","next_evaluation_date")
    def _compute_traffic_light(self):
        today = date.today()
        for rec in self:
            if rec.status in ("suspended","excluded"): rec.traffic_light = "red"; continue
            if any(d.doc_status == "expired" for d in rec.document_ids): rec.traffic_light = "red"; continue
            if any(d.doc_status == "expiring" for d in rec.document_ids): rec.traffic_light = "yellow"; continue
            if rec.next_evaluation_date and rec.next_evaluation_date < today: rec.traffic_light = "yellow"; continue
            rec.traffic_light = "green"

    def action_approve(self):
        self.write({"status": "approved"})
    def action_suspend(self):
        self.write({"status": "suspended"})
    def action_exclude(self):
        self.write({"status": "excluded"})

class ResPartnerSupplierQual(models.Model):
    _inherit = "res.partner"
    supplier_qual_id = fields.Many2one("casafolino.supplier.qualification", compute="_compute_supplier_qual", store=False, search="_search_supplier_qual_id")
    supplier_qual_status = fields.Selection(related="supplier_qual_id.status", readonly=True)
    supplier_traffic_light = fields.Selection(related="supplier_qual_id.traffic_light", readonly=True)

    def _search_supplier_qual_id(self, operator, value):
        if operator in ('=', '!=', 'in', 'not in'):
            quals = self.env["casafolino.supplier.qualification"].search([("id", operator, value)])
            return [("id", "in", quals.mapped("partner_id").ids)]
        return []

    def _compute_supplier_qual(self):
        for rec in self:
            rec.supplier_qual_id = self.env["casafolino.supplier.qualification"].search([("partner_id","=",rec.id)], limit=1)

    def action_open_qualification(self):
        self.ensure_one()
        qual = self.env["casafolino.supplier.qualification"].search([("partner_id","=",self.id)], limit=1)
        if not qual:
            qual = self.env["casafolino.supplier.qualification"].create({"partner_id": self.id})
        return {"type":"ir.actions.act_window","name":f"Qualifica {self.name}","res_model":"casafolino.supplier.qualification","res_id":qual.id,"view_mode":"form","target":"current"}
