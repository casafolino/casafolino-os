# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CfHaccpTracciabilita(models.Model):
    _name = "cf.haccp.tracciabilita"
    _description = "Scheda Tracciabilità HACCP"
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
    lotto_mp = fields.Char(string="Lotto Materia Prima")
    lotto_pf = fields.Char(string="Lotto Prodotto Finito", required=True)
    production_id = fields.Many2one("mrp.production",
                                     string="Ordine di Produzione")
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
    date = fields.Date(string="Data", required=True, default=fields.Date.today)
    customer_count = fields.Integer(
        string="Clienti collegati",
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
    note = fields.Text(string="Note")

    @api.depends(
        "production_id",
        "production_id.product_id",
        "production_id.lot_producing_id",
        "production_id.haccp_ccp_ids.ccp_ok",
        "partner_ids",
    )
    def _compute_trace_audit(self):
        Nc = self.env["cf.haccp.nc"]
        Quarantine = self.env["cf.haccp.quarantine"]
        CcpLog = self.env["cf.haccp.ccp.log"]
        for rec in self:
            production = rec.production_id
            lot = production.lot_producing_id
            product = production.product_id.product_tmpl_id
            rec.lot_id = lot
            rec.product_id = product
            rec.customer_count = len(rec.partner_ids)

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

            if rec.quarantine_count or rec.ccp_ko_count:
                rec.trace_status = "blocked"
            elif rec.nc_count or not rec.customer_count or not production or not lot:
                rec.trace_status = "watch"
            else:
                rec.trace_status = "complete"

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
