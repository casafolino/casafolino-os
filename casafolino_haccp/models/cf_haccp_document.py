# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfHaccpDocument(models.Model):
    _name = "cf.haccp.document"
    _description = "Documento HACCP"
    _inherit = ["mail.thread"]
    _order = "date_expiry asc, name"
    _rec_name = "name"

    name = fields.Char(string="Nome Documento", required=True)
    doc_type = fields.Selection([
        ("haccp_plan","Piano HACCP"),("procedure","Procedura"),
        ("certificate","Certificato"),("supplier_doc","Documento Fornitore"),
        ("calibration","Certificato Calibrazione"),("training","Formazione"),
        ("audit","Report Audit"),("other","Altro"),
    ], string="Tipo", required=True)
    partner_id = fields.Many2one("res.partner", string="Fornitore/Ente")
    product_id = fields.Many2one("product.template", string="Prodotto")
    date_issue = fields.Date(string="Data Emissione")
    date_expiry = fields.Date(string="Data Scadenza")
    document_ref = fields.Char(string="N° Documento")
    notes = fields.Text(string="Note")
    attachment_ids = fields.Many2many("ir.attachment",
        "cf_haccp_doc_attach_rel", "doc_id", "attach_id", string="File Allegati")
    state = fields.Selection([
        ("valid","Valido"),("expiring","In Scadenza"),("expired","Scaduto"),
    ], string="Stato", compute="_compute_state", store=True)

    @api.depends("date_expiry")
    def _compute_state(self):
        today = date.today()
        for rec in self:
            if not rec.date_expiry:
                rec.state = "valid"
                continue
            days = (rec.date_expiry - today).days
            rec.state = "expired" if days < 0 else "expiring" if days <= 30 else "valid"

    @api.model
    def send_expiry_alerts(self):
        expiring = self.search([("state", "in", ["expiring", "expired"])])
        for rec in expiring:
            rec.message_post(body=f"Documento {rec.name} scade il {rec.date_expiry}.")
