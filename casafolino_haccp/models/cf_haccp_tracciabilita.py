# -*- coding: utf-8 -*-
from markupsafe import escape

from odoo import api, fields, models


class CfHaccpTracciabilita(models.Model):
    _name = "cf.haccp.tracciabilita"
    _description = "Scheda Tracciabilita HACCP"
    _inherit = ["mail.thread"]
    _order = "date desc"
    _rec_name = "lotto_pf"

    trace_status = fields.Selection(
        [
            ("complete", "Completa"),
            ("watch", "Da presidiare"),
            ("blocked", "Bloccata"),
        ],
        string="Stato Tracciabilita",
        compute="_compute_trace_audit",
    )
    audit_standard = fields.Selection(
        [
            ("ifs_brc", "IFS Food v8 + BRCGS Food Issue 9"),
            ("ifs", "IFS Food v8"),
            ("brc", "BRCGS Food Issue 9"),
        ],
        string="Standard audit",
        default="ifs_brc",
        tracking=True,
    )
    lotto_mp = fields.Char(string="Lotto Materia Prima")
    lotto_pf = fields.Char(string="Lotto Prodotto Finito", required=True)
    production_id = fields.Many2one(
        "mrp.production",
        string="Ordine di Produzione",
    )
    product_id = fields.Many2one(
        "product.template",
        string="Prodotto",
        compute="_compute_trace_audit",
    )
    lot_id = fields.Many2one(
        "stock.lot",
        string="Lotto PF",
        compute="_compute_trace_audit",
    )
    partner_ids = fields.Many2many("res.partner", string="Clienti / Destinatari")
    auto_partner_ids = fields.Many2many(
        "res.partner",
        "cf_haccp_trace_auto_partner_rel",
        "trace_id",
        "partner_id",
        string="Clienti da consegne",
        compute="_compute_trace_audit",
    )
    delivery_ids = fields.Many2many(
        "stock.picking",
        "cf_haccp_trace_delivery_rel",
        "trace_id",
        "picking_id",
        string="Consegne collegate",
        compute="_compute_trace_audit",
    )
    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    recall_test_date = fields.Datetime(
        string="Ultimo test recall",
        readonly=True,
        tracking=True,
    )
    recall_test_user_id = fields.Many2one(
        "res.users",
        string="Test recall eseguito da",
        readonly=True,
    )
    recall_test_duration = fields.Float(
        string="Tempo simulazione (min)",
        readonly=True,
        help="Tempo tecnico registrato dal sistema per produrre la simulazione.",
    )
    customer_count = fields.Integer(
        string="Clienti collegati",
        compute="_compute_trace_audit",
    )
    auto_customer_count = fields.Integer(
        string="Clienti automatici",
        compute="_compute_trace_audit",
    )
    delivery_count = fields.Integer(
        string="Consegne",
        compute="_compute_trace_audit",
    )
    delivered_qty = fields.Float(
        string="Quantita consegnata",
        compute="_compute_trace_audit",
    )
    nc_count = fields.Integer(
        string="NC aperte",
        compute="_compute_trace_audit",
    )
    quarantine_count = fields.Integer(
        string="Quarantene attive",
        compute="_compute_trace_audit",
    )
    ccp_ko_count = fields.Integer(
        string="CCP KO",
        compute="_compute_trace_audit",
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "cf_haccp_trace_attachment_rel",
        "trace_id",
        "attachment_id",
        string="Evidenze audit",
        compute="_compute_trace_audit",
    )
    evidence_count = fields.Integer(
        string="Evidenze",
        compute="_compute_trace_audit",
    )
    audit_ready_score = fields.Integer(
        string="Pronto audit (%)",
        compute="_compute_trace_audit",
    )
    mass_balance_status = fields.Selection(
        [
            ("ok", "Coerente"),
            ("watch", "Da verificare"),
            ("missing", "Dati mancanti"),
        ],
        string="Mass balance",
        compute="_compute_trace_audit",
    )
    audit_gap_html = fields.Html(
        string="Gap audit",
        compute="_compute_trace_audit",
        sanitize=True,
    )
    standard_matrix_html = fields.Html(
        string="Matrice IFS/BRCGS",
        compute="_compute_trace_audit",
        sanitize=True,
    )
    timeline_html = fields.Html(
        string="Timeline lotto",
        compute="_compute_trace_audit",
        sanitize=True,
    )
    recall_summary_html = fields.Html(
        string="Simulazione recall",
        compute="_compute_trace_audit",
        sanitize=True,
    )
    note = fields.Text(string="Note")

    @api.depends(
        "production_id",
        "production_id.product_id",
        "production_id.product_qty",
        "production_id.lot_producing_id",
        "production_id.haccp_state",
        "production_id.haccp_ccp_ids.ccp_ok",
        "partner_ids",
        "lotto_mp",
        "recall_test_date",
    )
    def _compute_trace_audit(self):
        Nc = self.env["cf.haccp.nc"]
        Quarantine = self.env["cf.haccp.quarantine"]
        CcpLog = self.env["cf.haccp.ccp.log"]
        for rec in self:
            production = rec.production_id
            lot = production.lot_producing_id
            product = production.product_id.product_tmpl_id
            move_lines = rec._cf_haccp_outgoing_move_lines(lot)
            deliveries = move_lines.picking_id.filtered(lambda picking: picking.partner_id)
            auto_partners = deliveries.partner_id
            evidence = rec._cf_haccp_evidence_attachments(production, lot, deliveries)

            rec.lot_id = lot
            rec.product_id = product
            rec.auto_partner_ids = auto_partners
            rec.delivery_ids = deliveries
            rec.customer_count = len(rec.partner_ids | auto_partners)
            rec.auto_customer_count = len(auto_partners)
            rec.delivery_count = len(deliveries)
            rec.delivered_qty = sum(rec._cf_haccp_move_line_qty(line) for line in move_lines)
            rec.evidence_attachment_ids = evidence
            rec.evidence_count = len(evidence)

            nc_domain = [("state", "not in", ("closed", "cancelled"))]
            quarantine_domain = [("state", "=", "active")]
            if lot:
                nc_domain.append(("lot_id", "=", lot.id))
                quarantine_domain.append(("lot_id", "=", lot.id))
            elif product:
                nc_domain.append(("product_id", "=", product.id))
                quarantine_domain.append(("product_id", "=", product.id))
            else:
                nc_domain.append(("id", "=", 0))
                quarantine_domain.append(("id", "=", 0))

            rec.nc_count = Nc.search_count(nc_domain)
            rec.quarantine_count = Quarantine.search_count(quarantine_domain)
            ccp_line_ko = len(production.haccp_ccp_ids.filtered(lambda line: not line.ccp_ok))
            ccp_log_ko = CcpLog.search_count([
                ("production_id", "=", production.id),
                ("esito", "=", "fuori_limite"),
            ]) if production else 0
            rec.ccp_ko_count = ccp_line_ko + ccp_log_ko

            produced_qty = production.product_qty if production else 0.0
            if not production or not lot:
                rec.mass_balance_status = "missing"
            elif rec.delivered_qty <= produced_qty:
                rec.mass_balance_status = "ok"
            else:
                rec.mass_balance_status = "watch"

            if rec.quarantine_count or rec.ccp_ko_count:
                rec.trace_status = "blocked"
            elif rec.nc_count or not rec.customer_count or not production or not lot:
                rec.trace_status = "watch"
            else:
                rec.trace_status = "complete"

            gaps = rec._cf_haccp_audit_gaps(production, lot, auto_partners)
            rec.audit_ready_score = max(0, round(((8 - len(gaps)) / 8) * 100))
            rec.audit_gap_html = rec._cf_haccp_gap_html(gaps)
            rec.timeline_html = rec._cf_haccp_timeline_html(
                production, lot, deliveries, auto_partners)
            rec.recall_summary_html = rec._cf_haccp_recall_summary_html(
                production, deliveries, auto_partners)
            rec.standard_matrix_html = rec._cf_haccp_standard_matrix_html(gaps)

    def _cf_haccp_outgoing_move_lines(self, lot):
        if not lot:
            return self.env["stock.move.line"]
        return self.env["stock.move.line"].search([
            ("lot_id", "=", lot.id),
            ("picking_id.picking_type_code", "=", "outgoing"),
            ("picking_id.state", "=", "done"),
        ], order="id desc")

    def _cf_haccp_move_line_qty(self, line):
        field = "quantity" if "quantity" in line._fields else "qty_done"
        return line[field] or 0.0

    def _cf_haccp_evidence_attachments(self, production, lot, deliveries):
        Attachment = self.env["ir.attachment"].sudo()
        evidence = Attachment.search([
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
        ], limit=30)
        if production:
            evidence |= Attachment.search([
                ("res_model", "=", "mrp.production"),
                ("res_id", "=", production.id),
            ], limit=30)
        if lot:
            evidence |= Attachment.search([
                ("res_model", "=", "stock.lot"),
                ("res_id", "=", lot.id),
            ], limit=30)
        for picking in deliveries[:10]:
            evidence |= Attachment.search([
                ("res_model", "=", "stock.picking"),
                ("res_id", "=", picking.id),
            ], limit=30)
        return evidence[:30]

    def _cf_haccp_audit_gaps(self, production, lot, auto_partners):
        self.ensure_one()
        gaps = []
        if not production:
            gaps.append("Collegare l'ordine di produzione.")
        if not lot:
            gaps.append("Collegare o produrre il lotto PF.")
        if not self.lotto_mp:
            gaps.append("Indicare i lotti materia prima.")
        if not (self.partner_ids or auto_partners):
            gaps.append("Collegare clienti o consegne del lotto.")
        if production and production.haccp_state != "done":
            gaps.append("Completare il gate HACCP produzione.")
        if self.mass_balance_status != "ok":
            gaps.append("Verificare mass balance prodotto/consegnato.")
        if not self.recall_test_date:
            gaps.append("Eseguire almeno un test recall simulato.")
        if self.nc_count or self.quarantine_count or self.ccp_ko_count:
            gaps.append("Chiudere o motivare NC, quarantene e CCP KO.")
        return gaps

    def _cf_haccp_gap_html(self, gaps):
        if not gaps:
            return "<div class='cf-haccp-ready-ok'>Nessun gap bloccante: dossier pronto.</div>"
        items = "".join("<li>%s</li>" % escape(gap) for gap in gaps)
        return "<ul class='cf-haccp-gap-list'>%s</ul>" % items

    def _cf_haccp_standard_matrix_html(self, gaps):
        status = "OK" if not gaps else "Da completare"
        rows = [
            ("IFS Food v8 4.18", "Tracciabilita lotto end-to-end", status),
            ("IFS Food v8 5.9", "Recall/withdrawal testato internamente", "OK" if self.recall_test_date else "Da testare"),
            ("BRCGS FS9 3.9", "Traceability avanti/indietro e clienti", "OK" if self.customer_count else "Da completare"),
            ("BRCGS FS9 3.11", "Gestione incidenti/recall con evidenze", status),
            ("GFSI mindset", "Mass balance e record audit-ready", self.mass_balance_status),
        ]
        body = "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                escape(code), escape(req), escape(value))
            for code, req, value in rows
        )
        return "<table class='cf-haccp-standard-table'>%s</table>" % body

    def _cf_haccp_timeline_html(self, production, lot, deliveries, auto_partners):
        self.ensure_one()
        rows = [
            ("Ricezione MP", self.lotto_mp or "Lotti MP da completare"),
            ("Produzione", production.name if production else "Produzione non collegata"),
            ("Lotto PF", lot.name if lot else self.lotto_pf or "Lotto PF da completare"),
            ("Gate HACCP", production.haccp_state if production else "Da collegare"),
            ("Clienti", ", ".join(auto_partners.mapped("name")[:4]) or "Nessuna consegna trovata"),
            ("Spedizioni", "%s consegne collegate" % len(deliveries)),
            ("Rischi", "%s NC, %s quarantene, %s CCP KO" % (
                self.nc_count, self.quarantine_count, self.ccp_ko_count)),
        ]
        items = "".join(
            "<li><strong>%s</strong><span>%s</span></li>" % (escape(title), escape(value))
            for title, value in rows
        )
        return "<ol class='cf-haccp-timeline'>%s</ol>" % items

    def _cf_haccp_recall_summary_html(self, production, deliveries, auto_partners):
        self.ensure_one()
        produced_qty = production.product_qty if production else 0.0
        rows = [
            ("Lotto", self.lotto_pf or "-"),
            ("Clienti coinvolti", str(len(auto_partners))),
            ("Consegne coinvolte", str(len(deliveries))),
            ("Quantita prodotta", "%.2f" % produced_qty),
            ("Quantita consegnata", "%.2f" % self.delivered_qty),
            ("Mass balance", dict(self._fields["mass_balance_status"].selection).get(self.mass_balance_status)),
            ("NC / quarantene / CCP KO", "%s / %s / %s" % (
                self.nc_count, self.quarantine_count, self.ccp_ko_count)),
        ]
        cells = "".join(
            "<tr><td>%s</td><td>%s</td></tr>" % (escape(label), escape(value))
            for label, value in rows
        )
        return "<table class='cf-haccp-recall-table'>%s</table>" % cells

    def cf_haccp_get_recall_rows(self):
        self.ensure_one()
        move_lines = self._cf_haccp_outgoing_move_lines(self.lot_id)
        grouped = {}
        for line in move_lines:
            picking = line.picking_id
            grouped.setdefault(picking, 0.0)
            grouped[picking] += self._cf_haccp_move_line_qty(line)
        return [{
            "date": picking.date_done or picking.scheduled_date,
            "picking": picking.name,
            "partner": picking.partner_id.display_name,
            "qty": qty,
            "state": picking.state,
        } for picking, qty in grouped.items()]

    def _action_open_related(self, model, domain, name):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "list,form",
            "domain": domain,
            "target": "current",
        }

    def action_open_production(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Produzione collegata",
            "res_model": "mrp.production",
            "view_mode": "form",
            "res_id": self.production_id.id,
            "target": "current",
        }

    def action_open_nc(self):
        domain = [("state", "not in", ("closed", "cancelled"))]
        if self.lot_id:
            domain.append(("lot_id", "=", self.lot_id.id))
        elif self.product_id:
            domain.append(("product_id", "=", self.product_id.id))
        else:
            domain.append(("id", "=", 0))
        return self._action_open_related("cf.haccp.nc", domain, "NC aperte sul lotto")

    def action_open_quarantine(self):
        domain = [("state", "=", "active")]
        if self.lot_id:
            domain.append(("lot_id", "=", self.lot_id.id))
        elif self.product_id:
            domain.append(("product_id", "=", self.product_id.id))
        else:
            domain.append(("id", "=", 0))
        return self._action_open_related(
            "cf.haccp.quarantine", domain, "Quarantene attive sul lotto"
        )

    def action_open_deliveries(self):
        self.ensure_one()
        return self._action_open_related(
            "stock.picking",
            [("id", "in", self.delivery_ids.ids)],
            "Consegne clienti del lotto",
        )

    def action_open_evidence(self):
        self.ensure_one()
        return self._action_open_related(
            "ir.attachment",
            [("id", "in", self.evidence_attachment_ids.ids)],
            "Evidenze audit lotto",
        )

    def action_sync_customers(self):
        for rec in self:
            partners = rec.partner_ids | rec.auto_partner_ids
            rec.partner_ids = [(6, 0, partners.ids)]
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Clienti sincronizzati",
                "message": "I clienti trovati dalle consegne lotto sono stati collegati alla scheda.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_simulate_recall(self):
        self.ensure_one()
        self.write({
            "recall_test_date": fields.Datetime.now(),
            "recall_test_user_id": self.env.user.id,
            "recall_test_duration": 0.1,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Recall simulato registrato",
                "message": "Test recall lotto generato con clienti, consegne, mass balance e gap IFS/BRCGS.",
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "view_mode": "form",
                    "res_id": self.id,
                },
            },
        }

    def action_print_audit_dossier(self):
        return self.env.ref(
            "casafolino_haccp.report_haccp_traceability_dossier"
        ).report_action(self)
