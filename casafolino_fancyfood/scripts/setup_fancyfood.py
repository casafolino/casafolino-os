"""Idempotent prod data wiring for casafolino_fancyfood.

Run inside the Odoo shell (env available), with the 4 source files placed on the
host at /tmp/fancyfood/ :
    docker exec -i odoo-app odoo shell -d folinofood --no-http < setup_fancyfood.py
"""
import base64


def _b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read())


FILES = {
    "catalogue": ("/tmp/fancyfood/CasaFolino_Catalogue_EN_300dpi.pdf",
                  "CasaFolino_Catalogue_2026.pdf", "application/pdf",
                  "casafolino.fancyfood.catalogue_att_id"),
    "profile":   ("/tmp/fancyfood/Company_Profile_corretto.pdf",
                  "CasaFolino Company Profile.pdf", "application/pdf",
                  "casafolino.fancyfood.profile_att_id"),
    "brochure":  ("/tmp/fancyfood/Company_Brochure_EN.pdf",
                  "CasaFolino Company Brochure.pdf", "application/pdf",
                  "casafolino.fancyfood.brochure_att_id"),
    "logo":      ("/tmp/fancyfood/folino_logo.png",
                  "folino_logo.png", "image/png",
                  "casafolino.fancyfood.logo_att_id"),
}

ICP = env["ir.config_parameter"].sudo()
Att = env["ir.attachment"].sudo()
att_ids = {}

for key, (path, name, mime, param) in FILES.items():
    data = _b64(path)
    existing = ICP.get_param(param)
    att = Att.browse(int(existing)) if existing else Att.browse()
    if att and att.exists():
        att.write({"datas": data, "name": name, "mimetype": mime, "public": True})
    else:
        att = Att.create({
            "name": name, "datas": data, "mimetype": mime,
            "public": True, "res_model": False, "res_id": False,
        })
        ICP.set_param(param, str(att.id))
    att_ids[key] = att.id
    print("attachment", key, "->", att.id, "(%s bytes)" % att.file_size)

# IT catalogue: reuse the existing Italian general catalogue attachment (41437),
# only if present and not already configured. IT PDF route falls back to EN otherwise.
IT_PARAM = "casafolino.fancyfood.catalogue_it_att_id"
if not ICP.get_param(IT_PARAM):
    it_att = Att.search(
        [("name", "ilike", "Catalogo Generale%ITA%"), ("mimetype", "=", "application/pdf")],
        order="id desc", limit=1,
    )
    if not it_att:
        it_att = Att.browse(41437).exists()
    if it_att:
        ICP.set_param(IT_PARAM, str(it_att.id))
        print("IT catalogue attachment ->", it_att.id)

# wire Company Profile + Brochure onto both templates
prof, broc = att_ids["profile"], att_ids["brochure"]
for xmlid in ("casafolino_fancyfood.mail_template_fancyfood_en",
              "casafolino_fancyfood.mail_template_fancyfood_it"):
    tmpl = env.ref(xmlid, raise_if_not_found=False)
    if tmpl:
        tmpl.attachment_ids = [(6, 0, [prof, broc])]
        print("wired attachments on", xmlid)

# backfill tokens for already-tagged partners
tag = env.ref("casafolino_fancyfood.tag_partner_fancyfood", raise_if_not_found=False)
if tag:
    parts = env["res.partner"].sudo().search([("category_id", "in", tag.ids)])
    parts._ensure_fancyfood_token()
    print("tokens backfilled for", len(parts), "partner(s)")

env.cr.commit()
print("DONE fancyfood setup")
