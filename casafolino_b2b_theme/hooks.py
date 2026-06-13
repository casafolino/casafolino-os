# -*- coding: utf-8 -*-

import base64
from pathlib import Path


def _post_init_hook(env):
    website = env.ref("casafolino_b2b_portal.website_b2b_casafolino", raise_if_not_found=False)
    if not website:
        website = env["website"].search([("domain", "ilike", "b2b.casafolino.com")], limit=1)
    if not website:
        return

    logo_path = Path("/mnt/extra-addons/custom/casafolino_b2b_portal/static/src/img/brand/casafolino-logo.svg")
    logo = base64.b64encode(logo_path.read_bytes()) if logo_path.exists() else False
    company_values = {
        "name": "CasaFolino Srl Societa' Benefit",
        "phone": "+39 0968 18 88 076",
        "email": "info@casafolino.com",
        "website": "https://casafolino.com",
        "street": "Via Prunia, 1",
        "city": "Lamezia Terme",
        "zip": "88046",
        "vat": "IT03783120797",
        "social_facebook": "https://www.facebook.com/casafolino",
        "social_instagram": "https://www.instagram.com/casafolino",
        "social_linkedin": "https://www.linkedin.com/company/casafolino",
    }
    if logo:
        company_values["logo"] = logo
        company_values["logo_web"] = logo
    website.company_id.write(company_values)

    website_values = {
        "name": "CasaFolino B2B",
        "homepage_url": "/b2b",
        "contact_us_button_url": "/contactus",
        "social_facebook": "https://www.facebook.com/casafolino",
        "social_instagram": "https://www.instagram.com/casafolino",
        "social_linkedin": "https://www.linkedin.com/company/casafolino",
    }
    if logo:
        website_values["logo"] = logo
    website.write(website_values)

    menu_model = env["website.menu"].sudo()
    root = menu_model.search([("website_id", "=", website.id), ("parent_id", "=", False)], limit=1)
    if not root:
        root = menu_model.create({"name": "Menu CasaFolino B2B", "url": "/", "website_id": website.id})

    wanted = [
        ("Catalogo", "/b2b", 10),
        ("Ordini", "/my/orders", 20),
        ("Fatture", "/my/invoices?filterby=invoices", 30),
        ("Contatti", "/contactus", 40),
    ]
    keep_urls = {url for _, url, _ in wanted}
    for name, url, sequence in wanted:
        menu = menu_model.search(
            [("website_id", "=", website.id), ("parent_id", "=", root.id), ("url", "=", url)],
            limit=1,
        )
        values = {
            "name": name,
            "url": url,
            "website_id": website.id,
            "parent_id": root.id,
            "sequence": sequence,
        }
        if menu:
            menu.write(values)
        else:
            menu_model.create(values)

    demo_menus = menu_model.search(
        [
            ("website_id", "=", website.id),
            ("parent_id", "=", root.id),
            ("url", "not in", list(keep_urls)),
        ]
    )
    demo_menus.unlink()

    env["ir.ui.view"].sudo().search(
        [
            "|",
            ("key", "=", "casafolino_v3.test"),
            ("arch_db", "ilike", "TEMA V3 CARICATO"),
        ]
    ).write({"active": False})

    replacements = {
        "+1 555-555-5556": "+39 0968 18 88 076",
        "+1 555-555-5555": "+39 0968 18 88 076",
        "+1%20555-555-5556": "+39%200968%2018%2088%20076",
        "+1%20555-555-5555": "+39%200968%2018%2088%20076",
        "info@yourcompany.example.com": "info@casafolino.com",
        "Nome azienda": "CasaFolino Srl Societa' Benefit",
        "YourLogo": "CasaFolino",
        "Siamo un team di persone che, con passione, si è posto l'obiettivo di migliorare la vita di tutti grazie a prodotti rivoluzionari. Sviluppiamo soluzioni eccellenti per risolvere i problemi della tua azienda. I nostri prodotti sono progettati per le piccole e medie imprese che vogliono ottimizzare le proprie prestazioni.": "CasaFolino seleziona e distribuisce specialita' alimentari italiane per operatori professionali, retail gourmet, Ho.Re.Ca. e distributori. Il portale B2B e' riservato agli acquisti all'ingrosso dei prodotti CasaFolino.",
    }
    views = env["ir.ui.view"].sudo().search(
        [
            "|",
            "|",
            "|",
            ("website_id", "=", website.id),
            ("arch_db", "ilike", "yourcompany"),
            ("arch_db", "ilike", "+1 555"),
            ("arch_db", "ilike", "+1%20555"),
        ]
    )
    for view in views:
        arch = str(view.arch_db or "")
        new_arch = arch
        for old, new in replacements.items():
            new_arch = new_arch.replace(old, new)
        if new_arch != arch:
            view.write({"arch_db": new_arch})
