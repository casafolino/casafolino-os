# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

DOCUMENT_TYPES = [
    ("brc_ifs","Certificato BRC/IFS"),("iso_9001","Certificato ISO 9001"),
    ("microbiological","Analisi Microbiologiche"),("allergen_decl","Dichiarazione Allergeni"),
    ("kosher","Certificato Kosher"),("halal","Certificato Halal"),
    ("bio_organic","Certificato Biologico"),("visura","Visura Camerale"),
    ("contract","Contratto Fornitura"),("tech_sheet","Scheda Tecnica MP"),
    ("analysis","Certificato Analisi / CoA"),("other","Altro"),
]

class CfSupplierDocument(models.Model):
    _name = "casafolino.supplier.document"
    _description = "Documento Fornitore Qualificato"
    _inherit = ["mail.thread"]
    _order = "expiry_date asc, partner_id"
    _rec_name = "name"

    name = fields.Char(string="Nome Documento", required=True)
    partner_id = fields.Many2one("res.partner", string="Fornitore", required=True,
        ondelete="cascade", domain="[('supplier_rank','>',0)]")
    document_type = fields.Selection(DOCUMENT_TYPES, string="Tipo", required=True, default="other")
    attachment_id = fields.Many2one("ir.attachment", string="File Allegato")
    has_file = fields.Boolean(compute="_compute_has_file", store=True)
    issue_date = fields.Date(string="Data Emissione")
    expiry_date = fields.Date(string="Data Scadenza", tracking=True)
    no_expiry = fields.Boolean(string="Nessuna Scadenza", default=False)
    alert_days_before = fields.Integer(string="Alert Giorni Prima", default=30)
    doc_status = fields.Selection([
        ("valid","Valido"),("expiring","In Scadenza"),("expired","Scaduto"),
        ("no_expiry","Nessuna Scadenza"),("missing","File Mancante"),
    ], string="Status", compute="_compute_doc_status", store=True, tracking=True)
    days_to_expiry = fields.Integer(compute="_compute_doc_status", store=False)
    notes = fields.Text(string="Note")
    reference_number = fields.Char(string="N° Riferimento")

    @api.depends("attachment_id")
    def _compute_has_file(self):
        for rec in self:
            rec.has_file = bool(rec.attachment_id)

    @api.depends("expiry_date","no_expiry","alert_days_before","attachment_id")
    def _compute_doc_status(self):
        today = date.today()
        for rec in self:
            if rec.no_expiry:
                rec.doc_status = "no_expiry"; rec.days_to_expiry = 0; continue
            if not rec.expiry_date:
                rec.doc_status = "missing" if not rec.attachment_id else "valid"
                rec.days_to_expiry = 0; continue
            days = (rec.expiry_date - today).days
            rec.days_to_expiry = days
            rec.doc_status = "expired" if days < 0 else "expiring" if days <= rec.alert_days_before else "valid"

    @api.model
    def send_expiry_alerts(self):
        expiring = self.search([("doc_status","in",("expiring","expired")),("no_expiry","=",False)])
        for doc in expiring:
            doc.message_post(body=f"Documento {doc.name} scade il {doc.expiry_date}.")
