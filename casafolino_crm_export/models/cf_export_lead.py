# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
import logging
_logger = logging.getLogger(__name__)

ROTTING_THRESHOLDS = {
    "dach": 10, "france": 10, "spain": 10, "europe_other": 14,
    "gulf_halal": 14, "usa_canada": 14, "gdo": 21, "other": 14,
}

class CfExportLead(models.Model):
    _name = "cf.export.lead"
    _description = "Trattativa Export CasaFolino"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, lead_score desc, date_last_contact desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Nome Trattativa", required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Azienda/Contatto", required=True, tracking=True)
    stage_id = fields.Many2one("cf.export.stage", string="Fase", required=True, tracking=True,
        group_expand="_read_group_stage_ids",
        default=lambda self: self.env["cf.export.stage"].search([], order="sequence asc", limit=1))
    priority = fields.Selection([("0","Normale"),("1","Alta"),("2","Urgente")], default="0", tracking=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one("res.users", string="Responsabile", default=lambda self: self.env.user)
    pipeline_type = fields.Selection([
        ("dach","DACH"),("france","Francia"),("spain","Spagna"),
        ("europe_other","Europa Altro"),("gulf_halal","Gulf/Halal"),
        ("usa_canada","USA/Canada"),("gdo","GDO"),("other","Altro"),
    ], string="Pipeline", required=True, default="dach", tracking=True)
    country_id = fields.Many2one(related="partner_id.country_id", store=True, readonly=True)
    expected_revenue = fields.Monetary(string="Fatturato Atteso", currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"), readonly=True)
    date_open = fields.Date(string="Data Apertura", default=fields.Date.today, readonly=True)
    date_last_contact = fields.Date(string="Ultimo Contatto", tracking=True)
    date_next_followup = fields.Date(string="Prossimo Follow-up", tracking=True)
    lead_score = fields.Integer(string="Score", compute="_compute_lead_score", store=True)
    forecast_probability = fields.Float(string="Prob. Chiusura %", compute="_compute_lead_score", store=True)
    forecast_value = fields.Monetary(string="Forecast", compute="_compute_forecast_value", store=True, currency_field="currency_id")
    rotting_days = fields.Integer(string="Giorni Stagnazione", compute="_compute_rotting", store=True)
    rotting_state = fields.Selection([("ok","OK"),("warning","Attenzione"),("danger","Urgente"),("dead","Stagnante")],
        compute="_compute_rotting", store=True)
    sample_ids = fields.One2many("cf.export.sample", "lead_id", string="Campionature")
    sale_order_ids = fields.One2many("sale.order", "cf_export_lead_id", string="Ordini")
    tag_ids = fields.Many2many("cf.export.tag", string="Tag")
    kanban_state = fields.Selection([("normal","In corso"),("done","Pronto"),("blocked","Bloccato")], default="normal")
    description = fields.Html(string="Note")

    @api.depends("date_last_contact","sample_ids","sale_order_ids","priority","stage_id","date_next_followup")
    def _compute_lead_score(self):
        today = date.today()
        for rec in self:
            score = 0
            if rec.date_last_contact:
                days = (today - rec.date_last_contact).days
                if days <= 7: score += 20
                elif days > 14: score -= 20
            if rec.sample_ids: score += 15
            if any(s.state == "feedback_ok" for s in rec.sample_ids): score += 20
            if rec.sale_order_ids: score += 25
            if rec.stage_id and rec.stage_id.sequence >= 4: score += 10
            if rec.priority == "1": score += 5
            elif rec.priority == "2": score += 10
            if not rec.date_next_followup: score -= 10
            if rec.kanban_state == "blocked": score -= 15
            rec.lead_score = max(0, min(100, score))
            pt = rec.lead_score
            rec.forecast_probability = 10.0 if pt <= 30 else 35.0 if pt <= 60 else 65.0 if pt <= 80 else 85.0

    @api.depends("expected_revenue","forecast_probability")
    def _compute_forecast_value(self):
        for rec in self:
            rec.forecast_value = rec.expected_revenue * (rec.forecast_probability / 100.0)

    @api.depends("date_last_contact","pipeline_type","stage_id")
    def _compute_rotting(self):
        today = date.today()
        for rec in self:
            if rec.stage_id and (rec.stage_id.is_won or rec.stage_id.is_lost):
                rec.rotting_days = 0; rec.rotting_state = "ok"; continue
            threshold = ROTTING_THRESHOLDS.get(rec.pipeline_type, 14)
            days = (today - rec.date_last_contact).days if rec.date_last_contact else 0
            rec.rotting_days = days
            pct = days / threshold * 100 if threshold > 0 else 0
            rec.rotting_state = "ok" if pct < 50 else "warning" if pct < 80 else "danger" if pct < 100 else "dead"

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        return stages.search([], order="sequence asc")

    def action_mark_contacted(self):
        for rec in self:
            rec.date_last_contact = date.today()
            rec.message_post(body="Contatto registrato oggi.")

    def write(self, vals):
        old_stages = {rec.id: rec.stage_id.id for rec in self}
        result = super().write(vals)
        if "stage_id" in vals:
            for rec in self:
                if rec.stage_id.id != old_stages.get(rec.id):
                    rec._trigger_stage_sequences()
        return result

    def _trigger_stage_sequences(self):
        sequences = self.env["cf.export.sequence"].search([
            ("trigger_stage_id","=",self.stage_id.id),("active","=",True)])
        for seq in sequences:
            seq.start_for_lead(self)

    @api.model
    def send_weekly_report(self):
        template = self.env.ref("casafolino_crm_export.email_template_weekly_report", raise_if_not_found=False)
        if template:
            admin = self.env.ref("base.user_admin")
            if admin and admin.email:
                template.send_mail(admin.id, force_send=True)

class CfExportStage(models.Model):
    _name = "cf.export.stage"
    _description = "Fase Pipeline Export"
    _order = "sequence asc, id asc"
    name = fields.Char(string="Nome Fase", required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(default=False)
    is_won = fields.Boolean(default=False)
    is_lost = fields.Boolean(default=False)
    color = fields.Integer(default=0)

class CfExportTag(models.Model):
    _name = "cf.export.tag"
    _description = "Tag Export"
    name = fields.Char(string="Tag", required=True)
    color = fields.Integer(default=0)

class CfExportSample(models.Model):
    _name = "cf.export.sample"
    _description = "Campionatura Export"
    _inherit = ["mail.thread"]
    _order = "date_sent desc"
    _rec_name = "reference"
    reference = fields.Char(required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.export.sample") or "CAMP-NUOVO")
    lead_id = fields.Many2one("cf.export.lead", required=True, ondelete="cascade")
    partner_id = fields.Many2one(related="lead_id.partner_id", store=True, readonly=True)
    state = fields.Selection([
        ("draft","Da Preparare"),("prepared","Preparata"),("sent","Spedita"),
        ("received","Ricevuta"),("feedback_ok","Feedback Positivo"),
        ("feedback_ko","Feedback Negativo"),("no_feedback","Nessun Feedback"),
    ], default="draft", tracking=True, required=True)
    product_ids = fields.Many2many("product.template", string="Prodotti", required=True)
    date_sent = fields.Date(string="Data Spedizione", tracking=True)
    feedback_notes = fields.Text(string="Note Feedback")

class CfExportSequence(models.Model):
    _name = "cf.export.sequence"
    _description = "Sequenza Follow-up Export"
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    trigger = fields.Selection([("stage_change","Cambio Stage"),("manual","Manuale")], default="stage_change")
    trigger_stage_id = fields.Many2one("cf.export.stage", string="Stage Trigger")
    step_ids = fields.One2many("cf.export.sequence.step", "sequence_id", string="Step")

    def start_for_lead(self, lead):
        existing = self.env["cf.export.sequence.log"].search([
            ("lead_id","=",lead.id),("sequence_id","=",self.id),("state","=","running")])
        if existing: return
        log = self.env["cf.export.sequence.log"].create({
            "lead_id": lead.id, "sequence_id": self.id,
            "state": "running", "date_started": date.today()})
        from datetime import timedelta
        for step in self.step_ids.sorted("day_offset"):
            self.env["cf.export.sequence.log.line"].create({
                "log_id": log.id, "step_id": step.id,
                "scheduled_date": date.today() + timedelta(days=step.day_offset),
                "state": "pending"})

class CfExportSequenceStep(models.Model):
    _name = "cf.export.sequence.step"
    _description = "Step Sequenza"
    sequence_id = fields.Many2one("cf.export.sequence", required=True, ondelete="cascade")
    day_offset = fields.Integer(string="Giorno N", required=True)
    action_type = fields.Selection([
        ("email","Email"),("activity_call","Chiamata"),
        ("activity_task","Task"),("internal_notify","Notifica"),
    ], required=True)
    activity_note = fields.Char(string="Nota")

class CfExportSequenceLog(models.Model):
    _name = "cf.export.sequence.log"
    _description = "Log Sequenza"
    lead_id = fields.Many2one("cf.export.lead", required=True, ondelete="cascade")
    sequence_id = fields.Many2one("cf.export.sequence", required=True)
    state = fields.Selection([("running","In esecuzione"),("completed","Completata"),("cancelled","Annullata")], default="running")
    date_started = fields.Date(string="Avviata il")
    line_ids = fields.One2many("cf.export.sequence.log.line", "log_id")

class CfExportSequenceLogLine(models.Model):
    _name = "cf.export.sequence.log.line"
    _description = "Step Log Sequenza"
    log_id = fields.Many2one("cf.export.sequence.log", required=True, ondelete="cascade")
    step_id = fields.Many2one("cf.export.sequence.step", required=True)
    scheduled_date = fields.Date(string="Data Pianificata")
    state = fields.Selection([("pending","In attesa"),("done","Eseguito"),("cancelled","Annullato")], default="pending")

class SaleOrderExportLead(models.Model):
    _inherit = "sale.order"
    cf_export_lead_id = fields.Many2one("cf.export.lead", string="Trattativa Export", ondelete="set null", copy=False)
