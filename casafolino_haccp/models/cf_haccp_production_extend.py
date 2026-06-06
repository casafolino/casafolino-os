# -*- coding: utf-8 -*-
import hashlib
import json

from odoo import models, fields, api
from odoo.exceptions import UserError


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
    cf_skip_quality_checks_retroactive = fields.Boolean(
        string="Salta controlli qualita retroattivi",
        help="Campo di compatibilita per view storiche di produzione presenti nel DB.",
    )
    cf_skip_quality_checks_note = fields.Text(
        string="Motivo salto controlli qualita",
        help="Campo di compatibilita per view storiche di produzione presenti nel DB.",
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
    haccp_traceability_ids = fields.One2many(
        "cf.haccp.tracciabilita",
        "production_id",
        string="Schede Tracciabilita",
    )
    haccp_traceability_count = fields.Integer(
        string="Schede Tracciabilita",
        compute="_compute_haccp_traceability_count",
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

    @api.depends("haccp_traceability_ids")
    def _compute_haccp_traceability_count(self):
        for rec in self:
            rec.haccp_traceability_count = len(rec.haccp_traceability_ids)

    def _cf_haccp_raw_lot_names(self):
        self.ensure_one()
        lots = self.move_raw_ids.move_line_ids.lot_id
        if not lots and "lot_ids" in self.move_raw_ids._fields:
            lots = self.move_raw_ids.lot_ids
        return ", ".join(lots.mapped("name"))

    def _cf_haccp_enforce_production_gate(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "cf_haccp.enforce_production_gate", "1"
        )
        return value not in ("0", "False", "false")

    def _cf_haccp_check_production_gate(self):
        required_checks = [
            ("haccp_area_ok", "area sanificata"),
            ("haccp_attrezzature_ok", "attrezzature calibrate"),
            ("haccp_igiene_ok", "igiene personale"),
            ("haccp_dpi_ok", "DPI"),
            ("haccp_allergeni_ok", "cambio linea/allergeni"),
            ("haccp_curva_ok", "curva temperaggio"),
            ("haccp_peso_ok", "peso porzione"),
            ("haccp_metalli_ok", "rilevatore metalli"),
            ("haccp_imballo_ok", "imballaggio"),
            ("haccp_etichetta_ok", "etichetta"),
            ("haccp_lotto_etichetta_ok", "lotto/scadenza su etichetta"),
        ]
        for rec in self:
            if not rec._cf_haccp_enforce_production_gate():
                continue
            missing = [label for field, label in required_checks if not rec[field]]
            failed_ccp = rec.haccp_ccp_ids.filtered(lambda line: not line.ccp_ok)
            if rec.haccp_esito != "conforme":
                missing.append("esito produzione conforme")
            if rec.haccp_stato_firma != "approvato":
                missing.append("firma e approvazione responsabile qualita")
            if not rec.haccp_ccp_ids:
                missing.append("almeno un CCP monitorato")
            if failed_ccp:
                raise UserError(
                    "Chiusura produzione bloccata: esistono CCP non conformi. "
                    "Registrare azione correttiva o bloccare il lotto."
                )
            if missing:
                raise UserError(
                    "Chiusura produzione bloccata: completare HACCP produzione (%s)."
                    % ", ".join(missing)
                )

    def button_mark_done(self):
        self._cf_haccp_check_production_gate()
        return super().button_mark_done()

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
            if not rec.haccp_firma_operatore:
                raise UserError("Firma operatore richiesta prima dell'approvazione HACCP.")
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

    def action_haccp_open_traceability(self):
        self.ensure_one()
        trace = self.haccp_traceability_ids[:1]
        if not trace:
            trace = self.env["cf.haccp.tracciabilita"].create({
                "production_id": self.id,
                "lotto_pf": self.lot_producing_id.name or self.name,
                "lotto_mp": self._cf_haccp_raw_lot_names(),
                "date": fields.Date.today(),
            })
        return {
            "type": "ir.actions.act_window",
            "name": "Tracciabilita lotto",
            "res_model": "cf.haccp.tracciabilita",
            "view_mode": "form",
            "res_id": trace.id,
            "target": "current",
            "context": {
                "default_production_id": self.id,
                "default_lotto_pf": self.lot_producing_id.name or self.name,
                "default_lotto_mp": self._cf_haccp_raw_lot_names(),
            },
        }


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
