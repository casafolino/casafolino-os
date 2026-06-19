# Provisiona console_api. odoo shell -d folinofood.
# NB: Odoo limita le API key dei PORTAL user a max 1 giorno (non viable per service-user) →
# si usa la PASSWORD come secret RPC (senza scadenza, server-side, revocabile cambiandola).
# Scrive /tmp/console_api_creds DENTRO il container (secret NON stampato).
import secrets
u = env["res.users"].sudo().search([("login", "=", "console_api")], limit=1)
if not u:
    print("PROV> ERRORE: console_api assente")
else:
    pwd = secrets.token_urlsafe(30)
    u.write({"password": pwd})
    env.cr.commit()
    with open("/tmp/console_api_creds", "w") as f:
        f.write("ODOO_USERNAME=console_api\nODOO_API_KEY=%s\n" % pwd)
    print("PROV> console_api id=%s: password (len=%d) set + commit → /tmp/console_api_creds" % (u.id, len(pwd)))
