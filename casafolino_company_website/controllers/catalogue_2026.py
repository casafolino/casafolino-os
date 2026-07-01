# -*- coding: utf-8 -*-
"""Renders the structured /catalogue/en-2026 fair catalog page.

Product data source: data/catalog_products.json (regenerate with
scripts/build_catalog_json.py). See README for the phase-2 plan to replace
this with a live product.template read.
"""
import json
from html import escape

from odoo.modules.module import get_module_resource

MODULE = "casafolino_company_website"

HEAD_CONSENT_SNIPPET = (
    '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}'
    "gtag('consent','default',{ad_storage:'denied',analytics_storage:'denied',"
    "ad_user_data:'denied',ad_personalization:'denied',wait_for_update:500});</script>\n"
    '  <script src="/assets/consent.js" defer></script>'
)

CATEGORY_ORDER = [
    ("spreads", "Spreads"),
    ("flavored-honeys", "Flavored honeys"),
    ("ready-risottos", "Ready risottos"),
    ("italian-spice-mixes", "Italian spice mixes"),
    ("gastronomic-mousses", "Gastronomic mousses"),
    ("crispy-chilli", "Crispy chilli"),
    ("cantucci", "Cantucci"),
    ("biscuits", "Biscuits"),
    ("chocolate-bars", "Chocolate bars"),
    ("chocolate-chunks", "Chocolate chunks"),
]

_PRODUCTS_CACHE = None


def load_products():
    global _PRODUCTS_CACHE
    if _PRODUCTS_CACHE is not None:
        return _PRODUCTS_CACHE
    path = get_module_resource(MODULE, "data", "catalog_products.json")
    with open(path, "r", encoding="utf-8") as handle:
        _PRODUCTS_CACHE = json.load(handle)
    return _PRODUCTS_CACHE


def _chip(group, value, label, active=False):
    cls = "filter-chip active" if active else "filter-chip"
    return (
        f'<button type="button" class="{cls}" data-filter-group="{escape(group)}" '
        f'data-filter-value="{escape(value)}">{escape(label)}</button>'
    )


def _product_card(p):
    return f'''<article class="product-list-card" data-category="{escape(p["category_slug"])}" data-format="{escape(p["format"])}">
        <a href="{escape(p["detail_url"])}"><img src="{escape(p["image"])}" alt="{escape(p["name"])}" loading="lazy"><h3>{escape(p["name"])}</h3><p>{escape(p["sku"])} &middot; {escape(p["format"])}</p></a>
        <div class="product-card-actions">
          <button type="button" data-request-type="techsheet" data-sku="{escape(p["sku"])}" data-name="{escape(p["name"])}">Tech sheet</button>
          <button type="button" class="primary" data-request-type="quote" data-sku="{escape(p["sku"])}" data-name="{escape(p["name"])}">Quote</button>
        </div>
      </article>'''


def render_catalogue_2026():
    products = load_products()
    category_chips = _chip("category", "all", "All categories", active=True) + "".join(
        _chip("category", slug, label) for slug, label in CATEGORY_ORDER
    )
    formats = sorted({p["format"] for p in products}, key=lambda f: float(f.split()[0]))
    format_chips = _chip("format", "all", "All formats", active=True) + "".join(
        _chip("format", fmt, fmt) for fmt in formats
    )
    cards = "\n        ".join(_product_card(p) for p in products)

    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Product Catalog 2026 — CasaFolino Italian Mediterranean Food for B2B</title>
  <meta name="description" content="Browse the full CasaFolino 2026 product catalog: {len(products)} products across 10 categories, filterable by category and format. Request a tech sheet or a quote directly.">
  <link rel="canonical" href="https://company.casafolino.com/catalogue/en-2026">
  <link rel="icon" href="/assets/logo-thumb.png" type="image/png">
  <link rel="apple-touch-icon" href="/assets/logo-thumb.png">
  <meta property="og:image" content="https://company.casafolino.com/assets/logo.png">
  <link rel="stylesheet" href="/assets/site.css">
  {HEAD_CONSENT_SNIPPET}
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/en/"><img class="brand-mark" src="/assets/logo.png" alt="" aria-hidden="true">Casa Folino<small>1962</small></a>
    <nav class="nav"><a href="/en/">Home</a><a href="/en/company-profile/">Company</a><a href="/en/catalog/">Catalog</a><a href="/catalogue/en-2026">Catalog 2026</a><a href="/en/services/">Services</a><a href="/en/fairs/">Fairs</a><a href="/en/communications/">Communications</a><a href="/en/certifications/">Certifications</a><a href="/en/sustainability/">Sustainability</a><a href="/en/contact/">Contact</a></nav>
  </header>
  <main>
    <section class="hero">
      <div class="hero-copy">
        <p class="kicker">2026 fair catalog</p>
        <h1>CasaFolino product catalog 2026 — filter, compare, request</h1>
        <p class="lead">Searchable version of the CasaFolino catalog: {len(products)} products across 10 categories. Filter by category or format, then request a tech sheet or a quote — it reaches our commercial team directly.</p>
        <div class="hero-actions">
          <a class="button" href="/en/catalog/">Legacy catalog pages</a>
          <a class="button" href="/en/contact/">Business inquiry</a>
        </div>
      </div>
      <div class="hero-document"><img src="/assets/catalog-cover.jpg" alt="CasaFolino product catalog"></div>
    </section>
    <section class="facts"><div class="fact"><strong>1962</strong><span>Founded by Antonio and Guido Folino</span></div><div class="fact"><strong>{len(products)}</strong><span>Products in this catalog</span></div><div class="fact"><strong>10</strong><span>Product categories</span></div><div class="fact"><strong>BRC</strong><span>IFS, Organic, Kosher, Halal certified facility</span></div></section>

    <section class="content-section">
      <p class="section-lead">All products below are manufactured in our BRC &amp; IFS certified facility in Lamezia Terme, Italy. This is a facility-level certification, not a per-product claim — ask our commercial team for the certificate that applies to a specific order.</p>
      <div class="filter-bar" aria-label="Catalog filters">
        <div>
          <p class="kicker">Category</p>
          {category_chips}
        </div>
        <div>
          <p class="kicker">Format</p>
          {format_chips}
        </div>
      </div>
      <p class="results-count" data-results-count>{len(products)} products</p>
      <div class="product-list-grid" data-product-grid>
        {cards}
      </div>
    </section>
  </main>

  <dialog class="request-dialog" id="request-dialog">
    <div class="request-dialog-inner">
      <button type="button" class="request-dialog-close" data-dialog-close aria-label="Close">&times;</button>
      <p class="kicker" data-dialog-kicker>Request</p>
      <h2 data-dialog-title>Request tech sheet</h2>
      <p class="lead" data-dialog-lead>Tell us where to send it — a member of our commercial team will follow up.</p>
      <form class="contact-form" id="request-form">
        <input type="hidden" name="lang" value="en">
        <input type="hidden" name="request_type" data-field="request_type">
        <input type="hidden" name="sku" data-field="sku">
        <input type="hidden" name="product_name" data-field="product_name">
        <input class="website-url" type="text" name="website_url" tabindex="-1" autocomplete="off" aria-hidden="true">
        <div class="form-row">
          <label>Name and surname<input type="text" name="name" required autocomplete="name"></label>
          <label>Company<input type="text" name="company" autocomplete="organization"></label>
        </div>
        <div class="form-row">
          <label>Email<input type="email" name="email" required autocomplete="email"></label>
          <label>Country<input type="text" name="country" autocomplete="country-name"></label>
        </div>
        <label>Message<textarea name="message" rows="4"></textarea></label>
        <label class="privacy-consent"><input type="checkbox" name="privacy_consent" value="1" required> I have read the <a href="/en/privacy-policy/">Privacy Policy</a> and consent to the processing of my data to receive a commercial reply. *</label>
        <div class="form-feedback" data-form-feedback></div>
        <div class="hero-actions"><button type="submit" class="button primary">Send request</button></div>
      </form>
    </div>
  </dialog>

  <footer class="footer institutional-footer" itemscope itemtype="https://schema.org/Organization">
    <meta itemprop="name" content="CasaFolino Srl Societ&agrave; Benefit">
    <meta itemprop="foundingDate" content="1962">
    <meta itemprop="vatID" content="IT03783120797">
    <meta itemprop="taxID" content="03783120797">
    <meta itemprop="identifier" content="SDI K95IV18">
    <meta itemprop="email" content="info@casafolino.com">
    <meta itemprop="email" content="antonio@casafolino.com">
    <meta itemprop="telephone" content="+39 0968 18 88 076">
    <span itemprop="address" itemscope itemtype="https://schema.org/PostalAddress">
      <meta itemprop="streetAddress" content="Via Prunia, 1">
      <meta itemprop="addressLocality" content="Lamezia Terme">
      <meta itemprop="addressRegion" content="CZ">
      <meta itemprop="postalCode" content="88046">
      <meta itemprop="addressCountry" content="IT">
    </span>
    <div class="footer-grid">
      <section>
        <h2>Company</h2>
        <strong>CasaFolino Srl Societ&agrave; Benefit</strong>
        <p>The Mediterranean larder — authentic Italian food for international partners since 1962.</p>
      </section>
      <section>
        <h2>Legal information</h2>
        <p>Registered office: Via Prunia, 1, 88046 Lamezia Terme (CZ), Italy</p>
        <p>VAT / Tax code (P.IVA): IT03783120797</p>
        <p>SDI: K95IV18</p>
      </section>
      <section>
        <h2>Contact</h2>
        <p>Lamezia Terme, Calabria — Italy</p>
        <p>Email: <a href="mailto:info@casafolino.com">info@casafolino.com</a></p>
        <p>Phone: <a href="tel:+3909681888076">+39 0968 18 88 076</a></p>
        <p>Direct contact: <a href="mailto:antonio@casafolino.com">antonio@casafolino.com</a></p>
      </section>
      <section>
        <h2>Explore</h2>
        <nav><a href="/en/company-profile/">Company</a><a href="/en/catalog/">Catalog</a><a href="/en/services/">Services</a><a href="/en/fairs/">Fairs</a><a href="/en/communications/">Communications</a><a href="/en/certifications/">Certifications</a><a href="/en/contact/">Contact</a></nav>
      </section>
    </div>
    <div class="footer-bottom">&copy; 2026 CasaFolino Srl Societ&agrave; Benefit — All rights reserved. | <a href="/en/privacy-policy/">Privacy Policy</a> | <a href="/en/cookie-policy/">Cookie Policy</a></div>
  </footer>

  <script>
    (function () {{
      var state = {{ category: "all", format: "all" }};
      var chips = document.querySelectorAll(".filter-chip");
      var cards = document.querySelectorAll("[data-product-grid] .product-list-card");
      var countEl = document.querySelector("[data-results-count]");
      function update() {{
        var visible = 0;
        cards.forEach(function (card) {{
          var catMatch = state.category === "all" || card.dataset.category === state.category;
          var fmtMatch = state.format === "all" || card.dataset.format === state.format;
          var show = catMatch && fmtMatch;
          card.hidden = !show;
          if (show) visible++;
        }});
        countEl.textContent = visible + " product" + (visible === 1 ? "" : "s");
      }}
      chips.forEach(function (chip) {{
        chip.addEventListener("click", function () {{
          var group = chip.dataset.filterGroup;
          state[group] = chip.dataset.filterValue;
          document.querySelectorAll('[data-filter-group="' + group + '"]').forEach(function (other) {{
            other.classList.toggle("active", other === chip);
          }});
          update();
          if (group === "category" && window.cfTrackEvent) {{
            window.cfTrackEvent("view_catalog_category", {{ catalog_category: state.category }});
          }}
        }});
      }});

      var dialog = document.getElementById("request-dialog");
      var form = document.getElementById("request-form");
      var feedback = form.querySelector("[data-form-feedback]");
      document.querySelectorAll("[data-request-type]").forEach(function (btn) {{
        btn.addEventListener("click", function () {{
          var type = btn.dataset.requestType;
          var sku = btn.dataset.sku;
          var name = btn.dataset.name;
          form.querySelector('[data-field="request_type"]').value = type;
          form.querySelector('[data-field="sku"]').value = sku;
          form.querySelector('[data-field="product_name"]').value = name;
          document.querySelector("[data-dialog-title]").textContent = (type === "quote" ? "Request quote — " : "Request tech sheet — ") + name;
          document.querySelector("[data-dialog-kicker]").textContent = sku;
          feedback.style.display = "none";
          feedback.className = "form-feedback";
          dialog.showModal();
          if (window.cfTrackEvent) {{
            window.cfTrackEvent(type === "quote" ? "request_quote" : "request_datasheet", {{ sku: sku, product_name: name }});
          }}
        }});
      }});
      dialog.querySelector("[data-dialog-close]").addEventListener("click", function () {{ dialog.close(); }});

      form.addEventListener("submit", function (event) {{
        event.preventDefault();
        var data = new FormData(form);
        fetch("/company/catalogue/lead", {{ method: "POST", body: data }})
          .then(function (res) {{ return res.ok ? res.json() : Promise.reject(); }})
          .then(function () {{
            feedback.textContent = "Request sent. CasaFolino will follow up shortly.";
            feedback.className = "form-feedback";
            feedback.style.display = "block";
            form.reset();
            if (window.cfTrackEvent) {{
              window.cfTrackEvent("business_inquiry_submit", {{
                request_type: data.get("request_type"),
                sku: data.get("sku")
              }});
            }}
            setTimeout(function () {{ dialog.close(); }}, 1800);
          }})
          .catch(function () {{
            feedback.textContent = "Please complete name, email and privacy consent.";
            feedback.className = "form-feedback error";
            feedback.style.display = "block";
          }});
      }});
    }})();
  </script>
</body>
</html>'''
