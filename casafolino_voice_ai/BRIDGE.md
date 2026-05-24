# CasaFolino Voice AI Bridge

Il modulo Odoo gestisce regole, agenti, clienti, consensi, coda outbound e log. Il bridge telefonico deve occuparsi solo di collegare provider voce/OpenAI Realtime a questi endpoint.

## Endpoint Odoo

Tutti gli endpoint operativi possono essere protetti con:

```http
Authorization: Bearer <casafolino_voice_ai.webhook_token>
```

Configurare da Odoo:

```text
Voice AI -> Impostazioni
```

## Health

```bash
curl https://erp.casafolino.com/voice_ai/health
```

## Config bridge

```bash
curl https://erp.casafolino.com/voice_ai/config \
  -H "Authorization: Bearer TOKEN"
```

Risponde con modello Realtime, voce, URI trasferimento, outbound enabled e presenza API key.

## Simula inbound

```bash
curl -X POST https://erp.casafolino.com/voice_ai/openai/webhook \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "realtime.call.incoming",
    "data": {
      "call_id": "test_001",
      "from": "+393331112233",
      "to": "+390000000000"
    }
  }'
```

Odoo crea `casafolino.voice.call` e restituisce agente, tool schema e routing.

## Tool chiamabili dal modello

```text
POST /voice_ai/tool/lookup_customer
POST /voice_ai/tool/create_callback
POST /voice_ai/tool/record_call_outcome
POST /voice_ai/tool/opt_out_customer
POST /voice_ai/tool/transfer_to_human
```

## Outbound

Il bridge legge il prossimo job pronto:

```bash
curl https://erp.casafolino.com/voice_ai/outbound/next \
  -H "Authorization: Bearer TOKEN"
```

Se `job` e vuoto non ci sono chiamate da fare. Se presente, contiene numero, cliente, motivo, lingua e payload agente.

## Sequenza bridge consigliata

```text
1. Provider riceve/avvia chiamata.
2. Bridge chiama Odoo /voice_ai/openai/webhook o /voice_ai/outbound/next.
3. Bridge apre sessione OpenAI Realtime con payload agente.
4. Quando il modello richiede un tool, bridge inoltra a /voice_ai/tool/<name>.
5. A fine chiamata bridge chiama record_call_outcome o /voice_ai/call/outcome.
```

