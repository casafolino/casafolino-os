# -*- coding: utf-8 -*-
import hashlib
import json

from markupsafe import Markup

from odoo import models, fields, api, _


class MrpProductionHaccpExtend(models.Model):
    _inherit = "mrp.production"

    # ── STATO HACCP ──
    haccp_state = fields.Selection(
        [("pending", "Da completare"), ("done", "Completato")],
        compute="_compute_haccp_state", store=True, string="Stato HACCP",
    )
    haccp_esito = fields.Selection(
        [
            ("pending", "Da verificare"),
            ("conforme", "Conforme"),
            ("non_conforme", "Non Conforme"),
            ("bloccato", "Bloccato"),
            ("attesa_analisi", "In Attesa Analisi"),
        ],
        default="pending", string="Esito Produzione", tracking=True,
    )

    # ── PREREQUISITI ──
    haccp_area_ok = fields.Boolean("Area Sanificata")
    haccp_ref_sanificazione = fields.Char("Rif. Registro Sanificazione")
    haccp_attrezzature_ok = fields.Boolean("Attrezzature Calibrate")
    haccp_ref_calibrazione = fields.Char("Rif. Ultima Calibrazione")
    haccp_igiene_ok = fields.Boolean("Igiene Personale Verificata")
    haccp_dpi_ok = fields.Boolean("DPI Indossati Correttamente")
    haccp_allergeni_ok = fields.Boolean("Cambio Linea Allergeni Verificato")

    # ── CCP LINES ──
    haccp_ccp_ids = fields.One2many(
        "cf.haccp.ccp.line", "production_id", "Monitoraggio CCP",
    )

    # ── TEMPERATURE CIOCCOLATO/CREME ──
    haccp_temp_fusione = fields.Float("Temperatura Fusione (°C)")
    haccp_temp_t1 = fields.Float("Temperaggio T1 (°C)")
    haccp_temp_t2 = fields.Float("Temperaggio T2 (°C)")
    haccp_temp_t3 = fields.Float("Temperaggio T3 (°C)")
    haccp_curva_ok = fields.Boolean("Curva Temperaggio OK")

    # ── CONTROLLI IN PROCESSO ──
    haccp_peso_ok = fields.Boolean("Peso Porzione OK")
    haccp_peso_medio = fields.Float("Peso Medio (g)")
    haccp_metalli_ok = fields.Boolean("Rilevatore Metalli OK")
    haccp_campione = fields.Boolean("Campione Trattenuto")
    haccp_ref_campione = fields.Char("Rif. Campione")

    # ── CONFEZIONAMENTO ──
    haccp_imballo_ok = fields.Boolean("Imballaggio Approvato")
    haccp_etichetta_ok = fields.Boolean("Etichetta Corretta")
    haccp_lotto_etichetta_ok = fields.Boolean("Lotto/Scadenza su Etichetta")

    # ── RESA ──
    haccp_resa = fields.Float("Resa (%)", compute="_compute_resa", store=True)
    haccp_scarti = fields.Float("Scarti (kg)")
    haccp_note = fields.Text("Note")

    # ── FIRMA ──
    haccp_operatore_id = fields.Many2one(
        "res.users", "Operatore",
        default=lambda self: self.env.user,
    )
    haccp_responsabile_id = fields.Many2one("res.users", "Responsabile Qualita")
    haccp_firma_operatore = fields.Char(readonly=True)
    haccp_firma_responsabile = fields.Char(readonly=True)
    haccp_stato_firma = fields.Selection(
        [("bozza", "Bozza"), ("firmato", "Firmato"), ("approvato", "Approvato")],
        default="bozza", string="Stato Firma",
    )
    haccp_data_firma = fields.Datetime("Data Firma", readonly=True)
    haccp_data_approvazione = fields.Datetime("Data Approvazione", readonly=True)
    cf_skip_quality_checks_retroactive = fields.Boolean(
        "Salta controlli qualita retroattivi",
        tracking=True,
        help=(
            "Da usare solo per registrare produzioni gia eseguite nel passato, "
            "quando i controlli qualita sono stati gestiti fuori dalla linea di produzione."
        ),
    )
    cf_skip_quality_checks_note = fields.Text(
        "Motivo salto controlli qualita",
        tracking=True,
    )

    @api.depends("haccp_esito")
    def _compute_haccp_state(self):
        for rec in self:
            rec.haccp_state = "done" if rec.haccp_esito != "pending" else "pending"

    @api.depends("product_qty", "haccp_scarti")
    def _compute_resa(self):
        for rec in self:
            if rec.product_qty:
                rec.haccp_resa = (
                    (rec.product_qty - rec.haccp_scarti) / rec.product_qty
                ) * 100
            else:
                rec.haccp_resa = 0.0

    def action_haccp_firma_operatore(self):
        for rec in self:
            payload = json.dumps({
                "model": rec._name, "id": rec.id,
                "user": rec.env.uid, "ts": str(fields.Datetime.now()),
                "db": rec.env.cr.dbname,
            }, sort_keys=True)
            rec.haccp_firma_operatore = hashlib.sha256(payload.encode()).hexdigest()
            rec.haccp_stato_firma = "firmato"
            rec.haccp_data_firma = fields.Datetime.now()

    def action_haccp_approva(self):
        for rec in self:
            payload = json.dumps({
                "model": rec._name, "id": rec.id,
                "user": rec.env.uid, "ts": str(fields.Datetime.now()),
                "firma_op": rec.haccp_firma_operatore or "",
                "db": rec.env.cr.dbname,
            }, sort_keys=True)
            rec.haccp_firma_responsabile = hashlib.sha256(payload.encode()).hexdigest()
            rec.haccp_responsabile_id = rec.env.uid
            rec.haccp_stato_firma = "approvato"
            rec.haccp_data_approvazione = fields.Datetime.now()

    def action_genera_pdf_produzione(self):
        return self.env.ref(
            "casafolino_haccp.report_haccp_produzione"
        ).report_action(self)

    def _cf_quality_skip_note(self):
        self.ensure_one()
        return (
            self.cf_skip_quality_checks_note
            or _("Produzione retroattiva: controlli qualita saltati su richiesta.")
        )

    def _cf_mark_quality_checks_skipped(self):
        for rec in self:
            if not rec.cf_skip_quality_checks_retroactive:
                continue
            pending_checks = rec.check_ids.filtered(lambda check: check.quality_state == "none")
            if not pending_checks:
                continue

            note = rec._cf_quality_skip_note()
            for check in pending_checks:
                check.do_pass()
                if "additional_note" in check._fields:
                    check.additional_note = note
                elif "note" in check._fields:
                    check.note = note

            rec.message_post(
                body=Markup(
                    "<p><strong>%s</strong></p><p>%s</p>"
                ) % (
                    _("Controlli qualita saltati per registrazione retroattiva."),
                    note,
                )
            )
        return True

    def pre_button_mark_done(self):
        self._cf_mark_quality_checks_skipped()
        return super().pre_button_mark_done()

    def _check_qc_status(self):
        if self and all(rec.cf_skip_quality_checks_retroactive for rec in self):
            return True
        return super()._check_qc_status()


class CfHaccpCcpLine(models.Model):
    _name = "cf.haccp.ccp.line"
    _description = "Monitoraggio CCP Produzione"

    production_id = fields.Many2one("mrp.production", ondelete="cascade")
    ccp_id = fields.Char("CCP ID", help="Es: CCP-01-TEMP")
    descrizione = fields.Char("Descrizione")
    tipo_pericolo = fields.Selection(
        [
            ("biologico", "Biologico"),
            ("chimico", "Chimico"),
            ("fisico", "Fisico"),
            ("allergene", "Allergene"),
        ],
        string="Tipo Pericolo",
    )
    limite_critico = fields.Char("Limite Critico", help="Es: >72°C per 15 sec")
    valore_misurato = fields.Float("Valore Misurato")
    unita = fields.Selection(
        [("C", "°C"), ("pH", "pH"), ("min", "min"), ("bar", "bar"), ("ppm", "ppm")],
        string="Unita",
    )
    ora_misura = fields.Datetime("Ora Misurazione", default=fields.Datetime.now)
    ccp_ok = fields.Boolean("Nei Limiti")
    azione_correttiva = fields.Text("Azione Correttiva")


class MrpWorkorderQualitySkip(models.Model):
    _inherit = "mrp.workorder"

    def _cf_workorders_to_skip_quality_checks(self):
        return self.filtered(
            lambda wo: wo.production_id.cf_skip_quality_checks_retroactive
        )

    def _cf_mark_workorder_quality_checks_skipped(self):
        for workorder in self._cf_workorders_to_skip_quality_checks():
            workorder.production_id._cf_mark_quality_checks_skipped()
            pending_checks = workorder.check_ids.filtered(
                lambda check: check.quality_state == "none"
            )
            if not pending_checks:
                continue

            note = workorder.production_id._cf_quality_skip_note()
            for check in pending_checks:
                check.do_pass()
                if "additional_note" in check._fields:
                    check.additional_note = note
                elif "note" in check._fields:
                    check.note = note
        return True

    def verify_quality_checks(self):
        skipped = self._cf_workorders_to_skip_quality_checks()
        skipped._cf_mark_workorder_quality_checks_skipped()
        remaining = self - skipped
        if remaining:
            return super(MrpWorkorderQualitySkip, remaining).verify_quality_checks()
        return True

    def pre_record_production(self):
        skipped = self._cf_workorders_to_skip_quality_checks()
        skipped._cf_mark_workorder_quality_checks_skipped()
        remaining = self - skipped
        if remaining:
            return super(MrpWorkorderQualitySkip, remaining).pre_record_production()
        return True

    def get_summary_data(self):
        if self._cf_workorders_to_skip_quality_checks():
            self._cf_mark_workorder_quality_checks_skipped()
        return super().get_summary_data()
