# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request, Response


class WorkspaceHealthController(http.Controller):

    @http.route("/workspace/health", type="http", auth="none", methods=["GET"], csrf=False)
    def health(self, **kw):
        return Response(
            json.dumps({"status": "ok"}),
            content_type="application/json",
            status=200,
        )
