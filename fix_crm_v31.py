#!/usr/bin/env python3
"""
CasaFolino CRM Export — Fix Completo v3.1
Esegui sul SERVER: sudo python3 /tmp/fix_crm_v31.py
"""
import os

BASE = "/docker/enterprise18/addons/custom/casafolino_crm_export"

def w(path, content):
    full = os.path.join(BASE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  OK {path}")

print("Build CRM Export v3.1...")

# ─────────────────────────────────────────────
# models/cf_export_lead.py — aggiunge esecuzione reale step sequenze
# ─────────────────────────────────────────────
w("models/cf_export_lead.py", """\
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta
import logging
_logger = logging.getLogger(__name__)

ROTTING_THRESHOLDS = {
    "dach": 10, "france": 10, "spain": 10, "europe_other": 14,
    "gulf_halal": 14, "usa_canada": 14, "gdo": 21, "other": 14,
}


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
    description = fields.Text(string="Descrizione")


class CfExportTag(models.Model):
    _name = "cf.export.tag"
    _description = "Tag Export"
    name = fields.Char(string="Tag", required=True)
    color = fields.Integer(default=0)


class CfExportFair(models.Model):
    _name = "cf.export.fair"
    _description = "Fiera"
    _inherit = ["mail.thread"]
    _order = "date_start desc"
    _rec_name = "name"

    name = fields.Char(string="Nome Fiera", required=True)
    date_start = fields.Date(string="Data Inizio")
    date_end = fields.Date(string="Data Fine")
    location = fields.Char(string="Luogo")
    country_id = fields.Many2one("res.country", string="Paese")
    pipeline_type = fields.Selection([
        ("dach", "DACH"), ("france", "Francia"), ("spain", "Spagna"),
        ("europe_other", "Europa Altro"), ("gulf_halal", "Gulf/Halal"),
        ("usa_canada", "USA/Canada"), ("gdo", "GDO"), ("other", "Altro"),
    ], string="Mercato Target")
    lead_ids = fields.One2many("cf.export.lead", "fair_id", string="Trattative")
    lead_count = fields.Integer(string="N. Contatti", compute="_compute_lead_count")
    notes = fields.Text(string="Note")
    state = fields.Selection([
        ("planned", "Pianificata"), ("active", "In corso"),
        ("done", "Conclusa"), ("cancelled", "Annullata"),
    ], default="planned", tracking=True)

    @api.depends("lead_ids")
    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = len(rec.lead_ids)

    def action_view_leads(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Trattative Fiera",
            "res_model": "cf.export.lead",
            "view_mode": "list,form,kanban",
            "domain": [("fair_id", "=", self.id)],
            "context": {"default_fair_id": self.id},
        }


class CfExportCertification(models.Model):
    _name = "cf.export.certification"
    _description = "Certificazione Richiesta Export"
    name = fields.Char(string="Certificazione", required=True)
    code = fields.Char(string="Codice")
    color = fields.Integer(default=0)


class CfExportLead(models.Model):
    _name = "cf.export.lead"
    _description = "Trattativa Export CasaFolino"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, lead_score desc, date_last_contact desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Nome Trattativa", required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Azienda/Contatto", required=True, tracking=True)
    stage_id = fields.Many2one(
        "cf.export.stage", string="Fase", required=True, tracking=True,
        group_expand="_read_group_stage_ids",
        default=lambda self: self.env["cf.export.stage"].search([], order="sequence asc", limit=1),
    )
    priority = fields.Selection([("0", "Normale"), ("1", "Alta"), ("2", "Urgente")], default="0", tracking=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one("res.users", string="Responsabile", default=lambda self: self.env.user, tracking=True)
    kanban_state = fields.Selection([
        ("normal", "In corso"), ("done", "Pronto"), ("blocked", "Bloccato")
    ], default="normal", tracking=True)
    pipeline_type = fields.Selection([
        ("dach", "DACH"), ("france", "Francia"), ("spain", "Spagna"),
        ("europe_other", "Europa Altro"), ("gulf_halal", "Gulf/Halal"),
        ("usa_canada", "USA/Canada"), ("gdo", "GDO"), ("other", "Altro"),
    ], string="Pipeline", required=True, default="dach", tracking=True)
    country_id = fields.Many2one(related="partner_id.country_id", store=True, readonly=True)
    language = fields.Selection([
        ("it", "Italiano"), ("en", "Inglese"), ("de", "Tedesco"),
        ("fr", "Francese"), ("es", "Spagnolo"), ("ar", "Arabo"), ("other", "Altro"),
    ], string="Lingua Contatto", default="en")
    source = fields.Selection([
        ("fair", "Fiera"), ("linkedin", "LinkedIn"), ("referral", "Referral"),
        ("cold_email", "Cold Email"), ("cold_call", "Cold Call"),
        ("inbound", "Inbound"), ("marketplace", "Marketplace"), ("other", "Altro"),
    ], string="Fonte Lead", tracking=True)
    fair_id = fields.Many2one("cf.export.fair", string="Fiera", tracking=True)
    tag_ids = fields.Many2many("cf.export.tag", string="Tag")
    certifications_required = fields.Many2many("cf.export.certification", string="Certificazioni Richieste")
    contact_ids = fields.Many2many(
        "res.partner", "cf_export_lead_contact_rel", "lead_id", "partner_id",
        string="Contatti Aggiuntivi",
    )
    pricelist_id = fields.Many2one("product.pricelist", string="Listino Prezzi", tracking=True)
    expected_revenue = fields.Monetary(string="Fatturato Atteso", currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.ref("base.EUR"), readonly=True)
    lead_score = fields.Integer(string="Score", compute="_compute_lead_score", store=True)
    forecast_probability = fields.Float(string="Prob. Chiusura %", compute="_compute_lead_score", store=True)
    forecast_value = fields.Monetary(string="Forecast", compute="_compute_forecast_value", store=True, currency_field="currency_id")
    date_open = fields.Date(string="Data Apertura", default=fields.Date.today, readonly=True)
    date_last_contact = fields.Date(string="Ultimo Contatto", tracking=True)
    date_next_followup = fields.Date(string="Prossimo Follow-up", tracking=True)
    rotting_days = fields.Integer(string="Giorni Stagnazione", compute="_compute_rotting", store=True)
    rotting_state = fields.Selection([
        ("ok", "OK"), ("warning", "Attenzione"), ("danger", "Urgente"), ("dead", "Stagnante"),
    ], compute="_compute_rotting", store=True)
    sample_ids = fields.One2many("cf.export.sample", "lead_id", string="Campionature")
    sale_order_ids = fields.One2many("sale.order", "cf_export_lead_id", string="Ordini")
    sequence_log_ids = fields.One2many("cf.export.sequence.log", "lead_id", string="Sequenze Attive")
    description = fields.Html(string="Note")
    sample_count = fields.Integer(compute="_compute_counts", store=False)
    order_count = fields.Integer(compute="_compute_counts", store=False)
    order_total = fields.Monetary(compute="_compute_counts", store=False, currency_field="currency_id")

    @api.depends("sample_ids", "sale_order_ids")
    def _compute_counts(self):
        for rec in self:
            rec.sample_count = len(rec.sample_ids)
            rec.order_count = len(rec.sale_order_ids)
            rec.order_total = sum(rec.sale_order_ids.mapped("amount_total"))

    @api.depends("date_last_contact", "sample_ids", "sale_order_ids", "priority",
                 "stage_id", "date_next_followup", "kanban_state")
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
            if rec.pricelist_id: score += 5
            rec.lead_score = max(0, min(100, score))
            pt = rec.lead_score
            rec.forecast_probability = (
                10.0 if pt <= 30 else 35.0 if pt <= 60 else 65.0 if pt <= 80 else 85.0
            )

    @api.depends("expected_revenue", "forecast_probability")
    def _compute_forecast_value(self):
        for rec in self:
            rec.forecast_value = rec.expected_revenue * (rec.forecast_probability / 100.0)

    @api.depends("date_last_contact", "pipeline_type", "stage_id")
    def _compute_rotting(self):
        today = date.today()
        for rec in self:
            if rec.stage_id and (rec.stage_id.is_won or rec.stage_id.is_lost):
                rec.rotting_days = 0
                rec.rotting_state = "ok"
                continue
            threshold = ROTTING_THRESHOLDS.get(rec.pipeline_type, 14)
            days = (today - rec.date_last_contact).days if rec.date_last_contact else 0
            rec.rotting_days = days
            pct = days / threshold * 100 if threshold > 0 else 0
            rec.rotting_state = (
                "ok" if pct < 50 else "warning" if pct < 80 else "danger" if pct < 100 else "dead"
            )

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        return stages.search([], order="sequence asc")

    def action_mark_contacted(self):
        for rec in self:
            rec.date_last_contact = date.today()
            rec.message_post(body="Contatto registrato oggi.")

    def action_schedule_followup(self):
        for rec in self:
            rec.date_next_followup = date.today() + timedelta(days=7)
            rec.message_post(body="Follow-up pianificato per %s." % rec.date_next_followup)

    def action_view_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Ordini",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("cf_export_lead_id", "=", self.id)],
            "context": {"default_cf_export_lead_id": self.id},
        }

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
            ("trigger_stage_id", "=", self.stage_id.id),
            ("active", "=", True),
        ])
        for seq in sequences:
            seq.start_for_lead(self)

    @api.model
    def run_sequence_steps(self):
        """Cron giornaliero: esegue step in scadenza oggi"""
        today = date.today()
        lines = self.env["cf.export.sequence.log.line"].search([
            ("state", "=", "pending"),
            ("scheduled_date", "<=", str(today)),
        ])
        for line in lines:
            lead = line.log_id.lead_id
            step = line.step_id
            try:
                if step.action_type == "activity_call":
                    self.env["mail.activity"].create({
                        "res_model_id": self.env["ir.model"].search([("model", "=", "cf.export.lead")], limit=1).id,
                        "res_id": lead.id,
                        "activity_type_id": self.env.ref("mail.mail_activity_data_call").id,
                        "summary": step.activity_note or "Follow-up chiamata",
                        "date_deadline": str(today),
                        "user_id": lead.user_id.id or self.env.uid,
                    })
                elif step.action_type == "activity_task":
                    self.env["mail.activity"].create({
                        "res_model_id": self.env["ir.model"].search([("model", "=", "cf.export.lead")], limit=1).id,
                        "res_id": lead.id,
                        "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                        "summary": step.activity_note or "Follow-up task",
                        "date_deadline": str(today),
                        "user_id": lead.user_id.id or self.env.uid,
                    })
                elif step.action_type == "internal_notify":
                    lead.message_post(
                        body="Sequenza: %s" % (step.activity_note or step.sequence_id.name),
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                    )
                line.write({"state": "done", "done_date": str(today)})
            except Exception as e:
                _logger.warning("Errore step sequenza %s: %s", line.id, e)
        # Chiudi log completati
        logs = self.env["cf.export.sequence.log"].search([("state", "=", "running")])
        for log in logs:
            if all(l.state in ("done", "cancelled") for l in log.line_ids):
                log.state = "completed"


class CfExportSample(models.Model):
    _name = "cf.export.sample"
    _description = "Campionatura Export"
    _inherit = ["mail.thread"]
    _order = "date_sent desc"
    _rec_name = "reference"

    reference = fields.Char(
        required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.export.sample") or "CAMP-NUOVO",
    )
    lead_id = fields.Many2one("cf.export.lead", required=True, ondelete="cascade")
    partner_id = fields.Many2one(related="lead_id.partner_id", store=True, readonly=True)
    state = fields.Selection([
        ("draft", "Da Preparare"), ("prepared", "Preparata"), ("sent", "Spedita"),
        ("received", "Ricevuta"), ("feedback_ok", "Feedback Positivo"),
        ("feedback_ko", "Feedback Negativo"), ("no_feedback", "Nessun Feedback"),
    ], default="draft", tracking=True, required=True)
    product_ids = fields.Many2many("product.template", string="Prodotti", required=True)
    date_sent = fields.Date(string="Data Spedizione", tracking=True)
    date_feedback_expected = fields.Date(string="Feedback Atteso Entro")
    tracking_number = fields.Char(string="Tracking Spedizione")
    feedback_notes = fields.Text(string="Note Feedback")
    feedback_score = fields.Selection([
        ("1", "1 stella"), ("2", "2 stelle"), ("3", "3 stelle"),
        ("4", "4 stelle"), ("5", "5 stelle"),
    ], string="Valutazione")


class CfExportSequence(models.Model):
    _name = "cf.export.sequence"
    _description = "Sequenza Follow-up Export"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    trigger = fields.Selection([
        ("stage_change", "Cambio Stage"), ("manual", "Manuale"),
    ], default="stage_change")
    trigger_stage_id = fields.Many2one("cf.export.stage", string="Stage Trigger")
    step_ids = fields.One2many("cf.export.sequence.step", "sequence_id", string="Step")
    description = fields.Text(string="Descrizione")

    def start_for_lead(self, lead):
        existing = self.env["cf.export.sequence.log"].search([
            ("lead_id", "=", lead.id),
            ("sequence_id", "=", self.id),
            ("state", "=", "running"),
        ])
        if existing:
            return
        log = self.env["cf.export.sequence.log"].create({
            "lead_id": lead.id,
            "sequence_id": self.id,
            "state": "running",
            "date_started": date.today(),
        })
        for step in self.step_ids.sorted("day_offset"):
            self.env["cf.export.sequence.log.line"].create({
                "log_id": log.id,
                "step_id": step.id,
                "scheduled_date": date.today() + timedelta(days=step.day_offset),
                "state": "pending",
            })

    def action_start_manual(self):
        """Avvia manualmente per i lead selezionati dal contesto"""
        lead_ids = self.env.context.get("active_ids", [])
        leads = self.env["cf.export.lead"].browse(lead_ids)
        for lead in leads:
            self.start_for_lead(lead)


class CfExportSequenceStep(models.Model):
    _name = "cf.export.sequence.step"
    _description = "Step Sequenza"
    _order = "day_offset asc"

    sequence_id = fields.Many2one("cf.export.sequence", required=True, ondelete="cascade")
    day_offset = fields.Integer(string="Giorno +N", required=True)
    action_type = fields.Selection([
        ("email", "Email"), ("activity_call", "Chiamata"),
        ("activity_task", "Task"), ("internal_notify", "Notifica Interna"),
    ], required=True)
    activity_note = fields.Char(string="Nota / Oggetto")


class CfExportSequenceLog(models.Model):
    _name = "cf.export.sequence.log"
    _description = "Log Sequenza Attiva"
    _order = "date_started desc"

    lead_id = fields.Many2one("cf.export.lead", required=True, ondelete="cascade")
    sequence_id = fields.Many2one("cf.export.sequence", required=True)
    state = fields.Selection([
        ("running", "In esecuzione"), ("completed", "Completata"), ("cancelled", "Annullata"),
    ], default="running")
    date_started = fields.Date(string="Avviata il")
    line_ids = fields.One2many("cf.export.sequence.log.line", "log_id", string="Step")

    def action_cancel(self):
        self.write({"state": "cancelled"})
        for line in self.line_ids.filtered(lambda l: l.state == "pending"):
            line.state = "cancelled"


class CfExportSequenceLogLine(models.Model):
    _name = "cf.export.sequence.log.line"
    _description = "Step Log Sequenza"
    _order = "scheduled_date asc"

    log_id = fields.Many2one("cf.export.sequence.log", required=True, ondelete="cascade")
    step_id = fields.Many2one("cf.export.sequence.step", required=True)
    scheduled_date = fields.Date(string="Data Pianificata")
    done_date = fields.Date(string="Eseguito il")
    state = fields.Selection([
        ("pending", "In attesa"), ("done", "Eseguito"), ("cancelled", "Annullato"),
    ], default="pending")

    def action_mark_done(self):
        self.write({"state": "done", "done_date": date.today()})


class SaleOrderExportLead(models.Model):
    _inherit = "sale.order"
    cf_export_lead_id = fields.Many2one(
        "cf.export.lead", string="Trattativa Export", ondelete="set null", copy=False,
    )
""")

# ─────────────────────────────────────────────
# data/cf_export_default_sequences.xml
# Sequenze precaricate pronte all'uso
# ─────────────────────────────────────────────
w("data/cf_export_default_sequences.xml", """\
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">

    <!-- Sequenza post-campionatura: +3gg, +7gg, +14gg -->
    <record id="seq_post_campionatura" model="cf.export.sequence">
        <field name="name">Post Campionatura</field>
        <field name="trigger">stage_change</field>
        <field name="trigger_stage_id" ref="stage_sample"/>
        <field name="active">True</field>
        <field name="description">Avviata automaticamente quando la trattativa entra in Campionatura Inviata</field>
    </record>
    <record id="seq_step_camp_1" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_post_campionatura"/>
        <field name="day_offset">3</field>
        <field name="action_type">activity_task</field>
        <field name="activity_note">Conferma ricezione campionatura</field>
    </record>
    <record id="seq_step_camp_2" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_post_campionatura"/>
        <field name="day_offset">7</field>
        <field name="action_type">activity_call</field>
        <field name="activity_note">Chiamata feedback campionatura</field>
    </record>
    <record id="seq_step_camp_3" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_post_campionatura"/>
        <field name="day_offset">14</field>
        <field name="action_type">activity_task</field>
        <field name="activity_note">Follow-up finale — invia offerta se feedback positivo</field>
    </record>

    <!-- Sequenza post-offerta: +3gg, +10gg, +20gg -->
    <record id="seq_post_offerta" model="cf.export.sequence">
        <field name="name">Post Offerta</field>
        <field name="trigger">stage_change</field>
        <field name="trigger_stage_id" ref="stage_offer"/>
        <field name="active">True</field>
        <field name="description">Avviata automaticamente quando l offerta viene inviata</field>
    </record>
    <record id="seq_step_off_1" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_post_offerta"/>
        <field name="day_offset">3</field>
        <field name="action_type">activity_task</field>
        <field name="activity_note">Conferma ricezione offerta</field>
    </record>
    <record id="seq_step_off_2" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_post_offerta"/>
        <field name="day_offset">10</field>
        <field name="action_type">activity_call</field>
        <field name="activity_note">Chiamata chiarimenti offerta</field>
    </record>
    <record id="seq_step_off_3" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_post_offerta"/>
        <field name="day_offset">20</field>
        <field name="action_type">activity_call</field>
        <field name="activity_note">Decisione finale — negoziazione o chiusura</field>
    </record>

    <!-- Sequenza riattivazione cliente inattivo -->
    <record id="seq_reattivazione" model="cf.export.sequence">
        <field name="name">Riattivazione Cliente Attivo</field>
        <field name="trigger">manual</field>
        <field name="active">True</field>
        <field name="description">Da avviare manualmente su clienti attivi che non ordinano da tempo</field>
    </record>
    <record id="seq_step_reat_1" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_reattivazione"/>
        <field name="day_offset">0</field>
        <field name="action_type">internal_notify</field>
        <field name="activity_note">Sequenza riattivazione avviata</field>
    </record>
    <record id="seq_step_reat_2" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_reattivazione"/>
        <field name="day_offset">5</field>
        <field name="action_type">activity_call</field>
        <field name="activity_note">Chiamata di ricontatto — novita prodotti</field>
    </record>
    <record id="seq_step_reat_3" model="cf.export.sequence.step">
        <field name="sequence_id" ref="seq_reattivazione"/>
        <field name="day_offset">15</field>
        <field name="action_type">activity_task</field>
        <field name="activity_note">Invia nuova campionatura o promo stagionale</field>
    </record>

</odoo>
""")

# ─────────────────────────────────────────────
# data/cf_export_cron.xml — cron giornaliero sequenze
# File XML con <odoo/> vuoto se cron non funziona,
# ma in Odoo 18 i cron vanno definiti con ir.cron direttamente
# ─────────────────────────────────────────────
w("data/cf_export_cron.xml", """\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="ir_cron_cf_export_sequences" model="ir.cron">
        <field name="name">CRM Export: Esegui Step Sequenze</field>
        <field name="model_id" search="[('model','=','cf.export.lead')]"/>
        <field name="state">code</field>
        <field name="code">model.run_sequence_steps()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">days</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>
</odoo>
""")

# ─────────────────────────────────────────────
# views/cf_export_views.xml — COMPLETO con tutte le viste
# ─────────────────────────────────────────────
w("views/cf_export_views.xml", """\
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- ACTIONS -->
    <record id="action_cf_export_lead" model="ir.actions.act_window">
        <field name="name">Pipeline Export</field>
        <field name="res_model">cf.export.lead</field>
        <field name="view_mode">kanban,list,form</field>
        <field name="context">{"search_default_my_leads": 1}</field>
    </record>
    <record id="action_cf_export_lead_dach" model="ir.actions.act_window">
        <field name="name">Pipeline DACH / Europa</field>
        <field name="res_model">cf.export.lead</field>
        <field name="view_mode">kanban,list,form</field>
        <field name="domain">[("pipeline_type","in",["dach","france","spain","europe_other"])]</field>
    </record>
    <record id="action_cf_export_lead_gulf" model="ir.actions.act_window">
        <field name="name">Pipeline Gulf / Halal</field>
        <field name="res_model">cf.export.lead</field>
        <field name="view_mode">kanban,list,form</field>
        <field name="domain">[("pipeline_type","=","gulf_halal")]</field>
    </record>
    <record id="action_cf_export_lead_gdo" model="ir.actions.act_window">
        <field name="name">Pipeline GDO</field>
        <field name="res_model">cf.export.lead</field>
        <field name="view_mode">kanban,list,form</field>
        <field name="domain">[("pipeline_type","=","gdo")]</field>
    </record>
    <record id="action_cf_export_sample" model="ir.actions.act_window">
        <field name="name">Campionature</field>
        <field name="res_model">cf.export.sample</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_export_fair" model="ir.actions.act_window">
        <field name="name">Fiere</field>
        <field name="res_model">cf.export.fair</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_export_sequence" model="ir.actions.act_window">
        <field name="name">Sequenze Follow-up</field>
        <field name="res_model">cf.export.sequence</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_export_sequence_log" model="ir.actions.act_window">
        <field name="name">Log Sequenze</field>
        <field name="res_model">cf.export.sequence.log</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_export_stages" model="ir.actions.act_window">
        <field name="name">Fasi Pipeline</field>
        <field name="res_model">cf.export.stage</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_export_cert" model="ir.actions.act_window">
        <field name="name">Certificazioni</field>
        <field name="res_model">cf.export.certification</field>
        <field name="view_mode">list,form</field>
    </record>
    <record id="action_cf_export_tag" model="ir.actions.act_window">
        <field name="name">Tag Export</field>
        <field name="res_model">cf.export.tag</field>
        <field name="view_mode">list,form</field>
    </record>

    <!-- LEAD KANBAN -->
    <record id="view_cf_export_lead_kanban" model="ir.ui.view">
        <field name="name">cf.export.lead.kanban</field>
        <field name="model">cf.export.lead</field>
        <field name="arch" type="xml">
            <kanban default_group_by="stage_id" quick_create="false" group_create="false">
                <field name="name"/>
                <field name="partner_id"/>
                <field name="stage_id"/>
                <field name="lead_score"/>
                <field name="forecast_value"/>
                <field name="expected_revenue"/>
                <field name="rotting_state"/>
                <field name="priority"/>
                <field name="user_id"/>
                <field name="kanban_state"/>
                <field name="pipeline_type"/>
                <field name="sample_count"/>
                <field name="date_next_followup"/>
                <templates>
                    <t t-name="card">
                        <div class="oe_kanban_card">
                            <div class="oe_kanban_content">
                                <div class="o_kanban_record_top">
                                    <div class="o_kanban_record_headings">
                                        <strong class="o_kanban_record_title">
                                            <field name="name"/>
                                        </strong>
                                        <span class="o_kanban_record_subtitle">
                                            <field name="partner_id"/>
                                        </span>
                                    </div>
                                    <field name="priority" widget="priority"/>
                                </div>
                                <div class="o_kanban_record_body">
                                    <span class="badge bg-secondary">
                                        <field name="pipeline_type"/>
                                    </span>
                                    <t t-if="record.sample_count.raw_value > 0">
                                        <span class="badge bg-info ms-1">
                                            <field name="sample_count"/> camp.
                                        </span>
                                    </t>
                                    <t t-if="record.rotting_state.raw_value == 'dead'">
                                        <span class="badge bg-danger ms-1">Stagnante</span>
                                    </t>
                                    <t t-elif="record.rotting_state.raw_value == 'danger'">
                                        <span class="badge bg-warning ms-1">Urgente</span>
                                    </t>
                                    <t t-if="record.date_next_followup.raw_value">
                                        <div class="mt-1 small text-muted">
                                            Follow-up: <field name="date_next_followup"/>
                                        </div>
                                    </t>
                                </div>
                                <div class="o_kanban_record_bottom">
                                    <div class="oe_kanban_bottom_left">
                                        <span class="fw-bold">
                                            <field name="forecast_value" widget="monetary"/>
                                        </span>
                                        <span class="text-muted ms-1 small">
                                            (<field name="lead_score"/>pts)
                                        </span>
                                    </div>
                                    <div class="oe_kanban_bottom_right">
                                        <field name="kanban_state" widget="state_selection"/>
                                        <field name="user_id" widget="many2one_avatar_user"/>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>

    <!-- LEAD LIST -->
    <record id="view_cf_export_lead_list" model="ir.ui.view">
        <field name="name">cf.export.lead.list</field>
        <field name="model">cf.export.lead</field>
        <field name="arch" type="xml">
            <list string="Pipeline Export"
                  decoration-danger="rotting_state in ('danger','dead')"
                  decoration-warning="rotting_state == 'warning'">
                <field name="name"/>
                <field name="partner_id"/>
                <field name="pipeline_type"/>
                <field name="stage_id"/>
                <field name="expected_revenue" sum="Totale Atteso"/>
                <field name="forecast_value" sum="Totale Forecast"/>
                <field name="lead_score"/>
                <field name="date_last_contact"/>
                <field name="date_next_followup"/>
                <field name="rotting_state" widget="badge"
                    decoration-success="rotting_state == 'ok'"
                    decoration-warning="rotting_state == 'warning'"
                    decoration-danger="rotting_state in ('danger','dead')"/>
                <field name="user_id" widget="many2one_avatar_user"/>
                <field name="kanban_state" widget="state_selection"/>
            </list>
        </field>
    </record>

    <!-- LEAD SEARCH -->
    <record id="view_cf_export_lead_search" model="ir.ui.view">
        <field name="name">cf.export.lead.search</field>
        <field name="model">cf.export.lead</field>
        <field name="arch" type="xml">
            <search string="Cerca Trattative">
                <field name="name"/>
                <field name="partner_id"/>
                <field name="user_id"/>
                <field name="tag_ids"/>
                <separator/>
                <filter string="Le mie trattative" name="my_leads" domain="[('user_id','=',uid)]"/>
                <filter string="Follow-up oggi" name="followup_today"
                    domain="[('date_next_followup','&lt;=',context_today().strftime('%Y-%m-%d'))]"/>
                <filter string="Stagnanti" name="rotting"
                    domain="[('rotting_state','in',['danger','dead'])]"/>
                <filter string="Alta Priorita" name="high_priority"
                    domain="[('priority','in',['1','2'])]"/>
                <separator/>
                <filter string="DACH / Europa" name="pipe_dach"
                    domain="[('pipeline_type','in',['dach','france','spain','europe_other'])]"/>
                <filter string="Gulf / Halal" name="pipe_gulf"
                    domain="[('pipeline_type','=','gulf_halal')]"/>
                <filter string="GDO" name="pipe_gdo"
                    domain="[('pipeline_type','=','gdo')]"/>
                <filter string="USA / Canada" name="pipe_usa"
                    domain="[('pipeline_type','=','usa_canada')]"/>
                <separator/>
                <filter string="Archiviate" name="inactive" domain="[('active','=',False)]"/>
                <group expand="0" string="Raggruppa per">
                    <filter string="Fase" name="group_stage" context="{'group_by':'stage_id'}"/>
                    <filter string="Pipeline" name="group_pipeline" context="{'group_by':'pipeline_type'}"/>
                    <filter string="Responsabile" name="group_user" context="{'group_by':'user_id'}"/>
                    <filter string="Fiera" name="group_fair" context="{'group_by':'fair_id'}"/>
                    <filter string="Fonte" name="group_source" context="{'group_by':'source'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- LEAD FORM -->
    <record id="view_cf_export_lead_form" model="ir.ui.view">
        <field name="name">cf.export.lead.form</field>
        <field name="model">cf.export.lead</field>
        <field name="arch" type="xml">
            <form string="Trattativa Export">
                <header>
                    <button name="action_mark_contacted" string="Registra Contatto"
                        type="object" class="btn-secondary"/>
                    <button name="action_schedule_followup" string="Follow-up +7gg"
                        type="object" class="btn-secondary"/>
                    <field name="stage_id" widget="statusbar" options="{'clickable': '1'}"/>
                </header>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button name="%(action_cf_export_sample)d" type="action"
                            class="oe_stat_button" icon="fa-flask">
                            <field name="sample_count" widget="statinfo" string="Campionature"/>
                        </button>
                        <button name="action_view_orders" type="object"
                            class="oe_stat_button" icon="fa-shopping-cart">
                            <field name="order_count" widget="statinfo" string="Ordini"/>
                        </button>
                    </div>
                    <div class="oe_title">
                        <h1><field name="name" placeholder="Nome trattativa..."/></h1>
                        <h3><field name="partner_id" placeholder="Azienda/Contatto"/></h3>
                    </div>
                    <group>
                        <group string="Classificazione">
                            <field name="pipeline_type"/>
                            <field name="source"/>
                            <field name="fair_id" invisible="source != 'fair'"/>
                            <field name="language"/>
                            <field name="user_id" widget="many2one_avatar_user"/>
                            <field name="priority" widget="priority"/>
                        </group>
                        <group string="Certificazioni e Tag">
                            <field name="certifications_required" widget="many2many_tags"/>
                            <field name="tag_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
                            <field name="pricelist_id"/>
                        </group>
                    </group>
                    <group>
                        <group string="Forecast">
                            <field name="expected_revenue"/>
                            <field name="lead_score" widget="percentpie"/>
                            <field name="forecast_probability"/>
                            <field name="forecast_value"/>
                            <field name="order_total" string="Ordinato Totale"/>
                        </group>
                        <group string="Follow-up">
                            <field name="date_last_contact"/>
                            <field name="date_next_followup"/>
                            <field name="rotting_days"/>
                            <field name="rotting_state" widget="badge"
                                decoration-success="rotting_state == 'ok'"
                                decoration-warning="rotting_state == 'warning'"
                                decoration-danger="rotting_state in ('danger','dead')"/>
                            <field name="kanban_state" widget="state_selection"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Campionature" name="samples">
                            <field name="sample_ids">
                                <list editable="bottom">
                                    <field name="reference" readonly="1"/>
                                    <field name="product_ids" widget="many2many_tags"/>
                                    <field name="date_sent"/>
                                    <field name="date_feedback_expected"/>
                                    <field name="tracking_number"/>
                                    <field name="state" widget="badge"/>
                                    <field name="feedback_score"/>
                                    <field name="feedback_notes"/>
                                </list>
                            </field>
                        </page>
                        <page string="Ordini" name="orders">
                            <field name="sale_order_ids">
                                <list>
                                    <field name="name"/>
                                    <field name="date_order"/>
                                    <field name="amount_total" sum="Totale"/>
                                    <field name="state" widget="badge"/>
                                </list>
                            </field>
                        </page>
                        <page string="Contatti" name="contacts">
                            <field name="contact_ids">
                                <list>
                                    <field name="name"/>
                                    <field name="function"/>
                                    <field name="email"/>
                                    <field name="phone"/>
                                </list>
                            </field>
                        </page>
                        <page string="Sequenze Attive" name="sequences">
                            <field name="sequence_log_ids">
                                <list>
                                    <field name="sequence_id"/>
                                    <field name="state" widget="badge"
                                        decoration-success="state == 'completed'"
                                        decoration-info="state == 'running'"
                                        decoration-muted="state == 'cancelled'"/>
                                    <field name="date_started"/>
                                </list>
                            </field>
                        </page>
                        <page string="Note" name="notes">
                            <field name="description"/>
                        </page>
                    </notebook>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <!-- CAMPIONATURE LIST + FORM -->
    <record id="view_cf_export_sample_list" model="ir.ui.view">
        <field name="name">cf.export.sample.list</field>
        <field name="model">cf.export.sample</field>
        <field name="arch" type="xml">
            <list string="Campionature"
                  decoration-success="state == 'feedback_ok'"
                  decoration-danger="state == 'feedback_ko'">
                <field name="reference"/>
                <field name="partner_id"/>
                <field name="product_ids" widget="many2many_tags"/>
                <field name="date_sent"/>
                <field name="date_feedback_expected"/>
                <field name="tracking_number"/>
                <field name="state" widget="badge"/>
                <field name="feedback_score"/>
            </list>
        </field>
    </record>
    <record id="view_cf_export_sample_form" model="ir.ui.view">
        <field name="name">cf.export.sample.form</field>
        <field name="model">cf.export.sample</field>
        <field name="arch" type="xml">
            <form string="Campionatura">
                <header>
                    <field name="state" widget="statusbar" options="{'clickable': '1'}"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="reference" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="lead_id"/>
                            <field name="partner_id" readonly="1"/>
                            <field name="product_ids" widget="many2many_tags"/>
                        </group>
                        <group>
                            <field name="date_sent"/>
                            <field name="date_feedback_expected"/>
                            <field name="tracking_number"/>
                            <field name="feedback_score"/>
                        </group>
                    </group>
                    <group string="Feedback">
                        <field name="feedback_notes" nolabel="1"/>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <!-- FIERE LIST + FORM -->
    <record id="view_cf_export_fair_list" model="ir.ui.view">
        <field name="name">cf.export.fair.list</field>
        <field name="model">cf.export.fair</field>
        <field name="arch" type="xml">
            <list string="Fiere">
                <field name="name"/>
                <field name="date_start"/>
                <field name="date_end"/>
                <field name="location"/>
                <field name="country_id"/>
                <field name="pipeline_type"/>
                <field name="lead_count"/>
                <field name="state" widget="badge"
                    decoration-info="state == 'planned'"
                    decoration-success="state == 'active'"
                    decoration-muted="state in ('done','cancelled')"/>
            </list>
        </field>
    </record>
    <record id="view_cf_export_fair_form" model="ir.ui.view">
        <field name="name">cf.export.fair.form</field>
        <field name="model">cf.export.fair</field>
        <field name="arch" type="xml">
            <form string="Fiera">
                <header>
                    <button name="action_view_leads" string="Vedi Trattative"
                        type="object" class="btn-primary"
                        invisible="lead_count == 0"/>
                    <field name="state" widget="statusbar" options="{'clickable': '1'}"/>
                </header>
                <sheet>
                    <div class="oe_button_box">
                        <button name="action_view_leads" type="object"
                            class="oe_stat_button" icon="fa-handshake-o">
                            <field name="lead_count" widget="statinfo" string="Trattative"/>
                        </button>
                    </div>
                    <div class="oe_title">
                        <h1><field name="name"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="date_start"/>
                            <field name="date_end"/>
                            <field name="location"/>
                            <field name="country_id"/>
                        </group>
                        <group>
                            <field name="pipeline_type"/>
                        </group>
                    </group>
                    <field name="notes" placeholder="Note sulla fiera..."/>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <!-- SEQUENZE LIST + FORM -->
    <record id="view_cf_export_sequence_list" model="ir.ui.view">
        <field name="name">cf.export.sequence.list</field>
        <field name="model">cf.export.sequence</field>
        <field name="arch" type="xml">
            <list string="Sequenze Follow-up">
                <field name="name"/>
                <field name="trigger"/>
                <field name="trigger_stage_id"/>
                <field name="active" widget="boolean_toggle"/>
            </list>
        </field>
    </record>
    <record id="view_cf_export_sequence_form" model="ir.ui.view">
        <field name="name">cf.export.sequence.form</field>
        <field name="model">cf.export.sequence</field>
        <field name="arch" type="xml">
            <form string="Sequenza Follow-up">
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name"/></h1>
                    </div>
                    <group>
                        <field name="trigger"/>
                        <field name="trigger_stage_id" invisible="trigger != 'stage_change'"/>
                        <field name="active"/>
                        <field name="description"/>
                    </group>
                    <field name="step_ids">
                        <list editable="bottom">
                            <field name="day_offset"/>
                            <field name="action_type"/>
                            <field name="activity_note"/>
                        </list>
                    </field>
                </sheet>
            </form>
        </field>
    </record>

    <!-- LOG SEQUENZE LIST + FORM -->
    <record id="view_cf_export_seq_log_list" model="ir.ui.view">
        <field name="name">cf.export.sequence.log.list</field>
        <field name="model">cf.export.sequence.log</field>
        <field name="arch" type="xml">
            <list string="Log Sequenze">
                <field name="lead_id"/>
                <field name="sequence_id"/>
                <field name="state" widget="badge"
                    decoration-info="state == 'running'"
                    decoration-success="state == 'completed'"
                    decoration-muted="state == 'cancelled'"/>
                <field name="date_started"/>
            </list>
        </field>
    </record>
    <record id="view_cf_export_seq_log_form" model="ir.ui.view">
        <field name="name">cf.export.sequence.log.form</field>
        <field name="model">cf.export.sequence.log</field>
        <field name="arch" type="xml">
            <form string="Log Sequenza">
                <header>
                    <button name="action_cancel" string="Annulla Sequenza"
                        type="object" class="btn-danger"
                        invisible="state != 'running'"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <group>
                        <field name="lead_id"/>
                        <field name="sequence_id"/>
                        <field name="date_started"/>
                    </group>
                    <field name="line_ids">
                        <list editable="bottom">
                            <field name="step_id"/>
                            <field name="scheduled_date"/>
                            <field name="done_date"/>
                            <field name="state" widget="badge"
                                decoration-warning="state == 'pending'"
                                decoration-success="state == 'done'"
                                decoration-muted="state == 'cancelled'"/>
                            <button name="action_mark_done" string="Fatto"
                                type="object" icon="fa-check"
                                invisible="state != 'pending'"/>
                        </list>
                    </field>
                </sheet>
            </form>
        </field>
    </record>

    <!-- CERTIFICAZIONI LIST -->
    <record id="view_cf_export_cert_list" model="ir.ui.view">
        <field name="name">cf.export.certification.list</field>
        <field name="model">cf.export.certification</field>
        <field name="arch" type="xml">
            <list string="Certificazioni" editable="bottom">
                <field name="name"/>
                <field name="code"/>
                <field name="color" widget="color_picker"/>
            </list>
        </field>
    </record>

</odoo>
""")

# ─────────────────────────────────────────────
# views/menus.xml
# ─────────────────────────────────────────────
w("views/menus.xml", """\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_export_root" name="Export CRM" sequence="20"
        web_icon="casafolino_crm_export,static/description/icon.png"/>
    <menuitem id="menu_cf_export_pipeline" name="Tutte le Pipeline"
        parent="menu_cf_export_root" action="action_cf_export_lead" sequence="1"/>
    <menuitem id="menu_cf_export_dach" name="DACH / Europa"
        parent="menu_cf_export_root" action="action_cf_export_lead_dach" sequence="2"/>
    <menuitem id="menu_cf_export_gulf" name="Gulf / Halal"
        parent="menu_cf_export_root" action="action_cf_export_lead_gulf" sequence="3"/>
    <menuitem id="menu_cf_export_gdo" name="GDO"
        parent="menu_cf_export_root" action="action_cf_export_lead_gdo" sequence="4"/>
    <menuitem id="menu_cf_export_samples" name="Campionature"
        parent="menu_cf_export_root" action="action_cf_export_sample" sequence="10"/>
    <menuitem id="menu_cf_export_fairs" name="Fiere"
        parent="menu_cf_export_root" action="action_cf_export_fair" sequence="11"/>
    <menuitem id="menu_cf_export_config" name="Configurazione"
        parent="menu_cf_export_root" sequence="99" groups="base.group_system"/>
    <menuitem id="menu_cf_export_stages" name="Fasi Pipeline"
        parent="menu_cf_export_config" action="action_cf_export_stages" sequence="1"/>
    <menuitem id="menu_cf_export_sequences" name="Sequenze Follow-up"
        parent="menu_cf_export_config" action="action_cf_export_sequence" sequence="2"/>
    <menuitem id="menu_cf_export_seq_log" name="Log Sequenze"
        parent="menu_cf_export_config" action="action_cf_export_sequence_log" sequence="3"/>
    <menuitem id="menu_cf_export_certs" name="Certificazioni"
        parent="menu_cf_export_config" action="action_cf_export_cert" sequence="4"/>
    <menuitem id="menu_cf_export_tags" name="Tag"
        parent="menu_cf_export_config" action="action_cf_export_tag" sequence="5"/>
</odoo>
""")

# ─────────────────────────────────────────────
# __manifest__.py aggiornato con nuovi data file
# ─────────────────────────────────────────────
w("__manifest__.py", """\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino CRM Export",
    "version": "18.0.3.1.0",
    "category": "Sales/CRM",
    "summary": "CRM Export B2B — Pipeline, Scoring, Sequenze, Fiere, Campionature",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_export_stages.xml",
        "data/cf_export_cron.xml",
        "views/cf_export_views.xml",
        "views/menus.xml",
        "data/cf_export_default_sequences.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
""")

print("\nBuild completato!")
print("\nEsegui sul server:")
print("sudo docker exec odoo-app odoo -d folinofood_stage -u casafolino_crm_export --stop-after-init --no-http 2>&1 | tail -20 && sudo docker restart odoo-app && sudo docker exec -it odoo-db psql -U odoo -d folinofood_stage -c \"DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';\"")
