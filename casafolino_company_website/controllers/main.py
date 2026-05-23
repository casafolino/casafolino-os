# -*- coding: utf-8 -*-
import mimetypes
import os
from urllib.parse import urlencode

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

    def _redirect_back(self, status):
        referer = request.httprequest.referrer or "/en/contact/"
        separator = "&" if "?" in referer else "?"
        return request.redirect(f"{referer}{separator}{urlencode({'contact': status})}", code=303)

    def _clean(self, value, limit=500):
        return (value or "").strip()[:limit]

    @http.route("/", type="http", auth="public", website=False, sitemap=False)
    def company_root(self, **kwargs):
        return request.redirect("/en/", code=302)

    @http.route(["/robots.txt"], type="http", auth="public", website=False, sitemap=False)
    def company_robots(self, **kwargs):
        host = (request.httprequest.host or "").split(":", 1)[0].lower()
        if host == "erp.casafolino.com":
            return request.make_response(
                "User-agent: *\nDisallow: /\n",
                headers=[
                    ("Cache-Control", "public, max-age=300"),
                    ("X-Content-Type-Options", "nosniff"),
                    ("Content-Type", "text/plain; charset=utf-8"),
                ],
            )
        return self._serve_file("robots.txt", content_type="text/plain; charset=utf-8")

    @http.route(["/sitemap.xml"], type="http", auth="public", website=False, sitemap=False)
    def company_sitemap(self, **kwargs):
        return self._serve_file("sitemap.xml", content_type="application/xml; charset=utf-8")

    @http.route(
        [
            "/assets/site.css",
            "/assets/catalog-cover.jpg",
            "/assets/logo.svg",
            "/assets/logo-thumb.svg",
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
        ["/assets/catalog/<path:filename>"],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def company_catalog_asset(self, filename=None, **kwargs):
        if not filename or "/" in filename or not filename.endswith(".jpg"):
            return request.not_found()
        return self._serve_file("assets", "catalog", filename)

    @http.route(
        ["/company/contact/submit"],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
        methods=["POST"],
        csrf=False,
    )
    def company_contact_submit(self, **post):
        if self._clean(post.get("website_url"), 200):
            return self._redirect_back("sent")

        contact_name = self._clean(post.get("name"), 120)
        company = self._clean(post.get("company"), 160)
        email = self._clean(post.get("email"), 160)
        phone = self._clean(post.get("phone"), 80)
        country = self._clean(post.get("country"), 120)
        interest = self._clean(post.get("interest"), 120)
        message = self._clean(post.get("message"), 3000)
        lang = self._clean(post.get("lang"), 12)
        source_url = self._clean(request.httprequest.referrer, 300)

        if not contact_name or not email or not message:
            return self._redirect_back("missing")

        description = "\n".join(
            line
            for line in [
                "Lead generato dal form website CasaFolino Company.",
                f"Nome: {contact_name}",
                f"Azienda: {company}" if company else "",
                f"Email: {email}",
                f"Telefono: {phone}" if phone else "",
                f"Paese: {country}" if country else "",
                f"Interesse: {interest}" if interest else "",
                f"Lingua: {lang}" if lang else "",
                f"Pagina sorgente: {source_url}" if source_url else "",
                "",
                "Messaggio:",
                message,
            ]
            if line
        )

        lead_vals = {
            "name": f"Website inquiry - {company or contact_name}",
            "type": "lead",
            "contact_name": contact_name,
            "partner_name": company,
            "email_from": email,
            "phone": phone,
            "description": description,
        }
        Lead = request.env["crm.lead"].sudo()
        if "team_id" in Lead._fields:
            Team = request.env["crm.team"].sudo()
            domain = [("use_leads", "=", True)] if "use_leads" in Team._fields else []
            team = Team.search(domain, limit=1)
            if team:
                lead_vals["team_id"] = team.id
        if "referred" in Lead._fields:
            lead_vals["referred"] = "CasaFolino Company Website"
        if "website" in Lead._fields and source_url:
            lead_vals["website"] = source_url

        lead = Lead.create(lead_vals)
        if hasattr(lead, "message_post"):
            lead.message_post(body="Lead creato automaticamente dal form contatti del sito Company CasaFolino.")
        return self._redirect_back("sent")

    @http.route(
        [
            "/en/",
            "/en/company-profile/",
            "/en/catalog/",
            "/en/catalog/spreads/",
            "/en/catalog/flavored-honeys/",
            "/en/catalog/ready-risottos/",
            "/en/catalog/italian-spice-mixes/",
            "/en/catalog/gastronomic-mousses/",
            "/en/catalog/crispy-chilli/",
            "/en/catalog/cantucci/",
            "/en/catalog/biscuits/",
            "/en/catalog/chocolate-bars/",
            "/en/catalog/chocolate-chunks/",
            "/en/services/",
            "/en/services/private-label/",
            "/en/services/custom-recipes/",
            "/en/services/b2b-supply/",
            "/en/services/distribution/",
            "/en/certifications/",
            "/en/sustainability/",
            "/en/contact/",
            "/it/",
            "/it/profilo-aziendale/",
            "/it/catalogo/",
            "/it/catalogo/creme-spalmabili/",
            "/it/catalogo/mieli-aromatizzati/",
            "/it/catalogo/risotti-pronti/",
            "/it/catalogo/mix-spezie-italiane/",
            "/it/catalogo/mousse-gastronomiche/",
            "/it/catalogo/crispy-chilli/",
            "/it/catalogo/cantucci/",
            "/it/catalogo/biscotti/",
            "/it/catalogo/barrette-cioccolato/",
            "/it/catalogo/chunks-cioccolato/",
            "/it/servizi/",
            "/it/servizi/private-label/",
            "/it/servizi/ricette-su-misura/",
            "/it/servizi/forniture-b2b/",
            "/it/servizi/distribuzione/",
            "/it/certificazioni/",
            "/it/sostenibilita/",
            "/it/contatti/",
            "/es/",
            "/es/empresa/",
            "/es/catalogo/",
            "/es/catalogo/cremas-untables/",
            "/es/catalogo/mieles-aromatizadas/",
            "/es/catalogo/risottos-listos/",
            "/es/catalogo/mezclas-especias-italianas/",
            "/es/catalogo/mousses-gastronomicas/",
            "/es/catalogo/crispy-chilli/",
            "/es/catalogo/cantucci/",
            "/es/catalogo/galletas/",
            "/es/catalogo/barras-chocolate/",
            "/es/catalogo/chunks-chocolate/",
            "/es/servicios/",
            "/es/servicios/marca-privada/",
            "/es/servicios/recetas-a-medida/",
            "/es/servicios/suministro-b2b/",
            "/es/servicios/distribucion/",
            "/es/certificaciones/",
            "/es/sostenibilidad/",
            "/es/contacto/",
            "/fr/",
            "/fr/entreprise/",
            "/fr/catalogue/",
            "/fr/catalogue/cremes-a-tartiner/",
            "/fr/catalogue/miels-aromatises/",
            "/fr/catalogue/risottos-prets/",
            "/fr/catalogue/melanges-epices-italiennes/",
            "/fr/catalogue/mousses-gastronomiques/",
            "/fr/catalogue/crispy-chilli/",
            "/fr/catalogue/cantucci/",
            "/fr/catalogue/biscuits/",
            "/fr/catalogue/tablettes-chocolat/",
            "/fr/catalogue/morceaux-chocolat/",
            "/fr/services/",
            "/fr/services/marque-privee/",
            "/fr/services/recettes-sur-mesure/",
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
