# -*- coding: utf-8 -*-
import json
import re
from urllib.parse import quote

from odoo import http
from odoo.http import request
from odoo.tools import email_normalize, html2plaintext


B2B_HOSTS = {"b2b.casafolino.com", "www.b2b.casafolino.com"}
COMPANY_HOSTS = {"company.casafolino.com", "www.company.casafolino.com"}
ERP_HOSTS = {"erp.casafolino.com", "51.44.170.55"}


class CasaFolinoB2BPortal(http.Controller):
    FALLBACK_IMAGES = [
        "/casafolino_b2b_portal/static/src/img/products/crema-pistacchio.png",
        "/casafolino_b2b_portal/static/src/img/products/caramello-salato.png",
        "/casafolino_b2b_portal/static/src/img/products/miedelizie-nocciole.png",
        "/casafolino_b2b_portal/static/src/img/products/risotto-tartufo.png",
        "/casafolino_b2b_portal/static/src/img/products/spezia-puttanesca.png",
        "/casafolino_b2b_portal/static/src/img/products/mousse-gianduia.png",
    ]

    MOCKUP_IMAGES = {
        "pistachio": "/casafolino_b2b_portal/static/src/img/products/crema-pistacchio.png",
        "pistacchio": "/casafolino_b2b_portal/static/src/img/products/crema-pistacchio.png",
        "caramel": "/casafolino_b2b_portal/static/src/img/products/caramello-salato.png",
        "caramello": "/casafolino_b2b_portal/static/src/img/products/caramello-salato.png",
        "hazelnut": "/casafolino_b2b_portal/static/src/img/products/miedelizie-nocciole.png",
        "nocciole": "/casafolino_b2b_portal/static/src/img/products/miedelizie-nocciole.png",
        "truffle": "/casafolino_b2b_portal/static/src/img/products/risotto-tartufo.png",
        "tartufo": "/casafolino_b2b_portal/static/src/img/products/risotto-tartufo.png",
        "puttanesca": "/casafolino_b2b_portal/static/src/img/products/spezia-puttanesca.png",
        "gianduia": "/casafolino_b2b_portal/static/src/img/products/mousse-gianduia.png",
    }

    CATEGORY_FALLBACKS = {
        "Ready Risotto": "/casafolino_b2b_portal/static/src/img/products/risotto-tartufo.png",
        "Italian Seasoning Mix": "/casafolino_b2b_portal/static/src/img/products/spezia-puttanesca.png",
        "Spreadable Creams": "/casafolino_b2b_portal/static/src/img/products/crema-pistacchio.png",
        "Honey Mousse & Crispy Chilli": "/casafolino_b2b_portal/static/src/img/products/mousse-gianduia.png",
        "Flavored Honey": "/casafolino_b2b_portal/static/src/img/products/miedelizie-nocciole.png",
        "Caramel Chocolate Bars": "/casafolino_b2b_portal/static/src/img/products/caramello-salato.png",
    }

    PRIORITY_CATEGORIES = [
        {
            "label": "Creme spalmabili",
            "match": ("crema", "creme", "spalmabil", "spread", "spreadable"),
            "summary": "Referenze dolci e premium per scaffale gourmet, gelaterie, horeca e confezioni regalo.",
        },
        {
            "label": "Miele",
            "match": ("miele", "honey", "miedelizie"),
            "summary": "Mieli e mieli arricchiti per retail, degustazioni, breakfast e gift box.",
        },
        {
            "label": "Crispy",
            "match": ("crispy", "chilli", "chili", "crunchy", "croccante"),
            "summary": "Condimenti croccanti ad alta rotazione per cucina, gastronomia e street food.",
        },
        {
            "label": "Mousse",
            "match": ("mousse", "paté", "pate", "gastronomic"),
            "summary": "Mousse gastronomiche pronte per formaggi, taglieri, aperitivi e banco gastronomia.",
        },
    ]

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

    def _is_b2b_host(self):
        return bool(self._request_hostnames() & B2B_HOSTS)

    def _is_company_host(self):
        return bool(self._request_hostnames() & COMPANY_HOSTS)

    def _guard_b2b_site(self):
        if self._is_erp_host():
            return request.redirect("/web/login", code=302)
        if not (self._is_b2b_host() or self._is_company_host()):
            return request.not_found()
        return None

    def _current_partner(self):
        if request.env.user == request.website.user_id:
            return request.env["res.partner"]
        return request.env.user.partner_id.commercial_partner_id

    def _account_state(self):
        partner = self._current_partner()
        if not partner:
            return "guest"
        if partner.cf_b2b_status == "approved":
            return "approved"
        if partner.cf_b2b_status == "pending":
            return "pending"
        if partner.cf_b2b_status == "suspended":
            return "suspended"
        return "guest"

    def _min_amount(self):
        value = request.env["ir.config_parameter"].sudo().get_param("casafolino_b2b.min_order_amount", "250")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 250.0

    def _min_jars(self):
        value = request.env["ir.config_parameter"].sudo().get_param("casafolino_b2b.min_jars", "48")
        try:
            return int(value)
        except (TypeError, ValueError):
            return 48

    def _cart(self):
        cart = request.session.setdefault("cf_b2b_cart", {})
        return {int(product_id): int(qty) for product_id, qty in cart.items() if int(qty) > 0}

    def _save_cart(self, cart):
        request.session["cf_b2b_cart"] = {str(product_id): int(qty) for product_id, qty in cart.items() if int(qty) > 0}

    def _product_domain(self):
        return [("sale_ok", "=", True), ("cf_b2b_enabled", "=", True)]

    def _registration_tag(self):
        tag_name = "b2b company" if self._is_company_host() else "b2b ecommerce"
        Tag = request.env["res.partner.category"].sudo()
        return Tag.search([("name", "=", tag_name)], limit=1) or Tag.create({"name": tag_name})

    def _registration_source(self):
        return "company" if self._is_company_host() else "ecommerce"

    def _google_places_src(self):
        key = request.env["ir.config_parameter"].sudo().get_param("casafolino_b2b.google_places_api_key")
        if not key:
            return False
        return (
            "https://maps.googleapis.com/maps/api/js"
            f"?key={quote(key)}&libraries=places&callback=cfB2BInitPlaces&loading=async&language=it"
        )

    def _subscribe_b2b_newsletter_email(self, name, email):
        email = (email or "").strip()
        if not email:
            return False
        mailing_list = request.env.ref(
            "casafolino_b2b_portal.mailing_list_b2b_newsletter",
            raise_if_not_found=False,
        )
        if not mailing_list:
            return False
        Contact = request.env["mailing.contact"].sudo()
        normalized_email = email_normalize(email) or email.lower()
        domain = [("email", "=", email)]
        if "email_normalized" in Contact._fields:
            domain = ["|", ("email", "=", email), ("email_normalized", "=", normalized_email)]
        contact = Contact.search(domain, limit=1)
        if contact:
            contact.write({"name": contact.name or name, "email": email})
        else:
            contact = Contact.create({"name": name or email, "email": email})
        if "list_ids" in Contact._fields:
            contact.write({"list_ids": [(4, mailing_list.id)]})
            return True
        Subscription = request.env["mailing.subscription"].sudo()
        subscription = Subscription.search(
            [("contact_id", "=", contact.id), ("list_id", "=", mailing_list.id)],
            limit=1,
        )
        if subscription:
            subscription.write({"opt_out": False})
        else:
            Subscription.create({"contact_id": contact.id, "list_id": mailing_list.id, "opt_out": False})
        return True

    def _subscribe_b2b_newsletter(self, partner):
        return self._subscribe_b2b_newsletter_email(partner.name, partner.email)

    def _newsletter_response(self, success, redirect_url="/b2b/newsletter"):
        if request.httprequest.headers.get("X-Requested-With") == "XMLHttpRequest":
            return request.make_response(
                json.dumps({"success": bool(success)}),
                headers=[("Content-Type", "application/json")],
            )
        suffix = "subscribed=1" if success else "missing=1"
        separator = "&" if "?" in redirect_url else "?"
        return request.redirect(f"{redirect_url}{separator}{suffix}")

    def _product_price(self, product, qty=1):
        partner = self._current_partner()
        pricelist = partner.property_product_pricelist if partner else request.website.pricelist_id
        priced_product = product.product_variant_id or product
        if pricelist and hasattr(pricelist, "_get_product_price"):
            try:
                return pricelist._get_product_price(priced_product, qty or 1, partner=partner)
            except TypeError:
                return pricelist._get_product_price(priced_product, qty or 1, partner)
        return product.list_price

    def _product_image_url(self, product, category, index):
        if product.image_1024:
            unique = product.write_date.strftime("%Y%m%d%H%M%S") if product.write_date else product.id
            return f"/web/image/product.template/{product.id}/image_1024?unique={unique}"
        searchable = f"{product.name or ''} {product.default_code or ''}".lower()
        for keyword, image_url in self.MOCKUP_IMAGES.items():
            if keyword in searchable:
                return image_url
        return self.CATEGORY_FALLBACKS.get(category) or self.FALLBACK_IMAGES[index % len(self.FALLBACK_IMAGES)]

    def _case_size(self, product):
        case_size = product.cf_b2b_case_size or 12
        return case_size if case_size >= 12 else 12

    def _product_text(self, product):
        raw = product.website_description or product.description_sale or product.description or ""
        text = html2plaintext(raw).strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _product_blurb(self, product, category):
        text = self._product_text(product)
        if text:
            return text[:170] + ("..." if len(text) > 170 else "")
        if self._priority_rank(f"{product.name} {category}") < 4:
            return "Referenza CasaFolino selezionata per assortimenti B2B, scaffale gourmet e ordini a cartone."
        return "Prodotto CasaFolino disponibile per fornitura professionale con listino riservato e colli B2B."

    def _priority_rank(self, value):
        normalized = (value or "").lower()
        for index, rule in enumerate(self.PRIORITY_CATEGORIES):
            if any(token in normalized for token in rule["match"]):
                return index
        return len(self.PRIORITY_CATEGORIES)

    def _product_priority_rank(self, product, category):
        product_rank = self._priority_rank(f"{product.name} {product.default_code or ''}")
        if product_rank < len(self.PRIORITY_CATEGORIES):
            return product_rank
        return self._priority_rank(category)

    def _product_detail_url(self, product):
        return f"/b2b/product/{product.id}"

    def _product_payload(self, product, index=0, account_state=None):
        account_state = account_state or self._account_state()
        category = product.public_categ_ids[:1].name or product.categ_id.name or "Catalogo"
        case_size = self._case_size(product)
        rank = self._product_priority_rank(product, category)
        return {
            "record": product,
            "category": category,
            "case_size": case_size,
            "price": self._product_price(product, case_size) if account_state == "approved" else 0.0,
            "image_url": self._product_image_url(product, category, index),
            "blurb": self._product_blurb(product, category),
            "detail_url": self._product_detail_url(product),
            "priority_rank": rank,
            "priority_label": self.PRIORITY_CATEGORIES[rank]["label"] if rank < len(self.PRIORITY_CATEGORIES) else category,
        }

    def _catalog_products(self, account_state=None):
        account_state = account_state or self._account_state()
        Product = request.env["product.template"].sudo()
        products = Product.search(self._product_domain(), order="sequence, name", limit=160)
        result = [self._product_payload(product, index, account_state) for index, product in enumerate(products)]
        return sorted(result, key=lambda item: (item["priority_rank"], item["category"], item["record"].sequence, item["record"].name))

    def _category_slug(self, category):
        slug = re.sub(r"[^a-z0-9]+", "-", (category or "").lower()).strip("-")
        return slug or "categoria"

    def _category_url(self, category):
        return "/b2b/category/%s" % quote(self._category_slug(category))

    def _catalog_sections(self, products, limit=None):
        sections = []
        by_category = {}
        for item in products:
            by_category.setdefault(item["category"], []).append(item)
        for category in sorted(by_category, key=lambda name: (self._priority_rank(name), name)):
            category_products = by_category[category]
            visible_products = category_products[:limit] if limit else category_products
            sections.append(
                {
                    "name": category,
                    "slug": self._category_slug(category),
                    "url": self._category_url(category),
                    "products": visible_products,
                    "total_count": len(category_products),
                    "has_more": bool(limit and len(category_products) > limit),
                }
            )
        return sections

    def _priority_sections(self, products):
        sections = []
        for index, rule in enumerate(self.PRIORITY_CATEGORIES):
            section_products = [item for item in products if item["priority_rank"] == index]
            if section_products:
                sections.append({"name": rule["label"], "summary": rule["summary"], "products": section_products})
        return sections

    def _cart_lines(self):
        products = request.env["product.template"].sudo().browse(self._cart().keys()).exists()
        quantities = self._cart()
        lines = []
        for product in products:
            qty = quantities.get(product.id, 0)
            if not qty:
                continue
            price_unit = self._product_price(product, qty)
            lines.append(
                {
                    "product": product,
                    "qty": qty,
                    "case_size": self._case_size(product),
                    "price_unit": price_unit,
                    "subtotal": qty * price_unit,
                }
            )
        return lines

    def _cart_totals(self):
        lines = self._cart_lines()
        total_qty = sum(line["qty"] for line in lines)
        total_amount = sum(line["subtotal"] for line in lines)
        return {
            "lines": lines,
            "total_qty": total_qty,
            "total_amount": total_amount,
            "min_amount": self._min_amount(),
            "min_jars": self._min_jars(),
            "can_checkout": (
                self._account_state() == "approved"
                and total_amount >= self._min_amount()
                and total_qty >= self._min_jars()
            ),
        }

    @http.route(["/b2b", "/b2b/"], type="http", auth="public", website=True, sitemap=True)
    def b2b_catalog(self, **kwargs):
        guard = self._guard_b2b_site()
        if guard:
            return guard
        account_state = self._account_state()
        products = self._catalog_products(account_state)
        return request.render(
            "casafolino_b2b_portal.catalog",
            {
                "account_state": account_state,
                "products": products,
                "priority_sections": self._priority_sections(products),
                "category_sections": self._catalog_sections(products, limit=4),
                "cart": self._cart_totals(),
            },
        )

    @http.route(["/b2b/category/<path:category_slug>"], type="http", auth="public", website=True, sitemap=True)
    def b2b_category(self, category_slug, **kwargs):
        guard = self._guard_b2b_site()
        if guard:
            return guard
        account_state = self._account_state()
        products = self._catalog_products(account_state)
        sections = self._catalog_sections(products)
        section = next((item for item in sections if item["slug"] == category_slug), None)
        if not section:
            return request.not_found()
        return request.render(
            "casafolino_b2b_portal.catalog",
            {
                "account_state": account_state,
                "products": section["products"],
                "priority_sections": [],
                "category_sections": [section],
                "category_page": section,
                "cart": self._cart_totals(),
            },
        )

    @http.route(["/b2b/product/<int:product_id>"], type="http", auth="public", website=True, sitemap=True)
    def b2b_product(self, product_id, **kwargs):
        guard = self._guard_b2b_site()
        if guard:
            return guard
        product = request.env["product.template"].sudo().browse(product_id).exists()
        if not product or not product.sale_ok or not product.cf_b2b_enabled:
            return request.not_found()
        account_state = self._account_state()
        item = self._product_payload(product, 0, account_state)
        related = [candidate for candidate in self._catalog_products(account_state) if candidate["record"].id != product.id]
        return request.render(
            "casafolino_b2b_portal.product_detail",
            {
                "account_state": account_state,
                "item": item,
                "description": self._product_text(product) or item["blurb"],
                "related_products": related[:4],
                "cart": self._cart_totals(),
            },
        )

    @http.route(["/b2b/register"], type="http", auth="public", website=True, sitemap=True, methods=["GET", "POST"], csrf=True)
    def b2b_register(self, **post):
        guard = self._guard_b2b_site()
        if guard:
            return guard
        if request.httprequest.method == "POST":
            if post.get("website_url"):
                return request.redirect("/b2b/register?sent=1")
            required = ["name", "email", "vat"]
            if any(not (post.get(field) or "").strip() for field in required):
                return request.redirect("/b2b/register?missing=1")
            partner = request.env["res.partner"].sudo().create(
                {
                    "name": (post.get("name") or "").strip(),
                    "company_type": "company",
                    "email": (post.get("email") or "").strip(),
                    "phone": (post.get("phone") or "").strip(),
                    "vat": (post.get("vat") or "").strip(),
                    "cf_b2b_vat_code": (post.get("vat") or "").strip(),
                    "cf_b2b_sdi_pec": (post.get("sdi_pec") or "").strip(),
                    "cf_b2b_category": post.get("category") or "other",
                    "cf_b2b_google_place_id": (post.get("google_place_id") or "").strip(),
                    "cf_b2b_google_place_types": (post.get("google_place_types") or "").strip(),
                    "cf_b2b_source": self._registration_source(),
                    "street": (post.get("street") or "").strip(),
                    "cf_b2b_status": "pending",
                    "comment": (post.get("notes") or "").strip(),
                    "category_id": [(4, self._registration_tag().id)],
                }
            )
            partner.message_post(body="Richiesta accesso B2B ricevuta da b2b.casafolino.com.")
            if post.get("newsletter_opt_in"):
                self._subscribe_b2b_newsletter(partner)
            partner.action_cf_b2b_send_pending_notifications()
            return request.redirect("/b2b/register?sent=1")
        return request.render(
            "casafolino_b2b_portal.register",
            {
                "sent": post.get("sent"),
                "missing": post.get("missing"),
                "google_places_src": self._google_places_src(),
            },
        )

    @http.route(["/b2b/newsletter"], type="http", auth="public", website=True, sitemap=True, methods=["GET", "POST"], csrf=True)
    def b2b_newsletter(self, **post):
        guard = self._guard_b2b_site()
        if guard:
            return guard
        if request.httprequest.method == "POST":
            if post.get("website_url"):
                return self._newsletter_response(True)
            name = (post.get("name") or "").strip()
            email = (post.get("email") or "").strip()
            if not email:
                return self._newsletter_response(False)
            return self._newsletter_response(self._subscribe_b2b_newsletter_email(name, email))
        return request.render(
            "casafolino_b2b_portal.newsletter",
            {
                "subscribed": post.get("subscribed"),
                "missing": post.get("missing"),
            },
        )

    @http.route(["/b2b/cart/add"], type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def b2b_cart_add(self, product_id=None, quantity=None, **kwargs):
        guard = self._guard_b2b_site()
        if guard:
            return guard
        product = request.env["product.template"].sudo().browse(int(product_id or 0)).exists()
        if not product or self._account_state() != "approved":
            return request.redirect("/b2b")
        case_size = self._case_size(product)
        qty = int(quantity or case_size)
        qty = max(case_size, qty)
        if qty % case_size:
            qty = ((qty // case_size) + 1) * case_size
        cart = self._cart()
        cart[product.id] = cart.get(product.id, 0) + qty
        self._save_cart(cart)
        self._sync_website_sale_cart(self._current_partner(), self._cart_totals())
        return request.redirect("/b2b")

    @http.route(["/b2b/cart/clear"], type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def b2b_cart_clear(self, **kwargs):
        guard = self._guard_b2b_site()
        if guard:
            return guard
        self._save_cart({})
        order = request.website.sale_get_order()
        if order:
            order.sudo().order_line.filtered(lambda line: not line.is_delivery).unlink()
            request.session["website_sale_cart_quantity"] = 0
        return request.redirect("/b2b")

    def _sync_website_sale_cart(self, partner, cart):
        order = request.website.sale_get_order(force_create=True)
        order = order.sudo()
        partner_values = {
            "partner_id": partner.id,
            "partner_invoice_id": partner.id,
            "partner_shipping_id": partner.id,
            "origin": "b2b.casafolino.com",
            "note": "Ordine ricevuto e pagato dal portale B2B CasaFolino.",
        }
        if partner.property_product_pricelist:
            partner_values["pricelist_id"] = partner.property_product_pricelist.id
        fiscal_position = request.env["account.fiscal.position"].sudo().with_company(order.company_id)._get_fiscal_position(partner, partner)
        partner_values["fiscal_position_id"] = fiscal_position.id if fiscal_position else False
        order.write(partner_values)
        order.order_line.filtered(lambda line: not line.is_delivery).unlink()
        for line in cart["lines"]:
            variant = line["product"].product_variant_id
            if not variant:
                continue
            request.env["sale.order.line"].sudo().create(
                {
                    "order_id": order.id,
                    "product_id": variant.id,
                    "product_uom_qty": line["qty"],
                    "price_unit": line["price_unit"],
                }
            )
        order._recompute_prices()
        order._recompute_taxes()
        request.session["sale_order_id"] = order.id
        request.session["website_sale_cart_quantity"] = order.cart_quantity
        return order

    @http.route(["/b2b/checkout"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def b2b_checkout(self, **kwargs):
        guard = self._guard_b2b_site()
        if guard:
            return guard
        partner = self._current_partner()
        cart = self._cart_totals()
        if not partner or not cart["can_checkout"]:
            return request.redirect("/b2b?checkout=blocked")
        self._sync_website_sale_cart(partner, cart)
        self._save_cart({})
        return request.redirect("/shop/checkout")

    @http.route(["/b2b/order/submit"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def b2b_order_submit(self, **kwargs):
        return self.b2b_checkout(**kwargs)
