import http from 'node:http';
import { URL } from 'node:url';
import fs from 'node:fs/promises';
import path from 'node:path';
import WebSocket, { WebSocketServer } from 'ws';

const config = {
  port: Number(process.env.PORT || 8088),
  odooBaseUrl: stripTrailingSlash(process.env.ODOO_BASE_URL || 'https://erp.casafolino.com'),
  odooDb: process.env.ODOO_DB || 'folinofood',
  odooWebhookToken: process.env.ODOO_WEBHOOK_TOKEN || '',
  openaiApiKey: process.env.OPENAI_API_KEY || '',
  twilioAccountSid: process.env.TWILIO_ACCOUNT_SID || '',
  twilioAuthToken: process.env.TWILIO_AUTH_TOKEN || '',
  twilioPhoneNumber: process.env.TWILIO_PHONE_NUMBER || '',
  humanTransferUri: process.env.HUMAN_TRANSFER_URI || '',
  publicBridgeUrl: stripTrailingSlash(process.env.PUBLIC_BRIDGE_URL || ''),
  logLevel: process.env.LOG_LEVEL || 'info',
  requestTimeoutMs: Number(process.env.REQUEST_TIMEOUT_MS || 10000),
  vadThreshold: Number(process.env.OPENAI_VAD_THRESHOLD || 0.78),
  vadPrefixPaddingMs: Number(process.env.OPENAI_VAD_PREFIX_PADDING_MS || 300),
  vadSilenceDurationMs: Number(process.env.OPENAI_VAD_SILENCE_DURATION_MS || 850),
  bargeInMinIntervalMs: Number(process.env.BARGE_IN_MIN_INTERVAL_MS || 350),
  voiceProvider: (process.env.VOICE_PROVIDER || 'openai').toLowerCase(),
  deepgramApiKey: process.env.DEEPGRAM_API_KEY || '',
  deepgramAgentUrl: process.env.DEEPGRAM_AGENT_URL || 'wss://agent.deepgram.com/v1/agent/converse',
  deepgramListenModel: process.env.DEEPGRAM_LISTEN_MODEL || 'flux-general-multi',
  deepgramThinkProvider: process.env.DEEPGRAM_THINK_PROVIDER || 'open_ai',
  deepgramThinkModel: process.env.DEEPGRAM_THINK_MODEL || 'gpt-4o-mini',
  deepgramSpeakModel: process.env.DEEPGRAM_SPEAK_MODEL || 'aura-2-livia-it',
  deepgramSpeakSpeed: Number(process.env.DEEPGRAM_SPEAK_SPEED || 1.12),
  deepgramEotThreshold: Number(process.env.DEEPGRAM_EOT_THRESHOLD || 0.86),
  deepgramEagerEotThreshold: process.env.DEEPGRAM_EAGER_EOT_THRESHOLD ? Number(process.env.DEEPGRAM_EAGER_EOT_THRESHOLD) : null,
  deepgramEotTimeoutMs: Number(process.env.DEEPGRAM_EOT_TIMEOUT_MS || 2800),
  elevenLabsApiKey: process.env.ELEVENLABS_API_KEY || '',
  elevenLabsVoiceId: process.env.ELEVENLABS_VOICE_ID || '',
  elevenLabsModelId: process.env.ELEVENLABS_MODEL_ID || 'eleven_turbo_v2_5',
  elevenLabsLanguageCode: process.env.ELEVENLABS_LANGUAGE_CODE || 'it',
  openaiRealtimeModel: process.env.OPENAI_REALTIME_MODEL || 'gpt-realtime',
  openaiVoice: process.env.OPENAI_VOICE || 'marin',
};

const activeCalls = new Map();

const BASE_INSTRUCTIONS = `
Sei Giulia di CasaFolino, l'assistente vocale ufficiale di CasaFolino Srls (Folino Food), azienda fondata nel 1962 a Lamezia Terme (CZ) dai fratelli Antonio e Guido Folino.
Rileva dinamicamente la lingua parlata dal cliente fin dal primo turno di conversazione e rispondi fluidamente nella stessa lingua (italiano, inglese, francese, spagnolo, tedesco, ecc.) adattandoti all'istante con tono estremamente naturale, gentile, familiare, professionale e caloroso. Rispondi in modo conciso e naturale per facilitare la conversazione telefonica (massimo 1-2 frasi brevi per risposta).
Parla con ritmo telefonico leggermente piu rapido del normale, senza pause lunghe. Dopo aver raccolto il nome, chiama il cliente per nome in modo naturale e non eccessivo.
Non interrompere il cliente mentre sta elencando dati come nome, telefono, email, azienda o dettagli dell'ordine: aspetta che finisca, poi conferma in modo breve. Evita micro-risposte come "grazie" dopo ogni singolo frammento.

Il tuo scopo è assistere i clienti che chiamano, rispondere alle loro domande sui prodotti di CasaFolino, verificare lo stato dell'ordine, gestire contatti e richieste commerciali (lead), o aprire segnalazioni di assistenza.

KNOWLEDGE BASE (INFORMAZIONI AZIENDALI):
1. CHI SIAMO: CasaFolino produce e vende specialità enogastronomiche tipiche calabresi di altissima qualità artigianale dal 1962.
2. PRODOTTI DI PUNTA:
   - 'Nduja di Spilinga (crema piccante spalmabile di maiale e peperoncino).
   - Salumi tipici calabresi (Soppressata calabrese, Salsiccia dop, Capocollo).
   - Formaggi locali (Pecorino Crotonese, Caciocavallo Silano).
   - Conserve e Sott'oli (Cipolla Rossa di Tropea Calabria IGP caramellata o in agrodolce, peperoncini ripieni).
   - Creme spalmabili dolci (pistacchio, nocciola, mandorla, caffè) e cioccolato artigianale (marchio Chocorotto).
   - Spezie e Tisane biologiche (marchi Dulcis Et Salis, Tisantea).
3. SEDE E LOGISTICA: La sede principale, gli uffici e il magazzino si trovano a Lamezia Terme (Catanzaro, Calabria). Spediamo in tutta Italia e all'estero tramite corriere espresso. Le consegne in Italia avvengono in 24/48 ore.
4. STRUMENTI A DISPOSIZIONE (TOOL CALLS):
   - Se il cliente fa domande su ordini o vuole essere riconosciuto, usa il tool 'lookup_customer' fornendo il suo nome.
   - Se il cliente chiede lo stato di un ordine, usa il tool 'lookup_order_status'.
   - Se il cliente è un nuovo contatto, vuole collaborare o lascia una richiesta commerciale, usa il tool 'create_crm_lead'.
   - Se il cliente ha un problema, reclamo o vuole fare una segnalazione (pacco danneggiato, merce mancante), usa il tool 'create_ticket'.
   - Se il cliente fa richieste complesse o chiede di parlare con una persona reale (come Antonio Folino), usa il tool 'transfer_to_human' specificando il reparto generale e il motivo.

COMPORTAMENTO DIALOGO:
- Presentati all'inizio come "Giulia di CasaFolino" con voce calda, disponibile, sorridente e familiare, come una reception CasaFolino: mai rigida, mai troppo formale, mai da IVR.
- All'inizio comunica la posizione in coda, rassicurando che i tempi di attesa sono molto bassi.
- Dopo l'accoglienza chiedi immediatamente nome, cognome, telefono, email e azienda; salva il contatto prima di passare al motivo della chiamata.
- Chiedi i dati con tono sciolto e veloce, in una frase breve; se il cliente si ferma, raccogli quello che manca una domanda alla volta.
- Se vuole fare un ordine, chiedi se preferisce farlo con te al telefono oppure parlare con un commerciale. Se non puoi trasferire subito, raccogli i dati e proponi richiamata.
- Se ha problemi con un ordine, chiedi nome, email o telefono e usa lookup_customer e lookup_order_status quando hai dati sufficienti.
- Se vuole informazioni commerciali, chiedi cosa serve: catalogo, listino, private label, campionature, certificazioni o altro. Usa create_crm_lead, create_email_activity, create_callback o create_ticket secondo il caso.
- Dopo aver salvato il contatto, chiedi il motivo della chiamata: ordine nuovo, problema con un ordine o informazioni commerciali.
- Fai una domanda per volta, con frasi brevi e gentili.
- Usa sempre record_call_outcome prima di chiudere, cosi il cliente riceve una mail di riepilogo della conversazione.
- Per richieste commerciali, cataloghi, listini e campionature il referente interno e Antonio, con Martina in copia. Per assistenza, ordini, reclami, documenti e backoffice il referente interno e Martina, con Antonio in copia.
- Se il cliente chiede il catalogo in una lingua diversa dall'inglese, invia il catalogo italiano.
`;

function stripTrailingSlash(value) {
  return value.replace(/\/+$/, '');
}

function escapeXml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function currentQueuePosition(callSid) {
  const liveCalls = [...activeCalls.values()].filter(call => {
    return call.callSid && call.callSid !== callSid && call.direction !== 'outbound_pending';
  });
  return liveCalls.length + 1;
}

function formatGreetingText(text, callSid) {
  const queuePosition = String(currentQueuePosition(callSid));
  return String(text || '').replaceAll('{queue_position}', queuePosition);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function activeProvider() {
  if (['deepgram', 'elevenlabs'].includes(config.voiceProvider)) {
    return config.voiceProvider;
  }
  return 'openai';
}

function buildInstructions(agentPayload) {
  return agentPayload?.instructions
    ? `${BASE_INSTRUCTIONS}\n\nISTRUZIONI DINAMICHE DA ODOO:\n${agentPayload.instructions}`
    : BASE_INSTRUCTIONS;
}

function buildGreeting(agentPayload, callSid) {
  const rawGreetingText = agentPayload?.first_message || "Buongiorno, sono Giulia di CasaFolino. Lei è la chiamata numero {queue_position} in coda, ma non si preoccupi: i tempi di attesa sono molto bassi. Per aprire la chiamata mi dice nome, cognome, telefono, email e azienda? Poi la aiuto subito.";
  return formatGreetingText(rawGreetingText, callSid);
}

function mapToolsForDeepgram(tools) {
  return (tools || []).map(tool => ({
    name: tool.name,
    description: tool.description || '',
    parameters: tool.parameters || { type: 'object', properties: {} },
  })).filter(tool => tool.name);
}

function buildSpeakSettings() {
  if (activeProvider() === 'elevenlabs') {
    if (!config.elevenLabsApiKey || !config.elevenLabsVoiceId) {
      throw new Error('VOICE_PROVIDER=elevenlabs requires ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID');
    }
    return {
      provider: {
        type: 'eleven_labs',
        model_id: config.elevenLabsModelId,
        language_code: config.elevenLabsLanguageCode,
      },
      endpoint: {
        url: `wss://api.elevenlabs.io/v1/text-to-speech/${config.elevenLabsVoiceId}/multi-stream-input`,
        headers: {
          'xi-api-key': config.elevenLabsApiKey,
        },
      },
    };
  }
  return {
    provider: {
      type: 'deepgram',
      model: config.deepgramSpeakModel,
    },
  };
}

function buildDeepgramSettings(agentPayload, callSid) {
  const listenProvider = {
    type: 'deepgram',
    model: config.deepgramListenModel,
    language: 'it',
    smart_format: true,
  };
  if (config.deepgramListenModel.startsWith('flux-')) {
    listenProvider.version = 'v2';
    listenProvider.language_hints = ['it', 'en', 'fr', 'es', 'de'];
    listenProvider.eot_threshold = config.deepgramEotThreshold;
    listenProvider.eot_timeout_ms = config.deepgramEotTimeoutMs;
    if (config.deepgramEagerEotThreshold !== null) {
      listenProvider.eager_eot_threshold = config.deepgramEagerEotThreshold;
    }
    delete listenProvider.language;
    delete listenProvider.smart_format;
  }
  return {
    type: 'Settings',
    tags: ['casafolino', 'prod', activeProvider()],
    flags: { history: true },
    audio: {
      input: { encoding: 'mulaw', sample_rate: 8000 },
      output: { encoding: 'mulaw', sample_rate: 8000, container: 'none' },
    },
    agent: {
      listen: { provider: listenProvider },
      think: {
        provider: {
          type: config.deepgramThinkProvider,
          model: config.deepgramThinkModel,
          temperature: 0.3,
        },
        prompt: buildInstructions(agentPayload),
        functions: mapToolsForDeepgram(agentPayload?.tools),
      },
      speak: buildSpeakSettings(),
      greeting: buildGreeting(agentPayload, callSid),
    },
  };
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

async function readFormUrlEncoded(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString('utf8') || '';
  const params = new URLSearchParams(raw);
  const body = {};
  for (const [key, value] of params.entries()) {
    body[key] = value;
  }
  return body;
}

function sendJson(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json',
    'content-length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

function sendTwiML(res, twiml) {
  res.writeHead(200, {
    'content-type': 'application/xml',
    'content-length': Buffer.byteLength(twiml),
  });
  res.end(twiml);
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

async function pollOutboundCalls() {
  if (!config.twilioAccountSid || !config.twilioAuthToken || !config.twilioPhoneNumber) {
    return;
  }
  try {
    const bridgeConfig = await odooRequest('/voice_ai/config');
    if (!bridgeConfig.allow_outbound) {
      log('debug', 'outbound calling disabled in Odoo config');
      return;
    }
    
    const nextResponse = await odooRequest('/voice_ai/outbound/next');
    if (!nextResponse.ok || !nextResponse.job || !nextResponse.job.job_id) {
      return;
    }
    
    const job = nextResponse.job;
    log('info', 'Found ready outbound job from Odoo', { job_id: job.job_id, phone: job.phone });
    
    const jobId = job.job_id;
    activeCalls.set(`job_${jobId}`, {
      direction: 'outbound',
      jobId: jobId,
      odooCallId: job.agent?.metadata?.call_id || job.job_id,
      agentPayload: job.agent,
      phone: job.phone,
      startedAt: new Date().toISOString()
    });
    
    const twilioUrl = `https://api.twilio.com/2010-04-01/Accounts/${config.twilioAccountSid}/Calls.json`;
    const response = await fetch(twilioUrl, {
      method: 'POST',
      headers: {
        Authorization: `Basic ${Buffer.from(`${config.twilioAccountSid}:${config.twilioAuthToken}`).toString('base64')}`,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        From: config.twilioPhoneNumber,
        To: job.phone,
        Url: `${config.publicBridgeUrl}/twilio/outbound?job_id=${jobId}`
      })
    });
    
    const data = await response.json();
    if (!response.ok) {
      activeCalls.delete(`job_${jobId}`);
      throw new Error(`Twilio Call API failed: ${JSON.stringify(data)}`);
    }
    log('info', 'Twilio outbound call placed successfully', { callSid: data.sid, job_id: jobId });
    
  } catch (error) {
    log('error', 'Outbound poller error', { message: error.message });
  }
}

async function handleTwilioInbound(req, res) {
  const body = await readFormUrlEncoded(req);
  log('info', 'Received Twilio inbound call webhook', { callSid: body.CallSid, from: body.From });
  
  const streamUrl = `wss://${config.publicBridgeUrl.replace(/^https?:\/\//, '')}/media-stream`;
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${streamUrl}">
      <Parameter name="from" value="${escapeXml(body.From || '')}" />
      <Parameter name="to" value="${escapeXml(body.To || '')}" />
      <Parameter name="callSid" value="${escapeXml(body.CallSid || '')}" />
    </Stream>
  </Connect>
</Response>`;
  
  sendTwiML(res, twiml);
}

async function handleTwilioOutbound(req, res, url) {
  const body = await readFormUrlEncoded(req);
  const jobId = url.searchParams.get('job_id');
  log('info', 'Outbound call answered by customer', { callSid: body.CallSid, jobId });
  
  const streamUrl = `wss://${config.publicBridgeUrl.replace(/^https?:\/\//, '')}/media-stream?job_id=${jobId}`;
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${streamUrl}">
      <Parameter name="from" value="${escapeXml(body.From || '')}" />
      <Parameter name="to" value="${escapeXml(body.To || '')}" />
      <Parameter name="callSid" value="${escapeXml(body.CallSid || '')}" />
    </Stream>
  </Connect>
</Response>`;
  
  sendTwiML(res, twiml);
}

async function redirectLiveCallToFallback(callSid, reason = 'openai_error') {
  if (!callSid || !config.twilioAccountSid || !config.twilioAuthToken || !config.publicBridgeUrl) {
    log('error', 'Cannot redirect live call to fallback: missing call SID or Twilio config', { callSid, reason });
    return false;
  }
  const twilioUrl = `https://api.twilio.com/2010-04-01/Accounts/${config.twilioAccountSid}/Calls/${callSid}.json`;
  const fallbackUrl = `${config.publicBridgeUrl}/twilio/fallback?reason=${encodeURIComponent(reason)}`;
  const response = await fetch(twilioUrl, {
    method: 'POST',
    headers: {
      Authorization: `Basic ${Buffer.from(`${config.twilioAccountSid}:${config.twilioAuthToken}`).toString('base64')}`,
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({ Url: fallbackUrl })
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Twilio fallback redirect failed: ${response.status} ${detail}`);
  }
  log('warn', 'Live call redirected to Twilio fallback', { callSid, reason });
  return true;
}

async function handleTwilioFallback(req, res, url) {
  const reason = url.searchParams.get('reason') || 'temporary_unavailable';
  log('warn', 'Twilio fallback TwiML requested', { reason });
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="it-IT" voice="alice">Buongiorno, sono Giulia di CasaFolino. In questo momento sto avendo un problema tecnico temporaneo sulla linea. Non si preoccupi: abbiamo registrato la chiamata e la invitiamo a richiamare tra qualche minuto. Grazie da CasaFolino.</Say>
</Response>`;
  sendTwiML(res, twiml);
}

async function handleTwilioTransfer(req, res, url) {
  const target = url.searchParams.get('target') || config.humanTransferUri;
  log('info', 'Twilio call transfer TwiML requested', { target });
  if (!target || !/^(tel:|sip:)/i.test(target.trim())) {
    log('error', 'Twilio transfer requested without a valid human target', { target });
    const twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say language="it-IT">Mi dispiace, al momento non riesco a trasferire la chiamata. Resti pure in linea con Giulia.</Say></Response>';
    sendTwiML(res, twiml);
    return;
  }
  
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Dial>${target}</Dial>
</Response>`;
  
  sendTwiML(res, twiml);
}

async function router(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  try {
    if (req.method === 'GET' && (url.pathname === '/client' || url.pathname === '/mock-client')) {
      const htmlPath = path.join(process.cwd(), 'scripts', 'mock-client.html');
      try {
        const content = await fs.readFile(htmlPath, 'utf8');
        res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
        res.end(content);
      } catch (err) {
        log('error', 'failed to read mock-client.html', { message: err.message });
        sendJson(res, 500, { ok: false, error: 'Could not load client page' });
      }
      return;
    }

    if (req.method === 'POST' && url.pathname === '/log') {
      try {
        const body = await readJson(req);
        log(body.level || 'info', 'CLIENT_DIAGNOSTIC', body);
        sendJson(res, 200, { ok: true });
      } catch (err) {
        sendJson(res, 500, { ok: false, error: err.message });
      }
      return;
    }

    if (req.method === 'GET' && url.pathname === '/health') {
      sendJson(res, 200, {
        ok: true,
        service: 'casafolino-voice-bridge',
        twilio: {
          has_sid: Boolean(config.twilioAccountSid),
          phone: config.twilioPhoneNumber,
        },
        odoo: config.odooBaseUrl,
        db: config.odooDb,
        has_openai_key: Boolean(config.openaiApiKey),
    has_deepgram_key: Boolean(config.deepgramApiKey),
    voice_provider: activeProvider(),
        has_deepgram_key: Boolean(config.deepgramApiKey),
        voice_provider: activeProvider(),
        providers: {
          openai: { configured: Boolean(config.openaiApiKey) },
          deepgram: {
            configured: Boolean(config.deepgramApiKey),
            listen_model: config.deepgramListenModel,
            think_model: config.deepgramThinkModel,
            speak_model: config.deepgramSpeakModel,
          },
          elevenlabs: {
            configured: Boolean(config.elevenLabsApiKey && config.elevenLabsVoiceId),
            model_id: config.elevenLabsModelId,
            voice_id: config.elevenLabsVoiceId ? 'configured' : '',
            language_code: config.elevenLabsLanguageCode,
          },
        },
        active_calls: activeCalls.size,
      });
      return;
    }

    if (req.method === 'POST' && url.pathname === '/twilio/inbound') {
      await handleTwilioInbound(req, res);
      return;
    }

    if (req.method === 'POST' && url.pathname === '/twilio/outbound') {
      await handleTwilioOutbound(req, res, url);
      return;
    }

    if (req.method === 'POST' && url.pathname === '/twilio/transfer') {
      await handleTwilioTransfer(req, res, url);
      return;
    }

    if (req.method === 'POST' && url.pathname === '/twilio/fallback') {
      await handleTwilioFallback(req, res, url);
      return;
    }

    sendJson(res, 404, { ok: false, error: 'not found' });
  } catch (error) {
    log('error', 'request failed', { message: error.message });
    sendJson(res, 500, { ok: false, error: error.message });
  }
}

const server = http.createServer(router);
const wss = new WebSocketServer({ noServer: true });

server.on('upgrade', (req, socket, head) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (url.pathname === '/media-stream') {
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit('connection', ws, req);
    });
  } else {
    socket.destroy();
  }
});

wss.on('connection', (ws, req) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const jobId = url.searchParams.get('job_id');
  
  let streamSid = null;
  let callSid = null;
  let odooCallId = null;
  let agentPayload = null;
  let openAiWs = null;
  let deepgramWs = null;
  let callState = 'connecting';
  let transcript = [];
  let lastSpeechStartedAt = 0;
  let lastDeepgramClearAt = 0;
  let fallbackRedirected = false;
  
  log('info', 'New Twilio WebSocket media-stream connection established', { jobId });
  
  ws.on('message', async (message) => {
    let msg;
    try {
      msg = JSON.parse(message);
    } catch {
      log('warn', 'received non-JSON WebSocket message from Twilio');
      return;
    }
    
    if (msg.event === 'start') {
      streamSid = msg.start.streamSid;
      callSid = msg.start.callSid;
      log('info', 'Twilio media stream start event received', { streamSid, callSid });
      
      try {
        if (jobId) {
          const activeCall = activeCalls.get(`job_${jobId}`);
          if (activeCall) {
            odooCallId = activeCall.odooCallId;
            agentPayload = activeCall.agentPayload;
            activeCalls.set(callSid, {
              ...activeCall,
              callSid,
              streamSid
            });
            activeCalls.delete(`job_${jobId}`);
          }
        }
        
        // 1. Start Odoo agent resolution in parallel if not already cached/loaded
        let odooResolvePromise = null;
        if (!agentPayload) {
          log('info', 'Starting background Odoo agent resolution...', { callSid });
          const fromNum = msg.start.customParameters?.from || req.headers['x-twilio-from'] || '+390000000000';
          const toNum = msg.start.customParameters?.to || req.headers['x-twilio-to'] || '+390000000000';
          
          odooResolvePromise = odooRequest('/voice_ai/openai/webhook', {
            method: 'POST',
            body: {
              type: 'realtime.call.incoming',
              data: {
                call_id: callSid,
                from: fromNum,
                to: toNum
              }
            }
          }).then(odooResponse => {
            if (!odooResponse.ok) {
              throw new Error(`Odoo webhook failed: ${JSON.stringify(odooResponse)}`);
            }
            odooCallId = odooResponse.call_id;
            agentPayload = odooResponse.agent;
            
            activeCalls.set(callSid, {
              direction: 'inbound',
              callSid,
              streamSid,
              odooCallId,
              agentPayload,
              startedAt: new Date().toISOString()
            });
            log('info', 'Odoo agent resolution completed in background');
            return odooResponse;
          }).catch(err => {
            log('error', 'Background Odoo resolution failed', { message: err.message });
          });
        }
        
        if (['deepgram', 'elevenlabs'].includes(activeProvider())) {
          if (!config.deepgramApiKey) {
            throw new Error('VOICE_PROVIDER=deepgram but DEEPGRAM_API_KEY is missing');
          }
          if (odooResolvePromise) {
            await Promise.race([odooResolvePromise, sleep(1500)]);
          }
          log('info', 'Connecting to Deepgram Voice Agent WebSocket...', {
            listen_model: config.deepgramListenModel,
            think_model: config.deepgramThinkModel,
            speak_model: config.deepgramSpeakModel,
          });
          deepgramWs = new WebSocket(config.deepgramAgentUrl, {
            headers: { Authorization: `Token ${config.deepgramApiKey}` },
          });

          deepgramWs.on('open', () => {
            log('info', 'Deepgram Voice Agent connection successfully opened');
            callState = 'active';
            deepgramWs.send(JSON.stringify(buildDeepgramSettings(agentPayload, callSid)));
          });

          deepgramWs.on('message', async (data, isBinary) => {
            if (isBinary) {
              if (streamSid) {
                ws.send(JSON.stringify({
                  event: 'media',
                  streamSid,
                  media: { payload: Buffer.from(data).toString('base64') },
                }));
              }
              return;
            }
            let deepgramMsg;
            try {
              deepgramMsg = JSON.parse(data.toString());
            } catch {
              log('debug', 'Received non-JSON text message from Deepgram');
              return;
            }
            if (!['ConversationText'].includes(deepgramMsg.type)) {
              log('info', `Received Deepgram event: ${deepgramMsg.type}`);
            }
            if (['UserStartedSpeaking', 'StartOfTurn'].includes(deepgramMsg.type) && streamSid) {
              const now = Date.now();
              if (now - lastDeepgramClearAt >= Math.max(250, config.bargeInMinIntervalMs)) {
                lastDeepgramClearAt = now;
                log('info', 'Detected Deepgram barge-in. Clearing Twilio playback buffer...', { type: deepgramMsg.type });
                ws.send(JSON.stringify({ event: 'clear', streamSid }));
              }
            }
            if (deepgramMsg.type === 'ConversationText' && deepgramMsg.content) {
              const label = deepgramMsg.role === 'user' ? 'Cliente' : 'Agente';
              transcript.push(`${label}: ${deepgramMsg.content}`);
              log('info', `Transcript update: ${label}: ${deepgramMsg.content}`);
            }
            if (deepgramMsg.type === 'FunctionCallRequest') {
              for (const fn of deepgramMsg.functions || []) {
                const name = fn.name;
                let args = {};
                try {
                  args = JSON.parse(fn.arguments || '{}');
                } catch (err) {
                  log('error', 'Failed to parse Deepgram tool arguments', { name, message: err.message });
                }
                try {
                  const odooResult = await odooRequest(`/voice_ai/tool/${encodeURIComponent(name)}`, {
                    method: 'POST',
                    body: { ...args, call_id: odooCallId },
                  });
                  log('info', 'Tool execution result from Odoo via Deepgram', { name, odooResult });
                  deepgramWs.send(JSON.stringify({
                    type: 'FunctionCallResponse',
                    id: fn.id,
                    name,
                    content: JSON.stringify(odooResult),
                  }));
                } catch (err) {
                  log('error', 'Failed to dispatch Deepgram tool call to Odoo', { name, message: err.message });
                  deepgramWs.send(JSON.stringify({
                    type: 'FunctionCallResponse',
                    id: fn.id,
                    name,
                    content: JSON.stringify({ ok: false, error: err.message }),
                  }));
                }
              }
            }
            if (deepgramMsg.type === 'Error') {
              log('error', 'Deepgram Voice Agent error', deepgramMsg);
            }
          });

          deepgramWs.on('close', () => {
            log('info', 'Deepgram Voice Agent connection closed');
            if (callState === 'active') {
              ws.close();
            }
          });

          deepgramWs.on('error', (err) => {
            log('error', 'Deepgram Voice Agent connection error', { message: err.message });
          });
          return;
        }

        // 2. Connect immediately to OpenAI Realtime WebSocket (GA)
        const model = config.openaiRealtimeModel;
        log('info', 'Connecting immediately to OpenAI Realtime WebSocket (GA)...', { model });
        
        openAiWs = new WebSocket(`wss://api.openai.com/v1/realtime?model=${model}`, {
          headers: {
            Authorization: `Bearer ${config.openaiApiKey}`,
          }
        });
        
        openAiWs.on('open', () => {
          log('info', 'OpenAI Realtime GA connection successfully opened');
          callState = 'active';
          
          // Send initial session setup immediately with default/cached instructions
          const baseInstructionsForSession = buildInstructions(agentPayload);
          const initialVoice = agentPayload?.voice || config.openaiVoice || 'shimmer';
          const initialTools = agentPayload?.tools || [];
          
          const sessionUpdate = {
            type: 'session.update',
            session: {
              type: 'realtime',
              instructions: baseInstructionsForSession,
              audio: {
                input: {
                  format: {
                    type: 'audio/pcmu'
                  },
                  turn_detection: {
                    type: 'server_vad',
                    threshold: config.vadThreshold,
                    prefix_padding_ms: config.vadPrefixPaddingMs,
                    silence_duration_ms: config.vadSilenceDurationMs
                  }
                },
                output: {
                  format: {
                    type: 'audio/pcmu'
                  },
                  voice: initialVoice
                }
              },
              tools: initialTools,
              tool_choice: 'auto'
            }
          };
          openAiWs.send(JSON.stringify(sessionUpdate));
          
          // Trigger the greeting immediately using a hidden user prompt so the model synthesizes natural assistant audio
          const greetingText = buildGreeting(agentPayload, callSid);
          const greetingPrompt = `Greeting trigger: saluta il cliente presentandoti come Giulia di CasaFolino, con questa esatta frase: "${greetingText}"`;
          openAiWs.send(JSON.stringify({
            type: 'conversation.item.create',
            item: {
              type: 'message',
              role: 'user',
              content: [{ type: 'input_text', text: greetingPrompt }]
            }
          }));
          openAiWs.send(JSON.stringify({ type: 'response.create' }));
          
          // 3. Once background Odoo promise resolves, update the session with custom instructions/tools in parallel
          if (odooResolvePromise) {
            odooResolvePromise.then(res => {
              if (res && res.agent && openAiWs.readyState === WebSocket.OPEN) {
                log('info', 'Updating OpenAI session with custom resolved Odoo instructions and tools');
                const resolvedInstructions = buildInstructions(res.agent);
                const updatePayload = {
                  type: 'session.update',
                  session: {
                    type: 'realtime',
                    instructions: resolvedInstructions,
                    tools: res.agent.tools || [],
                    tool_choice: 'auto'
                  }
                };
                openAiWs.send(JSON.stringify(updatePayload));
              }
            });
          }
        });
        
        openAiWs.on('message', async (data) => {
          let openAiMsg;
          try {
            openAiMsg = JSON.parse(data);
          } catch {
            return;
          }
          
          // Diagnostic logging of OpenAI Realtime server events (excluding high-frequency audio deltas and speech events)
          const silentEvents = [
            'response.audio.delta',
            'response.output_audio.delta',
            'input_audio_buffer.speech_started',
            'input_audio_buffer.speech_stopped',
            'rate_limits.updated'
          ];
          if (!silentEvents.includes(openAiMsg.type)) {
            log('info', `Received OpenAI event: ${openAiMsg.type}`, { eventId: openAiMsg.event_id || null });
          }

          if (openAiMsg.type === 'input_audio_buffer.speech_started') {
            const now = Date.now();
            if (now - lastSpeechStartedAt < config.bargeInMinIntervalMs) {
              log('debug', 'Ignoring duplicate/noisy speech_started event', { elapsed_ms: now - lastSpeechStartedAt });
              return;
            }
            lastSpeechStartedAt = now;
            log('info', 'Detected user barge-in / speech started. Interrupting agent response...');
            if (streamSid) {
              ws.send(JSON.stringify({
                event: 'clear',
                streamSid: streamSid
              }));
            }
            openAiWs.send(JSON.stringify({
              type: 'response.cancel'
            }));
          }
          
          if ((openAiMsg.type === 'response.audio.delta' || openAiMsg.type === 'response.output_audio.delta') && openAiMsg.delta && streamSid) {
            if (!ws.firstAudioSent) {
              ws.firstAudioSent = true;
              log('info', 'Streaming first audio delta chunk to Twilio');
            }
            ws.send(JSON.stringify({
              event: 'media',
              streamSid,
              media: {
                payload: openAiMsg.delta
              }
            }));
          }
          
          if ((openAiMsg.type === 'conversation.item.create' || openAiMsg.type === 'conversation.item.created') && openAiMsg.item) {
            const role = openAiMsg.item.role;
            const textContent = openAiMsg.item.content?.find(c => c.type === 'text')?.text;
            if (role && textContent) {
              const label = role === 'user' ? 'Cliente' : 'Agente';
              transcript.push(`${label}: ${textContent}`);
              log('info', `Transcript update: ${label}: ${textContent}`);
            }
          }
          
          if (openAiMsg.type === 'response.done' && openAiMsg.response?.output) {
            for (const item of openAiMsg.response.output) {
              if (item.type === 'function_call') {
                const name = item.name;
                let args = {};
                try {
                  args = JSON.parse(item.arguments || '{}');
                } catch (err) {
                  log('error', 'Skipping OpenAI tool call with invalid JSON arguments', {
                    name,
                    message: err.message,
                    arguments_preview: String(item.arguments || '').slice(0, 200),
                  });
                  openAiWs.send(JSON.stringify({
                    type: 'conversation.item.create',
                    item: {
                      type: 'function_call_output',
                      call_id: item.call_id,
                      output: JSON.stringify({
                        ok: false,
                        error: 'tool_arguments_invalid',
                        message: 'Non ho ricevuto tutti i dati in modo chiaro: chiedi al cliente di ripetere solo le informazioni mancanti.',
                      }),
                    },
                  }));
                  openAiWs.send(JSON.stringify({ type: 'response.create' }));
                  continue;
                }
                log('info', 'Executing Odoo tool call', { name, args });
                
                try {
                  const odooResult = await odooRequest(`/voice_ai/tool/${encodeURIComponent(name)}`, {
                    method: 'POST',
                    body: {
                      ...args,
                      call_id: odooCallId
                    }
                  });
                  
                  log('info', 'Tool execution result from Odoo', { name, odooResult });
                  if (name === 'transfer_to_human' && odooResult.transfer_requested && !config.humanTransferUri) {
                    odooResult.transfer_requested = false;
                    odooResult.transfer_available = false;
                    odooResult.message = 'Trasferimento telefonico non configurato: continua la chiamata con il cliente, raccogli la richiesta e proponi una richiamata dall ufficio di Lamezia Terme.';
                    log('warn', 'transfer_to_human requested but HUMAN_TRANSFER_URI is not configured; keeping call on AI', { department: odooResult.department, reason: odooResult.reason });
                  }
                  
                  openAiWs.send(JSON.stringify({
                    type: 'conversation.item.create',
                    item: {
                      type: 'function_call_output',
                      call_id: item.call_id,
                      output: JSON.stringify(odooResult)
                    }
                  }));
                  openAiWs.send(JSON.stringify({ type: 'response.create' }));
                  
                  if (name === 'transfer_to_human' && odooResult.transfer_requested) {
                    log('info', 'Intercepted transfer_to_human: initiating Twilio call redirect');
                    
                    setTimeout(async () => {
                      try {
                        const twilioUrl = `https://api.twilio.com/2010-04-01/Accounts/${config.twilioAccountSid}/Calls/${callSid}.json`;
                        const resRedirect = await fetch(twilioUrl, {
                          method: 'POST',
                          headers: {
                            Authorization: `Basic ${Buffer.from(`${config.twilioAccountSid}:${config.twilioAuthToken}`).toString('base64')}`,
                            'Content-Type': 'application/x-www-form-urlencoded'
                          },
                          body: new URLSearchParams({
                            Url: `${config.publicBridgeUrl}/twilio/transfer?target=${encodeURIComponent(config.humanTransferUri)}`
                          })
                        });
                        if (!resRedirect.ok) {
                          const errData = await resRedirect.json();
                          throw new Error(JSON.stringify(errData));
                        }
                        log('info', 'Twilio live call successfully redirected to human');
                      } catch (err) {
                        log('error', 'Twilio call redirection failed', { message: err.message });
                      }
                    }, 2500);
                  }
                  
                } catch (err) {
                  log('error', 'Failed to dispatch tool call to Odoo', { name, message: err.message });
                }
              }
            }
          }
          
          if (openAiMsg.type === 'error') {
            if (openAiMsg.error?.code === 'response_cancel_not_active') {
              log('warn', 'Ignoring harmless OpenAI cancel error because no response is active', openAiMsg.error);
              return;
            }
            log('error', 'OpenAI Realtime session error', openAiMsg.error);
            if (!fallbackRedirected && callSid) {
              fallbackRedirected = true;
              try {
                await redirectLiveCallToFallback(callSid, openAiMsg.error?.code || openAiMsg.error?.type || 'openai_error');
              } catch (err) {
                log('error', 'Failed to redirect call after OpenAI error', { message: err.message });
              }
            }
          }
        });
        
        openAiWs.on('close', () => {
          log('info', 'OpenAI Realtime connection closed');
          if (callState === 'active' && !fallbackRedirected) {
            ws.close();
          }
        });
        
        openAiWs.on('error', (err) => {
          log('error', 'OpenAI Realtime connection error', { message: err.message });
        });
        
      } catch (err) {
        log('error', 'Initialization of call bridge failed', { message: err.message });
        ws.close();
      }
    }
    
    if (msg.event === 'media' && openAiWs && openAiWs.readyState === WebSocket.OPEN) {
      openAiWs.send(JSON.stringify({
        type: 'input_audio_buffer.append',
        audio: msg.media.payload
      }));
    }

    if (msg.event === 'media' && deepgramWs && deepgramWs.readyState === WebSocket.OPEN) {
      deepgramWs.send(Buffer.from(msg.media.payload, 'base64'));
    }
    
    if (msg.event === 'stop') {
      log('info', 'Twilio stream stopped');
      if (openAiWs) {
        openAiWs.close();
      }
      if (deepgramWs) {
        deepgramWs.close();
      }
      callState = 'ended';
    }
  });
  
  ws.on('close', async () => {
    log('info', 'Twilio WebSocket closed');
    callState = 'ended';
    if (openAiWs) {
      openAiWs.close();
    }
    if (deepgramWs) {
      deepgramWs.close();
    }
    
    if (odooCallId) {
      try {
        log('info', 'Logging final call result and transcript to Odoo...', { odooCallId });
        await odooRequest('/voice_ai/call/outcome', {
          method: 'POST',
          body: {
            call_id: odooCallId,
            state: 'completed',
            outcome: jobId ? 'resolved' : 'other',
            summary: jobId ? 'Chiamata outbound completata dal centralino AI' : 'Chiamata inbound completata dal centralino AI',
            transcript: transcript.join('\n')
          }
        });
        activeCalls.delete(callSid);
      } catch (err) {
        log('error', 'Failed to log final call result to Odoo', { message: err.message });
      }
    }
  });
});

server.listen(config.port, () => {
  log('info', 'CasaFolino Twilio-OpenAI Voice Bridge listening', {
    port: config.port,
    odoo: config.odooBaseUrl,
    db: config.odooDb,
    has_openai_key: Boolean(config.openaiApiKey),
    has_twilio: Boolean(config.twilioAccountSid),
  });
  
  // Start the background outbound poller loop (every 15 seconds)
  if (config.twilioAccountSid && config.twilioAuthToken && config.twilioPhoneNumber) {
    log('info', 'Outbound Queue Poller started');
    setInterval(pollOutboundCalls, 15000);
  } else {
    log('warn', 'Outbound Queue Poller NOT started (missing Twilio credentials in .env)');
  }
});
