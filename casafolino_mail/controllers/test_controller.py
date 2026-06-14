from odoo import http
from odoo.http import request


class CfTestController(http.Controller):

    @http.route('/cf/ping', type='http', auth='public', csrf=False, methods=['GET'])
    def ping(self, **kw):
        return 'pong'
