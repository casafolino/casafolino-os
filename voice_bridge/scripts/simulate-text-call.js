const config = {
  odooBaseUrl: (process.env.ODOO_BASE_URL || 'http://51.44.170.55:4589').replace(/\/+$/, ''),
  odooToken: process.env.ODOO_WEBHOOK_TOKEN || '',
  openaiApiKey: process.env.OPENAI_API_KEY || '',
  model: process.env.SIM_MODEL || 'gpt-4.1-mini',
  scenario: process.env.SCENARIO || 'Vorrei ricevere il catalogo CasaFolino e sapere se avete certificazioni BRC e IFS. Mi interessa anche una private label al pistacchio.',
};

if (!config.openaiApiKey) {
  throw new Error('OPENAI_API_KEY is required');
}
if (!config.odooToken) {
  throw new Error('ODOO_WEBHOOK_TOKEN is required');
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      accept: 'application/json',
      ...(options.body ? { 'content-type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  const body = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(`${url} failed with ${response.status}: ${JSON.stringify(body)}`);
  }
  return body;
}

function toChatTool(tool) {
  return {
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: tool.parameters || { type: 'object', properties: {} },
    },
  };
}

async function odoo(path, body) {
  return requestJson(`${config.odooBaseUrl}${path}`, {
    method: body ? 'POST' : 'GET',
    headers: {
      authorization: `Bearer ${config.odooToken}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function chat(messages, tools) {
  return requestJson('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${config.openaiApiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      messages,
      tools,
      tool_choice: 'auto',
      temperature: 0.2,
    }),
  });
}

const incoming = await odoo('/voice_ai/openai/webhook', {
  type: 'realtime.call.incoming',
  data: {
    call_id: `sim_${Date.now()}`,
    from: '+390000000000',
    to: '+390000000000',
  },
});

const agent = incoming.agent || {};
const callId = incoming.call_id;
const tools = (agent.tools || []).map(toChatTool);
const messages = [
  {
    role: 'system',
    content: `${agent.instructions || 'Sei l assistente CasaFolino.'}

Questa e una simulazione testuale pre-SIP. Usa gli strumenti quando servono. Non inventare prezzi, disponibilita, consegne o condizioni commerciali.

Regola di test: prima di rispondere a domande fattuali su prodotti, formati, certificazioni, mercati, capacita produttiva o private label, usa lookup_knowledge. Prima di rispondere su ordini, usa lookup_order_status se hai un riferimento ordine o dati cliente sufficienti.`,
  },
  {
    role: 'user',
    content: config.scenario,
  },
];
const trace = [];

for (let step = 0; step < 6; step += 1) {
  const completion = await chat(messages, tools);
  const message = completion.choices?.[0]?.message;
  if (!message) {
    throw new Error('OpenAI response missing message');
  }

  messages.push(message);

  if (!message.tool_calls?.length) {
    console.log(JSON.stringify({
      call_id: callId,
      assistant: message.content,
      tools_used: messages
        .filter((item) => item.role === 'tool')
        .map((item) => item.name),
      trace,
    }, null, 2));
    process.exit(0);
  }

  for (const toolCall of message.tool_calls) {
    const name = toolCall.function.name;
    const args = JSON.parse(toolCall.function.arguments || '{}');
    const result = await odoo(`/voice_ai/tool/${encodeURIComponent(name)}`, {
      ...args,
      call_id: callId,
    });
    trace.push({ name, args, result });
    messages.push({
      role: 'tool',
      tool_call_id: toolCall.id,
      name,
      content: JSON.stringify(result),
    });
  }
}

console.log(JSON.stringify({
  call_id: callId,
  assistant: 'Simulation stopped after maximum tool loop count.',
}, null, 2));
