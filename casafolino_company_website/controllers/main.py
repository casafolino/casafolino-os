# -*- coding: utf-8 -*-
import mimetypes
import os
from urllib.parse import urlencode

from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_resource


MODULE = "casafolino_company_website"
SITE_ROOT = "static/src/site"
COMPANY_HOSTS = {"company.casafolino.com", "www.company.casafolino.com"}
B2B_HOSTS = {"b2b.casafolino.com", "www.b2b.casafolino.com"}
ERP_HOSTS = {"erp.casafolino.com", "51.44.170.55"}


class CasaFolinoCompanyWebsite(http.Controller):
    COUNTRY_LANGUAGE = {
        "IT": "it",
        "SM": "it",
        "VA": "it",
        "ES": "es",
        "MX": "es",
        "AR": "es",
        "CL": "es",
        "CO": "es",
        "PE": "es",
        "UY": "es",
        "FR": "fr",
        "BE": "fr",
        "LU": "fr",
        "MC": "fr",
        "CA": "fr",
    }
    SUPPORTED_LANGUAGES = {"en", "it", "es", "fr"}

    def _request_hosts(self):
        headers = request.httprequest.headers
        return {
            (request.httprequest.host or "").lower(),
            (headers.get("Host") or "").lower(),
            (headers.get("X-Forwarded-Host") or "").lower(),
        }

    def _request_hostnames(self):
        return {host.split(":", 1)[0] for host in self._request_hosts() if host}

    def _is_erp_host(self):
        hosts = self._request_hosts()
        hostnames = self._request_hostnames()
        return bool(hostnames & ERP_HOSTS) or any(host.endswith(":4589") for host in hosts)

    def _is_company_host(self):
        return bool(self._request_hostnames() & COMPANY_HOSTS)

    def _is_b2b_host(self):
        return bool(self._request_hostnames() & B2B_HOSTS)

    def _erp_login_redirect(self):
        return request.redirect("/web/login", code=302)

    def _guard_company_site(self):
        if self._is_erp_host():
            return self._erp_login_redirect()
        if self._is_b2b_host():
            return request.redirect("/b2b", code=302)
        if not self._is_company_host():
            return request.not_found()
        return None

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

    def _preferred_language(self):
        headers = request.httprequest.headers
        country = (
            headers.get("CF-IPCountry")
            or headers.get("CloudFront-Viewer-Country")
            or headers.get("X-Vercel-IP-Country")
            or headers.get("X-Country-Code")
            or headers.get("X-Geo-Country")
            or ""
        ).upper()
        if country in self.COUNTRY_LANGUAGE:
            return self.COUNTRY_LANGUAGE[country]

        accept_language = headers.get("Accept-Language", "")
        for raw_part in accept_language.split(","):
            code = raw_part.split(";", 1)[0].strip().lower().split("-", 1)[0]
            if code in self.SUPPORTED_LANGUAGES:
                return code
        return "en"

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
        guard = self._guard_company_site()
        if guard:
            return guard
        return request.redirect(f"/{self._preferred_language()}/", code=302)

    @http.route(
        ["/en/web/login", "/it/web/login", "/es/web/login", "/fr/web/login"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def company_localized_backend_login(self, **kwargs):
        if request.website and request.env.user != request.website.user_id:
            return request.redirect("/odoo", code=302)
        response = self._erp_login_redirect()
        response.set_cookie("frontend_lang", "en_US", max_age=60 * 60 * 24 * 365, path="/")
        return response

    @http.route(["/robots.txt"], type="http", auth="public", website=False, sitemap=False)
    def company_robots(self, **kwargs):
        if self._is_erp_host():
            return request.make_response(
                "User-agent: *\nDisallow: /\n",
                headers=[
                    ("Cache-Control", "public, max-age=300"),
                    ("X-Content-Type-Options", "nosniff"),
                    ("Content-Type", "text/plain; charset=utf-8"),
                ],
            )
        if not self._is_company_host():
            return request.not_found()
        return self._serve_file("robots.txt", content_type="text/plain; charset=utf-8")

    @http.route(["/sitemap.xml"], type="http", auth="public", website=False, sitemap=False)
    def company_sitemap(self, **kwargs):
        guard = self._guard_company_site()
        if guard:
            return guard
        return self._serve_file("sitemap.xml", content_type="application/xml; charset=utf-8")

    @http.route(
        [
            "/assets/site.css",
            "/assets/language.js",
            "/assets/catalog-cover.jpg",
            "/assets/logo.svg",
            "/assets/logo-thumb.svg",
            "/assets/logo.png",
            "/assets/logo-thumb.png",
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
        guard = self._guard_company_site()
        if guard:
            return guard
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
        guard = self._guard_company_site()
        if guard:
            return guard
        if not filename or "/" in filename or not filename.endswith(".jpg"):
            return request.not_found()
        return self._serve_file("assets", "catalog", filename)

    @http.route(
        ["/assets/products/<path:filename>"],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def company_product_asset(self, filename=None, **kwargs):
        guard = self._guard_company_site()
        if guard:
            return guard
        if not filename or "/" in filename or not filename.endswith(".jpg"):
            return request.not_found()
        return self._serve_file("assets", "products", filename)

    @http.route(
        ["/assets/fairs/<path:filename>"],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def company_fair_asset(self, filename=None, **kwargs):
        guard = self._guard_company_site()
        if guard:
            return guard
        if not filename or "/" in filename or not filename.endswith(".jpg"):
            return request.not_found()
        return self._serve_file("assets", "fairs", filename)

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
        guard = self._guard_company_site()
        if guard:
            return guard

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

        if not contact_name or not email or not message or post.get("privacy_consent") != "1":
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
            "/en/fairs/",
            "/en/communications/",
            "/en/privacy-policy/",
            "/en/cookie-policy/",
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
            "/it/privacy-policy/",
            "/it/cookie-policy/",
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
            "/es/privacy-policy/",
            "/es/cookie-policy/",
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
            "/fr/privacy-policy/",
            "/fr/cookie-policy/",
        ],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def company_page(self, **kwargs):
        guard = self._guard_company_site()
        if guard:
            return guard
        parts = [part for part in request.httprequest.path.strip("/").split("/") if part]
        lang = parts[0] if parts else "en"
        return self._serve_page(lang, parts[1:])

    @http.route(
        ["/en/catalog/<path:catalog_path>/"],
        type="http",
        auth="public",
        website=False,
        sitemap=False,
    )
    def company_en_catalog_page(self, catalog_path=None, **kwargs):
        guard = self._guard_company_site()
        if guard:
            return guard
        parts = ["catalog"] + [part for part in (catalog_path or "").split("/") if part]
        return self._serve_page("en", parts)
