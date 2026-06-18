# Provisiona utente API PROD dedicato, SOLA LETTURA. Eseguito in `odoo shell -d folinofood`.
# Crea: gruppo RO + ACL read-only sui modelli letti dalla console + utente + api key.
# Scrive /tmp/console.prod.env DENTRO il container (la chiave NON viene stampata).
LOGIN = "console_prod_ro"
GROUP = "Console (sola lettura)"
# modelli che la console legge (gli altri read arrivano da group_user: res.partner/users/country)
READ_MODELS = [
    "crm.lead", "crm.stage", "casafolino.mail.message",
    "project.project", "cf.export.sample", "cf.export.fair", "sale.order",
]

def out(msg):
    print("PROVISION> " + msg)

# gruppo RO (idempotente)
grp = env["res.groups"].search([("name", "=", GROUP)], limit=1)
if not grp:
    grp = env["res.groups"].create({"name": GROUP})
    out("group creato id=%s" % grp.id)
else:
    out("group esistente id=%s" % grp.id)

# ACL read-only (idempotente per modello)
IMA = env["ir.model.access"]
for mname in READ_MODELS:
    model = env["ir.model"].search([("model", "=", mname)], limit=1)
    if not model:
        out("MODELLO ASSENTE (skip): %s" % mname)
        continue
    acc = IMA.search([("group_id", "=", grp.id), ("model_id", "=", model.id)], limit=1)
    vals = {"name": "console_ro_%s" % mname.replace(".", "_"),
            "model_id": model.id, "group_id": grp.id,
            "perm_read": True, "perm_write": False, "perm_create": False, "perm_unlink": False}
    if acc:
        acc.write(vals)
    else:
        IMA.create(vals)
    out("ACL read-only: %s" % mname)

# utente dedicato (idempotente), interno, NESSUN gruppo admin/settings
user = env["res.users"].search([("login", "=", LOGIN)], limit=1)
gids = [(6, 0, [env.ref("base.group_user").id, grp.id])]
if not user:
    user = env["res.users"].with_context(no_reset_password=True, mail_create_nosubscribe=True).create({
        "name": "Console PROD (sola lettura)",
        "login": LOGIN,
        "groups_id": gids,
        "notification_type": "inbox",
    })
    out("utente creato id=%s login=%s" % (user.id, LOGIN))
else:
    user.write({"groups_id": gids})
    out("utente esistente id=%s aggiornato" % user.id)

# api key (genera nuova; le vecchie restano ma usiamo questa)
import datetime
# prod impone max 90 giorni → 89 giorni. NB: chiave da ruotare prima della scadenza.
expiry = datetime.datetime.now() + datetime.timedelta(days=89)
gen = env["res.users.apikeys"].with_user(user)
try:
    key = gen._generate("rpc", "console prod ro", expiry)
except TypeError:
    # versioni con firma a 2 arg
    key = gen._generate("rpc", "console prod ro")
out("api key generata (len=%d, scad=%s)" % (len(key), expiry.date()))

# scrive env DENTRO il container — chiave mai su stdout
content = "".join([
    "CONSOLE_USE_MOCK=0\n",
    "ODOO_URL=http://odoo-app:8069\n",
    "ODOO_DB=folinofood\n",
    "ODOO_USERNAME=%s\n" % LOGIN,
    "ODOO_API_KEY=%s\n" % key,
])
with open("/tmp/console.prod.env", "w") as f:
    f.write(content)
out("scritto /tmp/console.prod.env (chiave inclusa, non stampata)")

env.cr.commit()
out("COMMIT OK")
