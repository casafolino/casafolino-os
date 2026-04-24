# Fix Cron 82 — IMAP Timeout + Deferred Body Download

**Data**: 2026-04-25
**Modulo**: casafolino_mail
**File modificato**: `casafolino_mail/models/casafolino_mail_account.py`
**Commit**: `3a7ea9e`

---

## Problema

Cron 82 (CasaFolino Mail Sync V2) si bloccava all'infinito quando Gmail smetteva di rispondere mid-FETCH. Causa: `imaplib.IMAP4_SSL()` senza parametro `timeout` + Odoo senza workers (nessun watchdog). Body download inline amplificava la finestra di rischio (2N+1 comandi IMAP per N email).

## Fix applicato (3 righe)

1. **timeout=60** su `IMAP4_SSL()` e `IMAP4()` — se Gmail non risponde entro 60s, `socket.timeout` viene lanciato e catturato dal try/except esistente
2. **Body download deferred** — rimossa chiamata `_download_body_imap()` inline; cron 85 (Body Fetch Pending, ogni 10 min) scarica i body in background

## Diff

```diff
- imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
+ imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, timeout=60)

- imap = imaplib.IMAP4(self.imap_host, self.imap_port)
+ imap = imaplib.IMAP4(self.imap_host, self.imap_port, timeout=60)

- new_msg._download_body_imap(imap, folder_name, uid_str)
+ # Body download deferred to cron 85 (Body Fetch Pending)
```

## Risultati prod

- Cron 82: 3 account in **24.3s** (prima: 473s per 52 email con body inline)
- Zero errori, zero timeout, zero traceback
- Cron 85: scarica 50 body per run in ~10s
- TEST OK utente: email reali visibili in Mail Hub

## Rollback

```bash
# 1. Disabilita cron 82
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c \
  "UPDATE ir_cron SET active=false WHERE id=82;"

# 2. Ripristina codice precedente
cd /home/ubuntu/casafolino-os && git checkout 089df27 -- casafolino_mail/models/casafolino_mail_account.py && \
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http 2>&1 | tail -10 && \
docker restart odoo-app
```
