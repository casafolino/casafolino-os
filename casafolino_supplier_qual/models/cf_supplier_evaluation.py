# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class CfSupplierEvaluation(models.Model):
    _name = "casafolino.supplier.evaluation"
    _description = "Valutazione Fornitore"
    _inherit = ["mail.thread"]
    _order = "date desc"
    _rec_name = "display_name_computed"
    display_name_computed = fields.Char(compute="_compute_display_name", store=True, compute_sudo=False)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade", tracking=True)
    date = fields.Date(default=fields.Date.today, required=True)
    evaluator_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    punteggio_qualita = fields.Selection([("1","1"),("2","2"),("3","3"),("4","4"),("5","5")], required=True)
    punteggio_puntualita = fields.Selection([("1","1"),("2","2"),("3","3"),("4","4"),("5","5")], required=True)
    punteggio_documentazione = fields.Selection([("1","1"),("2","2"),("3","3"),("4","4"),("5","5")], required=True)
    punteggio_totale = fields.Float(compute="_compute_punteggio", store=True, digits=(3,2))
    risultato = fields.Selection([("confirmed","Confermato"),("observation","In Osservazione"),("excluded","Escluso")], compute="_compute_risultato", store=True, required=True)
    note = fields.Text()

    @api.depends("partner_id","date")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name_computed = f"{rec.partner_id.name or ''} - {rec.date or ''}"

    @api.depends("punteggio_qualita","punteggio_puntualita","punteggio_documentazione")
    def _compute_punteggio(self):
        for rec in self:
            scores = [int(v) for v in [rec.punteggio_qualita,rec.punteggio_puntualita,rec.punteggio_documentazione] if v]
            rec.punteggio_totale = sum(scores)/len(scores) if scores else 0.0

    @api.depends("punteggio_totale")
    def _compute_risultato(self):
        for rec in self:
            rec.risultato = "confirmed" if rec.punteggio_totale >= 3.5 else "observation" if rec.punteggio_totale >= 2.0 else "excluded"

    def action_apply_result(self):
        for rec in self:
            qual = self.env["casafolino.supplier.qualification"].search([("partner_id","=",rec.partner_id.id)],limit=1)
            if not qual:
                qual = self.env["casafolino.supplier.qualification"].create({"partner_id":rec.partner_id.id})
            qual.last_evaluation_date = rec.date
            qual.next_evaluation_date = rec.date + relativedelta(years=1)
            qual.status = "approved" if rec.risultato=="confirmed" else "evaluation" if rec.risultato=="observation" else "excluded"
