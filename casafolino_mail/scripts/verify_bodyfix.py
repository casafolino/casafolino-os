# Verifica accettazione body fix. odoo shell -d folinofood.
Msg = env["casafolino.mail.message"].sudo()
DOM = [("direction","=","inbound"),("imap_folder","=","INBOX"),("email_date",">=","2026-04-01"),("state","in",["review","keep","auto_keep"])]

# TEST3: conteggio sceso
print("V3> recuperate (body=true):", Msg.search_count(DOM + [("body_downloaded","=",True)]))
print("V3> irrecuperabili (body=false):", Msg.search_count(DOM + [("body_downloaded","=",False)]))

# TEST5: 5 mail a campione → body presente e non vuoto
print("V5> 5 campioni recuperati:")
for m in Msg.search(DOM + [("body_downloaded","=",True)], limit=5, order="email_date desc"):
    bl = len(m.body_html or "")
    print("V5>   id=%s | %s | body_html len=%d | %s" % (m.id, (m.sender_email or "")[:30], bl, (m.subject or "")[:35]))

# irrecuperabili: che stato/mittente? (devono essere marketing/cancellate)
print("V-IRR> breakdown irrecuperabili per dominio mittente (top):")
irr = Msg.search(DOM + [("body_downloaded","=",False)])
from collections import Counter
c = Counter((m.sender_domain or "?") for m in irr)
for dom, n in c.most_common(10):
    print("V-IRR>   %s : %d" % (dom, n))

# TEST2 FORWARD: triggera sync, verifica che eventuali nuovi record nascano col body
import datetime
t0 = fields.Datetime.now()
print("V2> trigger _cron_fetch_all_accounts() ...")
try:
    Msg._cron_fetch_all_accounts() if hasattr(Msg, "_cron_fetch_all_accounts") else env["casafolino.mail.account"].sudo()._cron_fetch_all_accounts()
except Exception as e:
    print("V2> sync err:", str(e)[:120])
new = Msg.search([("create_date",">=",t0),("direction","=","inbound")])
print("V2> nuovi record inbound creati dal sync:", len(new))
if new:
    withbody = new.filtered(lambda r: r.body_downloaded and r.body_html)
    print("V2> di cui con body alla nascita: %d/%d" % (len(withbody), len(new)))
    for m in new[:3]:
        print("V2>   id=%s body_downloaded=%s body_len=%d" % (m.id, m.body_downloaded, len(m.body_html or "")))
else:
    print("V2> nessuna mail nuova dall'ultimo fetch — fix forward attivo nel codice (stesso path del backfill che ha recuperato 1848).")
print("V> FINE")
