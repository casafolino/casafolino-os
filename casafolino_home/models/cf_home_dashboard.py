# -*- coding: utf-8 -*-
from odoo import models, api
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class CfHomeDashboard(models.AbstractModel):
    """Modello astratto — fornisce solo il metodo RPC per la home dashboard."""
    _name = "cf.home.dashboard"
    _description = "CasaFolino Home Dashboard"

    @api.model
    def get_all_kpis(self):
        env = self.env
        today = date.today()
        result = {}

        # ── MAIL non lette ──────────────────────────────────────────────
        if "cf.mail.message" in env:
            result["mail_unread"] = env["cf.mail.message"].search_count([
                ("is_read", "=", False),
                ("is_archived", "=", False),
                ("folder", "=", "INBOX"),
            ])
        else:
            result["mail_unread"] = 0

        # ── CRM — deal attivi + rotting + follow-up oggi ────────────────
        if "cf.export.lead" in env:
            leads = env["cf.export.lead"].search([("active", "=", True)])
            won_lost_ids = leads.filtered(
                lambda l: l.stage_id and (l.stage_id.is_won or l.stage_id.is_lost)
            ).ids
            active_leads = leads.filtered(lambda l: l.id not in won_lost_ids)
            result["crm_active"] = len(active_leads)
            result["crm_rotting"] = len(active_leads.filtered(
                lambda l: l.rotting_state in ("danger", "dead")
            ))
            result["crm_followup_today"] = len(leads.filtered(
                lambda l: l.date_next_followup and l.date_next_followup <= today
            ))
            result["crm_forecast"] = round(sum(active_leads.mapped("forecast_value")), 2)
        else:
            result.update(crm_active=0, crm_rotting=0, crm_followup_today=0, crm_forecast=0)

        # ── HACCP — NC aperte / critiche ────────────────────────────────
        if "cf.haccp.nc" in env:
            nc = env["cf.haccp.nc"].search([("state", "not in", ["closed", "cancelled"])])
            result["haccp_nc_open"] = len(nc)
            result["haccp_nc_critical"] = len(nc.filtered(lambda n: n.severity == "critical"))
        else:
            result.update(haccp_nc_open=0, haccp_nc_critical=0)

        # ── TREASURY — saldo attuale ─────────────────────────────────────
        if "cf.treasury.snapshot" in env:
            snap = env["cf.treasury.snapshot"].search([], limit=1, order="date desc")
            result["treasury_balance"] = snap.total_balance if snap else 0.0
        elif "cf.treasury" in env:
            snap = env["cf.treasury"].search([], limit=1, order="date desc")
            result["treasury_balance"] = snap.total_balance if snap else 0.0
        else:
            result["treasury_balance"] = 0.0

        # ── KPI — vendite YTD ───────────────────────────────────────────
        if "cf.kpi.dashboard" in env:
            kpi = env["cf.kpi.dashboard"].search([], limit=1, order="date desc")
            result["kpi_ytd"] = kpi.sales_ytd if kpi else 0.0
            result["kpi_mo_open"] = kpi.mo_open if kpi else 0
        else:
            result.update(kpi_ytd=0.0, kpi_mo_open=0)

        # ── PRODUZIONE — commesse oggi ──────────────────────────────────
        if "cf.production.job" in env:
            jobs = env["cf.production.job"].search([
                ("state", "in", ["confirmed", "in_progress"]),
            ])
            result["prod_active"] = len(jobs)
            result["prod_in_progress"] = len(jobs.filtered(lambda j: j.state == "in_progress"))
        else:
            result.update(prod_active=0, prod_in_progress=0)

        # ── SCADENZE IMMINENTI (7gg) — strumenti HACCP + recall ─────────
        soon = today + timedelta(days=7)
        expiring_count = 0
        if "cf.haccp.instrument" in env:
            expiring_count += env["cf.haccp.instrument"].search_count([
                ("next_calibration", ">=", today),
                ("next_calibration", "<=", soon),
            ])
        if "cf.supplier.document" in env:
            expiring_count += env["cf.supplier.document"].search_count([
                ("expiry_date", ">=", today),
                ("expiry_date", "<=", soon),
            ])
        result["expiring_soon"] = expiring_count

        return result
