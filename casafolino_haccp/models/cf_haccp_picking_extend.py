# -*- coding: utf-8 -*-
import hashlib
import json

from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPickingHaccpExtend(models.Model):
    _inherit = "stock.picking"

    # ── STATO HACCP (computed, non cliccabile) ──
    haccp_state = fields.Selection(
        [("pending", "Da completare"), ("done", "Completato")],
        compute="_compute_haccp_state", store=True, string="Stato HACCP",
    )

    # ── ESITO GLOBALE (scelta operatore) ──
    haccp_esito = fields.Selection(
        [
            ("pending", "Da verificare"),
            ("conforme", "Conforme"),
            ("accettato_riserva", "Accettato con Riserva"),
            ("quarantena", "In Quarantena"),
            ("rifiutato", "Rifiutato"),
        ],
        string="Esito", default="pending", tracking=True,
    )

    # ── TRASPORTO ──
    haccp_trasporto_tipo = fields.Selection(
        [("refrigerato", "Refrigerato"), ("secco", "Secco"),
         ("congelato", "Congelato"), ("misto", "Misto")],
        string="Tipo Trasporto",
    )
    haccp_targa = fields.Char("Targa Veicolo")
    haccp_temp_trasporto = fields.Float("Temperatura Vano (°C)")
    haccp_temp_trasporto_ok = fields.Boolean("Temperatura OK")
    haccp_vano_pulito = fields.Selection(
        [("ok", "OK"), ("nok", "Non OK"), ("na", "N/A")], string="Pulizia Vano",
    )
    haccp_odori_anomali = fields.Boolean("Odori Anomali")
    haccp_infestanti_vano = fields.Boolean("Infestanti nel Vano")

    # ── IMBALLAGGIO ──
    haccp_imballo_esterno_ok = fields.Boolean("Imballaggio Esterno OK")
    haccp_imballo_primario_ok = fields.Boolean("Imballaggio Primario OK")
    haccp_umidita = fields.Boolean("Umidita/Condensa")
    haccp_muffe = fields.Boolean("Muffe Visibili")
    haccp_sigilli_ok = fields.Boolean("Sigilli Integri")

    # ── ETICHETTATURA ──
    haccp_etichetta_ok = fields.Boolean("Etichetta Presente e Leggibile")
    haccp_allergeni_ok = fields.Boolean("Allergeni Dichiarati")
    haccp_scadenza_ok = fields.Boolean("Scadenza/TMC OK")
    haccp_lotto_ok = fields.Boolean("N. Lotto Presente")

    # ── OPERATORI E FIRMA ──
    haccp_operatore_id = fields.Many2one(
        "res.users", "Operatore Controllo",
        default=lambda self: self.env.user,
    )
    haccp_data_controllo = fields.Datetime(
        "Data Controllo", default=fields.Datetime.now,
    )
    haccp_responsabile_id = fields.Many2one("res.users", "Responsabile Approvazione")
    haccp_data_approvazione = fields.Datetime("Data Approvazione")
    haccp_note = fields.Text("Note")
    haccp_firma_operatore = fields.Char("Hash Firma Operatore", readonly=True)
    haccp_firma_responsabile = fields.Char("Hash Firma Responsabile", readonly=True)
    haccp_stato_firma = fields.Selection(
        [("bozza", "Bozza"), ("firmato", "Firmato Operatore"), ("approvato", "Approvato")],
        default="bozza", string="Stato Firma",
    )
    haccp_data_firma = fields.Datetime("Data Firma", readonly=True)

    # ── RIGHE PER PRODOTTO ──
    haccp_line_ids = fields.One2many(
        "cf.haccp.picking.line", "picking_id", "Controlli per Prodotto",
    )

    @api.depends("haccp_esito", "haccp_line_ids.esito_riga")
    def _compute_haccp_state(self):
        for rec in self:
            if rec.picking_type_code != "incoming":
                rec.haccp_state = "done"
                continue
            if rec.haccp_esito != "pending" and all(
                l.esito_riga != "pending" for l in rec.haccp_line_ids
            ):
                rec.haccp_state = "done"
            else:
                rec.haccp_state = "pending"

    def _cf_haccp_enforce_receipt_gate(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "cf_haccp.enforce_receipt_gate", "1"
        )
        return value not in ("0", "False", "false")

    def _cf_haccp_requires_receipt_gate(self):
        self.ensure_one()
        if self.picking_type_code != "incoming":
            return False
        products = self.move_ids.mapped("product_id.product_tmpl_id")
        return any(product.is_raw_material for product in products)

    def _cf_haccp_check_receipt_gate(self):
        for rec in self:
            if not rec._cf_haccp_enforce_receipt_gate():
                continue
            if not rec._cf_haccp_requires_receipt_gate():
                continue
            missing = []
            if not rec.haccp_line_ids:
                missing.append("almeno una riga controllo prodotto")
            if rec.haccp_esito == "pending":
                missing.append("esito globale HACCP")
            if rec.haccp_stato_firma != "approvato":
                missing.append("firma e approvazione responsabile")
            if rec.haccp_esito == "accettato_riserva" and not rec.haccp_note:
                missing.append("note obbligatorie per accettazione con riserva")
            pending_lines = rec.haccp_line_ids.filtered(lambda line: line.esito_riga == "pending")
            if pending_lines:
                missing.append("esito su tutte le righe prodotto")
            blocked_lines = rec.haccp_line_ids.filtered(
                lambda line: line.esito_riga in ("quarantena", "rifiutato")
            )
            if rec.haccp_esito in ("quarantena", "rifiutato") or blocked_lines:
                raise UserError(
                    "Validazione bloccata: il controllo HACCP e in stato "
                    "quarantena/rifiutato. Aprire quarantena o NC prima di "
                    "validare la ricezione."
                )
            if missing:
                raise UserError(
                    "Validazione bloccata: completare HACCP ricezione (%s)."
                    % ", ".join(missing)
                )

    def button_validate(self):
        self._cf_haccp_check_receipt_gate()
        return super().button_validate()

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
            rec.haccp_data_controllo = fields.Datetime.now()

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
            rec.haccp_data_approvazione = fields.Datetime.now()
            rec.haccp_stato_firma = "approvato"
            if all(l.esito_riga == "conforme" for l in rec.haccp_line_ids):
                rec.haccp_esito = "conforme"

    def action_genera_pdf_ricezione(self):
        return self.env.ref(
            "casafolino_haccp.report_haccp_ricezione"
        ).report_action(self)


class CfHaccpPickingLine(models.Model):
    _name = "cf.haccp.picking.line"
    _description = "Controllo HACCP per Prodotto Ricevuto"

    picking_id = fields.Many2one("stock.picking", ondelete="cascade")
    move_id = fields.Many2one(
        "stock.move", "Movimento",
        domain="[('picking_id', '=', picking_id)]",
    )
    product_id = fields.Many2one(
        "product.product", related="move_id.product_id", store=True,
    )
    lot_id = fields.Many2one("stock.lot", "Lotto")
    qty = fields.Float("Quantita", related="move_id.quantity", store=True)
    expiry_date = fields.Date("Data Scadenza")
    temp_prodotto = fields.Float("Temperatura (°C)")
    temp_ok = fields.Boolean("Temp. OK")
    colore_ok = fields.Selection(
        [("ok", "OK"), ("anomalia", "Anomalia"), ("na", "N/A")], string="Colore",
    )
    odore_ok = fields.Selection(
        [("ok", "OK"), ("anomalia", "Anomalia"), ("na", "N/A")], string="Odore",
    )
    consistenza_ok = fields.Selection(
        [("ok", "OK"), ("anomalia", "Anomalia"), ("na", "N/A")], string="Consistenza",
    )
    campione = fields.Boolean("Campione Prelevato")
    ref_campione = fields.Char("Rif. Campione")
    esito_riga = fields.Selection(
        [
            ("pending", "Da verificare"),
            ("conforme", "Conforme"),
            ("accettato_riserva", "Con Riserva"),
            ("quarantena", "Quarantena"),
            ("rifiutato", "Rifiutato"),
        ],
        default="pending", string="Esito", required=True,
    )
    note = fields.Text("Note")
