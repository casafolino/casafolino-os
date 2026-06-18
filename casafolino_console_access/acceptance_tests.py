# 5 test di accettazione per console_prod_rw. Eseguito in `odoo shell -d folinofood`.
# Impersona l'utente con .with_user(): rispetta ACL + record rules. NESSUN COMMIT (rollback).
from odoo.exceptions import AccessError
def T(n, msg): print("TEST%s> %s" % (n, msg))

u = env.ref("casafolino_console_access.user_console_prod_rw")
T("", "utente console_prod_rw id=%s, gruppi=%s" % (u.id, u.groups_id.mapped("name")))
MM = env["casafolino.mail.message"].with_user(u)
Lead = env["crm.lead"].with_user(u)
Partner = env["res.partner"].with_user(u)

# --- TEST 1: legge mail di tutte le caselle ---
try:
    tot = MM.search_count([])
    a1 = MM.search_count([("account_id", "=", 1)])
    a2 = MM.search_count([("account_id", "=", 2)])
    T(1, "READ mail OK — totale=%s | acc.1(Antonio)=%s | acc.2(Martina)=%s" % (tot, a1, a2))
except AccessError as e:
    T(1, "FALLITO read: %s" % str(e).split("\n")[0])

# --- TEST 2: crea crm.lead + res.partner ---
try:
    lead = Lead.create({"name": "TEST console_prod_rw lead", "type": "lead"})
    part = Partner.create({"name": "TEST console_prod_rw partner"})
    T(2, "CREATE OK — crm.lead id=%s, res.partner id=%s" % (lead.id, part.id))
except AccessError as e:
    T(2, "FALLITO create: %s" % str(e).split("\n")[0])

# --- TEST 3: unlink di una mail → deve essere bloccato ---
mid = env["casafolino.mail.message"].sudo().search([], limit=1).id
try:
    MM.browse(mid).unlink()
    T(3, "PROBLEMA: unlink RIUSCITO su mail id=%s (atteso blocco)" % mid)
except AccessError as e:
    T(3, "unlink BLOCCATO (atteso). Errore: %s" % str(e).split("\n")[0])

# --- TEST 4: account.move read + write → bloccato ---
try:
    n = env["account.move"].with_user(u).search_count([])
    T(4, "PROBLEMA: account.move READ riuscito, count=%s (atteso blocco)" % n)
except AccessError as e:
    T(4, "account.move READ BLOCCATO (atteso). Errore: %s" % str(e).split("\n")[0])

# --- TEST 5: write sul body di una mail ---
try:
    MM.browse(mid).write({"body_html": "<p>TEST</p>"})
    T(5, "body WRITE riuscito a livello-modello → blocco body è a livello APP (documentato). mail id=%s" % mid)
except AccessError as e:
    T(5, "body WRITE bloccato anche a livello permessi: %s" % str(e).split("\n")[0])

# write SOLO triage (state) → deve riuscire (è ciò che serve)
try:
    MM.browse(mid).write({"state": "review"})
    T("5b", "write triage (state) OK — è il permesso voluto. mail id=%s" % mid)
except AccessError as e:
    T("5b", "PROBLEMA: write triage bloccato: %s" % str(e).split("\n")[0])

env.cr.rollback()
print("=== ROLLBACK eseguito: nessun dato di test persistito ===")
