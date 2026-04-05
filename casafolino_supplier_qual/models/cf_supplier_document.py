# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class CfSupplierDocument(models.Model):
    _name = "casafolino.supplier.document"
    _description = "Documento Fornitore"
    _inherit = ["mail.thread"]
    _order = "expiry_date asc"
    _rec_name = "name"
    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    document_type = fields.Selection([
        ("brc_ifs","BRC/IFS"),("iso_9001","ISO 9001"),("microbiological","Analisi Microbiologiche"),
        ("allergen_decl","Dichiarazione Allergeni"),("kosher","Kosher"),("halal","Halal"),
        ("bio_organic","Biologico"),("visura","Visura Camerale"),("contract","Contratto"),
        ("tech_sheet","Scheda Tecnica"),("analysis","CoA"),("other","Altro"),
    ], required=True, default="other")
    attachment_id = fields.Many2one("ir.attachment")
    has_file = fields.Boolean(compute="_compute_has_file", store=True)
    issue_date = fields.Date()
    expiry_date = fields.Date(tracking=True)
    no_expiry = fields.Boolean(default=False)
    alert_days_before = fields.Integer(default=30)
    doc_status = fields.Selection([("valid","Valido"),("expiring","In Scadenza"),("expired","Scaduto"),("no_expiry","Nessuna Scadenza"),("missing","File Mancante")], compute="_compute_doc_status", store=True, tracking=True)
    days_to_expiry = fields.Integer(compute="_compute_days_to_expiry", store=False)
    notes = fields.Text()
    reference_number = fields.Char()

    @api.depends("attachment_id")
    def _compute_has_file(self):
        for rec in self:
            rec.has_file = bool(rec.attachment_id)

    @api.depends("expiry_date", "no_expiry", "alert_days_before", "attachment_id")
    def _compute_doc_status(self):
        today = date.today()
        for rec in self:
            if rec.no_expiry:
                rec.doc_status = "no_expiry"
                continue
            if not rec.expiry_date:
                rec.doc_status = "missing" if not rec.attachment_id else "valid"
                continue
            days = (rec.expiry_date - today).days
            rec.doc_status = "expired" if days < 0 else "expiring" if days <= rec.alert_days_before else "valid"

    @api.depends("expiry_date", "no_expiry", "alert_days_before")
    def _compute_days_to_expiry(self):
        today = date.today()
        for rec in self:
            if rec.no_expiry or not rec.expiry_date:
                rec.days_to_expiry = 0
            else:
                rec.days_to_expiry = (rec.expiry_date - today).days

    @api.model
    def send_expiry_alerts(self):
        for doc in self.search([("doc_status","in",("expiring","expired")),("no_expiry","=",False)]):
            doc.message_post(body=f"Documento {doc.name} scade il {doc.expiry_date}.")

    @api.model
    def cron_expiry_reminder(self):
        """Reminder certificati fornitori in scadenza entro 60 giorni."""
        from datetime import timedelta
        today = date.today()
        cutoff = today + timedelta(days=60)

        expiring = self.search([
            ('expiry_date', '<=', str(cutoff)),
            ('expiry_date', '>=', str(today)),
            ('doc_status', '!=', 'expired'),
            ('no_expiry', '=', False),
        ])

        if not expiring:
            return

        quality = self.env['res.users'].search([
            ('email', 'ilike', 'mirabelli')
        ], limit=1)
        if not quality:
            quality = self.env['res.users'].search(
                [('login', '=', 'antonio@casafolino.com')], limit=1)

        if quality and quality.email:
            body = "<p>Certificati fornitori in scadenza entro 60 giorni:</p><ul>"
            for doc in expiring:
                days_left = (doc.expiry_date - today).days
                partner_name = doc.partner_id.name if doc.partner_id else 'N/A'
                body += "<li><b>%s</b> — %s — scade il %s (<b>%d giorni</b>)</li>" % (
                    partner_name, doc.name,
                    doc.expiry_date.strftime('%d/%m/%Y'), days_left)
            body += "</ul>"

            self.env['mail.mail'].create({
                'subject': '%d certificati fornitori in scadenza' % len(expiring),
                'email_to': quality.email,
                'body_html': body,
            }).send()
