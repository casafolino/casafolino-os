# -*- coding: utf-8 -*-
import mimetypes
import os

from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_resource


MODULE = "casafolino_company_website"
SITE_ROOT = "static/src/site"


class CasaFolinoCompanyWebsite(http.Controller):
    def _read_site_file(self, *parts):
        path = get_module_resource(MODULE, SITE_ROOT, *parts)
        if not path or not os.path.isfile(path):
            return None, None
        with open(path, "rb") as handle:
            return handle.read(), path

    def _serve_file(self, *parts, status=200, content_type=None):
        payload, path = self._read_site_file(*parts)
        if payload is None:
            return request.not_found()
        response_type = content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"
        headers = [
            ("Cache-Control", "public, max-age=300"),
            ("X-Content-Type-Options", "nosniff"),
            ("Content-Type", response_type),
        ]
        return request.make_response(payload, headers=headers, status=status)

    def _serve_page(self, lang, page_parts=None):
        page_parts = page_parts or []
        payload, path = self._read_site_file(lang, *page_parts, "index.html")
        if payload is None:
            return request.not_found()
        html = payload.decode("utf-8")
        return request.make_response(
            html,
            headers=[
                ("Cache-Control", "public, max-age=300"),
                ("X-Content-Type-Options", "nosniff"),
                ("Content-Type", "text/html; charset=utf-8"),
            ],
        )

    @http.route("/", type="http", auth="public", website=False, sitemap=False)
    def company_root(self, **kwargs):
        return request.redirect("/en/", code=302)

    @http.route(["/robots.txt"], type="http", auth="public", website=False, sitemap=False)
    def company_robots(self, **kwargs):
        return self._serve_file("robots.txt", content_type="text/plain; charset=utf-8")

    @http.route(["/sitemap.xml"], type="http", auth="public", website=False, sitemap=False)
    def company_sitemap(self, **kwargs):
        return self._serve_file("sitemap.xml", content_type="application/xml; charset=utf-8")

    @http.route(
        [
            "/assets/site.css",
            "/assets/catalog-cover.jpg",
            "/assets/creams.jpg",
            "/assets/honeys.jpg",
            "/assets/risottos.jpg",
        ],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def company_asset(self, **kwargs):
        filename = request.httprequest.path.rsplit("/", 1)[-1]
        return self._serve_file("assets", filename)

    @http.route(
        [
            "/en/",
            "/en/company-profile/",
            "/en/catalog/",
            "/en/services/",
            "/en/services/private-label/",
            "/en/services/b2b-supply/",
            "/en/services/distribution/",
            "/en/certifications/",
            "/en/sustainability/",
            "/en/contact/",
            "/it/",
            "/it/profilo-aziendale/",
            "/it/catalogo/",
            "/it/servizi/",
            "/it/servizi/private-label/",
            "/it/servizi/forniture-b2b/",
            "/it/servizi/distribuzione/",
            "/it/certificazioni/",
            "/it/sostenibilita/",
            "/it/contatti/",
            "/es/",
            "/es/empresa/",
            "/es/catalogo/",
            "/es/servicios/",
            "/es/servicios/marca-privada/",
            "/es/servicios/suministro-b2b/",
            "/es/servicios/distribucion/",
            "/es/certificaciones/",
            "/es/sostenibilidad/",
            "/es/contacto/",
            "/fr/",
            "/fr/entreprise/",
            "/fr/catalogue/",
            "/fr/services/",
            "/fr/services/marque-privee/",
            "/fr/services/approvisionnement-b2b/",
            "/fr/services/distribution/",
            "/fr/certifications/",
            "/fr/durabilite/",
            "/fr/contact/",
        ],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def company_page(self, **kwargs):
        parts = [part for part in request.httprequest.path.strip("/").split("/") if part]
        lang = parts[0] if parts else "en"
        return self._serve_page(lang, parts[1:])
