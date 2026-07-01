import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# transparent 1x1 GIF
_PIXEL = base64.b64decode(
    b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


class FancyFoodController(http.Controller):

    # ---------- helpers ----------
    def _partner_by_token(self, token):
        if not token:
            return request.env["res.partner"].sudo().browse()
        return (
            request.env["res.partner"]
            .sudo()
            .search([("fancyfood_token", "=", token)], limit=1)
        )

    def _log_event(self, partner, etype):
        if not partner:
            return
        try:
            request.env["casafolino.fancyfood.event"].sudo().create(
                {"partner_id": partner.id, "event_type": etype}
            )
        except Exception:  # pragma: no cover - never break asset delivery
            _logger.exception("Fancy Food: failed to log %s event", etype)

    def _config_attachment(self, key):
        param = request.env["ir.config_parameter"].sudo().get_param(key)
        if not param:
            return request.env["ir.attachment"].sudo().browse()
        return request.env["ir.attachment"].sudo().browse(int(param)).exists()

    # ---------- open pixel (primary open-tracking) ----------
    @http.route("/fancyfood/px", type="http", auth="public", csrf=False, sitemap=False)
    def fancyfood_pixel(self, t=None, **kw):
        partner = self._partner_by_token(t)
        self._log_event(partner, "open")
        return request.make_response(
            _PIXEL,
            headers=[
                ("Content-Type", "image/gif"),
                ("Content-Length", str(len(_PIXEL))),
                ("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"),
                ("Pragma", "no-cache"),
            ],
        )

    # ---------- signature logo (secondary engagement signal) ----------
    @http.route("/fancyfood/logo", type="http", auth="public", csrf=False, sitemap=False)
    def fancyfood_logo(self, t=None, **kw):
        partner = self._partner_by_token(t)
        # secondary signal only — deliberately NOT an "open" (no double count)
        self._log_event(partner, "logo")
        att = self._config_attachment("casafolino.fancyfood.logo_att_id")
        if not att:
            return request.not_found()
        return request.make_response(
            att.raw,
            headers=[
                ("Content-Type", att.mimetype or "image/png"),
                ("Content-Length", str(len(att.raw))),
                ("Cache-Control", "public, max-age=3600"),
            ],
        )

    # ---------- tokenized catalogue PDF (click tracking) ----------
    @http.route(
        ["/catalogue/en-2026.pdf", "/catalogue/it-2026.pdf"],
        type="http", auth="public", csrf=False, sitemap=False,
    )
    def fancyfood_catalogue_pdf(self, t=None, **kw):
        partner = self._partner_by_token(t)
        if partner:
            self._log_event(partner, "click")
            try:
                partner.sudo()._fancyfood_register_click()
            except Exception:  # pragma: no cover
                _logger.exception("Fancy Food: click activity failed for %s", partner.id)
        att = self._config_attachment("casafolino.fancyfood.catalogue_att_id")
        if not att:
            return request.not_found()
        data = att.raw
        return request.make_response(
            data,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", str(len(data))),
                ("Content-Disposition",
                 "attachment; filename=\"CasaFolino_Catalogue_2026.pdf\""),
                ("Cache-Control", "public, max-age=300"),
            ],
        )
