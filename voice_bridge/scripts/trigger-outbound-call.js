import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const publicBridgeUrl = process.env.PUBLIC_BRIDGE_URL;
const fromNumber = '+15855661084';
const toNumber = '+393351665306';   // Il tuo cellulare personale

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

if (!publicBridgeUrl || publicBridgeUrl.includes('localhost')) {
  console.error('Error: PUBLIC_BRIDGE_URL must be set to a public HTTPS tunnel URL (e.g. Serveo) in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log(`📞 Avvio chiamata telefonica reale da Twilio a ${toNumber}...`);
  console.log(`📡 Collegamento al webhook del bridge locale: ${publicBridgeUrl}/twilio/outbound`);
  
  const twilioUrl = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Calls.json`;
  const response = await fetch(twilioUrl, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({
      From: fromNumber,
      To: toNumber,
      Url: `${publicBridgeUrl}/twilio/outbound?job_id=manual_test`
    })
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(`Twilio API failed: ${JSON.stringify(data)}`);
  }

  console.log('\n================================================================');
  console.log('🎉 LA TELEFONATA REALE È PARTITA CON SUCCESSO!');
  console.log('================================================================\n');
  console.log(`📱 Il tuo cellulare personale (${toNumber}) sta per squillare.`);
  console.log(`👉 Rispondi alla chiamata per parlare a voce con l'assistente virtuale Viola di CasaFolino!`);
  console.log('================================================================\n');
}

run().catch(err => {
  console.error('\n❌ Errore avvio chiamata:', err.message);
  process.exit(1);
});
