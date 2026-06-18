# Concede a 'Console (sola lettura)' la LETTURA di tutte le mail (Antonio+Martina)
# senza write. Record rule permissiva (OR) + ACL read su casafolino.mail.account.
# Eseguito in `odoo shell -d folinofood`. Solo READ, nessuna scrittura ai dati business.
def out(m): print("GRANT> " + m)

grp = env["res.groups"].search([("name", "=", "Console (sola lettura)")], limit=1)
if not grp:
    out("ERRORE: gruppo 'Console (sola lettura)' assente — esegui prima provision_prod_ro.py")
else:
    out("group id=%s" % grp.id)

    # record rule: vede TUTTE le casafolino.mail.message (read-only). Permissiva → OR con le altre.
    mm = env["ir.model"].search([("model", "=", "casafolino.mail.message")], limit=1)
    rname = "Console RO: vede tutte le mail (read-only)"
    rule = env["ir.rule"].search([("name", "=", rname)], limit=1)
    rvals = {"name": rname, "model_id": mm.id, "groups": [(6, 0, [grp.id])],
             "domain_force": "[(1, '=', 1)]",
             "perm_read": True, "perm_write": False, "perm_create": False, "perm_unlink": False}
    if rule:
        rule.write(rvals); out("record rule aggiornata id=%s" % rule.id)
    else:
        rule = env["ir.rule"].create(rvals); out("record rule creata id=%s" % rule.id)

    # ACL read su casafolino.mail.account (per nomi caselle / filtro)
    acc_model = env["ir.model"].search([("model", "=", "casafolino.mail.account")], limit=1)
    IMA = env["ir.model.access"]
    acc = IMA.search([("group_id", "=", grp.id), ("model_id", "=", acc_model.id)], limit=1)
    avals = {"name": "console_ro_casafolino_mail_account", "model_id": acc_model.id, "group_id": grp.id,
             "perm_read": True, "perm_write": False, "perm_create": False, "perm_unlink": False}
    if acc:
        acc.write(avals); out("ACL account aggiornata")
    else:
        IMA.create(avals); out("ACL account creata")

    env.cr.commit()
    out("COMMIT OK")
