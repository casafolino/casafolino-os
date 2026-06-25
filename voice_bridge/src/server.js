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
  publicBridgeUrl: stripTrailingSlash(process.env.PUBLIC_BRIDGE_URL || ''),
  logLevel: process.env.LOG_LEVEL || 'info',
  requestTimeoutMs: Number(process.env.REQUEST_TIMEOUT_MS || 25000),
  outboundPollIntervalMs: Number(process.env.OUTBOUND_POLL_INTERVAL_MS || 30000),
  // OpenAI Realtime: model + voice from env (were hardcoded before)
  openaiRealtimeModel: process.env.OPENAI_REALTIME_MODEL || 'gpt-realtime-2',
  openaiVoice: process.env.OPENAI_VOICE || 'coral',
  // Server VAD / barge-in tuning (env-driven; previously ignored -> OpenAI defaults)
  vadThreshold: Number(process.env.OPENAI_VAD_THRESHOLD || 0.5),
  vadPrefixPaddingMs: Number(process.env.OPENAI_VAD_PREFIX_PADDING_MS || 300),
  vadSilenceDurationMs: Number(process.env.OPENAI_VAD_SILENCE_DURATION_MS || 500),
  bargeInMinIntervalMs: Number(process.env.BARGE_IN_MIN_INTERVAL_MS || 0),
};

const activeCalls = new Map();
let outboundPollRunning = false;

const BASE_INSTRUCTIONS = `
Sei Giulia di CasaFolino, l'assistente virtuale ufficiale di CasaFolino Srls (Folino Food), azienda fondata nel 1962 a Lamezia Terme (CZ) dai fratelli Antonio e Guido Folino.
Rileva dinamicamente la lingua parlata dal cliente fin dal primo turno di conversazione e rispondi fluidamente nella stessa lingua (italiano, inglese, francese, spagnolo, tedesco, ecc.) adattandoti all'istante con tono estremamente naturale, amichevole, professionale e caloroso. Rispondi in modo conciso e naturale per facilitare la conversazione telefonica (massimo 1-2 frasi brevi per risposta).

Il tuo scopo è assistere i clienti che chiamano, rispondere alle loro domande sui prodotti di CasaFolino, verificare lo stato dell'ordine, gestire contatti e richieste commerciali (lead), o aprire segnalazioni di assistenza.

KNOWLEDGE BASE (INFORMAZIONI AZIENDALI):
1. CHI SIAMO: CasaFolino è un'azienda alimentare italiana a conduzione familiare, con radici dal 1962, sede in Calabria. Realizza prodotti gourmet italiani e mediterranei autentici, con ingredienti di alta qualità, tracciabilità, attenzione alla sostenibilità e formati gourmet pratici. Azienda seria, professionale, orientata anche all'export.
2. GAMMA PRODOTTI (reale): creme spalmabili e creme croccanti, mieli aromatizzati (incluso hot honey), crispy chilli, risotti pronti con riso di Sibari, mix di spezie italiane, mousse gastronomiche, merendine senza glutine, biscotti e cantucci, tavolette e granella di cioccolato, prodotti bio e gift box. Disponibili anche private label e ricette personalizzate.
3. SEDE E LOGISTICA: produzione in Italia, Calabria. Azienda export-oriented (vendita diretta, grossisti, retailer, distributori, e-commerce).
4. USO DELLA CONOSCENZA: per dettagli su prodotti, formati, grammature, certificazioni (BRC, IFS, Bio, Kosher, Halal, Rex), capacità produttiva, mercati o private label usa SEMPRE il tool lookup_knowledge invece di rispondere a memoria. Non citare prodotti che non rientrano nella gamma qui sopra.
5. STRUMENTI: hai a disposizione un set di tool operativi; quando e come usarli è definito nelle istruzioni operative dell'agente (tool_policy). Non descrivere al cliente che stai usando un tool: esegui solo l'azione utile.

COMPORTAMENTO DIALOGO:
- Presentati all'inizio come "Giulia di CasaFolino".
- Sii sempre educata, spigliata e mantieni le risposte brevi per non annoiare il cliente al telefono.
`;

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
  if (outboundPollRunning) {
    log('debug', 'Skipping outbound poll because previous poll is still running');
    return;
  }
  outboundPollRunning = true;
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
  } finally {
    outboundPollRunning = false;
  }
}

async function handleTwilioInbound(req, res) {
  const body = await readFormUrlEncoded(req);
  log('info', 'Received Twilio inbound call webhook', { callSid: body.CallSid, from: body.From });
  
  const streamUrl = `wss://${config.publicBridgeUrl.replace(/^https?:\/\//, '')}/media-stream`;
  // No <Say> pre-roll: it produced a robotic Polly voice + ~4s dead time before
  // the AI greeting. Connect straight to the media stream so Giulia speaks first.
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${streamUrl}" />
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
    <Stream url="${streamUrl}" />
  </Connect>
</Response>`;
  
  sendTwiML(res, twiml);
}

async function handleTwilioTransfer(req, res, url) {
  const target = url.searchParams.get('target') || config.humanTransferUri || 'tel:+390000000000';
  log('info', 'Twilio call transfer TwiML requested', { target });
  
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
  let callState = 'connecting';
  let transcript = [];
  let lastBargeInAt = 0;
  
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
          const baseInstructionsForSession = agentPayload?.instructions
            ? `${BASE_INSTRUCTIONS}\n\nISTRUZIONI DINAMICHE DA ODOO:\n${agentPayload.instructions}`
            : BASE_INSTRUCTIONS;
          // Voice: Odoo agent voice wins, else env OPENAI_VOICE (no more hardcoded 'shimmer')
          const initialVoice = agentPayload?.voice || config.openaiVoice;
          const initialTools = agentPayload?.tools || [];
          const turnDetection = {
            type: 'server_vad',
            threshold: config.vadThreshold,
            prefix_padding_ms: config.vadPrefixPaddingMs,
            silence_duration_ms: config.vadSilenceDurationMs
          };
          log('info', 'Configuring OpenAI session', { model, voice: initialVoice, turn_detection: turnDetection });

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
                  turn_detection: turnDetection
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
          
          // Trigger the greeting immediately using a hidden user prompt so the model synthesizes natural assistant audio.
          // Queue announcement is conditional: clean welcome when there is no real wait,
          // a "please hold" line only when the caller is actually queued (position > 1).
          const WELCOME_GREETING = agentPayload?.first_message || "Buongiorno, CasaFolino, sono Giulia. Come posso aiutarla?";
          const WAITING_GREETING = "Buongiorno, CasaFolino, sono Giulia. In questo momento c'è una breve attesa, resti in linea, la seguo tra pochissimo.";
          // Queue position: explicit override (Twilio customParameters.queue_position) wins;
          // otherwise estimate from concurrent inbound calls already in progress (+1 for this call).
          let queuePosition = Number(msg.start.customParameters?.queue_position);
          if (!Number.isFinite(queuePosition) || queuePosition < 1) {
            const concurrentInbound = Array.from(activeCalls.values()).filter(c => c.direction === 'inbound').length;
            queuePosition = concurrentInbound + 1;
          }
          const greetingText = queuePosition > 1 ? WAITING_GREETING : WELCOME_GREETING;
          log('info', 'Selecting inbound greeting', { queuePosition, waiting: queuePosition > 1 });
          const greetingPrompt = `Greeting trigger: saluta il cliente presentandoti come Giulia di CasaFolino, l'assistente virtuale, con questa esatta frase: "${greetingText}"`;
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
                const resolvedInstructions = res.agent.instructions
                  ? `${BASE_INSTRUCTIONS}\n\nISTRUZIONI DINAMICHE DA ODOO:\n${res.agent.instructions}`
                  : BASE_INSTRUCTIONS;
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
            if (config.bargeInMinIntervalMs > 0 && now - lastBargeInAt < config.bargeInMinIntervalMs) {
              log('debug', 'Barge-in ignored (within BARGE_IN_MIN_INTERVAL_MS)', { sinceLastMs: now - lastBargeInAt });
            } else {
              lastBargeInAt = now;
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
                const args = JSON.parse(item.arguments || '{}');
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
            log('error', 'OpenAI Realtime session error', openAiMsg.error);
          }
        });
        
        openAiWs.on('close', () => {
          log('info', 'OpenAI Realtime connection closed');
          if (callState === 'active') {
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
    
    if (msg.event === 'stop') {
      log('info', 'Twilio stream stopped');
      if (openAiWs) {
        openAiWs.close();
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

server.listen(config.port, '127.0.0.1', () => {
  log('info', 'CasaFolino Twilio-OpenAI Voice Bridge listening', {
    port: config.port,
    odoo: config.odooBaseUrl,
    db: config.odooDb,
    has_openai_key: Boolean(config.openaiApiKey),
    has_twilio: Boolean(config.twilioAccountSid),
  });
  
  // Start the background outbound poller loop.
  if (config.twilioAccountSid && config.twilioAuthToken && config.twilioPhoneNumber) {
    log('info', 'Outbound Queue Poller started', {
      interval_ms: config.outboundPollIntervalMs,
      request_timeout_ms: config.requestTimeoutMs,
    });
    setInterval(pollOutboundCalls, config.outboundPollIntervalMs);
    pollOutboundCalls();
  } else {
    log('warn', 'Outbound Queue Poller NOT started (missing Twilio credentials in .env)');
  }
});
