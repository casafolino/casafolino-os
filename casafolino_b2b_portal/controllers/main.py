# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class CasaFolinoB2BPortal(http.Controller):
    FALLBACK_IMAGES = [
        "/casafolino_b2b_portal/static/src/img/products/crema-pistacchio.png",
        "/casafolino_b2b_portal/static/src/img/products/caramello-salato.png",
        "/casafolino_b2b_portal/static/src/img/products/miedelizie-nocciole.png",
        "/casafolino_b2b_portal/static/src/img/products/risotto-tartufo.png",
        "/casafolino_b2b_portal/static/src/img/products/spezia-puttanesca.png",
        "/casafolino_b2b_portal/static/src/img/products/mousse-gianduia.png",
    ]

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
        domain = [("sale_ok", "=", True)]
        if "website_published" in request.env["product.template"]._fields:
            domain.append(("website_published", "=", True))
        return domain

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

    def _catalog_products(self):
        Product = request.env["product.template"].sudo()
        products = Product.search(self._product_domain(), order="sequence, name", limit=36)
        result = []
        for index, product in enumerate(products):
            case_size = product.cf_b2b_case_size or 6
            result.append(
                {
                    "record": product,
                    "case_size": case_size,
                    "price": self._product_price(product, case_size),
                    "image_url": (
                        f"/web/image/product.template/{product.id}/image_1024"
                        if product.image_1024
                        else self.FALLBACK_IMAGES[index % len(self.FALLBACK_IMAGES)]
                    ),
                }
            )
        return result

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
                    "case_size": product.cf_b2b_case_size or 6,
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
        return request.render(
            "casafolino_b2b_portal.catalog",
            {
                "account_state": self._account_state(),
                "products": self._catalog_products(),
                "cart": self._cart_totals(),
            },
        )

    @http.route(["/b2b/register"], type="http", auth="public", website=True, sitemap=True, methods=["GET", "POST"], csrf=True)
    def b2b_register(self, **post):
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
                    "street": (post.get("street") or "").strip(),
                    "cf_b2b_status": "pending",
                    "comment": (post.get("notes") or "").strip(),
                }
            )
            partner.message_post(body="Richiesta accesso B2B ricevuta da b2b.casafolino.com.")
            return request.redirect("/b2b/register?sent=1")
        return request.render("casafolino_b2b_portal.register", {"sent": kwargs.get("sent"), "missing": kwargs.get("missing")})

    @http.route(["/b2b/cart/add"], type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def b2b_cart_add(self, product_id=None, quantity=None, **kwargs):
        product = request.env["product.template"].sudo().browse(int(product_id or 0)).exists()
        if not product or self._account_state() != "approved":
            return request.redirect("/b2b")
        case_size = product.cf_b2b_case_size or 6
        qty = int(quantity or case_size)
        qty = max(case_size, qty)
        if qty % case_size:
            qty = ((qty // case_size) + 1) * case_size
        cart = self._cart()
        cart[product.id] = cart.get(product.id, 0) + qty
        self._save_cart(cart)
        return request.redirect("/b2b")

    @http.route(["/b2b/cart/clear"], type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def b2b_cart_clear(self, **kwargs):
        self._save_cart({})
        return request.redirect("/b2b")

    @http.route(["/b2b/order/submit"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def b2b_order_submit(self, **kwargs):
        partner = self._current_partner()
        cart = self._cart_totals()
        if not partner or not cart["can_checkout"]:
            return request.redirect("/b2b?checkout=blocked")
        order = request.env["sale.order"].sudo().create(
            {
                "partner_id": partner.id,
                "origin": "b2b.casafolino.com",
                "note": "Ordine ricevuto dal portale B2B CasaFolino.",
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": line["product"].product_variant_id.id,
                            "product_uom_qty": line["qty"],
                            "price_unit": line["price_unit"],
                        },
                    )
                    for line in cart["lines"]
                    if line["product"].product_variant_id
                ],
            }
        )
        self._save_cart({})
        return request.render("casafolino_b2b_portal.thank_you", {"order": order})
