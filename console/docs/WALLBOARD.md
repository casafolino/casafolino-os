# Wallboard multi-reparto — note operative

Sistema di wallboard da monitor con scene per reparto e **separazione dati server-side**.

## Scene

| URL (dev) | URL (prod, basePath `/console`) | Scope | Dati economici |
|---|---|---|---|
| `/wallboard/produzione?k=<TOKEN>` | `/console/wallboard/produzione?k=<TOKEN>` | `production` | **mai** |
| `/wallboard/vetrina?k=<TOKEN>` | `/console/wallboard/vetrina?k=<TOKEN>` | `vetrina` | solo % crescita (default) |
| `/wallboard/ufficio?k=<TOKEN>` | `/console/wallboard/ufficio?k=<TOKEN>` | `ufficio` | sì |

> **basePath**: la console gira sotto `/console` (nginx). Next applica un solo `basePath`
> globale, quindi in prod le scene vivono sotto `/console/wallboard/...`. Le fetch client
> usano `BP` (`lib/basePath.ts`) e si adattano da sole. Per servire URL puliti `/wallboard`
> serve un rewrite nginx → `/console/wallboard`, altrimenti usare direttamente `/console/wallboard`.

## Token-scena (sicurezza)

Ogni monitor apre la scena con `?k=<token>`. Il token mappa a uno scope; ogni endpoint
`/api/wb/*` dichiara gli scope ammessi (`lib/wb/scope.ts`). Scope non ammesso → **HTTP 403**,
nessun dato. Un monitor `production` non può ottenere fatturato/pipeline nemmeno via URL/devtools.

Variabili d'ambiente (3 token casuali, **mai committare** — vanno in `console.prod.env`):

```
WB_TOKEN_PROD=<random>
WB_TOKEN_VETRINA=<random>
WB_TOKEN_UFFICIO=<random>
# opzionale: esporre la CIFRA di fatturato anche in vetrina (default false → solo %)
SHOW_REVENUE_FIGURE=false
# opzionale: target fatturato mese (altrimenti letto da ir.config_parameter casafolino.wb_revenue_target)
```

Genera i token: `openssl rand -hex 24`.

> **Fallback dev**: in mock mode (`CONSOLE_USE_MOCK=1`) e senza `WB_TOKEN_*` impostati,
> gli endpoint accettano i nomi scope letterali (`?k=production|vetrina|ufficio`) come token,
> per testare in locale. Inattivo in prod reale (token env presenti).

## Endpoint → scope ammessi

| Endpoint | Scene |
|---|---|
| production-queue, mrp-active | produzione, ufficio |
| tasks-today, qc-blocks | produzione |
| shipments-today | produzione, vetrina |
| export-countries, next-fair, ticker | vetrina, ufficio |
| certifications | vetrina |
| revenue-mtd | vetrina, ufficio (**mai** production) |
| pipeline | **solo** ufficio |

## ACL Odoo (gateway `casafolino_console_access` v18.0.6.20.0)

Aggiunto **READ-ONLY** a `group_console_api` su: `stock.picking`, `mrp.production`,
`account.move` (deroga consapevole al divieto storico, solo lettura aggregata),
`cf.export.fair`, `res.country`. Nessun write/create/unlink, mai.

Deploy addon su EC2 (richiede pg_dump + stop crons → vedi CLAUDE.md deploy flow):

```bash
# pg_dump di sicurezza
docker exec -e PGPASSWORD=odoo odoo-app pg_dump -h odoo-db -U odoo folinofood > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql
# disabilita crons 82,83,84,53218 da UI (Settings → Technical → Scheduled Actions)
cd /home/ubuntu/casafolino-os && git pull
sudo cp -rf casafolino_console_access /docker/enterprise18/addons/custom/
docker exec odoo-app odoo -d folinofood_stage -u casafolino_console_access --stop-after-init --no-http 2>&1 | tail -15
docker restart odoo-app
# verifica stage, poi prod (-d folinofood), riabilita crons
```

## Refresh (SWR-like, polling client `usePoll`)

tasks 20s · mrp 30s · qc 20s · ordini 30s · spedizioni 60s · revenue/export 5min ·
ticker 60s · fiera 1h · certs mai · pipeline 60s. Pausa quando il tab è in background;
`prefers-reduced-motion` ferma il ticker.

## Nginx

```nginx
location /wallboard {
    proxy_pass http://127.0.0.1:3200;   # stesso container console
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
}
```

Con `NEXT_PUBLIC_BASE_PATH=/console` usare invece `/console/wallboard/...` (già coperto
dalla location `/console` esistente) — la location `/wallboard` separata serve solo se si
vogliono URL puliti, e va accoppiata a un `rewrite ^/wallboard(.*)$ /console/wallboard$1`.

---

## V2 — Azionabilità + scene logistica/direzione

### Nuove scene

| URL (dev) | Scope | Token env | Economici |
|---|---|---|---|
| `/wallboard/logistica?k=…` | `logistica` | `WB_TOKEN_LOGISTICA` | **mai** |
| `/wallboard/direzione?k=…` | `direzione` | `WB_TOKEN_DIREZIONE` | sì (fatturato) |

Genera i token: `openssl rand -hex 24`.

### Da tarare (confermare con Antonio)
- **`lib/wb/cutoffs.ts`** — orari ritiro corrieri (placeholder DHL 16:00 / GLS 15:30 / BRT 16:30). Match per substring sul nome `carrier_id`.
- **`lib/wb/thresholds.ts`** — soglie ritardo ordini, raccolta cut-off (warn 60min / alert 20min), raffreddamento follow-up (warn 5g / alert 7g), lotti non avviati. Pacing obiettivo: giornata lavorativa 08:00–18:00 (`workdayFraction`).
- **Obiettivo del giorno** — di default da Odoo: produzione = `mrp.production.date_start` di oggi; logistica = `stock.picking` outgoing `scheduled_date` di oggi. Nessun override manuale per ora (si può aggiungere via `ir.config_parameter`).

### Meccanismi trasversali
- **Soglie semaforiche**: un tile è colorato (warn/alert) solo se supera soglia; stato normale resta pastello.
- **FreshnessBadge** in header: secondi dall'ultimo fetch; giallo se fallito o > 90s.
- **Coda priorità**: ordini per scadenza più vicina poi dimensione; max 5 righe + "+N altri"; ritardi evidenziati.
- **Feedback completamenti**: flash verde 3s sull'incremento del contatore (disattivo con `prefers-reduced-motion`, contatore comunque aggiornato).
- **Rotazione viste**: `?rotate=20` cicla le sotto-viste ogni 20s; si blocca sulla vista critica se c'è un alert.

### Nuovi endpoint
`/api/wb/daily-goal?dept=produzione|logistica` · `/api/wb/cutoffs` · `/api/wb/exceptions` (scope direzione/ufficio, solo item warn/alert).

### ACL
Nessuna nuova ACL Odoo rispetto a v18.0.6.20.0: tutte le letture V2 (stock.picking, mrp.production, crm.lead) sono già concesse a `console_api`.
