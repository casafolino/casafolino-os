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
