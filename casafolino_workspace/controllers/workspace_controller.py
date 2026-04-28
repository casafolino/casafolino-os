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
