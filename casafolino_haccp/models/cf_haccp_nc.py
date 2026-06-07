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
            return {"query": "", "products": [], "lots": [], "traces": [], "summary": {}}

        Product = self.env["product.product"].sudo()
        Lot = self.env["stock.lot"].sudo()
        MoveLine = self.env["stock.move.line"].sudo()
        Production = self.env["mrp.production"].sudo()
        Trace = self.env["cf.haccp.tracciabilita"].sudo()

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
        all_lots = lots | produced_lots
        all_products = products | all_lots.mapped("product_id")

        traces = Trace.browse()
        for lot in all_lots[:40]:
            trace = Trace.search([("lot_id", "=", lot.id)], limit=1)
            if not trace:
                trace = Trace.create({"lot_id": lot.id, "lotto_pf": lot.name})
            traces |= trace

        outgoing_lines = MoveLine.search([
            ("lot_id", "in", all_lots.ids or [0]),
            ("picking_id.picking_type_id.code", "=", "outgoing"),
        ], limit=120)

        return {
            "query": query,
            "summary": {
                "products": len(all_products),
                "lots": len(all_lots),
                "traces": len(traces),
                "deliveries": len(outgoing_lines.mapped("picking_id")),
            },
            "products": [
                {
                    "id": product.id,
                    "name": product.display_name,
                    "sku": product.default_code or "",
                    "barcode": product.barcode or "",
                    "url": "/odoo/product.product/%s" % product.id,
                }
                for product in all_products[:20]
            ],
            "lots": [
                {
                    "id": lot.id,
                    "name": lot.name,
                    "product": lot.product_id.display_name,
                    "url": "/odoo/stock.lot/%s" % lot.id,
                    "trace_url": "/odoo/cf.haccp.tracciabilita/%s" % (
                        Trace.search([("lot_id", "=", lot.id)], limit=1).id
                    ),
                }
                for lot in all_lots[:40]
            ],
            "traces": [
                {
                    "id": trace.id,
                    "name": trace.display_name,
                    "lot": trace.lot_id.name if trace.lot_id else trace.lotto_pf,
                    "url": "/odoo/cf.haccp.tracciabilita/%s" % trace.id,
                }
                for trace in traces[:40]
            ],
        }
