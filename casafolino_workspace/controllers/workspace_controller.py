# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WorkspaceDashboardController(http.Controller):

    @http.route("/workspace/dashboard/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def dashboard_data(self, **kw):
        try:
            data = request.env["workspace.dashboard"].get_dashboard_data()
            return data
        except Exception as e:
            _logger.error("Workspace dashboard error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Lead section routes ────────────────────────────

    @http.route("/workspace/lead/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def lead_data(self, **kw):
        try:
            return request.env["workspace.lead"].get_lead_data()
        except Exception as e:
            _logger.error("Lead data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/lead/list", type="json", auth="user",
                methods=["POST"], csrf=False)
    def lead_list(self, filter_key="tutti", **kw):
        try:
            return request.env["workspace.lead"].get_lead_list(filter_key)
        except Exception as e:
            _logger.error("Lead list error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/lead/pipeline", type="json", auth="user",
                methods=["POST"], csrf=False)
    def lead_pipeline(self, **kw):
        try:
            return request.env["workspace.lead"].get_lead_pipeline()
        except Exception as e:
            _logger.error("Lead pipeline error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/lead/markets", type="json", auth="user",
                methods=["POST"], csrf=False)
    def lead_markets(self, **kw):
        try:
            return request.env["workspace.lead"].get_lead_markets()
        except Exception as e:
            _logger.error("Lead markets error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/lead/detail", type="json", auth="user",
                methods=["POST"], csrf=False)
    def lead_detail(self, lead_id=0, **kw):
        try:
            return request.env["workspace.lead"].get_lead_detail(int(lead_id))
        except Exception as e:
            _logger.error("Lead detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Project section routes ─────────────────────────

    @http.route("/workspace/proj/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def proj_data(self, **kw):
        try:
            return request.env["workspace.project"].get_proj_data()
        except Exception as e:
            _logger.error("Proj data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/proj/list", type="json", auth="user",
                methods=["POST"], csrf=False)
    def proj_list(self, filter_key="tutti", **kw):
        try:
            return request.env["workspace.project"].get_proj_list(filter_key)
        except Exception as e:
            _logger.error("Proj list error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/proj/kanban", type="json", auth="user",
                methods=["POST"], csrf=False)
    def proj_kanban(self, **kw):
        try:
            return request.env["workspace.project"].get_proj_kanban()
        except Exception as e:
            _logger.error("Proj kanban error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/proj/timeline", type="json", auth="user",
                methods=["POST"], csrf=False)
    def proj_timeline(self, **kw):
        try:
            return request.env["workspace.project"].get_proj_timeline()
        except Exception as e:
            _logger.error("Proj timeline error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/proj/detail", type="json", auth="user",
                methods=["POST"], csrf=False)
    def proj_detail(self, proj_id=0, **kw):
        try:
            return request.env["workspace.project"].get_proj_detail(int(proj_id))
        except Exception as e:
            _logger.error("Proj detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Mail section routes ────────────────────────────

    @http.route("/workspace/mail/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def mail_data(self, **kw):
        try:
            return request.env["workspace.mail"].get_mail_data()
        except Exception as e:
            _logger.error("Mail data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/mail/inbox", type="json", auth="user",
                methods=["POST"], csrf=False)
    def mail_inbox(self, filter_key="tutte", **kw):
        try:
            return request.env["workspace.mail"].get_inbox(filter_key)
        except Exception as e:
            _logger.error("Mail inbox error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/mail/threads", type="json", auth="user",
                methods=["POST"], csrf=False)
    def mail_threads(self, **kw):
        try:
            return request.env["workspace.mail"].get_threads()
        except Exception as e:
            _logger.error("Mail threads error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/mail/triage", type="json", auth="user",
                methods=["POST"], csrf=False)
    def mail_triage(self, **kw):
        try:
            return request.env["workspace.mail"].get_triage()
        except Exception as e:
            _logger.error("Mail triage error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/mail/detail", type="json", auth="user",
                methods=["POST"], csrf=False)
    def mail_detail(self, mail_id=0, **kw):
        try:
            return request.env["workspace.mail"].get_mail_detail(int(mail_id))
        except Exception as e:
            _logger.error("Mail detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/mail/action", type="json", auth="user",
                methods=["POST"], csrf=False)
    def mail_action(self, mail_id=0, action="", params=None, **kw):
        try:
            return request.env["workspace.mail"].execute_action(int(mail_id), action, params)
        except Exception as e:
            _logger.error("Mail action error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Calendar section routes ────────────────────────

    @http.route("/workspace/cal/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cal_data(self, **kw):
        try:
            return request.env["workspace.calendar"].get_cal_data()
        except Exception as e:
            _logger.error("Cal data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/cal/day", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cal_day(self, date=None, **kw):
        try:
            return request.env["workspace.calendar"].get_day_events(date)
        except Exception as e:
            _logger.error("Cal day error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/cal/week", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cal_week(self, week_start=None, **kw):
        try:
            return request.env["workspace.calendar"].get_week_events(week_start)
        except Exception as e:
            _logger.error("Cal week error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/cal/month", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cal_month(self, month_start=None, **kw):
        try:
            return request.env["workspace.calendar"].get_month_events(month_start)
        except Exception as e:
            _logger.error("Cal month error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/cal/detail", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cal_detail(self, event_id=0, **kw):
        try:
            return request.env["workspace.calendar"].get_event_detail(int(event_id))
        except Exception as e:
            _logger.error("Cal detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Quality section routes ─────────────────────────

    @http.route("/workspace/qa/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def qa_data(self, **kw):
        try:
            return request.env["workspace.quality"].get_qa_data()
        except Exception as e:
            _logger.error("QA data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/qa/list", type="json", auth="user",
                methods=["POST"], csrf=False)
    def qa_list(self, filter_key="tutto", **kw):
        try:
            return request.env["workspace.quality"].get_qa_list(filter_key)
        except Exception as e:
            _logger.error("QA list error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/qa/ccp", type="json", auth="user",
                methods=["POST"], csrf=False)
    def qa_ccp(self, **kw):
        try:
            return request.env["workspace.quality"].get_ccp_grid()
        except Exception as e:
            _logger.error("QA ccp error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/qa/docs", type="json", auth="user",
                methods=["POST"], csrf=False)
    def qa_docs(self, **kw):
        try:
            return request.env["workspace.quality"].get_docs_grid()
        except Exception as e:
            _logger.error("QA docs error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/qa/detail", type="json", auth="user",
                methods=["POST"], csrf=False)
    def qa_detail(self, item_type="", item_id=0, **kw):
        try:
            return request.env["workspace.quality"].get_qa_detail(item_type, int(item_id))
        except Exception as e:
            _logger.error("QA detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Cash & Bank section routes ────────────────────

    @http.route("/workspace/cash/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cash_data(self, **kw):
        try:
            return request.env["workspace.cash"].get_cash_data()
        except Exception as e:
            _logger.error("Cash data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/cash/accounts", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cash_accounts(self, **kw):
        try:
            return request.env["workspace.cash"].get_accounts()
        except Exception as e:
            _logger.error("Cash accounts error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/cash/bsl", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cash_bsl(self, filter_key="tutte", **kw):
        try:
            return request.env["workspace.cash"].get_bsl(filter_key)
        except Exception as e:
            _logger.error("Cash BSL error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/cash/invoices", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cash_invoices(self, filter_key="tutte", **kw):
        try:
            return request.env["workspace.cash"].get_invoices(filter_key)
        except Exception as e:
            _logger.error("Cash invoices error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/cash/detail", type="json", auth="user",
                methods=["POST"], csrf=False)
    def cash_detail(self, item_type="", item_id=0, **kw):
        try:
            return request.env["workspace.cash"].get_cash_detail(item_type, int(item_id))
        except Exception as e:
            _logger.error("Cash detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Decisions section routes ──────────────────────

    @http.route("/workspace/dec/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def dec_data(self, **kw):
        try:
            return request.env["workspace.decisions"].get_dec_data()
        except Exception as e:
            _logger.error("Dec data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/dec/list", type="json", auth="user",
                methods=["POST"], csrf=False)
    def dec_list(self, filter_key="tutte", **kw):
        try:
            return request.env["workspace.decisions"].get_dec_list(filter_key)
        except Exception as e:
            _logger.error("Dec list error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/dec/detail", type="json", auth="user",
                methods=["POST"], csrf=False)
    def dec_detail(self, item_type="", item_id=0, **kw):
        try:
            return request.env["workspace.decisions"].get_dec_detail(item_type, int(item_id))
        except Exception as e:
            _logger.error("Dec detail error: %s", e, exc_info=True)
            return {"error": str(e)}

    # ─── Investor & CdA section routes ─────────────────

    @http.route("/workspace/inv/data", type="json", auth="user",
                methods=["POST"], csrf=False)
    def inv_data(self, **kw):
        try:
            return request.env["workspace.investor"].get_inv_data()
        except Exception as e:
            _logger.error("Inv data error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/inv/events", type="json", auth="user",
                methods=["POST"], csrf=False)
    def inv_events(self, filter_key="tutti", **kw):
        try:
            return request.env["workspace.investor"].get_inv_events(filter_key)
        except Exception as e:
            _logger.error("Inv events error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/inv/comms", type="json", auth="user",
                methods=["POST"], csrf=False)
    def inv_comms(self, **kw):
        try:
            return request.env["workspace.investor"].get_inv_comms()
        except Exception as e:
            _logger.error("Inv comms error: %s", e, exc_info=True)
            return {"error": str(e)}

    @http.route("/workspace/inv/detail", type="json", auth="user",
                methods=["POST"], csrf=False)
    def inv_detail(self, item_type="", item_id=0, **kw):
        try:
            return request.env["workspace.investor"].get_inv_detail(item_type, int(item_id))
        except Exception as e:
            _logger.error("Inv detail error: %s", e, exc_info=True)
            return {"error": str(e)}
