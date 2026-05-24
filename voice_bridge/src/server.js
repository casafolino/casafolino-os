import http from 'node:http';
import { URL } from 'node:url';
import WebSocket from 'ws';

const config = {
  port: Number(process.env.PORT || 8088),
  odooBaseUrl: stripTrailingSlash(process.env.ODOO_BASE_URL || 'https://erp.casafolino.com'),
  odooDb: process.env.ODOO_DB || 'folinofood',
  odooWebhookToken: process.env.ODOO_WEBHOOK_TOKEN || '',
  openaiApiKey: process.env.OPENAI_API_KEY || '',
  openaiWebhookSecret: process.env.OPENAI_WEBHOOK_SECRET || '',
  logLevel: process.env.LOG_LEVEL || 'info',
  requestTimeoutMs: Number(process.env.REQUEST_TIMEOUT_MS || 10000),
};

const activeCalls = new Map();

function stripTrailingSlash(value) {
  return value.replace(/\/+$/, '');
}

function log(level, message, details = undefined) {
  const levels = ['debug', 'info', 'warn', 'error'];
  if (levels.indexOf(level) < levels.indexOf(config.logLevel)) {
    return;
  }
  const entry = {
    ts: new Date().toISOString(),
    level,
    message,
    ...(details ? { details } : {}),
  };
  console.log(JSON.stringify(entry));
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString('utf8') || '{}';
  return JSON.parse(raw);
}

function sendJson(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json',
    'content-length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

function requireBridgeSecret(req) {
  if (!config.openaiWebhookSecret) {
    return true;
  }
  return req.headers['x-casafolino-bridge-secret'] === config.openaiWebhookSecret;
}

function withDb(path) {
  const url = new URL(`${config.odooBaseUrl}${path}`);
  url.searchParams.set('db', config.odooDb);
  return url;
}

async function odooRequest(path, options = {}) {
  const headers = {
    accept: 'application/json',
    ...(options.body ? { 'content-type': 'application/json' } : {}),
    ...(config.odooWebhookToken ? { authorization: `Bearer ${config.odooWebhookToken}` } : {}),
    ...(options.headers || {}),
  };
  const response = await fetch(withDb(path), {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: AbortSignal.timeout(config.requestTimeoutMs),
  });
  const text = await response.text();
  let body = {};
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`Odoo ${path} failed with ${response.status}: ${JSON.stringify(body)}`);
  }
  return body;
}

async function openaiRequest(path, options = {}) {
  const response = await fetch(`https://api.openai.com${path}`, {
    method: options.method || 'POST',
    headers: {
      authorization: `Bearer ${config.openaiApiKey}`,
      'content-type': 'application/json',
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: AbortSignal.timeout(config.requestTimeoutMs),
  });
  const text = await response.text();
  let body = {};
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`OpenAI ${path} failed with ${response.status}: ${JSON.stringify(body)}`);
  }
  return body;
}

function normalizeRealtimeSession(agent, bridgeConfig) {
  const model = agent.model || bridgeConfig.realtime_model || 'gpt-realtime-2';
  const voice = agent.voice || bridgeConfig.realtime_voice || 'marin';
  return {
    type: 'realtime',
    model,
    instructions: agent.instructions || 'Rispondi come assistente telefonico CasaFolino.',
    output_modalities: ['audio'],
    audio: {
      input: {
        turn_detection: {
          type: 'semantic_vad',
        },
      },
      output: {
        voice,
      },
    },
    tools: agent.tools || [],
    tool_choice: agent.tool_choice || 'auto',
    metadata: agent.metadata || {},
  };
}

async function acceptOpenAiCall(externalCallId, sessionPayload) {
  return openaiRequest(`/v1/realtime/calls/${encodeURIComponent(externalCallId)}/accept`, {
    body: sessionPayload,
  });
}

async function referOpenAiCall(externalCallId, targetUri) {
  return openaiRequest(`/v1/realtime/calls/${encodeURIComponent(externalCallId)}/refer`, {
    body: { target_uri: targetUri },
  });
}

async function handleToolCall(ws, callContext, item) {
  const name = item.name;
  const args = item.arguments ? JSON.parse(item.arguments) : {};
  const payload = {
    ...args,
    call_id: callContext.odooCallId,
  };
  log('info', 'forwarding tool call to Odoo', { name, call_id: callContext.odooCallId });
  const output = await odooRequest(`/voice_ai/tool/${encodeURIComponent(name)}`, {
    method: 'POST',
    body: payload,
  });

  if (name === 'transfer_to_human' && callContext.humanTransferUri) {
    await referOpenAiCall(callContext.externalCallId, callContext.humanTransferUri);
  }

  ws.send(JSON.stringify({
    type: 'conversation.item.create',
    item: {
      type: 'function_call_output',
      call_id: item.call_id,
      output: JSON.stringify(output),
    },
  }));
  ws.send(JSON.stringify({ type: 'response.create' }));
}

function connectCallMonitor(callContext) {
  const url = `wss://api.openai.com/v1/realtime?call_id=${encodeURIComponent(callContext.externalCallId)}`;
  const ws = new WebSocket(url, {
    headers: {
      authorization: `Bearer ${config.openaiApiKey}`,
    },
  });
  activeCalls.set(callContext.externalCallId, { ...callContext, ws });

  ws.addEventListener('open', () => {
    log('info', 'OpenAI call monitor connected', { call_id: callContext.externalCallId });
    ws.send(JSON.stringify({ type: 'response.create' }));
  });

  ws.addEventListener('message', async (event) => {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      log('warn', 'received non-json realtime event');
      return;
    }

    if (payload.type === 'response.done') {
      const items = payload.response?.output || [];
      for (const item of items) {
        if (item.type === 'function_call') {
          try {
            await handleToolCall(ws, callContext, item);
          } catch (error) {
            log('error', 'tool call failed', { message: error.message, tool: item.name });
          }
        }
      }
    }

    if (payload.type === 'error') {
      log('error', 'realtime error event', payload);
    }
  });

  ws.addEventListener('close', () => {
    activeCalls.delete(callContext.externalCallId);
    log('info', 'OpenAI call monitor closed', { call_id: callContext.externalCallId });
  });

  ws.addEventListener('error', (event) => {
    log('error', 'OpenAI call monitor error', { call_id: callContext.externalCallId, event });
  });
}

async function handleRealtimeWebhook(req, res) {
  if (!requireBridgeSecret(req)) {
    sendJson(res, 401, { ok: false, error: 'unauthorized' });
    return;
  }

  const payload = await readJson(req);
  if (payload.type !== 'realtime.call.incoming') {
    sendJson(res, 200, { ok: true, ignored: payload.type });
    return;
  }

  const data = payload.data || {};
  const externalCallId = data.call_id || data.id;
  if (!externalCallId) {
    sendJson(res, 400, { ok: false, error: 'missing call_id' });
    return;
  }

  const [bridgeConfig, odooCall] = await Promise.all([
    odooRequest('/voice_ai/config'),
    odooRequest('/voice_ai/openai/webhook', {
      method: 'POST',
      body: payload,
    }),
  ]);

  if (!config.openaiApiKey) {
    sendJson(res, 503, {
      ok: false,
      error: 'OPENAI_API_KEY is not configured',
      odoo_call_id: odooCall.call_id,
    });
    return;
  }

  const sessionPayload = normalizeRealtimeSession(odooCall.agent || {}, bridgeConfig);
  await acceptOpenAiCall(externalCallId, sessionPayload);
  connectCallMonitor({
    externalCallId,
    odooCallId: odooCall.call_id,
    humanTransferUri: bridgeConfig.human_transfer_uri,
  });

  sendJson(res, 200, {
    ok: true,
    external_call_id: externalCallId,
    odoo_call_id: odooCall.call_id,
  });
}

async function handleOutboundNext(res) {
  const bridgeConfig = await odooRequest('/voice_ai/config');
  if (!bridgeConfig.allow_outbound) {
    sendJson(res, 409, { ok: false, error: 'outbound disabled in Odoo' });
    return;
  }
  const next = await odooRequest('/voice_ai/outbound/next');
  sendJson(res, 200, next);
}

async function router(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  try {
    if (req.method === 'GET' && url.pathname === '/health') {
      sendJson(res, 200, {
        ok: true,
        service: 'casafolino-voice-bridge',
        odoo: config.odooBaseUrl,
        db: config.odooDb,
        has_openai_key: Boolean(config.openaiApiKey),
        active_calls: activeCalls.size,
      });
      return;
    }

    if (req.method === 'GET' && url.pathname === '/outbound/next') {
      await handleOutboundNext(res);
      return;
    }

    if (req.method === 'POST' && url.pathname === '/webhooks/openai/realtime') {
      await handleRealtimeWebhook(req, res);
      return;
    }

    sendJson(res, 404, { ok: false, error: 'not found' });
  } catch (error) {
    log('error', 'request failed', { message: error.message });
    sendJson(res, 500, { ok: false, error: error.message });
  }
}

http.createServer(router).listen(config.port, () => {
  log('info', 'CasaFolino voice bridge listening', {
    port: config.port,
    odoo: config.odooBaseUrl,
    db: config.odooDb,
    has_openai_key: Boolean(config.openaiApiKey),
  });
});
