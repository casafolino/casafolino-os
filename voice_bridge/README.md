# CasaFolino Voice Bridge

Bridge esterno per collegare telefonia SIP/OpenAI Realtime a Odoo.

## Stato

Questo servizio e pronto per:

- ricevere webhook `realtime.call.incoming` da OpenAI SIP;
- chiedere a Odoo routing, agente e tool schema;
- accettare la chiamata Realtime;
- ascoltare gli eventi Realtime via WebSocket;
- inoltrare function call del modello agli endpoint Odoo;
- inoltrare richieste di trasferimento umano verso OpenAI `refer`.

La chiave OpenAI resta fuori dal codice e va inserita domani in `OPENAI_API_KEY`.

## Configurazione

```bash
cp .env.example .env
```

Variabili principali:

- `ODOO_BASE_URL`: URL Odoo raggiungibile dal bridge. Usare `http://51.44.170.55:4589` finche DNS/HTTPS non sono confermati.
- `ODOO_DB`: database Odoo, normalmente `folinofood`.
- `ODOO_WEBHOOK_TOKEN`: bearer token configurato in Odoo.
- `OPENAI_API_KEY`: chiave OpenAI, da aggiungere quando disponibile.
- `OPENAI_WEBHOOK_SECRET`: opzionale, usato per verificare header `x-casafolino-bridge-secret`.

## Avvio locale

```bash
npm install
npm start
```

Health check:

```bash
curl http://127.0.0.1:8088/health
```

Simulazione webhook:

```bash
curl -X POST http://127.0.0.1:8088/webhooks/openai/realtime \
  -H "Content-Type: application/json" \
  -d '{
    "type": "realtime.call.incoming",
    "data": {
      "call_id": "rtc_test_001",
      "from": "+393331112233",
      "to": "+390000000000"
    }
  }'
```

Senza `OPENAI_API_KEY` il bridge valida Odoo e ritorna `503`, senza accettare la chiamata.

## Flusso inbound reale

1. Il provider SIP indirizza il numero verso OpenAI SIP.
2. OpenAI invia `realtime.call.incoming` al bridge.
3. Il bridge chiama Odoo `/voice_ai/openai/webhook`.
4. Odoo crea la chiamata, risolve agente/routing e restituisce payload Realtime.
5. Il bridge chiama OpenAI `/v1/realtime/calls/{call_id}/accept`.
6. Il bridge apre WebSocket `wss://api.openai.com/v1/realtime?call_id=...`.
7. Quando il modello chiede un tool, il bridge inoltra a Odoo `/voice_ai/tool/<name>`.

## Note provider SIP

Quando Ehiweb rilascia numero e credenziali SIP, configurare il trunk verso:

```text
sip:<OPENAI_PROJECT_ID>@sip.api.openai.com;transport=tls
```

Il project ID e quello del progetto OpenAI dove e configurato il webhook.
