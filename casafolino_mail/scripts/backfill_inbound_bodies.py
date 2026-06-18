# Backfill one-shot body — INBOUND post-aprile con body mancante.
# Eseguito in `odoo shell -d folinofood`. NON è un cron.
# - match per message_id_rfc (robusto, UID cambiano)
# - BODY.PEEK[] + select readonly → MAI \Seen sulle Gmail reali
# - idempotente: agisce solo dove body_downloaded=false
# - throttling consapevole rate-limit Gmail (sleep nel one-shot, non nel cron)
# - conta e ELENCA le irrecuperabili (Message-ID non più su IMAP)
import time
from datetime import datetime

SINCE = "2026-04-01"
THROTTLE = 0.25          # s tra una mail e l'altra
BATCH_PAUSE = 2.0        # s ogni BATCH messaggi
BATCH = 40
GMAIL_ALL = "[Gmail]/Tutta la posta"   # contiene anche le archiviate

Msg = env["casafolino.mail.message"].sudo()
Account = env["casafolino.mail.account"].sudo()

pending = Msg.search([
    ("direction", "=", "inbound"),
    ("imap_folder", "=", "INBOX"),
    ("email_date", ">=", SINCE),
    ("body_downloaded", "=", False),
], order="account_id, email_date desc")
print("BF> da processare (inbound INBOX post-%s, no body): %d" % (SINCE, len(pending)))

by_acc = {}
for m in pending:
    by_acc.setdefault(m.account_id.id, []).append(m)

done = 0
irrecuperabili = []
seen_check = None

for aid, msgs in by_acc.items():
    acc = Account.browse(aid)
    print("BF> account %s: %d mail" % (acc.name, len(msgs)))
    try:
        imap = acc._get_imap_connection()
    except Exception as e:
        print("BF> ERRORE connessione %s: %s" % (acc.name, str(e)[:120]))
        continue
    # seleziona Tutta la posta (fallback INBOX) in READONLY
    folder = GMAIL_ALL
    status, _ = imap.select('"%s"' % folder, readonly=True)
    if status != "OK":
        folder = "INBOX"
        imap.select('"%s"' % folder, readonly=True)
    print("BF> folder selezionato (readonly): %s" % folder)

    for idx, m in enumerate(msgs):
        mid = (m.message_id_rfc or "").strip()
        if not mid:
            irrecuperabili.append((m.id, "no-message-id"))
            continue
        try:
            # match robusto per Message-ID header
            st, data = imap.search(None, 'HEADER Message-ID "%s"' % mid)
            uids = data[0].split() if (st == "OK" and data and data[0]) else []
            if not uids:
                irrecuperabili.append((m.id, mid))
                continue
            uid = uids[-1]

            # \Seen check sulla PRIMA mail: FLAGS prima/dopo il PEEK
            if seen_check is None:
                fs, fd = imap.fetch(uid, "(FLAGS)")
                seen_check = {"id": m.id, "before": (fd[0].decode() if fd and fd[0] else "")}

            st2, msg_data = imap.fetch(uid, "(BODY.PEEK[])")
            if st2 != "OK":
                irrecuperabili.append((m.id, "fetch-fail"))
                continue
            raw = None
            for part in msg_data:
                if isinstance(part, tuple):
                    raw = part[1]; break
            if not raw:
                irrecuperabili.append((m.id, "empty-body"))
                continue
            import email as _email
            parsed = _email.message_from_bytes(raw)
            body_html, body_text = Account._extract_body(parsed)
            if not (body_html or body_text):
                irrecuperabili.append((m.id, "no-text-part"))
                continue
            m.write({
                "body_html": body_html or ("<pre>%s</pre>" % body_text),
                "body_plain": body_text or False,
                "body_downloaded": True,
                "fetch_state": "done",
                "fetch_error_msg": False,
            })
            done += 1

            # \Seen check after, sulla stessa prima mail
            if seen_check and seen_check["id"] == m.id and "after" not in seen_check:
                fs2, fd2 = imap.fetch(uid, "(FLAGS)")
                seen_check["after"] = fd2[0].decode() if fd2 and fd2[0] else ""

            env.cr.commit()
            time.sleep(THROTTLE)
            if (idx + 1) % BATCH == 0:
                print("BF>   %s: %d/%d ok" % (acc.name, idx + 1, len(msgs)))
                time.sleep(BATCH_PAUSE)
        except Exception as e:
            irrecuperabili.append((m.id, "err:%s" % str(e)[:60]))
            env.cr.rollback()
    try:
        imap.logout()
    except Exception:
        pass

print("BF> ===== RISULTATO =====")
print("BF> recuperate: %d" % done)
print("BF> irrecuperabili: %d" % len(irrecuperabili))
if seen_check:
    print("BF> \\Seen check mail id=%s: FLAGS before=%s | after=%s" % (seen_check["id"], seen_check.get("before"), seen_check.get("after")))
if irrecuperabili:
    print("BF> elenco irrecuperabili (id, motivo) prime 30:")
    for r in irrecuperabili[:30]:
        print("BF>   ", r)
env.cr.commit()
print("BF> FINE (committato).")
