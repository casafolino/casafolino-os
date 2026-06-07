# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CfHaccpNc(models.Model):
    _name = "cf.haccp.nc"
    _description = "Non Conformita HACCP"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(string="N° NC", required=True, copy=False, readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("cf.haccp.nc") or "NC-NUOVO")
    state = fields.Selection([
        ("open","Aperta"),("analysis","In Analisi"),("action","Azione Correttiva"),
        ("verified","Verificata"),("closed","Chiusa"),("cancelled","Annullata"),
    ], string="Stato", default="open", tracking=True, required=True)
    severity = fields.Selection([
        ("low","Bassa"),("medium","Media"),("high","Alta"),("critical","Critica"),
    ], string="Gravita", default="medium", tracking=True, required=True)
    origin = fields.Selection([
        ("ccp","CCP Fuori Limite"),("receipt","Controllo Ricezione"),
        ("manual","Segnalazione Manuale"),("audit","Audit"),("customer","Reclamo Cliente"),
    ], string="Origine", default="manual", required=True)
    sp_id = fields.Many2one("cf.haccp.sp", string="Scheda Produzione")
    ccp_id = fields.Many2one("cf.haccp.ccp", string="CCP")
    receipt_id = fields.Many2one("cf.haccp.receipt", string="Ricezione")
    product_id = fields.Many2one("product.template", string="Prodotto")
    lot_id = fields.Many2one("stock.lot", string="Lotto")
    date = fields.Datetime(string="Data", default=fields.Datetime.now)
    reported_by = fields.Many2one("res.users", string="Segnalato da", default=lambda self: self.env.user)
    assigned_to = fields.Many2one("res.users", string="Assegnato a")
    responsabile_id = fields.Many2one("res.users", string="Responsabile chiusura")
    description = fields.Text(string="Descrizione", required=True)
    corrective_action = fields.Text(string="Azione Correttiva")
    azione_correttiva = fields.Text(string="Azione Correttiva Dettagliata")
    verifica_efficacia = fields.Text(string="Verifica Efficacia")
    data_chiusura = fields.Date(string="Data Chiusura Effettiva")
    notes = fields.Text(string="Note")
    firma_digitale = fields.Binary(string="Firma Digitale")

    def action_to_analysis(self):
        self.write({"state": "analysis"})

    def action_to_corrective(self):
        self.write({"state": "action"})

    def action_to_verified(self):
        self.write({"state": "verified"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    @api.model
    def get_dashboard_data(self):
        nc_counts = {}
        for key in ("open", "analysis", "action", "verified", "closed", "cancelled"):
            nc_counts[key] = self.search_count([("state", "=", key)])

        critical_open = self.search_count([
            ("state", "not in", ("closed", "cancelled")),
            ("severity", "in", ("high", "critical")),
        ])

        calib = self.env["cf.haccp.calibration"]
        docs = self.env["cf.haccp.document"]

        today = fields.Date.today()
        temp_ko_today = self.env["cf.haccp.temperature.log"].search_count([
            ("date", "=", today), ("esito", "=", "ko")])
        ccp_ko = self.env["cf.haccp.ccp.log"].search_count([
            ("esito", "=", "fuori_limite")])
        pest_next = self.env["cf.haccp.pest.control"].search(
            [("prossima_visita", "!=", False)], limit=1, order="prossima_visita asc")

        return {
            "nc_open": nc_counts.get("open", 0),
            "nc_analysis": nc_counts.get("analysis", 0),
            "nc_action": nc_counts.get("action", 0),
            "nc_critical_open": critical_open,
            "instruments_expiring": calib.search_count([("state", "=", "expiring")]),
            "instruments_expired": calib.search_count([("state", "=", "expired")]),
            "docs_expiring": docs.search_count([("state", "=", "expiring")]),
            "docs_expired": docs.search_count([("state", "=", "expired")]),
            "temp_ko_today": temp_ko_today,
            "ccp_ko_total": ccp_ko,
            "pest_next_visit": str(pest_next.prossima_visita) if pest_next else "",
            "overall_state": (
                "red" if (critical_open > 0 or temp_ko_today > 0 or
                          calib.search_count([("state", "=", "expired")]) > 0)
                else "yellow" if (nc_counts.get("open", 0) > 0 or ccp_ko > 0 or
                                   calib.search_count([("state", "=", "expiring")]) > 0)
                else "green"
            ),
        }

    @api.model
    def dashboard_lot_search(self, query):
        query = (query or "").strip()
        if not query:
            return {
                "query": "",
                "products": [],
                "lots": [],
                "chains": [],
                "summary": {},
            }

        Product = self.env["product.product"].sudo()
        Lot = self.env["stock.lot"].sudo()
        Production = self.env["mrp.production"].sudo()

        products = Product.search([
            "|", "|",
            ("barcode", "ilike", query),
            ("default_code", "ilike", query),
            ("name", "ilike", query),
        ], limit=20)
        lots = Lot.search([
            "|", "|",
            ("name", "ilike", query),
            ("ref", "ilike", query),
            ("product_id", "in", products.ids or [0]),
        ], limit=40)
        if not lots and products:
            lots = Lot.search([("product_id", "in", products.ids)], limit=40)

        consumed_productions = Production.search([
            ("move_raw_ids.move_line_ids.lot_id", "in", lots.ids or [0])
        ], limit=80)
        produced_lots = consumed_productions.mapped("lot_producing_id")
        direct_produced_lots = Production.search([
            ("lot_producing_id", "in", lots.ids or [0])
        ], limit=80).mapped("lot_producing_id")
        all_lots = lots | produced_lots | direct_produced_lots
        all_products = products | all_lots.mapped("product_id")

        chains = [self._dashboard_lot_chain(lot) for lot in all_lots[:30]]
        chains = sorted(chains, key=self._dashboard_chain_score, reverse=True)
        delivery_names = {
            delivery["name"]
            for chain in chains
            for delivery in chain["deliveries"] + chain["impacted_deliveries"]
        }

        return {
            "query": query,
            "summary": {
                "products": len(all_products),
                "lots": len(all_lots),
                "productions": sum(
                    len(chain["productions"]) + len(chain["impacted_productions"])
                    for chain in chains
                ),
                "deliveries": len(delivery_names),
            },
            "products": [
                {
                    "id": product.id,
                    "name": product.display_name,
                    "sku": product.default_code or "",
                    "barcode": product.barcode or "",
                }
                for product in all_products[:20]
            ],
            "lots": [
                {
                    "id": lot.id,
                    "name": lot.name,
                    "product": lot.product_id.display_name,
                }
                for lot in all_lots[:40]
            ],
            "chains": chains,
        }

    def _dashboard_chain_score(self, chain):
        return (
            len(chain["raw_lots"]) * 12
            + len(chain["impacted_lots"]) * 12
            + len(chain["deliveries"]) * 6
            + len(chain["impacted_deliveries"]) * 6
            + len(chain["productions"]) * 4
            + len(chain["impacted_productions"]) * 4
            + len(chain["suppliers"]) * 2
        )

    def _dashboard_lot_chain(self, lot):
        MoveLine = self.env["stock.move.line"].sudo()
        Production = self.env["mrp.production"].sudo()

        produced = Production.search([("lot_producing_id", "=", lot.id)], limit=40)
        consumed = Production.search([
            ("move_raw_ids.move_line_ids.lot_id", "=", lot.id)
        ], limit=80)

        raw_lots = produced.mapped("move_raw_ids.move_line_ids.lot_id")
        finished_lots = consumed.mapped("lot_producing_id")
        outgoing_lots = lot | finished_lots

        incoming_lines = MoveLine.search([
            ("lot_id", "=", lot.id),
            ("picking_id.picking_type_id.code", "=", "incoming"),
        ], limit=40)
        outgoing_lines = MoveLine.search([
            ("lot_id", "in", outgoing_lots.ids or [0]),
            ("picking_id.picking_type_id.code", "=", "outgoing"),
        ], limit=160)

        direct_outgoing = outgoing_lines.filtered(lambda line: line.lot_id == lot)
        impacted_outgoing = outgoing_lines.filtered(lambda line: line.lot_id != lot)

        return {
            "id": lot.id,
            "lot": lot.name or "",
            "product": lot.product_id.display_name or "",
            "sku": lot.product_id.default_code or "",
            "barcode": lot.product_id.barcode or "",
            "role": self._dashboard_lot_role(produced, consumed),
            "suppliers": self._dashboard_pickings(incoming_lines.mapped("picking_id")),
            "productions": self._dashboard_productions(produced),
            "raw_lots": self._dashboard_lots(raw_lots),
            "deliveries": self._dashboard_deliveries(direct_outgoing.mapped("picking_id")),
            "impacted_lots": self._dashboard_lots(finished_lots),
            "impacted_productions": self._dashboard_productions(consumed),
            "impacted_deliveries": self._dashboard_deliveries(impacted_outgoing.mapped("picking_id")),
        }

    def _dashboard_lot_role(self, produced, consumed):
        if produced and consumed:
            return "Prodotto finito e materia prima"
        if produced:
            return "Prodotto finito"
        if consumed:
            return "Materia prima"
        return "Lotto movimentato"

    def _dashboard_lots(self, lots):
        return [
            {
                "id": lot.id,
                "name": lot.name or "",
                "product": lot.product_id.display_name or "",
                "sku": lot.product_id.default_code or "",
            }
            for lot in lots[:80]
        ]

    def _dashboard_productions(self, productions):
        return [
            {
                "id": production.id,
                "model": "mrp.production",
                "name": production.display_name or production.name or "",
                "product": production.product_id.display_name or "",
                "lot": production.lot_producing_id.name or "",
                "qty": production.product_qty,
                "state": production.state or "",
                "date": str(production.date_finished or production.date_start or "")[:19],
            }
            for production in productions[:80]
        ]

    def _dashboard_pickings(self, pickings):
        return [
            {
                "id": picking.id,
                "model": "stock.picking",
                "name": picking.display_name or picking.name or "",
                "partner_id": picking.partner_id.id or False,
                "partner_model": "res.partner" if picking.partner_id else "",
                "partner": picking.partner_id.display_name or "",
                "date": str(picking.date_done or picking.scheduled_date or "")[:19],
                "state": picking.state or "",
            }
            for picking in pickings[:80]
        ]

    def _dashboard_deliveries(self, pickings):
        deliveries = self._dashboard_pickings(pickings)
        seen = set()
        unique = []
        for delivery in deliveries:
            key = delivery["id"]
            if key in seen:
                continue
            seen.add(key)
            unique.append(delivery)
        return unique

    @api.model
    def dashboard_create_lot_recall(self, lot_id):
        lot = self.env["stock.lot"].sudo().browse(int(lot_id or 0)).exists()
        if not lot:
            return {"error": "Lotto non trovato."}

        Recall = self.env["cf.recall.session"].sudo()
        session = Recall.create({
            "lot_id": lot.id,
            "direction": "both",
            "session_type": "real",
            "notes": (
                "Richiamo creato dalla dashboard HACCP per il lotto %s.\n"
                "Verificare clienti, produzioni e lotti collegati prima dell'invio comunicazioni."
            ) % (lot.name or ""),
        })
        session.action_run()
        return {
            "type": "ir.actions.act_window",
            "name": "Richiamo lotti interessati",
            "res_model": "cf.recall.session",
            "res_id": session.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "current",
        }
