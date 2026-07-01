#!/usr/bin/env python3
"""Regenerate data/catalog_products.json by parsing the existing EN catalog category pages.

Source of truth: static/src/site/en/catalog/<category>/index.html (product-list-grid markup).
Run manually after editing a category page:
    python3 scripts/build_catalog_json.py
"""
import json
import re
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent.parent
CATALOG_ROOT = MODULE_ROOT / "static/src/site/en/catalog"
OUT_PATH = MODULE_ROOT / "data/catalog_products.json"

CATEGORY_LABELS = {
    "spreads": "Spreads",
    "flavored-honeys": "Flavored honeys",
    "ready-risottos": "Ready risottos",
    "italian-spice-mixes": "Italian spice mixes",
    "gastronomic-mousses": "Gastronomic mousses",
    "crispy-chilli": "Crispy chilli",
    "cantucci": "Cantucci",
    "biscuits": "Biscuits",
    "chocolate-bars": "Chocolate bars",
    "chocolate-chunks": "Chocolate chunks",
}

CARD_RE = re.compile(
    r'<article class="product-list-card"><a href="/en/catalog/(?P<cat>[a-z-]+)/(?P<slug>[a-z0-9-]+)/">'
    r'<img src="/assets/products/(?P<img>[a-z0-9-]+\.jpg)" alt="[^"]*">'
    r'<h3>(?P<name>[^<]+)</h3><p>(?P<code>[A-Z0-9]+)\s*·\s*(?P<format>[^<]+)</p></a></article>',
)


def main():
    products = []
    seen_codes = set()
    for slug, label in CATEGORY_LABELS.items():
        page = CATALOG_ROOT / slug / "index.html"
        if not page.is_file():
            raise SystemExit(f"missing category page: {page}")
        html = page.read_text(encoding="utf-8")
        matches = list(CARD_RE.finditer(html))
        if not matches:
            raise SystemExit(f"no product cards parsed from {page} — markup changed?")
        for m in matches:
            code = m.group("code")
            if code in seen_codes:
                continue
            seen_codes.add(code)
            products.append(
                {
                    "sku": code,
                    "name": m.group("name").strip(),
                    "slug": m.group("slug"),
                    "category_slug": slug,
                    "category_label": label,
                    "format": m.group("format").strip(),
                    "image": f"/assets/products/{m.group('img')}",
                    "detail_url": f"/en/catalog/{slug}/{m.group('slug')}/",
                    "certifications": ["BRC", "IFS"],
                }
            )

    products.sort(key=lambda p: (p["category_label"], p["name"]))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(products)} products to {OUT_PATH}")


if __name__ == "__main__":
    main()
