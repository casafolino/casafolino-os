# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class CfSupplierEvaluation(models.Model):
    _name = "casafolino.supplier.evaluation"
    _description = "Valutazione Fornitore"
    _inherit = ["mail.thread"]
    _order = "date desc"
    _rec_name = "display_name_computed"

    display_name_computed = fields.Char(compute="_compute_display_name", store=True)
    partner_id = fields.Many2one("res.partner", string="Fornitore", required=True,
        ondelete="cascade", domain="[('supplier_rank','>',0)]", tracking=True)
    date = fields.Date(string="Data", default=fields.Date.today, required=True)
    evaluator_id = fields.Many2one("res.users", string="Valutatore", default=lambda self: self.env.user)
    punteggio_qualita = fields.Selection([
        ("1","1 - Insufficiente"),("2","2 - Scarso"),("3","3 - Sufficiente"),
        ("4","4 - Buono"),("5","5 - Eccellente"),
    ], string="Qualita Prodotti", required=True)
    punteggio_puntualita = fields.Selection([
        ("1","1 - Insufficiente"),("2","2 - Scarso"),("3","3 - Sufficiente"),
        ("4","4 - Buono"),("5","5 - Eccellente"),
    ], string="Puntualita Consegne", required=True)
    punteggio_documentazione = fields.Selection([
        ("1","1 - Insufficiente"),("2","2 - Scarso"),("3","3 - Sufficiente"),
        ("4","4 - Buono"),("5","5 - Eccellente"),
    ], string="Documentazione", required=True)
    punteggio_totale = fields.Float(compute="_compute_punteggio", store=True, digits=(3,2))
    risultato = fields.Selection([
        ("confirmed","Confermato"),("observation","In Osservazione"),("excluded","Escluso"),
    ], string="Risultato", required=True, compute="_compute_risultato", store=True)
    note = fields.Text(string="Note")
    corrective_actions = fields.Text(string="Azioni Correttive")

    @api.depends("partner_id","date")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name_computed = f"{rec.partner_id.name or ''} — {rec.date or ''}"

    @api.depends("punteggio_qualita","punteggio_puntualita","punteggio_documentazione")
    def _compute_punteggio(self):
        for rec in self:
            scores = [int(v) for v in [rec.punteggio_qualita, rec.punteggio_puntualita, rec.punteggio_documentazione] if v]
            rec.punteggio_totale = sum(scores) / len(scores) if scores else 0.0

    @api.depends("punteggio_totale")
    def _compute_risultato(self):
        for rec in self:
            pt = rec.punteggio_totale
            rec.risultato = "confirmed" if pt >= 3.5 else "observation" if pt >= 2.0 else "excluded"

    def action_apply_result(self):
        for rec in self:
            qual = self.env["casafolino.supplier.qualification"].search(
                [("partner_id","=",rec.partner_id.id)], limit=1)
            if not qual:
                qual = self.env["casafolino.supplier.qualification"].create({"partner_id": rec.partner_id.id})
            qual.last_evaluation_date = rec.date
            qual.next_evaluation_date = rec.date + relativedelta(years=1)
            if rec.risultato == "confirmed": qual.status = "approved"
            elif rec.risultato == "observation": qual.status = "evaluation"
            elif rec.risultato == "excluded": qual.status = "excluded"
