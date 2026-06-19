# RECON (rollback): un PORTAL user può read/write scoped via ACL diretta? odoo shell -d folinofood.
# Crea gruppo+ACL+rule+utente portal IN TRANSAZIONE, testa, poi ROLLBACK (niente persiste).
from odoo.exceptions import AccessError
def R(m): print("RECON> " + m)

# gruppo standalone (NO implied group_user → resta portal)
grp = env["res.groups"].create({"name": "TEST Portal API"})
IMA = env["ir.model.access"]
def acl(model, r, w, c, u):
    mid = env["ir.model"].search([("model", "=", model)], limit=1)
    if mid:
        IMA.create({"name": "test_%s" % model.replace(".", "_"), "model_id": mid.id, "group_id": grp.id,
                    "perm_read": r, "perm_write": w, "perm_create": c, "perm_unlink": u})
acl("crm.lead", 1, 1, 1, 0)
acl("res.partner", 1, 1, 1, 0)
acl("casafolino.mail.message", 1, 1, 0, 0)
# rule read-all mail per il gruppo
mm = env["ir.model"].search([("model", "=", "casafolino.mail.message")], limit=1)
env["ir.rule"].create({"name": "test read all mail", "model_id": mm.id, "groups": [(6,0,[grp.id])],
                       "domain_force": "[(1,'=',1)]", "perm_read": True, "perm_write": True, "perm_create": False, "perm_unlink": False})
env["ir.rule"].create({"name": "test read all lead", "model_id": env["ir.model"].search([("model","=","crm.lead")],limit=1).id,
                       "groups": [(6,0,[grp.id])], "domain_force": "[(1,'=',1)]", "perm_read": True, "perm_write": True, "perm_create": True, "perm_unlink": False})

# utente PORTAL (group_portal → share=True) + gruppo custom
u = env["res.users"].with_context(no_reset_password=True).create({
    "name": "TEST portal api", "login": "test_portal_api_recon",
    "groups_id": [(6, 0, [env.ref("base.group_portal").id, grp.id])],
})
R("utente creato id=%s share=%s (share=True atteso → portal, no seat)" % (u.id, u.share))

# TEST READ
for model in ["casafolino.mail.message", "crm.lead", "res.partner"]:
    try:
        n = env[model].with_user(u).search_count([])
        R("READ %s = %s" % (model, n))
    except AccessError as e:
        R("READ %s BLOCCATO: %s" % (model, str(e).split(chr(10))[0]))

# TEST WRITE lead (create)
try:
    lead = env["crm.lead"].with_user(u).create({"name": "TEST portal lead", "type": "lead"})
    R("CREATE crm.lead OK id=%s" % lead.id)
except AccessError as e:
    R("CREATE crm.lead BLOCCATO: %s" % str(e).split(chr(10))[0])
except Exception as e:
    R("CREATE crm.lead ERRORE(non-Access): %s: %s" % (type(e).__name__, str(e).split(chr(10))[0]))

# TEST WRITE triage state su 1 mail reale
mid = env["casafolino.mail.message"].sudo().search([], limit=1)
if mid:
    try:
        mid.with_user(u).write({"state": "review"})
        R("WRITE triage state OK su mail id=%s" % mid.id)
    except AccessError as e:
        R("WRITE triage BLOCCATO: %s" % str(e).split(chr(10))[0])
    except Exception as e:
        R("WRITE triage ERRORE(non-Access): %s: %s" % (type(e).__name__, str(e).split(chr(10))[0]))

# GUARDRAIL: unlink mail, account.move
try:
    mid.with_user(u).unlink(); R("PROBLEMA: unlink riuscito")
except Exception as e:
    R("unlink BLOCCATO (atteso): %s: %s" % (type(e).__name__, str(e).split(chr(10))[0][:60]))
try:
    n = env["account.move"].with_user(u).search_count([]); R("PROBLEMA: account.move letto=%s" % n)
except Exception as e:
    R("account.move BLOCCATO (atteso): %s: %s" % (type(e).__name__, str(e).split(chr(10))[0][:60]))

env.cr.rollback()
R("ROLLBACK — niente persiste.")
