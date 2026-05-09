from odoo import http
from odoo.http import request
import werkzeug


class CatalogueController(http.Controller):

    @http.route('/catalogue/en-2026', type='http', auth='public', website=False)
    def catalogue_en_2026(self, **kw):
        attachment = request.env['ir.attachment'].sudo().search(
            [('name', '=', 'CasaFolino Catalogue EN 2026 — Master'),
             ('public', '=', True),
             ('mimetype', '=', 'application/pdf')],
            limit=1, order='id desc'
        )
        if not attachment:
            return request.not_found()
        return werkzeug.utils.redirect(
            f'/web/content/{attachment.id}?download=true&filename=CasaFolino_Catalogue_EN_2026.pdf',
            code=302
        )
