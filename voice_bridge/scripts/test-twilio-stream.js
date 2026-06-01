import WebSocket from 'ws';

const config = {
  bridgeUrl: process.env.BRIDGE_URL || 'ws://localhost:8088/media-stream',
};

log('info', 'Starting mock Twilio call simulation...', { url: config.bridgeUrl });

function log(level, message, details = undefined) {
  console.log(JSON.stringify({
    ts: new Date().toISOString(),
    level,
    message,
    ...(details ? { details } : {}),
  }));
}

const ws = new WebSocket(config.bridgeUrl);

ws.on('open', () => {
  log('info', 'Connected to local voice bridge /media-stream');
  
  // Simulate Twilio stream start event
  const startEvent = {
    event: 'start',
    start: {
      streamSid: `mock_stream_${Date.now()}`,
      callSid: `mock_call_${Date.now()}`,
      customParameters: {
        from: '+393331112233', // Test customer number
        to: '+390984123456'    // Inbound PBX number
      }
    }
  };
  
  log('info', 'Sending simulated Twilio "start" event', startEvent);
  ws.send(JSON.stringify(startEvent));
  
  // Keep connection open for 15 seconds to receive the AI greeting
  setTimeout(() => {
    log('info', 'Closing mock call after 15 seconds.');
    ws.close();
  }, 15000);
});

let audioDeltaCount = 0;
ws.on('message', (data) => {
  let msg;
  try {
    msg = JSON.parse(data);
  } catch {
    log('warn', 'Received raw text/binary message', data.toString());
    return;
  }
  
  if (msg.event === 'media') {
    audioDeltaCount++;
    if (audioDeltaCount % 20 === 1) {
      log('info', `Received audio packets from AI (total: ${audioDeltaCount})`, {
        streamSid: msg.streamSid,
        payloadLength: msg.media.payload.length
      });
    }
  } else {
    log('info', 'Received event from bridge', msg);
  }
});

ws.on('close', () => {
  log('info', 'Mock Twilio WebSocket connection closed.');
});

ws.on('error', (err) => {
  log('error', 'WebSocket connection failed', { message: err.message });
});
